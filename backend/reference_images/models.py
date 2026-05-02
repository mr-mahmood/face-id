from django.db import models
from users.models import User
import numpy as np
from datetime import datetime
from django.db.models import QuerySet

def user_reference_path(instance, filename):
    ext = filename.split('.')[-1]  # keep original extension
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]  # up to milliseconds
    new_filename = f"{timestamp}.{ext}"
    return f"reference_images/{instance.user.id}/{new_filename}"

class ReferenceImages(models.Model):
    id:int
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reference_images")
    image = models.ImageField(upload_to=user_reference_path)
    embedding = models.BinaryField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reference_images'

    def set_embedding(self, emb: np.ndarray):
        self.embedding = emb.astype(np.float32).tobytes()

    def get_embedding(self) -> np.ndarray:
        return np.frombuffer(self.embedding, dtype=np.float32)

    
    @classmethod
    def get_user_reference_images(cls, user: User) -> QuerySet['ReferenceImages'] | None :
        images = cls.objects.filter(user=user)
        if not images.exists():
            return None
        return images