from typing import Any, Dict, List
import time

import httpx

from .config import get_settings


class PredictionClient:
    """HTTP client for the deployed prediction API with retries."""

    def __init__(self):
        self.settings = get_settings()

    def _wake_up_service(self, base_url: str, timeout: float = 60.0) -> bool:
        """Wake up a sleeping Render service by calling the health endpoint."""
        health_url = base_url.rstrip("/") + "/health"
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(health_url)
                response.raise_for_status()
                return True
        except Exception:
            return False

    def predict(self, payload: Dict[str, Any]) -> float:
        """Return the median prediction from the hosted API, retrying on transient errors."""

        url = str(self.settings.prediction_api_url)
        # Longer timeout for Render free tier (can take time to wake up)
        timeout = 60.0
        backoff = [0, 3, 8, 15]  # seconds - more retries with longer delays
        last_error: Exception | None = None

        # Try to wake up the service first
        print("🔄 Checking API health...")
        if not self._wake_up_service(url, timeout=timeout):
            print("⚠️  Health check failed, proceeding anyway...")

        for attempt, delay in enumerate(backoff, 1):
            if delay:
                print(f"⏳ Waiting {delay}s before retry {attempt}...")
                time.sleep(delay)
            try:
                print(f"📡 Calling prediction API (attempt {attempt}/{len(backoff)})...")
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                predictions: List[Dict[str, Any]] = data.get("predictions", [])
                if not predictions:
                    raise ValueError("Prediction API returned no rows.")
                median = float(predictions[0]["median"])
                print(f"✅ Prediction received: {median}")
                return median
            except httpx.TimeoutException as exc:
                last_error = exc
                print(f"⏱️  Timeout on attempt {attempt}: {exc}")
                if attempt < len(backoff):
                    continue
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code >= 500:
                    print(f"🔴 Server error {exc.response.status_code} on attempt {attempt}")
                    continue  # retry on server errors
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                print(f"⚠️  Error on attempt {attempt}: {exc}")
                if attempt < len(backoff):
                    continue

        raise RuntimeError(
            f"Prediction API failed after {len(backoff)} retries. "
            f"Last error: {last_error}. "
            f"The service may be sleeping (Render free tier). "
            f"Try again in a moment or check the API status."
        ) from last_error


prediction_client = PredictionClient()

