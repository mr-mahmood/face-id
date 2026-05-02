import os
import time
import multiprocessing
import numpy as np
import queue

from dotenv import load_dotenv
from vision.utils import log
from backend.cv_engine.face_detection import FaceDetector
from backend.cv_engine.face_embedding import FaceEmbedder
from backend.cv_engine.face_align import FaceAligner

load_dotenv()


class FaceProcessingWorker(multiprocessing.Process):
    """
    Performs:
        - Face detection (batch)
        - Face alignment
        - Face embedding (batch)
    Input: track objects containing multiple body ROIs
    Output: embeddings per track
    """

    def __init__(self, stop_event, input_queue, output_queue, batch_size=10, worker_id=0):
        super().__init__(name=f"Face Processing Worker-{worker_id}", daemon=False)
        self.stop_event = stop_event
        self.worker_id = worker_id
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.batch_size = batch_size

    def run(self):
        log(self.name, "Starting")

        detector = FaceDetector(
            model_path=os.getenv("Face_DETECTION_MODEL_PATH"),
            confidence_threshold=0.5,
            device=os.getenv("DEVICE", "cpu")
        )

        embedder = FaceEmbedder(
            model_path=os.getenv("EMBEDDING_MODEL_PATH"),
            device=os.getenv("DEVICE", "cpu")
        )

        aligner = FaceAligner()

        buffer = []
        batch_timeout = 2.0
        last_collect_time = time.time()

        while True:

            # -----------------------
            # Exit condition
            # -----------------------
            if self.stop_event.is_set():
                # Try to drain remaining queue items
                try:
                    while True:
                        item = self.input_queue.get_nowait()
                        buffer.append(item)
                except queue.Empty:
                    pass
                except KeyboardInterrupt:
                    log(self.name, "Shutdown signal received. Draining input queue and processing remaining data.")

                # If nothing left anywhere → break safely
                if not buffer:
                    break

            # -----------------------
            # Collect objects (normal mode)
            # -----------------------
            if not self.stop_event.is_set():
                try:
                    item = self.input_queue.get(timeout=0.2)
                    buffer.append(item)
                    last_collect_time = time.time()
                except queue.Empty:
                    pass
                except KeyboardInterrupt:
                    log(self.name, "Shutdown signal received. Draining input queue and processing remaining data.")

            total_rois = sum(len(obj["payload"]) for obj in buffer)
            time_waited = time.time() - last_collect_time

            should_process = (
                total_rois >= self.batch_size
                or time_waited >= batch_timeout
                or self.stop_event.is_set()  # force flush on shutdown
            )

            if not should_process:
                continue

            if not buffer:
                continue

            # -----------------------
            # Flatten ROIs
            # -----------------------
            roi_batch = []
            roi_meta = []  # (gate_id, track_id)

            for obj in buffer:
                for roi in obj["payload"]:
                    if roi is None or roi.size == 0 or roi.shape[0] == 0 or roi.shape[1] == 0:
                        continue  # skip invalid
                    roi_batch.append(roi.copy())
                    roi_meta.append((obj["gate_id"], obj["track_id"]))

            if not roi_batch:
                buffer.clear()
                continue  # skip this batch
            
            # -----------------------
            # Face Detection (single batch)
            # -----------------------
            try:
                detections_batch = detector.detect_batch(roi_batch)
            except Exception as e:
                log(self.name, f"Detection batch error: {e}")
                buffer.clear()
                continue

            # -----------------------
            # Alignment stage
            # -----------------------
            aligned_faces = []
            aligned_meta = []

            for roi_img, det, meta in zip(roi_batch, detections_batch, roi_meta):

                if det is None:
                    continue  # skip invalid

                try:
                    x1, y1, x2, y2 = det["bbox"]
                    left_eye = det["left_eye"]
                    right_eye = det["right_eye"]

                    w = x2 - x1
                    h = y2 - y1

                    if w <= 0 or h <= 0:
                        continue
                    
                    aligned = aligner.align_face(
                        img=roi_img,
                        facial_area=(x1, y1, w, h),
                        left_eye=left_eye,
                        right_eye=right_eye
                    )

                    aligned_faces.append(aligned)
                    aligned_meta.append(meta)

                except Exception as e:
                    log(self.name, f"Face aligner error: {e}")
                    continue  # skip bad face safely

            if not aligned_faces:
                buffer.clear()
                continue

            # -----------------------
            # Embedding stage (single batch)
            # -----------------------
            try:
                embeddings = embedder.get_embeddings(aligned_faces)
            except Exception as e:
                log(self.name, f"Embedding batch error: {e}")
                buffer.clear()
                continue

            # -----------------------
            # Regroup per track
            # -----------------------
            results_per_track = {}

            for emb, (gate_id, track_id) in zip(embeddings, aligned_meta):
                results_per_track.setdefault((gate_id, track_id), []).append(emb)

            # -----------------------
            # Send to output queue
            # -----------------------
            for obj in buffer:
                gate_id = obj["gate_id"]
                track_id = obj["track_id"]

                embeddings_list = results_per_track.get((gate_id, track_id), [])

                if not embeddings_list:
                    continue  # no valid faces

                output_item = {
                    "gate_id": gate_id,
                    "track_id": track_id,
                    "snapshot": obj["snapshot"].copy(),
                    "snapshot_bbox": obj["snapshot_bbox"],
                    "embeddings": embeddings_list
                }

                try:
                    self.output_queue.put(output_item, timeout=0.2)
                except queue.Full:
                    log(self.name, f"Output queue full. Dropping track {track_id}")

            buffer.clear()
            last_collect_time = time.time()

        log(self.name, "Stop")