"""
Auth Service - JWT based authentication
"""
import logging
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from app.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

class User(BaseModel):
    id: str
    email: str

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Validates JWT token from Authorization header.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        email: str = payload.get("email", "")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return User(id=user_id, email=email)
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
