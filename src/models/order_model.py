from pydantic import BaseModel, Field, conlist
from typing import List, Optional, Union
from datetime import datetime

class OrderModel(BaseModel):
    orderId: str
    orderInsertDate: datetime = Field(default_factory=datetime.now)
    orderStartDate: datetime
    assignedOperator: List[List[str]]
    orderStatus: int
    orderDescription: str
    codiceArticolo: str
    orderDeadline: datetime
    customerDeadline: datetime
    quantita: int
    phase: List[List[str]]
    phaseStatus: List[List[int]]
    phaseEndTime: List[List[int]]
    phaseLateMotivation: List[List[str]]
    phaseRealTime: List[List[int]]
    entrataCodaFase: List[List[datetime]]
    priority: int
    inCodaAt: List[List[str]]
    inLavorazioneAt: List[List[str]]
    dataInizioLavorazioni: Optional[datetime] = None  

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: int(v.timestamp() * 1000)  # For MongoDB format
        }
