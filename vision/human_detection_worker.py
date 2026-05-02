import os
import cv2
import time
import multiprocessing
from dotenv import load_dotenv
import numpy as np
from vision.utils import log
from backend.cv_engine.human_detection import HumanDetector
from vision.ByteTrack_wrapper import ByteTrackWrapper  
import queue

load_dotenv()


class HumanDetectionWorker(multiprocessing.Process):
    """
    Worker process that performs human detection and tracking per gate.
    Each gate has its own tracker and per-person buffer.
    """
    def __init__(self, gates_list, share_memory, stop_event, queue, worker_id=0):
        super().__init__(name=f"Human Detection Worker-{worker_id}", daemon=False)
        self.gates_list = gates_list
        self.share_memory = share_memory
        self.stop_event = stop_event
        self.worker_id = worker_id

        # Trackers per gate
        self.trackers = {}
        # Buffers of frames per person ID per gate
        self.person_buffers = {}
        # Tracks that have already been sent to reduce duplication
        self.sent_tracks_cache = {gate['gate_idx']: [] for gate in self.gates_list}
        self.CACHE_SIZE = 20
        self.BUFFER_SIZE = 5  # Number of frames to accumulate before sending
        
        self.queue = queue


    def run(self):
        log(self.name, f"Start listening to gates: {[g['id'] for g in self.gates_list]}")

        try:
            detector = HumanDetector(
                model_path=os.getenv("HUMAN_DETECTION_MODEL_PATH"),
                confidence_threshold=0.5,
                device=os.getenv("DEVICE", "cpu")
            )

            self.initialize_trackers()

            while not self.stop_event.is_set():
                batch_frames = []
                batch_gates = []

                # Collect frames ready for processing
                for gate in self.gates_list:
                    gate_idx = gate['gate_idx']
                    frame = self.share_memory.read_frame(gate_idx)
                    if frame is not None and frame.size > 0:
                        batch_frames.append(frame)
                        batch_gates.append(gate)

                if batch_frames:
                    try:
                        # Detect humans in batch
                        detections_batch = detector.detect_batch(batch_frames)

                        # Process each frame and its detections
                        for gate, detections, frame in zip(batch_gates, detections_batch, batch_frames):
                            self.process_frame_for_gate(gate, frame, detections)

                    except ValueError as e:
                        log(self.name, f"Batch detection warning: {e}")

        except KeyboardInterrupt:
            log(self.name, "Shutdown signal received")
        except Exception as e:
            log(self.name, f"Unexpected error: {e}")
        finally:
            cv2.destroyAllWindows()
            log(self.name, "stop")


    def send_data(self, gate_id, track_id, payload):
        main_frame = payload[1]["frame"].copy()
        x1, y1, x2, y2  = payload[1]["bbox"]
        cv2.rectangle(main_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        
        payload_to_queue = {
            "gate_id": gate_id,
            "track_id": track_id,
            "snapshot": main_frame,
            "snapshot_bbox": payload[1]["bbox"],
            "payload": []
        }
        
        for det in payload:
            x1, y1, x2, y2  = det["bbox"]
            payload_to_queue["payload"].append(det["frame"][y1:y2, x1:x2].copy())
        
        try:
            self.queue.put(payload_to_queue, timeout=1.0)  # short timeout
        except queue.Full:
            log(self.name, "Output queue full, dropping batch")
            if self.stop_event.is_set():
                return


    def initialize_trackers(self):
        for gate in self.gates_list:
            gate_idx = gate['gate_idx']
            self.trackers[gate_idx] = ByteTrackWrapper(frame_rate=10, low=0.5, high=0.8)
            self.person_buffers[gate_idx] = {}


    def process_frame_for_gate(self, gate, frame, detections):
        gate_idx = gate['gate_idx']
        gate_id = gate['id']
        tracker = self.trackers[gate_idx]

        # Update tracker with current frame detections
        tracked_objects, removed_tracks = tracker.update(detections)

        for obj in tracked_objects:
            if len(obj) >= 6:
                x1, y1, x2, y2, track_id, score = obj[:6]
                x1, y1, x2, y2, track_id = map(int, [x1, y1, x2, y2, track_id])
                score = float(score)

                payload = {"bbox": [x1, y1, x2, y2], "frame": frame}

                # Buffer frames per person until ready to send
                if track_id not in self.sent_tracks_cache[gate_idx]:
                    buffer = self.person_buffers[gate_idx].setdefault(track_id, [])
                    buffer.append(payload)

                    if len(buffer) >= self.BUFFER_SIZE:
                        self.send_data(gate_id, track_id, buffer)
                        self.sent_tracks_cache[gate_idx].append(track_id)
                        if len(self.sent_tracks_cache[gate_idx]) > self.CACHE_SIZE:
                            self.sent_tracks_cache[gate_idx].pop(0)
                        self.person_buffers[gate_idx].pop(track_id)

                # Draw detector bbox
                # cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # cv2.putText(
                #     frame,
                #     f"ID:{track_id} {score:.2f}",
                #     (x1, y1 - 10),
                #     cv2.FONT_HERSHEY_SIMPLEX,
                #     0.7,
                #     (255, 0, 0),
                #     2
                # )
            else:
                print("Tracker returned invalid object:", obj)

        # Handle tracks removed from tracker
        for removed_id in removed_tracks:
            buffer = self.person_buffers[gate_idx].get(removed_id, [])
            if len(buffer) > 1:
                self.send_data(gate_id, removed_id, buffer)
            self.person_buffers[gate_idx].pop(removed_id, None)

        # Show processed frame
        # cv2.imshow(f"{gate_idx} (Human Detection Worker-{self.worker_id})", frame)
        # cv2.waitKey(1)