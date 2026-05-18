import uvicorn
import logging
from fastapi import FastAPI, HTTPException
import sys
from loguru import logger
from config import settings
from devices.kettle_client import KettleClient
from devices.schemas import KettleState, SetTempRequest
from fastapi import BackgroundTasks


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

kettle_client = KettleClient(ip=settings.KETTLE_IP, token=settings.KETTLE_TOKEN)


@app.get("/api/v1/kettle/status", response_model=KettleState)
async def get_kettle_status():

    state = await kettle_client.get_state()
    
    if state is None:
        raise HTTPException(status_code=503, detail="Чайник недоступен")  
    return state


@app.post("/api/v1/kettle/set-temp")
async def set_temp(temp: SetTempRequest):
    
    is_succeses = await kettle_client.send_temp(temp.target_temp)
    
    if is_succeses:
        return {"success": True}
    else:
        raise HTTPException(status_code=503, detail="Чайник недоступен или вернул ошибку")
    
    
@app.post("/api/v1/kettle/stop")
async def stop_kettle():
    answer = await kettle_client.stop()    
    if answer:
        return {"success": True}
    else:
        raise HTTPException(status_code=503, detail="Чайник недоступен или вернул ошибку")
    

@app.post("/api/v1/kettle/spam_sound") 
async def start_spam(background_tasks: BackgroundTasks):
    background_tasks.add_task(kettle_client.spam_kettle_worker)
    return {"success": True, "message": "Начинаем спамить чайник звуком!"}  
       

@app.post("/api/v1/kettle/stop_spam")   
async def stop_spam():
    kettle_client._cancel_spam = True
    return {"success": True, "message": "Остановка принята"}     
    


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
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_config=None)
