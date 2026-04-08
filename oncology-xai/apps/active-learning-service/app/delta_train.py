"""
Delta training: freeze CTransPath backbone, fine-tune FuzzyArcLoss V2 head only.

Reads tile_data.npz from MinIO, trains on corrected tiles + buffer of originals,
saves versioned .pth to MinIO (never overwrites the original on disk).
"""
from __future__ import annotations

import io
import logging
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)

PATTERN_NAMES = ["micropapillary", "cribriform", "papillary", "lepidic", "solid", "acinar"]
PATTERN_TO_IDX = {p: i for i, p in enumerate(PATTERN_NAMES)}


def run_delta_training(
    storage,
    tile_data_key: str,
    current_pth_bytes: bytes,
    corrections: list[dict],
    n_epochs: int = 10,
    lr: float = 1e-5,
    buffer_ratio: float = 0.3,
) -> tuple[bytes | None, str]:
    """Run delta training and return (new_pth_bytes, version_tag) or (None, error_msg).

    Args:
        storage: StorageClient instance
        tile_data_key: MinIO key for tile_data.npz
        current_pth_bytes: bytes of the current .pth checkpoint
        corrections: list of {tile_index, corrected_pattern}
        n_epochs: training epochs
        lr: learning rate
        buffer_ratio: fraction of buffer tiles vs corrected tiles
    """
    try:
        tile_bytes = storage.download_bytes(tile_data_key)
        npz = np.load(io.BytesIO(tile_bytes))
        tile_embeddings = npz["tile_embeddings"]
        n_tiles = tile_embeddings.shape[0]
        logger.info("Loaded tile data: %d tiles, embeddings=%s", n_tiles, tile_embeddings.shape)

        ck = torch.load(io.BytesIO(current_pth_bytes), map_location="cpu", weights_only=False)
        head_weight = ck.get("loss_fn", {}).get("head.weight")
        if head_weight is None:
            head_weight = ck.get("loss_fn", {}).get("weight")
        if head_weight is None:
            return None, "No head weight found in checkpoint"

        config = ck.get("config", {})
        s_scale = config.get("S_SCALE", 30.0)

        head = nn.Linear(head_weight.shape[1], head_weight.shape[0], bias=False)
        head.weight = nn.Parameter(head_weight.clone())

        corrected_indices = []
        corrected_labels = []
        for c in corrections:
            idx = c["tile_index"]
            pat = c["corrected_pattern"]
            if 0 <= idx < n_tiles and pat in PATTERN_TO_IDX:
                corrected_indices.append(idx)
                corrected_labels.append(PATTERN_TO_IDX[pat])

        if not corrected_indices:
            return None, "No valid corrections"

        n_buffer = max(1, int(len(corrected_indices) * buffer_ratio / max(0.01, 1 - buffer_ratio)))
        all_indices = set(range(n_tiles))
        uncorrected = list(all_indices - set(corrected_indices))
        rng = np.random.default_rng(42)
        buffer_indices = rng.choice(uncorrected, size=min(n_buffer, len(uncorrected)), replace=False).tolist()

        emb_t = torch.from_numpy(tile_embeddings).float()
        with torch.no_grad():
            w_norm = F.normalize(head.weight, dim=1)
            e_norm = F.normalize(emb_t, dim=1)
            logits = s_scale * e_norm @ w_norm.T
            buffer_labels = logits[buffer_indices].argmax(dim=1).tolist()

        train_indices = corrected_indices + buffer_indices
        train_labels = corrected_labels + buffer_labels
        train_emb = emb_t[train_indices]
        train_y = torch.tensor(train_labels, dtype=torch.long)

        dataset = TensorDataset(train_emb, train_y)
        loader = DataLoader(dataset, batch_size=min(32, len(dataset)), shuffle=True)
        optimizer = torch.optim.Adam(head.parameters(), lr=lr)

        head.train()
        for epoch in range(n_epochs):
            total_loss = 0.0
            for emb_batch, y_batch in loader:
                e_norm = F.normalize(emb_batch, dim=1)
                w_norm = F.normalize(head.weight, dim=1)
                logits = s_scale * e_norm @ w_norm.T
                loss = F.cross_entropy(logits, y_batch)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            if (epoch + 1) % 5 == 0:
                logger.info("Delta train epoch %d/%d, loss=%.4f", epoch + 1, n_epochs, total_loss / len(loader))

        new_weight = head.weight.detach()
        if "loss_fn" in ck:
            if "head.weight" in ck["loss_fn"]:
                ck["loss_fn"]["head.weight"] = new_weight
            if "weight" in ck["loss_fn"]:
                ck["loss_fn"]["weight"] = new_weight

        version_tag = f"al_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        buf = io.BytesIO()
        torch.save(ck, buf)
        pth_bytes = buf.getvalue()

        logger.info("Delta training complete: %d corrections, %d buffer, version=%s",
                     len(corrected_indices), len(buffer_indices), version_tag)

        return pth_bytes, version_tag

    except Exception as e:
        logger.exception("Delta training failed: %s", e)
        return None, str(e)
