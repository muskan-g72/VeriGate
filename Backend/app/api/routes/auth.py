import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
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
from app.models.oauth_account import OAuthAccount, OAuthAuthorization
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    MessageResponse,
    OAuthCodeExchangeRequest,
    ResetPasswordRequest,
    Token,
)
from app.schemas.user import UserCreate, UserRead
from app.services.audit_service import record_audit_event
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/auth")

OAUTH_PROVIDERS = {
    "google": {"authorize": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token", "profile": "https://openidconnect.googleapis.com/v1/userinfo", "scope": "openid email profile"},
    "github": {"authorize": "https://github.com/login/oauth/authorize", "token": "https://github.com/login/oauth/access_token", "profile": "https://api.github.com/user", "emails": "https://api.github.com/user/emails", "scope": "read:user user:email"},
}


def _oauth_config(provider: str) -> tuple[dict, str, str]:
    config = OAUTH_PROVIDERS.get(provider)
    client_id = getattr(settings, f"{provider}_client_id", None)
    client_secret = getattr(settings, f"{provider}_client_secret", None)
    if not config or not client_id or not client_secret:
        raise HTTPException(status_code=404, detail="OAuth provider is not configured")
    return config, client_id, client_secret


def _oauth_redirect_uri(provider: str) -> str:
    base = settings.oauth_redirect_base or settings.backend_url
    return f"{base.rstrip('/')}/api/v1/auth/{provider}/callback"


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
        system_role=user_data.role,
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
    record_audit_event(
        database_session,
        user_id=user.id,
        action="user_created",
        resource_type="user",
        resource_id=user.id,
        description=f"User {user.email} registered ({user.system_role})",
    )
    database_session.commit()
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    database_session: Annotated[Session, Depends(get_db)],
) -> Token:
    email = form_data.username.lower()
    user = database_session.scalar(select(User).where(User.email == email))

    if user is not None and user.password_hash is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This account uses OAuth sign-in. Continue with its connected provider.")
    if user is None or not verify_password(form_data.password, user.password_hash):
        record_audit_event(
            database_session,
            user_id=user.id if user else None,
            action="failed_login",
            resource_type="auth",
            description=f"Failed login attempt for {email}",
        )
        database_session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        record_audit_event(
            database_session,
            user_id=user.id,
            action="inactive_login_attempt",
            resource_type="auth",
            description=f"Login attempt by inactive user {email}",
        )
        database_session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    record_audit_event(
        database_session,
        user_id=user.id,
        action="login",
        resource_type="auth",
        description=f"User {user.email} logged in ({user.system_role})",
    )
    database_session.commit()

    return Token(
        access_token=create_access_token(str(user.id), role=user.system_role),
        role=user.system_role,
    )


@router.get("/{provider}/login")
def oauth_login(provider: str, database_session: Annotated[Session, Depends(get_db)]):
    config, client_id, _ = _oauth_config(provider)
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64) if provider == "google" else None
    database_session.add(OAuthAuthorization(provider=provider, state=state, code_verifier=verifier, expires_at=datetime.now(UTC) + timedelta(minutes=10)))
    database_session.commit()
    params = {"client_id": client_id, "redirect_uri": _oauth_redirect_uri(provider), "response_type": "code", "scope": config["scope"], "state": state}
    if verifier:
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        params.update({"code_challenge": challenge, "code_challenge_method": "S256"})
    return RedirectResponse(str(httpx.URL(config["authorize"]).copy_merge_params(params)))


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str, database_session: Annotated[Session, Depends(get_db)]):
    config, client_id, client_secret = _oauth_config(provider)
    now = datetime.now(UTC)
    auth = database_session.scalar(select(OAuthAuthorization).where(OAuthAuthorization.state == state, OAuthAuthorization.provider == provider))
    if not auth or auth.consumed_at or auth.expires_at.replace(tzinfo=UTC) < now:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    auth.consumed_at = now
    token_payload = {"client_id": client_id, "client_secret": client_secret, "code": code, "redirect_uri": _oauth_redirect_uri(provider), "grant_type": "authorization_code"}
    if auth.code_verifier:
        token_payload["code_verifier"] = auth.code_verifier
    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(config["token"], data=token_payload, headers={"Accept": "application/json"})
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="OAuth provider did not return an access token")
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        profile_response = await client.get(config["profile"], headers=headers)
        profile_response.raise_for_status()
        profile = profile_response.json()
        if provider == "google":
            provider_id, email, verified, name = str(profile.get("sub", "")), profile.get("email"), profile.get("email_verified") is True, profile.get("name")
        else:
            emails_response = await client.get(config["emails"], headers=headers)
            emails_response.raise_for_status()
            primary = next((item for item in emails_response.json() if item.get("primary") and item.get("verified")), None)
            provider_id, email, verified, name = str(profile.get("id", "")), primary.get("email") if primary else None, bool(primary), profile.get("name") or profile.get("login")
    if not provider_id or not email or not verified:
        database_session.commit()
        raise HTTPException(status_code=400, detail="OAuth provider did not supply a verified email address")
    email = email.lower().strip()
    account = database_session.scalar(select(OAuthAccount).where(OAuthAccount.provider == provider, OAuthAccount.provider_user_id == provider_id))
    linked = False
    if account:
        user = account.user
    else:
        user = database_session.scalar(select(User).where(User.email == email))
        if user:
            linked = True
        else:
            user = User(email=email, full_name=name, system_role="user")
            database_session.add(user)
            database_session.flush()
        account = OAuthAccount(user_id=user.id, provider=provider, provider_user_id=provider_id, email=email)
        database_session.add(account)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    raw_exchange_code = secrets.token_urlsafe(32)
    auth.user_id = user.id
    auth.exchange_code_hash = hash_token(raw_exchange_code)
    if linked:
        record_audit_event(database_session, user_id=user.id, action="oauth_account_linked", resource_type="oauth_account", resource_id=account.id, description=f"Linked {provider} OAuth account")
    record_audit_event(database_session, user_id=user.id, action="oauth_login", resource_type="auth", resource_id=user.id, description=f"OAuth login with {provider}" if not linked else f"Linked {provider} OAuth account and logged in")
    database_session.commit()
    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/oauth/callback?code={raw_exchange_code}&provider={provider}")


@router.post("/oauth/exchange", response_model=Token)
def exchange_oauth_code(payload: OAuthCodeExchangeRequest, database_session: Annotated[Session, Depends(get_db)]) -> Token:
    record = database_session.scalar(select(OAuthAuthorization).where(OAuthAuthorization.exchange_code_hash == hash_token(payload.code)))
    now = datetime.now(UTC)
    if not record or record.exchange_used_at or not record.user_id or record.expires_at.replace(tzinfo=UTC) < now:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth sign-in code")
    record.exchange_used_at = now
    user = database_session.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    database_session.commit()
    return Token(access_token=create_access_token(str(user.id), role=user.system_role), role=user.system_role)


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
