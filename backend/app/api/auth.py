from fastapi import APIRouter, Request, Response

from app.api.dependencies import DB, Actor, limit
from app.repositories.players import current_user_view
from app.schemas.requests import (
    EmailRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenRequest,
)
from app.schemas.responses import CurrentUserOutput, MessageOutput, TokenOutput
from app.services import auth

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=CurrentUserOutput, status_code=201)
def register(data: RegisterRequest, request: Request, db: DB):
    limit(request, "register", str(data.email), count=3, seconds=3600)
    user = auth.register(db, data, request.app.state.settings)
    return current_user_view(db, user)


@router.post("/login", response_model=TokenOutput)
def login(data: LoginRequest, request: Request, db: DB):
    limit(request, "login", str(data.email))
    return auth.login(db, data, request.app.state.settings)


@router.post("/refresh", response_model=TokenOutput)
def refresh(data: RefreshRequest, request: Request, db: DB):
    limit(request, "refresh")
    return auth.refresh(db, data.refresh_token, request.app.state.settings)


@router.post("/logout", status_code=204)
def logout(actor: Actor, db: DB):
    auth.revoke_session(db, actor.session)
    return Response(status_code=204)


@router.post("/forgot-password", response_model=MessageOutput, status_code=202)
def forgot(data: EmailRequest, request: Request, db: DB):
    limit(request, "forgot", str(data.email), count=3, seconds=3600)
    auth.request_message(db, data.email, "reset", request.app.state.settings)
    return {"message": "If the account is eligible, recovery instructions will be sent."}


@router.post("/resend-verification", response_model=MessageOutput, status_code=202)
def resend(data: EmailRequest, request: Request, db: DB):
    limit(request, "verify-send", str(data.email), count=3, seconds=3600)
    auth.request_message(db, data.email, "verify", request.app.state.settings)
    return {"message": "If the account is eligible, verification instructions will be sent."}


@router.post("/verify-email", status_code=204)
def verify(data: TokenRequest, request: Request, db: DB):
    limit(request, "verify-consume")
    auth.consume_account_token(db, data.token, "verify")
    return Response(status_code=204)


@router.post("/reset-password", status_code=204)
def reset(data: ResetPasswordRequest, request: Request, db: DB):
    limit(request, "reset-consume")
    auth.consume_account_token(db, data.token, "reset", data.password)
    return Response(status_code=204)
