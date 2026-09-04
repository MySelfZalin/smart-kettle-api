from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from fastapi.params import Depends
from loguru import logger

from fast_api.api.jwt_check import verify_jwt
from fast_api.api.smart_kettle import kettle_client

yandex_smarthome_router = APIRouter(prefix="/v1.0", tags=["Yandex smarthome"])


@yandex_smarthome_router.get("/user/devices")
async def get_devices(
    x_request_id: Annotated[str, Header(alias="X-Request-Id")],
    payload: dict = Depends(verify_jwt),
):
    user_id = payload.get("sub", "unknown")
    logger.info(f"[{user_id}] запросил список устройств (X-Request-Id: {x_request_id})")
    return {
        "request_id": x_request_id,
        "payload": {
            "user_id": "admin",
            "devices": [
                {
                    "id": "my_smart_kettle",
                    "name": "Чайник",
                    "description": "Умный чайник с кастомной температурой",
                    "room": "Кухня",
                    "type": "devices.types.cooking.kettle",
                    "status_info": {"reportable": True},
                    "capabilities": [
                        {"type": "devices.capabilities.on_off", "retrievable": True},
                        {
                            "type": "devices.capabilities.range",
                            "retrievable": True,
                            "parameters": {
                                "instance": "temperature",
                                "random_access": True,
                                "range": {"max": 99, "min": 40, "precision": 1},
                                "unit": "unit.temperature.celsius",
                            },
                        },
                    ],
                    "properties": [
                        {
                            "type": "devices.properties.float",
                            "retrievable": True,
                            "parameters": {
                                "instance": "temperature",
                                "unit": "unit.temperature.celsius",
                            },
                        }
                    ],
                    "device_info": {
                        "manufacturer": "Xiaomi",
                        "model": "Kettle Kettle 2 Pro",
                    },
                }
            ],
        },
    }


@yandex_smarthome_router.post("/user/devices/query")
async def query_devices(
    x_request_id: Annotated[str, Header(alias="X-Request-Id")],
    payload: dict = Depends(verify_jwt),
):
    user_id = payload.get("sub", "unknown")
    logger.info(f"[{user_id}] запросил состояние устройств (X-Request-Id: {x_request_id})")

    state = await kettle_client.get_state()

    if state is None:
        raise HTTPException(status_code=503, detail="Чайник недоступен")

    is_on = state.status_code in [1, 2, 4]

    return {
        "request_id": x_request_id,
        "payload": {
            "devices": [
                {
                    "id": "my_smart_kettle",
                    "capabilities": [
                        {
                            "type": "devices.capabilities.on_off",
                            "state": {"instance": "on", "value": is_on},
                        },
                        {
                            "type": "devices.capabilities.range",
                            "state": {"instance": "temperature", "value": state.target},
                        },
                    ],
                    "properties": [
                        {
                            "type": "devices.properties.float",
                            "state": {
                                "instance": "temperature",
                                "value": state.current_temp,
                            },
                        }
                    ],
                }
            ]
        },
    }


@yandex_smarthome_router.post("/user/devices/action")
async def handle_action(
    request_data: dict,
    x_request_id: Annotated[str, Header(alias="X-Request-Id")],
    payload: dict = Depends(verify_jwt),
):
    user_id = payload.get("sub", "unknown")
    logger.info(f"[{user_id}] шлёт action (X-Request-Id: {x_request_id}): {request_data}")

    response_capabilities = []

    devices = request_data.get("payload", {}).get("devices", [])

    for device in devices:
        capabilities = device.get("capabilities", [])

        for cap in capabilities:
            cap_type = cap.get("type")
            instance = cap.get("state", {}).get("instance")
            value = cap.get("state", {}).get("value")

            success = False

            if cap_type == "devices.capabilities.on_off":
                if value is True:
                    success = await kettle_client.send_temp(99)
                else:
                    success = await kettle_client.stop()

            elif cap_type == "devices.capabilities.range" and instance == "temperature":
                success = await kettle_client.send_temp(value)

            if success:
                action_result = {"status": "DONE"}
            else:
                action_result = {"status": "ERROR", "error_code": "DEVICE_UNREACHABLE"}

            response_capabilities.append(
                {
                    "type": cap_type,
                    "state": {"instance": instance, "action_result": action_result},
                }
            )

    return {
        "request_id": x_request_id,
        "payload": {"devices": [{"id": "my_smart_kettle", "capabilities": response_capabilities}]},
    }
