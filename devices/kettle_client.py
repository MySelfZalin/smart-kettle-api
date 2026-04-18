import logging
from miio import Device, DeviceException
import asyncio
from .schemas import KettleState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KettleClient():
    def __init__(self, ip: str, token: str):
        self._kettle = Device(ip=ip, token=token)


    def _get_status_sync(self):
        payload = [
            {"did": "current_temp", "siid": 2, "piid": 3},
            {"did": "target_temp", "siid": 2, "piid": 4},
            {"did": "status", "siid": 2, "piid": 1},
            {"did": "kettle-lifting", "siid": 3, "piid": 7}
        ]
        return self._kettle.send("get_properties", payload)

    async def get_state(self) -> KettleState | None:
        try:
            print("Запрашиваем статус...")
            async with asyncio.timeout(5):
                raw_answer = await asyncio.to_thread(self._get_status_sync)
            
            
            current = 0
            target = 0
            status_code = 0
            is_lifting = None
                
            for item in raw_answer:
                if item["siid"] == 2 and item["piid"] == 3:
                    current = item["value"]  
                      
                elif item["siid"] == 2 and item["piid"] == 4:
                    target = item["value"]  
                      
                elif item["siid"] == 2 and item["piid"] == 1:
                    status_code = item["value"]  
                      
                elif item["siid"] == 3 and item["piid"] == 7:
                    is_lifting = item["value"]  
                      
            return KettleState(current_temp=current, target=target,
                               status_code=status_code, is_lifting=is_lifting)
            

        except asyncio.TimeoutError:
            logger.error("Чайник не ответил за 5 секунд (Таймаут)!")
        except DeviceException as e:
            logger.error(f"Ошибка протокола: {e}")
        except Exception as e:
            logger.exception("Неизвестная ошибка")
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
#=======================================

    # def _set_temp_sync(self, target_temp: int):
    #     payload = [
    #         {
    #             "did": "set_temp",
    #             "siid": 2, 
    #             "piid": 4, 
    #             "value": target_temp
    #         }
    #     ]
    #     return self._kettle.send("set_properties", payload)


















            # target = 80

            # print(f"\n2. Отправляем команду на нагрев до {target}°C...")
            # async with asyncio.timeout(5):
            #     set_result = await asyncio.to_thread(self._set_temp_sync, target)
            
            # print(f"Ответ на команду установки: {set_result}")


            # await asyncio.sleep(4)            