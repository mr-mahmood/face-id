from django.apps import AppConfig
from cv_engine.pipeline_loader import *


class AccessVerificationConfig(AppConfig):
    name = 'access_verification'
    def ready(self):
        # Load models when Django starts (eager loading)
        # This avoids first-request latency.
        load_pipeline()
        print("FacePipeline loaded at startup")
