import uvicorn
import logging
from fastapi import FastAPI
import sys
from loguru import logger
from fast_api.api.smart_kettle import kettle_router
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
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add("api.log", rotation="5 MB", retention="10 days", encoding="utf-8", level="INFO")
#================================================


app = FastAPI(title="Smart-Kettle API")

app.include_router(kettle_router)
app.include_router(yandex_auth_router)
app.include_router(yandex_smarthome_router)


@app.get("/")
def read_root():
    return {"status": "API is working", "project": "smart-kettle-api"}

  
    


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
    
    uvicorn.run("fast_api.main:app", host="0.0.0.0", port=8000, reload=False, log_config=None)
