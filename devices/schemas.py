from pydantic import BaseModel, computed_field


STATUS_MAP = {
            0: "Ожидание / Выключен",
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
        
        return STATUS_MAP.get(self.status_code, "Неизвестный статус")