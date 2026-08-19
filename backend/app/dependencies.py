from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.security import InvalidTokenError, decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "invalid_authentication",
            "message": "Valid authentication credentials are required.",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise authentication_error()

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")

        if subject is None:
            raise authentication_error()

        user_id = int(subject)
    except (InvalidTokenError, TypeError, ValueError):
        raise authentication_error() from None

    user = db.get(User, user_id)

    if user is None:
        raise authentication_error()

    return user


def require_role(required_role: UserRole) -> Callable:
    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "insufficient_permissions",
                    "message": f"This action requires the {required_role.value} role.",
                },
            )

        return current_user

    return role_checker


get_current_patient = require_role(UserRole.PATIENT)
get_current_doctor = require_role(UserRole.DOCTOR)