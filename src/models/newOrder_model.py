from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class PhaseModel(BaseModel):
    phaseId: str
    phaseName: str
    phaseStatus: int
    phaseRealTime: int  # Tempo reale in minuti
    cycleTime: int  # Tempo stimato in minuti
    queueInsertDate: datetime  # Data di entrata in coda
    queueRealInsertDate: Optional[datetime] = None  # Data reale di entrata in coda
    finishDate: datetime  # Data stimata di fine
    realFinishDate: Optional[datetime] = None  # Data reale di fine
    phaseLateMotivation: str
    operators: List[str] = []  # Operatori assegnati alla fase
    inCodaAt: List[str] = []  # Informazioni su chi/come la fase è in coda
    inLavorazioneAt: str = ""  # Informazioni su chi/come la fase è in lavorazione
    previousPhases: List[str] = []  # ID delle fasi precedenti
    nextPhases: List[str] = []  # ID delle fasi successive


class NewOrderModel(BaseModel):
    orderId: str
    orderInsertDate: datetime = Field(default_factory=datetime.now)
    orderStartDate: datetime
    orderDeadline: datetime
    customerDeadline: datetime
    orderDescription: str
    codiceArticolo: str
    famigliaDiProdotto: str
    orderStatus: int = 0  # 0 = Bozza/In Attesa
    priority: int = 0  # Priorità dell'ordine
    quantity: int
    realOrderFinishDate: Optional[datetime] = None  # Data reale di completamento ordine
    phases: List[PhaseModel] = []  # Lista di oggetti Phase
    startPhasesList: List[str] = []  # ID delle fasi iniziali
    selectedPhase: Optional[str] = None  # ID della fase selezionata (se applicabile)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: int(v.timestamp() * 1000),  # Per MongoDB
        }
