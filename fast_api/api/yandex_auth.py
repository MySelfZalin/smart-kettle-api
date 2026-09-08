import secrets
import time
from typing import Annotated
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import settings
from fast_api.api.oauth_store import create_oauth_store

yandex_auth_router = APIRouter(prefix="/auth/yandex", tags=["Yandex Authentication"])

templates = Jinja2Templates(directory="fast_api/api/templates")
code_store = create_oauth_store(settings.REDIS_URL)
ACCESS_TOKEN_TTL_SECONDS = 3600


YANDEX_BROKER_REDIRECT_URI = "https://social.yandex.net/broker/redirect"


@yandex_auth_router.get("/authorize")
async def authorize(
    client_id: str,
    response_type: str,
    redirect_uri: str,
    state: str,
    request: Request,
    scope: str | None = None,
):
    errors = []
    if settings.YANDEX_CLIENT_ID is None:
        errors.append("сервер не настроен: отсутствует YANDEX_CLIENT_ID")
    elif client_id != settings.YANDEX_CLIENT_ID:
        errors.append("неизвестный client_id")
    if response_type != "code":
        errors.append("response_type должен быть 'code'")
    if redirect_uri != YANDEX_BROKER_REDIRECT_URI:
        errors.append("redirect_uri не совпадает с адресом брокера Яндекса")
    if not state:
        errors.append("обязательный параметр state отсутствует")

    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "redirect_uri": redirect_uri,
            "state": state,
            "client_id": client_id,
            "scope": scope or "",
        },
    )


@yandex_auth_router.post("/login")
async def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    state: Annotated[str, Form()],
    client_id: Annotated[str, Form()] = "",
    scope: Annotated[str, Form()] = "",
):
    if redirect_uri != YANDEX_BROKER_REDIRECT_URI:
        raise HTTPException(
            status_code=400, detail="redirect_uri не совпадает с адресом брокера Яндекса"
        )

    import asyncio
    from fast_api.api.users_db import authenticate_user
    
    user_id = await asyncio.to_thread(authenticate_user, username, password)

    if not user_id:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "redirect_uri": redirect_uri,
                "state": state,
                "client_id": client_id,
                "scope": scope,
                "error": "Неверный логин или пароль, попробуйте еще раз",
            },
        )

    code = code_store.issue(user_id)
    params = {"state": state, "code": code, "client_id": client_id}
    if scope:
        params["scope"] = scope
    redirect_url = f"{redirect_uri}?{urlencode(params)}"
    return RedirectResponse(url=redirect_url, status_code=302)


@yandex_auth_router.post("/token")
async def get_token(
    grant_type: Annotated[str, Form()],
    code: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    client_secret: Annotated[str | None, Form()] = None,
):
    if client_id and client_id != settings.YANDEX_CLIENT_ID:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_client", "error_description": "Неизвестный client_id"},
        )

    if grant_type == "authorization_code":
        user_id = code_store.consume(code or "")
        if not user_id:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_grant",
                    "error_description": "Неверный или просроченный код авторизации",
                },
            )
    elif grant_type == "refresh_token":
        rotated = code_store.rotate_refresh(refresh_token or "")
        if rotated is None:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_grant",
                    "error_description": "Неверный или просроченный refresh-токен",
                },
            )
        user_id, refresh_token = rotated
    else:
        return JSONResponse(
            status_code=400,
            content={
                "error": "unsupported_grant_type",
                "error_description": "Неподдерживаемый grant_type",
            },
        )

    payload = {"sub": user_id, "exp": int(time.time()) + ACCESS_TOKEN_TTL_SECONDS}
    access_token = jwt.encode(payload=payload, key=settings.JWT_SECRET, algorithm="HS256")
    if grant_type == "authorization_code":
        refresh_token = code_store.issue_refresh(user_id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_TTL_SECONDS,
        "refresh_token": refresh_token,
    }
