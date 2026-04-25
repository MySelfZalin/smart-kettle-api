from fastapi import FastAPI, HTTPException
from config import settings
from devices.kettle_client import KettleClient
from devices.schemas import KettleState, SetTempRequest




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
        
    


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
