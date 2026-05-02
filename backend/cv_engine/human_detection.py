import torch
from ultralytics import YOLO


class HumanDetector:
    """
    Efficient wrapper around Ultralytics YOLO for detecting multiple humans per image
    in single images or batches.
    """
    def __init__(self, model_path, confidence_threshold=0.5, device="cpu"):
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
        # [
        #     {"confidence": 0.94, "bbox": [112, 76, 238, 210]},
        #     {"confidence": 0.91, "bbox": [98, 65, 220, 198]}
        # ]

    def detect_batch(self, images):
        with torch.no_grad():
            results = self.model(images, conf=self.confidence_threshold, verbose=self.verbose)
        return [self._process_result(result) for result in results]

        # Example output:
        # [
        #     [  # Image 1 detections
        #         {"confidence": 0.94, "bbox": [112, 76, 238, 210]},
        #         {"confidence": 0.91, "bbox": [98, 65, 220, 198]}
        #     ],
        #     [  # Image 2 detections
        #         {"confidence": 0.88, "bbox": [130, 80, 250, 220]}
        #     ]
        # ]
        
        
        
    def _process_result(self, result):
        boxes = result.boxes.xyxy.cpu().numpy().astype(int)
        confs = result.boxes.conf.cpu().numpy()
        return [{"confidence": float(conf), "bbox": box.tolist()} for box, conf in zip(boxes, confs)]