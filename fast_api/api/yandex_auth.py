from fastapi import APIRouter

yandex_auth_router = APIRouter(
    prefix="/auth/yandex",
    tags=["Yandex Authentication"]
)