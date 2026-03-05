"""Core module for checking Yappy updates from PyPI."""
from __future__ import annotations

import logging
import httpx
from packaging.version import parse as parse_version

logger = logging.getLogger(__name__)

VERSION = "0.1.0"

async def check_for_updates(current_version: str) -> str | None:
    """
    Check if a newer version of Yappy is available on PyPI.
    
    Args:
        current_version: The current version of the application.
        
    Returns:
        The latest version string if a newer version exists, else None.
    """
    url = "https://pypi.org/pypi/yappy/json"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            
            data = response.json()
            latest_version = data.get("info", {}).get("version")
            if not latest_version:
                return None
            
            if parse_version(latest_version) > parse_version(current_version):
                return latest_version
    except Exception as exc:
        logger.debug("Update check failed: %s", exc)
        return None
    
    return None
