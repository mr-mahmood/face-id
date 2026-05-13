import os
import time
import multiprocessing
from dotenv import load_dotenv
import cv2, queue
import base64
import requests

from vision.utils import fetch_gates_from_backend, split_gates, log
from vision.share_memory import SharedFrameStore
from vision.camera_worker import gateGroupProcess
from vision.human_detection_worker import HumanDetectionWorker
from vision.face_processing_worker import FaceProcessingWorker

load_dotenv()

def send_to_api(item):
    API_URL = "http://127.0.0.1:8000/api/cv/check-access/"
    HEADERS = {"Authorization": "Bearer sUpErsecreTcvtoken123@#fg5"}

    try:
        # Convert snapshot (BGR) to JPEG bytes
        _, buffer = cv2.imencode(".jpg", item["snapshot"])
        img_bytes = buffer.tobytes()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

        # Convert embeddings to list of lists
        embeddings_list = [emb.tolist() for emb in item["embeddings"]]

        payload = {
            "gate": item["gate_id"],
            "image": img_base64,
            "embeddings": embeddings_list,
        }

        # Send request
        response = requests.post(API_URL, json=payload, headers=HEADERS)  # add headers=HEADERS if needed
        if response.status_code != 200:
            print(f"API Error: {response.status_code}, {response.text}")

    except Exception as e:
        print(f"Failed to send to API: {e}")
    

def main():
    log("Main", "start")
    # -----------------------------------------------
    # Configuration
    # -----------------------------------------------
    WIDTH = int(os.getenv("WIDTH", 1920))
    HEIGHT = int(os.getenv("HEIGHT", 1080))
    CHANNELS = int(os.getenv("CHANNELS", 3))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 10))
    
    # -----------------------------------------------
    # Fetch gates / cameras and create chunks
    # -----------------------------------------------
    gates = fetch_gates_from_backend()
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 4})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 5})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 6})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 7})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 8})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 9})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 10})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 11})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 12})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 13})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 14})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 15})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 16})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 17})
    # gates.append({'id': 1, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 18})
    # gates.append({'id': 2, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 19})
    # gates.append({'id': 2, 'name': 'entery', 'camera': 'http://localhost:8080/video', 'role': 'ENTERY', 'is_active': True, 'area': 1, 'gate_idx': 20})

    num_cameras = len(gates)
    camera_chunks = split_gates(gates, chunk_size=CHUNK_SIZE)

    # -----------------------------------------------
    # Create shared memory store
    # -----------------------------------------------
    shared_memory = SharedFrameStore(
        num_cameras=num_cameras,
        width=WIDTH,
        height=HEIGHT,
        channels=CHANNELS
    )

    # Multiprocessing stop event
    stop_event = multiprocessing.Event()

    # -----------------------------------------------
    # Create Queues
    # -----------------------------------------------
    human_face_queue = multiprocessing.Queue(maxsize=200)
    face_embedder_queue = multiprocessing.Queue(maxsize=200)

    # -----------------------------------------------
    # Start Camera + Human Detection
    # -----------------------------------------------
    camera_processes = []
    human_detection_workers = []

    for chunk_id, chunk in enumerate(camera_chunks):

        camera_proc = gateGroupProcess(
            gates_list=chunk,
            share_memory=shared_memory,
            width=WIDTH,
            height=HEIGHT,
            processor_id=chunk_id,
            stop_event=stop_event
        )
        camera_proc.start()
        camera_processes.append(camera_proc)

        time.sleep(1)

        human_worker = HumanDetectionWorker(
            gates_list=chunk,
            share_memory=shared_memory,
            stop_event=stop_event,
            queue=human_face_queue,
            worker_id=chunk_id
        )
        human_worker.start()
        human_detection_workers.append(human_worker)

    # -----------------------------------------------
    # Start Face Processing Workers
    # -----------------------------------------------
    face_processing_workers = []
    time.sleep(2)
    for i in range(len(camera_chunks)//2 + 1):
        worker = FaceProcessingWorker(
            stop_event=stop_event,
            input_queue=human_face_queue,
            output_queue=face_embedder_queue,
            worker_id=i
        )
        worker.start()
        face_processing_workers.append(worker)

    log("Main", "System start")
    log("Main", "Quit the System with CONTROL-C")

    # -----------------------------------------------
    # Main loop → API sender
    # -----------------------------------------------
    try:
        while True:
            try:
                item = face_embedder_queue.get_nowait()
                send_to_api(item)
            except queue.Empty:
                time.sleep(1)
                continue

    except KeyboardInterrupt:
        log("Main", "Shutdown initiated")
        stop_event.set()

    # -----------------------------------------------
    # Shutdown sequence (reverse order)
    # -----------------------------------------------

    # 1️⃣ Stop cameras (producers of frames)
    for p in camera_processes:
        p.join(timeout=3)
        if p.is_alive():
            p.terminate()

    # 2️⃣ Stop human detection (producers of ROIs)
    for p in human_detection_workers:
        p.join(timeout=3)
        if p.is_alive():
            p.terminate()

    # 3️⃣ Stop face workers (producers of embeddings)
    for p in face_processing_workers:
        p.join()

    # At this point:
    # NO process can push to face_embedder_queue anymore.

    # -----------------------------------------------
    # Drain remaining embeddings
    # -----------------------------------------------
    log("Main", "Draining remaining API payloads")

    while True:
        try:
            item = face_embedder_queue.get_nowait()
            send_to_api(item)
        except queue.Empty:
            break

    log("Main", "API queue fully drained")
    shared_memory.close()
    log("Main", "All processes stopped")



if __name__ == "__main__":
    multiprocessing.freeze_support()  # safe on Windows
    main()