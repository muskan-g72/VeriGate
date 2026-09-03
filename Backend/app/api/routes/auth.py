from typing import Annotated

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.email import send_password_reset_email
from app.core.security import create_access_token, create_password_reset_token, decode_password_reset_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import ForgotPasswordRequest, MessageResponse, ResetPasswordRequest, Token
from app.schemas.user import UserCreate, UserRead

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


@router.post("/forgot-password", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    database_session: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    email = str(request.email).lower()
    user = database_session.scalar(select(User).where(User.email == email))
    if user is not None and user.is_active:
        token = create_password_reset_token(email)
        background_tasks.add_task(send_password_reset_email, email, token)
    return MessageResponse(message="If an account exists for that email, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: ResetPasswordRequest,
    database_session: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    try:
        email = decode_password_reset_token(request.token)
    except jwt.InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired") from error
    user = database_session.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired")
    user.password_hash = hash_password(request.password)
    database_session.commit()
    return MessageResponse(message="Your password has been updated.")
