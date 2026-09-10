import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from loguru import logger

from config import settings
from fast_api.api.metrics import metrics_client
from fast_api.api.smart_kettle import kettle_client, kettle_router
from fast_api.api.users_db import authenticate_user, init_db
from fast_api.api.yandex_auth import yandex_auth_router
from fast_api.api.yandex_callback import yandex_callback_client
from fast_api.api.yandex_smarthome import yandex_smarthome_router


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)
logger.add(
    "/app/logs/api.log",
    rotation="5 MB",
    retention="10 days",
    encoding="utf-8",
    level="INFO",
)
# ================================================

security = HTTPBasic()


async def poll_kettle_status():
    last_temp: int | None = None
    last_target: int | None = None
    last_is_on: bool | None = None
    last_is_lifting: bool | None = None
    last_online: bool = True
    last_sent_time: float = 0.0

    while True:
        try:
            state = await kettle_client.get_state()
            now = time.time()

            if state is not None:
                await metrics_client.write_kettle_state(
                    state.current_temp, state.target, state.status_code
                )

                is_on = state.status_code in (1, 2, 4)
                should_notify = (
                    last_temp is None
                    or not last_online
                    or abs(state.current_temp - last_temp) >= 1
                    or is_on != last_is_on
                    or state.target != last_target
                    or state.is_lifting != last_is_lifting
                    or (now - last_sent_time) >= 600
                )

                if should_notify:
                    sent = await yandex_callback_client.send_state(
                        current_temp=state.current_temp,
                        target_temp=state.target,
                        is_on=is_on,
                        online=True,
                    )
                    if sent:
                        last_temp = state.current_temp
                        last_target = state.target
                        last_is_on = is_on
                        last_is_lifting = state.is_lifting
                        last_online = True
                        last_sent_time = now
                    else:
                        # При ошибке шлюза Яндекса повторяем через 30 секунд (вместо 10 минут)
                        last_sent_time = now - 570
            elif last_online:
                sent = await yandex_callback_client.send_state(
                    current_temp=0,
                    target_temp=0,
                    is_on=False,
                    online=False,
                )
                if sent:
                    last_online = False
                    last_sent_time = now
                else:
                    last_sent_time = now - 570
        except Exception as e:  # noqa: BLE001 - из-за ошибки не прерывать работу сети и устройства
            logger.error(f"Error polling kettle: {e}")
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(poll_kettle_status())
    yield
    task.cancel()
    await yandex_callback_client.close()


app = FastAPI(
    title="Smart-Kettle API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.include_router(kettle_router)
app.include_router(yandex_auth_router)
app.include_router(yandex_smarthome_router)


@app.get("/")
def read_root():
    return {"status": "API is working", "project": "smart-kettle-api"}


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):

    user_id = authenticate_user(credentials.username, credentials.password)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/docs", include_in_schema=False)
async def get_swagger_documentation(username: str = Depends(verify_credentials)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")


@app.get("/openapi.json", include_in_schema=False)
async def openapi(username: str = Depends(verify_credentials)):
    return get_openapi(title=app.title, version=app.version, routes=app.routes)


if __name__ == "__main__":
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_error = logging.getLogger("uvicorn.error")

    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_access.setLevel(logging.INFO)
    uvicorn_error.setLevel(logging.INFO)

    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]

    uvicorn_logger.propagate = False
    uvicorn_access.propagate = False
    uvicorn_error.propagate = False

    init_db(settings.KETTLE_USERNAME, settings.KETTLE_PASSWORD)

    uvicorn.run("fast_api.main:app", host="0.0.0.0", port=8000, reload=False, log_config=None)
