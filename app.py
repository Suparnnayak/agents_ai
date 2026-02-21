"""
Hospital Forecast API — Entry point compatibility shim.

The real application lives in app/main.py.
This file exists so ``uvicorn app:app`` and ``python app.py``
both work from the project root.
"""

from app.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=10000)
