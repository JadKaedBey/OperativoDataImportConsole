from pydantic import BaseModel, ValidationError, Field

class codiceArticolo(BaseModel):
    codice_articolo: str = Field(alias="Codice Articolo")
    descrizione_articolo: str = Field(alias="Descrizione articolo")
    famiglia_di_prodotto: str = Field(alias="Famiglia di prodotto")
    fase_operativo: str = Field(alias="Fase Operativo")
    tempo_ciclo: float = Field(alias="Tempo Ciclo")
    info_lavorazione: str = Field(alias="Info lavorazione")