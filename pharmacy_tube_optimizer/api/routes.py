"""API routes for MediTube Optimizer."""


def get_status() -> dict[str, str]:
    """Return a simple status response for the API."""
    return {"service": "Meditube Optimizer", "status": "running"}


def get_sample_recommendations() -> dict[str, str]:
    """Return a sample tubing recommendation payload."""
    return {"recommendation": "Use Bin 7 for the current IV medication."}
