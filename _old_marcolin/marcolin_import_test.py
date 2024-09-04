import pandas as pd
import json
import uuid
import os

def process_and_export_data(file_path, output_directory):
    df = pd.read_excel(file_path)
    processed_data = {
        'Codice': [],
        'Fasi': [],
        'LT Fase Array': [],
        'Tempo Ciclo Array': [],
        'QTA': [],
        'Description': [],
        'JSON': []  # To hold JSON objects
    }
    
    for codice, group in df.groupby('Codice'):
        fasi = group['FaseOperativo'].tolist()
        lt_fase = group['LTFase'].tolist()
        tempo_ciclo = group['Tempo Ciclo'].tolist()
        qta = group['Qta'].iloc[0]
        description = group['Descrizione'].iloc[0] + " " + " ".join(group['Accessori'].dropna().unique())
        
        # Create JSON for the flowchart
        json_object = create_json_for_flowchart(fasi, tempo_ciclo)
        
        processed_data['Codice'].append(codice)
        processed_data['Fasi'].append(fasi)
        processed_data['LT Fase Array'].append(lt_fase)
        processed_data['Tempo Ciclo Array'].append(tempo_ciclo)
        processed_data['QTA'].append(qta)
        processed_data['Description'].append(description)
        processed_data['JSON'].append(json_object)
    
    # Export to Excel
    output_df = pd.DataFrame(processed_data)
    output_df.to_excel(os.path.join(output_directory, 'formatted_output.xlsx'), index=False)
    
    # Save JSON files
    save_json_files(processed_data, output_directory)

def create_json_for_flowchart(phases, cycle_times):
    elements = []
    last_id = None
    for i, (phase, time) in enumerate(zip(phases, cycle_times)):
        current_id = str(uuid.uuid4())
        element = {
            "positionDx": 100 + 200 * i,
            "positionDy": 240,
            "size": {"width": 100.0, "height": 50.0},
            "text": phase,
            "textColor": 4278190080,
            "id": current_id,
            "kind": 0,
            "handlers": [3, 2],
            "handlerSize": 15.0,
            "backgroundColor": 4294967295,
            "borderColor": 4293336434,
            "borderThickness": 3.0,
            "elevation": 4.0,
            "phaseDuration": time
        }
        if last_id:
            element['next'] = [{
                "destElementId": last_id,
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
                    "endArrowPositionY": 0.0
                },
                "pivots": []
            }]
        elements.append(element)
        last_id = current_id  # Update the last_id to the current
    return json.dumps({"elements": elements}, indent=4)

def save_json_files(processed_data, output_directory):
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    # Write each JSON to a separate file
    for codice, json_str in zip(processed_data['Codice'], processed_data['JSON']):
        json_path = os.path.join(output_directory, f'{codice}.json')
        with open(json_path, 'w') as file:
            file.write(json_str)

# Example usage
process_and_export_data("./marcolin.xlsx", './output_jsons')
