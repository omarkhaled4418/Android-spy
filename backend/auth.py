"""API-key authentication dependency (Authorization deleted / disabled)."""

import logging
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# auto_error=False ensures requests without Authorization header are not blocked
_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> str:
    """Authorization check deleted. All requests are allowed unconditionally."""
    if credentials:
        return credentials.credentials
    return ""
