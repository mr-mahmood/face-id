import cv2
import time
import threading
import multiprocessing as mp
import numpy as np
from vision.utils import log
from typing import Optional

class gateWorkerThread(threading.Thread):
    def __init__(
        self, stream_url, gate_id, gate_idx, width, height, share_memory, stop_event):
        super().__init__(name=f"Gates Worker-{gate_id}", daemon=False)
        self.stream_url = stream_url
        self.gate_id = gate_id
        self.gate_idx = gate_idx
        self.width = width
        self.height = height
        self.share_memory = share_memory
        self.stop_event = stop_event
        TARGET_FPS = 5
        self.target_interval = 1 / TARGET_FPS
        self.downscale_factor = 0.5
        self.motion_threshold = 0.02

        # Initialize background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=15, varThreshold=16, detectShadows=True
        )

    def detect_motion(self, frame):
        """
        Returns True if motion exceeds threshold
        """
        # Resize frame for lightweight motion detection
        small_frame = cv2.resize(frame, (0,0), fx=self.downscale_factor, fy=self.downscale_factor)
        fg_mask = self.bg_subtractor.apply(small_frame)
        motion_ratio = np.sum(fg_mask > 0) / fg_mask.size
        return motion_ratio > self.motion_threshold

    def run(self):
        cap: Optional[cv2.VideoCapture] = None
        log(f"Gates Worker-{self.gate_id}", "start")
        try:
            cap = cv2.VideoCapture(self.stream_url)
            if not cap.isOpened():
                log(f"Gates Worker-{self.gate_id}", "ERROR: Cannot open stream")
                return

            last_publish = time.monotonic()
            motion_hold_until = 0  # Timestamp until which gate stays "open"

            while not self.stop_event.is_set():
                if not cap.grab():
                    continue

                now = time.monotonic()
                if now - last_publish >= self.target_interval:
                    ret, frame = cap.retrieve()
                    if not ret:
                        continue

                    last_publish += self.target_interval

                    # Check if we're in the hold period
                    if now < motion_hold_until:
                        # Gate is still "open", continue writing the last frame if needed
                        resized = cv2.resize(frame, (self.width, self.height))
                        try:
                            self.share_memory.write_frame(self.gate_idx, resized)
                        except Exception as e:
                            log(f"Gates Worker-{self.gate_id}", f"Error writing to shared memory: {e}")
                        continue

                    # Detect motion
                    elif self.detect_motion(frame):
                        # Set hold period for 5 seconds
                        motion_hold_until = now + 5.0
                    
                    else:
                        time.sleep(0.5)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            log(f"Gates Worker-{self.gate_id}", f"Error: {e}")
        finally:
            if cap:
                cap.release()
            log(f"Gates Worker-{self.gate_id}", "stop")



class gateGroupProcess(mp.Process):
    def __init__(self, gates_list, share_memory, width, height, processor_id, stop_event):
        """
        gate_list: list of tuples -> [(name, url, idx), ...]
        """
        super().__init__(name=f"Gates Worker Manager-{processor_id}", daemon=False)
        self.gates_list = gates_list
        self.share_memory = share_memory
        self.width = width
        self.height = height
        self.stop_event = stop_event
        self.processor_id = processor_id
        self.threads = []

    def run(self):
        # Start gate threads
        for gate in self.gates_list:
            url = gate["camera"]
            id = gate["id"]
            idx = gate["gate_idx"]
            t = gateWorkerThread(
                url,
                id,
                idx,
                self.width,
                self.height,
                self.share_memory,
                stop_event=self.stop_event
            )
            t.start()
            self.threads.append(t)

        # Wait for all threads to finish
        try:
            for t in self.threads:
                t.join()
        except KeyboardInterrupt:
            pass
        finally:
            log(f"Gates Worker Manager-{self.processor_id}", "stop")
