import sys
from .logger import get_logger

logger = get_logger(__name__)

class CustomException(Exception):
    """Base custom exception for the pipeline."""
    def __init__(self, error_message: str, error_detail: sys = None):
        super().__init__(error_message)
        self.error_message = error_message
        self.error_detail = error_detail
        
        if error_detail:
            logger.error(f"{error_message}: {error_detail}")

