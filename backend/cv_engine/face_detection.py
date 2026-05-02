import torch
from ultralytics import YOLO


class FaceDetector:
    """
    Efficient wrapper around the Ultralytics YOLO model for face detection.
    Ensures exactly one face per image, and returns bounding box and eye keypoints.
    """
    def __init__(self, model_path, confidence_threshold = 0.5, device= "cpu",):
        self.verbose = False
        self.model = YOLO(str(model_path), verbose=self.verbose)
        self.model.to(device)
        self.model.fuse()  # Optimize conv+bn layers for faster inference
        self.device = device
        self.confidence_threshold = confidence_threshold

    def detect_single_image(self, image):
        with torch.no_grad():
            result = self.model(image, conf=self.confidence_threshold, verbose=self.verbose)[0]
        return self._process_result(result)

        # Example output:
        # {
        #     "confidence": 0.94,
        #     "bbox": [112, 76, 238, 210],
        #     "left_eye": (148.2, 118.6),
        #     "right_eye": (205.7, 116.9)
        # }

    def detect_batch(self, images):
        with torch.no_grad():
            results = self.model(images, conf=self.confidence_threshold, verbose=self.verbose)
        return [self._process_result(result) for i, result in enumerate(results)]

        # Example output:
        # [
        #     {
        #         "confidence": 0.94,
        #         "bbox": [112, 76, 238, 210],
        #         "left_eye": (148.2, 118.6),
        #         "right_eye": (205.7, 116.9),
        #     },
        #     {
        #         "confidence": 0.91,
        #         "bbox": [98, 65, 220, 198],
        #         "left_eye": (132.4, 110.3),
        #         "right_eye": (187.9, 108.5),
        #     },
        #     None,
        # ]
        
        
    def _process_result(self, result):
        try:
            # Check for face boxes
            if result.boxes is None or result.boxes.xyxy is None:
                return None

            num_faces = result.boxes.xyxy.shape[0]
            if num_faces != 1:
                return None

            # Bounding box and confidence
            box = result.boxes.xyxy[0].cpu().numpy().astype(int)
            conf = float(result.boxes.conf[0].cpu().item())

            # Keypoints (eyes)
            if result.keypoints is None or result.keypoints.xy is None:
                return None

            kpts = result.keypoints.xy[0].cpu().numpy()
            left_eye = tuple(kpts[0])
            right_eye = tuple(kpts[1])

            return {
                "confidence": conf,
                "bbox": box.tolist(),
                "left_eye": left_eye,
                "right_eye": right_eye,
            }

        except Exception as e:
            print(f'face detection error: {e}')
            return None