from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_password_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    Token,
)
from app.schemas.user import UserCreate, UserRead
from app.services.audit_service import record_audit_event
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserCreate,
    database_session: Annotated[Session, Depends(get_db)],
) -> User:
    user = User(
        email=str(user_data.email),
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    database_session.add(user)

    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        ) from error

    database_session.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    database_session: Annotated[Session, Depends(get_db)],
) -> Token:
    email = form_data.username.lower()
    user = database_session.scalar(select(User).where(User.email == email))

    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: CurrentUser) -> User:
    return current_user


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    request_data: ForgotPasswordRequest,
    database_session: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    generic_response = MessageResponse(
        message="If an account exists with this email, a password reset link has been sent."
    )
    email = request_data.email.lower().strip()
    user = database_session.scalar(select(User).where(User.email == email))

    # Avoid user enumeration: return generic message if user is not found or inactive
    if user is None or not user.is_active:
        return generic_response

    now = datetime.now(UTC)

    # Invalidate any existing unused reset tokens for this user
    database_session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    # Generate high-entropy reset token and store only its SHA-256 hash
    raw_token = generate_password_reset_token()
    token_hash = hash_token(raw_token)
    expires_at = now + timedelta(minutes=settings.password_reset_token_expire_minutes)

    reset_token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    database_session.add(reset_token_record)

    # Security: Do NOT write raw token or password to audit logs
    record_audit_event(
        database_session,
        user_id=user.id,
        action="password_reset_requested",
        resource_type="user",
        resource_id=user.id,
        description=f"Password reset link requested for user '{user.email}'",
    )

    database_session.commit()

    reset_link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={raw_token}"
    send_password_reset_email(user.email, reset_link)

    return generic_response


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request_data: ResetPasswordRequest,
    database_session: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    token_hash = hash_token(request_data.token.strip())
    reset_record = database_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
        )
    )

    if reset_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link",
        )

    if reset_record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link has already been used",
        )

    now = datetime.now(UTC)
    expires_at = reset_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has expired",
        )

    user = database_session.get(User, reset_record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account not found or inactive",
        )

    # Update password hash using Argon2id
    user.password_hash = hash_password(request_data.password)

    # Mark current token as used
    reset_record.used_at = now

    # Invalidate any other active tokens for this user
    database_session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != reset_record.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    # Security: Do NOT write raw token or password to audit logs
    record_audit_event(
        database_session,
        user_id=user.id,
        action="password_reset_completed",
        resource_type="user",
        resource_id=user.id,
        description=f"Password successfully reset for user '{user.email}'",
    )

    database_session.commit()

    return MessageResponse(
        message="Password has been successfully reset. You may now sign in."
    )
