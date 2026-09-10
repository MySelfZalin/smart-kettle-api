import time

import aiohttp
from loguru import logger

from config import settings

CALLBACK_URL_TEMPLATE = "https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/state"


class YandexCallbackClient:
    def __init__(self) -> None:
        self.skill_id = settings.YANDEX_SKILL_ID
        self.oauth_token = settings.YANDEX_OAUTH_TOKEN
        self.user_id = settings.YANDEX_USER_ID
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_state(
        self,
        current_temp: int,
        target_temp: int,
        is_on: bool,
        online: bool = True,
    ) -> bool:
        if not self.skill_id or not self.oauth_token:
            return False

        url = CALLBACK_URL_TEMPLATE.format(skill_id=self.skill_id)
        headers = {
            "Authorization": f"OAuth {self.oauth_token}",
            "Content-Type": "application/json",
        }

        if not online:
            device_data = {
                "id": "my_smart_kettle",
                "status": "offline",
            }
        else:
            device_data = {
                "id": "my_smart_kettle",
                "properties": [
                    {
                        "type": "devices.properties.float",
                        "state": {
                            "instance": "temperature",
                            "value": float(current_temp),
                        },
                    }
                ],
                "capabilities": [
                    {
                        "type": "devices.capabilities.on_off",
                        "state": {
                            "instance": "on",
                            "value": is_on,
                        },
                    },
                    {
                        "type": "devices.capabilities.range",
                        "state": {
                            "instance": "temperature",
                            "value": int(target_temp),
                        },
                    },
                ],
            }

        payload = {
            "ts": time.time(),
            "payload": {
                "user_id": self.user_id,
                "devices": [device_data],
            },
        }

        try:
            session = await self._get_session()
            async with session.post(url=url, headers=headers, json=payload) as response:
                if response.status in (200, 202):
                    logger.debug("Статус чайника успешно отправлен в Яндекс Callback API")
                    return True
                resp_text = await response.text()
                logger.warning(f"Яндекс Callback API вернул код {response.status}: {resp_text}")
                return False
        except aiohttp.ClientError as e:
            logger.error(f"Сетевая ошибка при отправке в Яндекс Callback API: {e}")
            return False
        except Exception as e:  # noqa: BLE001 - внешняя ошибка не должна прерывать поллер
            logger.exception(f"Непредвиденная ошибка в YandexCallbackClient: {e}")
            return False


yandex_callback_client = YandexCallbackClient()
