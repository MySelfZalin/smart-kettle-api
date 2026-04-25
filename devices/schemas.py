from pydantic import BaseModel, computed_field, Field


STATUS_MAP = {
            0: "Выключен",
            1: "Нагрев",
            2: "Кипячение",
            3: "Остывание",
            4: "Поддержание температуры"
        }

class KettleState(BaseModel):
    current_temp: int
    target: int
    status_code: int
    is_lifting: bool
    
    
    @computed_field
    def status(self) -> str:
        if self.is_lifting:
            return "Чайник поднят с платформы"
        
        return STATUS_MAP.get(self.status_code, "Неизвестный статус")


class SetTempRequest(BaseModel):
    target_temp: int = Field(ge=40, le=99)