import aiohttp
from loguru import logger

from config import settings


async def _get_state(session: aiohttp.ClientSession) -> dict | None:
    url = f"{settings.API_BASE_URL}/api/v1/kettle/status"

    try:
        async with session.get(
            url=url,
        ) as response:
            response.raise_for_status()
            result = await response.json()
            logger.info(f"У чайника запросили информацию с датчиков. Ответ API {result}")
            return result

    except aiohttp.ClientResponseError as e:
        # если вернули 400,404,500 и т.д.
        logger.error(f"Ошибка API (статус {e.status}): {e.message}")
        return None

    except aiohttp.ClientError as e:
        # если сервер недоступен (например упал fastapi)
        logger.error(f"Ошибка соединения с сервером: {e}")
        return None

    except Exception as e:  # noqa: BLE001 - не прерывать работу из-за ошибок API
        # всякие остальные случаи
        logger.exception(f"Непредвиденная ошибка в _get_state: {e}")
        return None


async def _boil(session: aiohttp.ClientSession, temp: int) -> dict:
    url = f"{settings.API_BASE_URL}/api/v1/kettle/set-temp"

    payload = {"target_temp": temp}

    try:
        async with session.post(url=url, json=payload) as response:
            response.raise_for_status()
            result = await response.json()
            logger.info(f"Чайнику передали запрос {payload}. Ответ API {result}")
            return result

    except aiohttp.ClientResponseError as e:
        # если вернули 400,404,500 и т.д.
        logger.error(f"Ошибка API (статус {e.status}): {e.message}")
        return {"success": False}

    except aiohttp.ClientError as e:
        # если сервер недоступен (например упал fastapi)
        logger.error(f"Ошибка соединения с сервером: {e}")
        return {"success": False}

    except Exception as e:  # noqa: BLE001 - не прерывать работу из-за ошибок API
        # всякие остальные случаи
        logger.exception(f"Непредвиденная ошибка в _boil: {e}")
        return {"success": False}


async def _stop_boil(session: aiohttp.ClientSession) -> dict:
    url = f"{settings.API_BASE_URL}/api/v1/kettle/stop"

    try:
        async with session.post(url=url) as response:
            response.raise_for_status()
            result = await response.json()
            logger.info(f"Чайник остановлен. Ответ API {result}")
            return result

    except aiohttp.ClientResponseError as e:
        # если вернули 400,404,500 и т.д.
        logger.error(f"Ошибка API (статус {e.status}): {e.message}")
        return {"success": False}

    except aiohttp.ClientError as e:
        # если сервер недоступен (например упал fastapi)
        logger.error(f"Ошибка соединения с сервером: {e}")
        return {"success": False}

    except Exception as e:  # noqa: BLE001 - не прерывать работу из-за ошибок API
        # всякие остальные случаи
        logger.exception(f"Непредвиденная ошибка в _boil: {e}")
        return {"success": False}
