import numpy as np
import torch
import torch.nn.functional as F
import cv2
import os
from typing import Tuple

class FaceEmbedder:
    def __init__(self, model_path, device="cpu"):
        self.device = device    # "cuda" if torch.cuda.is_available() else "cpu"
        self.model_path = model_path    # os.getenv("EMBEDDING_MODEL_PATH")
        self.model = torch.load(self.model_path, map_location=self.device, weights_only=False)
        self.model.eval()
        self.model.to(self.device)

    def _preprocess(self, img: np.ndarray, size: Tuple[int, int] = (112, 112)) -> torch.Tensor:
        img = cv2.resize(img, size)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = (img.astype(np.float32) - 127.5) / 128.0
        img = np.transpose(img, (2, 0, 1))  # C,H,W
        img = np.expand_dims(img, axis=0)   # N,C,H,W
        return torch.from_numpy(img).to(self.device)

    @torch.no_grad()
    def get_embedding(self, img: np.ndarray) -> np.ndarray:
        if img is None or img.size == 0:
            raise ValueError("Cannot compute embedding: empty image")

        if len(img.shape) != 3 or img.shape[2] != 3:
            raise ValueError("Embedding expects a 3-channel BGR image")
        
        x = self._preprocess(img)
        emb = self.model(x)
        
        if emb is None or emb.numel() == 0:
            raise ValueError("Model returned empty embedding")
        
        emb = F.normalize(emb, p=2, dim=1)
        return emb.squeeze(0).cpu().numpy().astype(np.float32)

    @torch.no_grad()
    def get_embeddings(self, images: list[np.ndarray]) -> np.ndarray:
        """
        Compute embeddings for a batch of images.
        Args:
            images: list of BGR images (np.ndarray)
        Returns:
            np.ndarray: Array of embeddings of shape (batch_size, embedding_dim)
        """
        batch = []
        for img in images:
            if img is None or img.size == 0:
                raise ValueError("Cannot compute embedding: empty image")
            if len(img.shape) != 3 or img.shape[2] != 3:
                raise ValueError("Embedding expects a 3-channel BGR image")
            batch.append(self._preprocess(img))

        batch_tensor = torch.cat(batch, dim=0)  # (N, C, H, W)
        embs = self.model(batch_tensor)
        embs = F.normalize(embs, p=2, dim=1)
        return embs.cpu().numpy().astype(np.float32)