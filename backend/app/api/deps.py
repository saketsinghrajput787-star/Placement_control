import uuid
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import settings
from app.models.user import User
from app.models.placement_session import PlacementSession

security = HTTPBearer()

def get_or_create_active_session(db: Session, session_id: Optional[str] = None) -> PlacementSession:
    if session_id:
        session_obj = db.query(PlacementSession).filter(PlacementSession.id == session_id).first()
        if session_obj:
            return session_obj
        # Create explicit session with given ID if not found
        session_obj = PlacementSession(
            id=session_id,
            name=f"Placement Session {session_id[:8]}",
            college_name="University Placement Office",
            status="ACTIVE"
        )
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
        return session_obj

    session_obj = db.query(PlacementSession).filter(PlacementSession.status == "ACTIVE").first()
    if not session_obj:
        session_obj = PlacementSession(
            id=str(uuid.uuid4()),
            name="University Placement Session 2026",
            college_name="University Placement Office",
            status="ACTIVE"
        )
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
    return session_obj

def get_current_session_id(
    request: Request,
    db: Session = Depends(get_db)
) -> str:
    # 1. Check header X-Placement-Session-ID
    header_session_id = request.headers.get("X-Placement-Session-ID") or request.headers.get("x-placement-session-id")
    if header_session_id and header_session_id.strip():
        session_obj = get_or_create_active_session(db, header_session_id.strip())
        return session_obj.id

    # 2. Check query parameter placement_session_id
    query_session_id = request.query_params.get("placement_session_id")
    if query_session_id and query_session_id.strip():
        session_obj = get_or_create_active_session(db, query_session_id.strip())
        return session_obj.id

    # 3. Fallback to active default session
    session_obj = get_or_create_active_session(db)
    return session_obj.id

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

def require_role(allowed_roles: list[str]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role {current_user.role}"
            )
        return current_user
    return role_checker
