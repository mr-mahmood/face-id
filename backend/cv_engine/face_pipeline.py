import time
import cv2

from .face_detection import FaceDetector
from .face_align import FaceAligner
from .face_embedding import FaceEmbedder
import numpy as np

class FacePipeline:
    """
    Full face enrollment pipeline (self-contained):
    1. Initializes detector, aligner, embedder from paths/params
    2. Detects exactly one face with keypoints
    3. Aligns the face
    4. Computes embedding
    Raises ValueError if anything fails
    """

    def __init__(
        self,
        detector_model_path: str,
        embedder_model_path: str,
        confidence_threshold: float = 0.5,
        device: str = "cuda",
    ):

        # --- Initialize detector ---
        self.detector = FaceDetector(
            model_path=detector_model_path,
            confidence_threshold=confidence_threshold,
            device=device,
        )

        # --- Initialize aligner ---
        self.aligner = FaceAligner()

        # --- Initialize embedder ---
        self.embedder = FaceEmbedder(
            model_path=embedder_model_path,
            device=device,
        )

    def process_single_image(self, image: np.ndarray):
        # --- 1. Detect face ---
        face_data = self.detector.detect_single_image(image)
        if face_data:
            bbox = face_data["bbox"]
            left_eye = face_data["left_eye"]
            right_eye = face_data["right_eye"]
            confidence = face_data["confidence"]

            # --- 2. Align face ---
            x1, y1, x2, y2 = bbox
            w, h = x2 - x1, y2 - y1
            aligned_face = self.aligner.align_face(
                img=image,
                facial_area=(x1, y1, w, h),
                left_eye=left_eye,
                right_eye=right_eye,
            )
            
            # cv2.imwrite('temp.jpg', aligned_face)

            # --- 3. Compute embedding ---
            embedding = self.embedder.get_embedding(aligned_face)

            return {
                "embedding": embedding,
                "aligned_face": aligned_face,
                "bbox": bbox,
                "left_eye": left_eye,
                "right_eye": right_eye,
                "confidence": confidence,
            }
        else:
            return None

    def process_batch_image(self, images: list[np.ndarray]):
        overall_start = time.perf_counter()

        # --- Detection ---
        det_start = time.perf_counter()
        faces = self.detector.detect_batch(images)
        det_time = (time.perf_counter() - det_start) * 1000  # ms
        # print(f"Detection time: {det_time:.2f} ms")

        # Prepare lists for batch processing
        valid_indices = []
        align_faces = []
        face_data = []

        # --- Alignment (loop) ---
        align_start_total = time.perf_counter()
        for idx, face in enumerate(images):
            face = faces[idx]  # corrected: use the faces list, not enumerate over images directly
            if face:
                valid_indices.append(idx)

                bbox = face["bbox"]
                left_eye = face["left_eye"]
                right_eye = face["right_eye"]

                x1, y1, x2, y2 = bbox
                w, h = x2 - x1, y2 - y1

                align_single_start = time.perf_counter()
                aligned_face = self.aligner.align_face(
                    img=images[idx],
                    facial_area=(x1, y1, w, h),
                    left_eye=left_eye,
                    right_eye=right_eye,
                )
                align_single_time = (time.perf_counter() - align_single_start) * 1000
                # print(f"  Alignment for image {idx}: {align_single_time:.2f} ms")

                align_faces.append(aligned_face)
                face_data.append({
                    "bbox": bbox,
                    "left_eye": left_eye,
                    "right_eye": right_eye,
                    "confidence": face["confidence"],
                })
        align_total_time = (time.perf_counter() - align_start_total) * 1000
        # print(f"Total alignment time: {align_total_time:.2f} ms")

        # --- Embedding (batch) ---
        embeddings = []
        if align_faces:
            emb_start = time.perf_counter()
            embeddings = self.embedder.get_embeddings(align_faces)
            emb_time = (time.perf_counter() - emb_start) * 1000
            # print(f"Embedding time: {emb_time:.2f} ms")
        else:
            # print("No aligned faces, skipping embedding.")
            pass

        # --- Build result ---
        finall_result = [None] * len(images)
        for pos, (idx, data, emb) in enumerate(zip(valid_indices, face_data, embeddings)):
            finall_result[idx] = { # type: ignore
                "embedding": emb,
                "aligned_face": align_faces[pos],
                "bbox": data["bbox"],
                "left_eye": data["left_eye"],
                "right_eye": data["right_eye"],
                "confidence": data["confidence"],
            }

        overall_time = (time.perf_counter() - overall_start) * 1000
        # print(f"Total batch processing time: {overall_time:.2f} ms")
        return finall_result