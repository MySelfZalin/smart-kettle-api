from fastapi import APIRouter, HTTPException, BackgroundTasks
from config import settings
from devices.kettle_client import KettleClient
from devices.schemas import KettleState, SetTempRequest

kettle_router = APIRouter(
    prefix="/api/v1/kettle",
    tags=["Smart Kettle"]
)

kettle_client = KettleClient(ip=settings.KETTLE_IP, token=settings.KETTLE_TOKEN)


@kettle_router.get("/status", response_model=KettleState)
async def get_kettle_status():

    state = await kettle_client.get_state()
    
    if state is None:
        raise HTTPException(status_code=503, detail="Чайник недоступен")  
    return state


@kettle_router.post("/set-temp")
async def set_temp(temp: SetTempRequest):
    
    is_success = await kettle_client.send_temp(temp.target_temp)
    
    if is_success:
        predict_resp = await kettle_client.predict_heating_time(target_temp=temp.target_temp)
        
        if predict_resp.get('success'):
            p_time = predict_resp.get("predict_time")
            if p_time == 0:
                return {"success": True, "already_hot": True, "predict_time": 0}
            else:
                return {"success": True, "already_hot": False, "predict_time": p_time}  
        else:
            return {"success": True, "already_hot": False, "predict_time": None}
    else:
        raise HTTPException(status_code=503, detail="Чайник недоступен или вернул ошибку")
    
    
@kettle_router.post("/stop")
async def stop_kettle():
    answer = await kettle_client.stop()    
    if answer:
        return {"success": True}
    else:
        raise HTTPException(status_code=503, detail="Чайник недоступен или вернул ошибку")


@kettle_router.post("/spam_sound") 
async def start_spam(background_tasks: BackgroundTasks):
    background_tasks.add_task(kettle_client.spam_kettle_worker)
    return {"success": True, "message": "Начинаем спамить чайник звуком!"}  
       

@kettle_router.post("/stop_spam")   
async def stop_spam():
    kettle_client._cancel_spam = True
    return {"success": True, "message": "Остановка принята"}   


@kettle_router.get("/heating-time")
async def get_kettle_heating_time(target_temp: int) -> dict:
    response = await kettle_client.predict_heating_time(target_temp=target_temp) 
    if response is None:
        return {"success": False}
        
    return {
        "success": True,
        "current_temp": response["current_temp"],
        "predict_time": response["predict_time"]
    }