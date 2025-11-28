import torch
import torch.nn as nn
from typing import Dict


class QuantileLoss(nn.Module):
    def __init__(self, quantile: float):
        super().__init__()
        self.q = quantile

    def forward(self, preds, target):
        diff = target - preds
        return torch.mean(torch.max(self.q * diff, (self.q - 1) * diff))


class TFTBlock(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        self.gate = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.Sigmoid()
        )
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, x):
        enc = self.encoder(x)
        gate = self.gate(x)
        enc = enc * gate
        out = self.decoder(enc)
        return out.squeeze(-1)


class TFTQuantileModel(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.block = TFTBlock(input_dim, hidden_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


def build_tft_models(input_dim: int, hidden_dim: int = 128) -> Dict[str, TFTQuantileModel]:
    return {
        "q10": TFTQuantileModel(input_dim, hidden_dim),
        "q50": TFTQuantileModel(input_dim, hidden_dim),
        "q90": TFTQuantileModel(input_dim, hidden_dim)
    }


def tft_quantile_loss(pred, target, quantile: float):
    return QuantileLoss(quantile)(pred, target)


def save_tft_model(model: nn.Module, path: str):
    torch.save(model.state_dict(), path)


def load_tft_model(model: nn.Module, path: str, map_location: str = "cpu"):
    state = torch.load(path, map_location=map_location)
    model.load_state_dict(state)
    model.eval()
    return model

