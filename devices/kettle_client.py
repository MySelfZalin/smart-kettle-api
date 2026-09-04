import asyncio

from loguru import logger
from miio import Device, DeviceException

from config import settings

from .schemas import KettleState


class KettleClient:
    def __init__(self, ip: str, token: str):
        self._kettle = Device(ip=ip, token=token)
        self._cancel_spam = False

    def _get_status_sync(self):
        payload = [
            {"did": "current_temp", "siid": 2, "piid": 3},
            {"did": "target_temp", "siid": 2, "piid": 4},
            {"did": "status", "siid": 2, "piid": 1},
            {"did": "kettle-lifting", "siid": 3, "piid": 7},
        ]
        return self._kettle.send("get_properties", payload)

    async def get_state(self) -> KettleState | None:
        for i in range(3):
            current_timeout = 5.0 if i == 0 else 2.0
            try:
                logger.debug("Запрашиваем статус...")
                async with asyncio.timeout(current_timeout):
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

                return KettleState(
                    current_temp=current,
                    target=target,
                    status_code=status_code,
                    is_lifting=is_lifting,
                )

            except TimeoutError:
                logger.error(f"Таймаут при отправке, попытка {i + 1} из 3")
                await asyncio.sleep(0.25)
            except DeviceException as e:
                logger.error(f"Ошибка протокола: {e}")
            except Exception as e:
                logger.exception(f"Неизвестная ошибка {e}")
        logger.error("🔴Чайник не отвечает!!!")
        return None

    async def predict_heating_time(self, target_temp: int) -> dict:
        state = await self.get_state()

        if state is None:
            logger.warning("Невозможно расчитать время, чайник не отвечает")
            return {"success": False}

        current_temp = state.current_temp

        if current_temp >= target_temp:
            return {"success": True, "predict_time": 0}

        v_max = 0.203  # Heating rate(degrees per second)
        c_start = 15  # Seconds lost during initial warmup

        delta_t = target_temp - current_temp
        base_time = delta_t / v_max

        if current_temp < 45:
            total_time = base_time + c_start
        else:
            total_time = base_time

        return {"success": True, "predict_time": int(total_time)}

    def _send_temp_sync(self, target_temp: int):
        is_quiet = settings.is_quiet_hours()
        payload = [
            {"did": "set_temp", "siid": 2, "piid": 4, "value": target_temp},
            {"did": "set_sound", "siid": 6, "piid": 1, "value": is_quiet},
        ]
        return self._kettle.send("set_properties", payload)

    async def send_temp(self, target_temp: int) -> bool:
        for i in range(3):
            current_timeout = 5.0 if i == 0 else 2.0
            try:
                async with asyncio.timeout(current_timeout):
                    answer = await asyncio.to_thread(self._send_temp_sync, target_temp)

                is_success = True
                for item in answer:
                    if item.get("code") != 0:
                        is_success = False

                if is_success:
                    return True
                else:
                    logger.error(f"Произошла ошибка {answer}")
                    return False

            except TimeoutError:
                logger.error(f"Таймаут при отправке, попытка {i + 1} из 3")
                await asyncio.sleep(0.25)
            except DeviceException as e:
                logger.error(f"Ошибка протокола: {e}")
                return False
            except Exception as e:
                logger.exception(f"Неизвестная ошибка {e}")
                return False
        logger.error("Не удалось отправить запрос за 3 попытки")
        return False

    def _stop_sync(self):
        is_quiet = settings.is_quiet_hours()

        self._kettle.send(
            "set_properties",
            [{"did": "set_sound", "siid": 6, "piid": 1, "value": is_quiet}],
        )
        return self._kettle.send("action", {"did": "stop_kettle", "siid": 3, "aiid": 1, "in": []})

    async def stop(self) -> bool:
        for i in range(3):
            current_timeout = 5.0 if i == 0 else 2.0
            try:
                async with asyncio.timeout(current_timeout):
                    answer = await asyncio.to_thread(self._stop_sync)

                if answer["code"] == 0:
                    return True
                else:
                    logger.error(f"Произошла ошибка {answer}")
                    return False

            except TimeoutError:
                logger.error(f"Таймаут при отправке, попытка {i + 1} из 3")
                await asyncio.sleep(0.25)
            except DeviceException as e:
                logger.error(f"Ошибка протокола: {e}")
                return False
            except Exception as e:
                logger.exception(f"Неизвестная ошибка {e}")
                return False

        logger.error("Не удалось отправить запрос за 3 попытки")
        return False

    async def spam_kettle_worker(self):
        self._cancel_spam = False

        for i in range(100):
            if self._cancel_spam:
                logger.info(f"Спам остановлен на {i} итерации")
                break

            try:
                await self.stop()
            except Exception as e:
                logger.error(f"Ошибка в спам-цикле: {e}")

            await asyncio.sleep(0.6)
