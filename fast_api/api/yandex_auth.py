import secrets
import time
from typing import Annotated
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import settings
from fast_api.api.oauth_store import create_oauth_store


yandex_auth_router = APIRouter(
    prefix="/auth/yandex",
    tags=["Yandex Authentication"]
)

templates = Jinja2Templates(directory="fast_api/api/templates")
code_store = create_oauth_store(settings.REDIS_URL)
ACCESS_TOKEN_TTL_SECONDS = 3600


@yandex_auth_router.get("/authorize")
async def authorize(client_id: str, response_type: str, redirect_uri: str, state: str, request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"redirect_uri": redirect_uri, "state": state}
    )


@yandex_auth_router.post("/login")
async def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    state: Annotated[str, Form()]
):
    username_ok = secrets.compare_digest(username, settings.KETTLE_USERNAME)
    password_ok = secrets.compare_digest(password, settings.KETTLE_PASSWORD)

    if not (username_ok and password_ok):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "redirect_uri": redirect_uri,
                "state": state,
                "error": "Неверный логин или пароль, попробуйте еще раз"
            }
        )

    code = code_store.issue()
    redirect_url = f"{redirect_uri}?{urlencode({'state': state, 'code': code})}"
    return RedirectResponse(url=redirect_url, status_code=302)


@yandex_auth_router.post("/token")
async def get_token(
    grant_type: Annotated[str, Form()],
    code: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    client_secret: Annotated[str | None, Form()] = None,
):
    if grant_type == "authorization_code":
        if not code_store.consume(code or ""):
            raise HTTPException(status_code=400, detail="Неверный или просроченный код авторизации")
        user_id = "admin"
    elif grant_type == "refresh_token":
        rotated = code_store.rotate_refresh(refresh_token or "")
        if rotated is None:
            raise HTTPException(status_code=400, detail="Неверный или просроченный refresh-токен")
        user_id, refresh_token = rotated
    else:
        raise HTTPException(status_code=400, detail="Неподдерживаемый grant_type")

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
