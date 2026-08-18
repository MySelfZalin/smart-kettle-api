import time
import secrets
import jwt
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from config import settings
from fast_api.api.oauth_store import code_store
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import Annotated


yandex_auth_router = APIRouter(
    prefix="/auth/yandex",
    tags=["Yandex Authentication"]
)

templates = Jinja2Templates(directory="fast_api/api/templates")


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
    redirect_url = f"{redirect_uri}?state={state}&code={code}"

    return RedirectResponse(url=redirect_url, status_code=302)


@yandex_auth_router.post("/token")
async def get_token(
    grant_type: Annotated[str, Form()],
    code: Annotated[str, Form()] = None,
    client_id: Annotated[str, Form()] = None,
    client_secret: Annotated[str, Form()] = None,
):
    if grant_type == "authorization_code":
        if not code_store.consume(code or ""):
            raise HTTPException(status_code=400, detail="Неверный или просроченный код авторизации")
        
    payload = {
        "sub": "admin",
        "exp": int(time.time()) + 31536000   
    }    
    
    access_token = jwt.encode(payload=payload, key=settings.JWT_SECRET,algorithm="HS256")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 31536000,
        "refresh_token": "refresh_token_for_kettle_888"
    }
    
        