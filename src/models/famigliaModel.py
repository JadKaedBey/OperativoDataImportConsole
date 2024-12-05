from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from bson import ObjectId  

# Helper model for ArrowParams
class ArrowParams(BaseModel):
    thickness: float
    headRadius: float
    tailLength: float
    color: int
    style: int
    tension: float
    startArrowPositionX: float
    startArrowPositionY: float
    endArrowPositionX: float
    endArrowPositionY: float

# Helper model for NextElement
class NextElement(BaseModel):
    destElementId: str
    arrowParams: ArrowParams
    pivots: List[Any] = []

# Model for DashboardElement
class DashboardElement(BaseModel):
    positionDx: float
    positionDy: float
    size_width: float = Field(100, alias="size.width")
    size_height: float = Field(50, alias="size.height")
    text: str
    textColor: int
    fontFamily: Optional[str]
    textSize: float
    textIsBold: bool
    id: str
    kind: int
    handlers: List[int]
    handlerSize: float
    backgroundColor: int
    borderColor: int
    borderThickness: float
    elevation: float
    next: List[NextElement]
    phaseDuration: int
    phaseTargetQueue: Optional[int]

# Model for GridBackgroundParams
class GridBackgroundParams(BaseModel):
    offset_dx: float = Field(..., alias="offset.dx")
    offset_dy: float = Field(..., alias="offset.dy")
    scale: float
    gridSquare: float
    gridThickness: float
    secondarySquareStep: int
    backgroundColor: int
    gridColor: int

# Model for Dashboard
class Dashboard(BaseModel):
    elements: List[DashboardElement]
    dashboardSizeWidth: float
    dashboardSizeHeight: float
    gridBackgroundParams: GridBackgroundParams
    blockDefaultZoomGestures: bool
    minimumZoomFactor: float
    arrowStyle: int

# Model for Element inside Catalog
class CatalogElement(BaseModel):
    pId: str
    property: str
    duration: int

# Model for Catalog
class Catalog(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    prodId: str
    prodotto: str
    descrizione: str
    famiglia: str
    elements: List[CatalogElement]

# Main Family Model
class FamilyModel(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    titolo: str
    descrizione: str
    image: str
    dashboard: Dashboard
    catalogo: List[Catalog]
