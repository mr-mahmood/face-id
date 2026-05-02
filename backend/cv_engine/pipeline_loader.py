import os
from cv_engine.face_pipeline import FacePipeline
from dotenv import load_dotenv

# global variable to hold the loaded pipeline
global_pipeline = None

def load_pipeline():
    global global_pipeline

    # only load in backend
    # if os.getenv("IS_BACKEND", "false").lower() != "true":
    #     return None

    # lazy-load
    if global_pipeline is None:
        load_dotenv()
        global_pipeline = FacePipeline(
            detector_model_path=os.getenv("FACE_DETECTION_MODEL_PATH", ""),
            embedder_model_path=os.getenv("EMBEDDING_MODEL_PATH", ""),
            device=os.getenv("DEVICE", "cpu")
        )
    return global_pipeline
