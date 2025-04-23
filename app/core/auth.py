from fastapi import Header, HTTPException, status

from app.core.config import settings

"""
Simple token-based authentication dependency for FastAPI routes.
"""


def verify_token(authorization: str = Header(...)) -> None:
    """
    FastAPI dependency to validate the Authorization header token.

    Args:
        authorization (str): The token passed in the Authorization header.

    Raises:
        HTTPException: If the token is invalid.
    """
    if authorization != f'{settings.auth_token}':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token',
        )
