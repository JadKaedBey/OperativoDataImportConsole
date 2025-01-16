from report_utils import show_family_upload_report
import pandas as pd
import ast
from bson import ObjectId

def custom_list_parser(cell_value):
    """
    Converte una stringa non valida come [Taglio, Pressopiega] in una lista Python valida: ["Taglio", "Pressopiega"].
    """
    if not isinstance(cell_value, str):
        return []
    text = cell_value.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
        items = [x.strip() for x in text.split(",")]
        items_quoted = [f'"{x}"' for x in items]
        new_text = "[" + ", ".join(items_quoted) + "]"
        try:
            return ast.literal_eval(new_text)
        except Exception as e:
            print(f"Error parsing cell: {cell_value} => {new_text}, {e}")
            return []
    else:
        return []

def create_json_for_flowchart(df, codice, descrizione):
    elements = {}
    connections = {}

    for _, row in df.iterrows():
        phase_id = str(ObjectId())
        phase_key = str(row["ID fase"])
        elements[phase_key] = {
            "id": phase_id,
            "positionDx": 101.2 + 200 * int(row["ID fase"]),
            "positionDy": 240.2,
            "size.width": 100.0,
            "size.height": 50.0,
            "text": row["FaseOperativo"],
            "textColor": 4278190080,
            "fontFamily": None,
            "textSize": 12.0,
            "textIsBold": False,
            "kind": 0,
            "handlers": [3, 2],
            "handlerSize": 15.0,
            "backgroundColor": 4294967295,
            "borderColor": 4293336434,
            "borderThickness": 3.0,
            "elevation": 4.0,
            "next": [],
            "phaseDuration": row["Tempo Ciclo"],
            "phaseTargetQueue": 0,
        }

        next_ids = custom_list_parser(row["ID fase successiva"])
        next_phases = custom_list_parser(row["Fase successiva"])
        for nid, nphase in zip(next_ids, next_phases):
            connections.setdefault(phase_key, []).append((str(nid), nphase))

    dashboard_elements = []
    for phase_id, element in elements.items():
        for next_id, _ in connections.get(phase_id, []):
            if next_id in elements:
                element["next"].append(
                    {
                        "destElementId": elements[next_id]["id"],
                        "arrowParams": {
                            "thickness": 1.7,
                            "headRadius": 6.0,
                            "tailLength": 25.0,
                            "color": 4278190080,
                            "style": 0,
                            "tension": 1.0,
                            "startArrowPositionX": 1.0,
                            "startArrowPositionY": 0.0,
                            "endArrowPositionX": -1.0,
                            "endArrowPositionY": 0.0,
                        },
                        "pivots": [],
                    }
                )
        dashboard_elements.append(element)

    json_output = {
        "_id": ObjectId(),
        "titolo": codice,
        "descrizione": descrizione,
        "image": "https://upload.wikimedia.org/wikipedia/commons/1/14/No_Image_Available.jpg",
        "dashboard": {
            "elements": dashboard_elements,
            "dashboardSizeWidth": 1279.0,
            "dashboardSizeHeight": 566.72,
            "gridBackgroundParams": {
                "offset.dx": -580.4256299112267,
                "offset.dy": -150.19796474249733,
                "scale": 1.0,
                "gridSquare": 20.0,
                "gridThickness": 0.7,
                "secondarySquareStep": 5,
                "backgroundColor": 4294967295,
                "gridColor": 520093696,
            },
            "blockDefaultZoomGestures": False,
            "minimumZoomFactor": 0.25,
            "arrowStyle": 0,
        },
    }

    return json_output

def safe_parse_literal(cell):
    try:
        if isinstance(cell, str):
            cell = cell.strip()
            if cell.startswith("[") and cell.endswith("]"):
                parsed_list = ast.literal_eval(cell)
                return [
                    (int(item) if isinstance(item, (int, str)) and str(item).isdigit() else item)
                    for item in parsed_list
                ]
            elif "," in cell:
                return [
                    int(item.strip()) if item.strip().isdigit() else item.strip()
                    for item in cell.split(",")
                ]
            elif cell.isdigit():
                return [int(cell)]
            else:
                return [cell]
        elif isinstance(cell, (int, float)):
            return [cell]
        else:
            return [cell]
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing cell: {repr(cell)} - {e}")
        return [cell]