"""
Production Configuration

Simplified configuration for V1 production deployment.
"""

from dataclasses import dataclass


@dataclass
class TrainingConfig:
    """Production training configuration."""
    csv_path: str = "dataset/synthetic_hospital_data.csv"
    output_dir: str = "models/forecast_system"
    test_size: float = 0.2
    random_state: int = 42


# Default configuration
DEFAULT_TRAINING_CONFIG = TrainingConfig()
