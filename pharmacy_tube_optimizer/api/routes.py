"""Route-facing API exports for MediTube Optimizer.

The WSGI application in :mod:`pharmacy_tube_optimizer.api.app` serves
``GET /bins``, ``GET /bins/{bin_id}``, and ``POST /bins/{bin_id}/tube``.
"""

from pharmacy_tube_optimizer.api.app import MediTubeApi, create_app


def get_status() -> dict[str, str]:
    """Return a simple status response for the API."""
    return {"service": "Meditube Optimizer", "status": "running"}


def get_sample_recommendations() -> dict[str, str]:
    """Return a sample tubing recommendation payload."""
    return {"recommendation": "Use Bin 7 for the current IV medication."}


__all__ = ["MediTubeApi", "create_app", "get_sample_recommendations", "get_status"]
