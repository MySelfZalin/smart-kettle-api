import asyncio
from config import settings
from devices.kettle_client import KettleClient








async def main():
    client = KettleClient(ip=settings.KETTLE_IP, token=settings.KETTLE_TOKEN)
    
    state = await client.get_state()
    if state:
        print(f"Температура сейчас - {state.current_temp}")
        print(f"Цель по нагреву - {state.target}")
        print(f"Код статуса работы - {state.status_code}")
        print(f"Статус работы - {state.status}")
        
        answer = "Нет" if state.is_lifting else "Да"
  
        print(f"Находится ли чайник на базе? - {answer}")



if __name__ == "__main__":
    asyncio.run(main())