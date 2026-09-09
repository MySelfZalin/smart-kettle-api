import logging
import sys

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from loguru import logger

import asyncio
from contextlib import asynccontextmanager

from config import settings
from fast_api.api.metrics import metrics_client
from fast_api.api.smart_kettle import kettle_client, kettle_router
from fast_api.api.users_db import authenticate_user, init_db
from fast_api.api.yandex_auth import yandex_auth_router
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
    while True:
        try:
            state = await kettle_client.get_state()
            if state is not None:
                await metrics_client.write_kettle_state(
                    state.current_temp, state.target, state.status_code
                )
        except Exception as e:
            logger.error(f"Error polling kettle: {e}")
        await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(poll_kettle_status())
    yield
    task.cancel()

app = FastAPI(title="Smart-Kettle API", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

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
