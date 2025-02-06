from report_utils import show_family_upload_report
import pandas as pd
import ast
from bson import ObjectId

def custom_list_parser2(cell_value):
    print(cell_value)

    if (isinstance(cell_value, float) or isinstance(cell_value, int)) and not pd.isna(cell_value):
        try:
            cell_value = str(int(float(cell_value)))
        except Exception:
            raise ValueError(f"'codice' non convertibile in stringa, ricevuto: {type(cell_value)}")

    if not isinstance(cell_value, str):
        print("sono qui")
        return []
    
    if cell_value.strip() == '':
        return []

    text = cell_value.strip()

    # Se inizia e finisce con [ ]
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
    elif "," in text:
        items = [x.strip() for x in text.split(",")]
        return items
    else:
        print(text)
        return [text]

def custom_list_parser(cell_value):
    """
    Converte una stringa non valida come [Taglio, Pressopiega] in una lista Python valida: ["Taglio", "Pressopiega"].
    """
    print(cell_value)
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
    """
    Crea un oggetto JSON pronto per il DB partendo dal DataFrame `df`,
    cercando di convertire i valori ricevuti nel tipo desiderato.
    Se non è possibile convertire un valore, solleva ValueError.
    
    Nota: se è presente la colonna "D. fase", per ogni fase verrà aggiunto
    il campo "phaseDescription" (contenuto convertito in stringa) con il testo presente.
    """

    # 1) Tenta di convertire 'codice' e 'descrizione' a stringa.
    try:
        codice = str(codice)
    except Exception:
        raise ValueError(f"'codice' non convertibile in stringa, ricevuto: {type(codice)}")

    try:
        descrizione = str(descrizione)
    except Exception:
        raise ValueError(f"'descrizione' non convertibile in stringa, ricevuto: {type(descrizione)}")

    elements = {}
    connections = {}

    # Verifichiamo se la colonna "D. fase" esiste (opzionale)
    has_phase_description = "D. fase" in df.columns

    # Scorriamo le righe del DataFrame
    for i, row in df.iterrows():

        # 2) Convertiamo "FaseOperativo" a stringa
        try:
            fase_operativo = str(row["FaseOperativo"])
        except Exception:
            raise ValueError(
                f"Riga {i}: 'FaseOperativo' non convertibile in stringa, "
                f"trovato: {row['FaseOperativo']} di tipo {type(row['FaseOperativo'])}"
            )

        # 3) Convertiamo "Tempo Ciclo" a int (tramite float)
        try:
            tempo_ciclo = int(float(row["Tempo Ciclo"]))
        except Exception:
            raise ValueError(
                f"Riga {i}: 'Tempo Ciclo' non convertibile in intero, "
                f"trovato: {row['Tempo Ciclo']} di tipo {type(row['Tempo Ciclo'])}"
            )

        # 4) Convertiamo "ID fase" in int per calcoli di posizione, ma lo useremo
        #    anche come chiave in formato stringa
        try:
            id_fase_int = int(float(row["ID fase"]))
        except Exception:
            raise ValueError(
                f"Riga {i}: 'ID fase' non convertibile in intero, "
                f"trovato: {row['ID fase']} di tipo {type(row['ID fase'])}"
            )

        phase_key = str(id_fase_int)

        # Se la colonna "D. fase" è presente e il valore non è NaN, lo convertiamo in stringa
        phase_desc = None
        if has_phase_description:
            if pd.notna(row["D. fase"]):
                phase_desc = str(row["D. fase"])

        try:
            next_ids_raw = custom_list_parser2(row["ID fase successiva"])
        except Exception as e:
            raise ValueError(
                f"Riga {i}: 'ID fase successiva' non è in un formato gestibile dalla funzione custom_list_parser: {e}."
            )

        try:
            next_phases_raw = custom_list_parser2(row["Fase successiva"])
        except Exception:
            raise ValueError(
                f"Riga {i}: 'Fase successiva' non è in un formato gestibile dalla funzione custom_list_parser."
            )

        # Convertiamo i next_ids e next_phases in stringhe
        next_ids = []
        for val in next_ids_raw:
            try:
                next_ids.append(str(val))
            except Exception:
                raise ValueError(
                    f"Riga {i}: impossibile convertire '{val}' in stringa per 'ID fase successiva'."
                )

        next_phases = []
        for val in next_phases_raw:
            try:
                next_phases.append(str(val))
            except Exception:
                raise ValueError(
                    f"Riga {i}: impossibile convertire '{val}' in stringa per 'Fase successiva'."
                )

        # Creiamo un ObjectId per l'elemento
        phase_id = str(ObjectId())

        # Popoliamo `elements`
        elements[phase_key] = {
            "id": phase_id,
            "positionDx": float(101.2 + 200 * id_fase_int),
            "positionDy": 240.2,
            "size.width": 100.0,
            "size.height": 50.0,
            "text": fase_operativo,
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
            "phaseDuration": tempo_ciclo,
        }
        # Se presente, aggiungiamo il campo "phaseDescription"
        if phase_desc is not None:
            elements[phase_key]["phaseDescription"] = phase_desc

        # Prepara le connessioni (non ancora collegate agli oggetti)
        for nid, nphase in zip(next_ids, next_phases):
            connections.setdefault(phase_key, []).append((str(nid), nphase))

    # Colleghiamo le relazioni "next"
    dashboard_elements = []
    for phase_id, element in elements.items():
        for next_id, _ in connections.get(phase_id, []):
            if next_id in elements:
                element["next"].append({
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
                })
        dashboard_elements.append(element)

    # Costruiamo il JSON finale
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
