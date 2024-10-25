# EXPORT Functions
import numpy as np
import pandas as pd
import datetime
import re
import ast
from bson import ObjectId
import os


def order_status_mapper(status):
    try:
        if isinstance(status, list):
            status = status[0] if status else None
        return {0: "Non iniziato", 1: "In corso", 4: "Completato"}.get(int(status), str(status))
    except (ValueError, TypeError):
        print(f"Invalid order status: {status}")
        return status

# Function to map phaseStatus (handles lists)
def phase_status_mapper(status_list):
    try:
        if isinstance(status_list, list):
            return [
                phase_status_mapper(item) if isinstance(item, list) else
                {0: "attesa di materiale", 1: "Non iniziato", 2: "In corso", 3: "In ritardo", 4: "Completato"}.get(int(item), str(item))
                for item in status_list
            ]
        else:
            return {0: "attesa di materiale", 1: "Non iniziato", 2: "In corso", 3: "In ritardo", 4: "Completato"}.get(int(status_list), str(status_list))
    except (ValueError, TypeError):
        print(f"Invalid phase status: {status_list}")
        return status_list

column_mapping = {
    'orderId': 'Order ID',
    'orderInsertDate': 'Order Insert Date',
    'codiceArticolo': 'Codice Articolo',
    'orderDescription': 'Order Description',
    'quantita': 'Quantità',
    'orderStatus': 'Order Status',
    'priority': 'Priorità',
    'inCodaAt': 'In Coda At',
    'orderDeadline': 'Order Deadline',
    'customerDeadline': 'Customer Deadline',
    'orderStartDate': 'Order Start Date',
    'dataInizioLavorazioni': 'Work Start Date',
    'phase': 'Fase',
    'phaseStatus': 'Stato Fase',
    'assignedOperator': 'Operatore Assegnato',
    'phaseLateMotivation': 'Motivazione Ritardo Fase',
    'phaseEndTime': 'Lead Time Fase',
    'phaseRealTime': 'Tempo Ciclo Performato',
    'entrataCodaFase': 'Entrata Coda Fase',
    'Sequenza': 'Sequenza' 
}

# Function to fetch machine names
def fetch_in_coda_at_names(client):
    id_to_name = {}
    for document in client['process_db']['macchinari'].find({}):
        id_to_name[str(document['_id'])] = document['name']

    print(id_to_name)
    return id_to_name

def fetch_in_lavorazione_at_names(client):
    uuid_to_name = {}
    
    # Iterate over each document in the 'macchinari' collection
    for document in client['process_db']['macchinari'].find({}):
        # Ensure the 'tablet' array exists in the document
        if 'tablet' in document and isinstance(document['tablet'], list):
            for uuid in document['tablet']:
                # Store each UUID with the corresponding machine name
                uuid_to_name[str(uuid)] = document['name']
    
    print(uuid_to_name)  # To verify the mappings
    return uuid_to_name

def map_in_coda_at(value, id_to_name):
    """Map ObjectId strings to machine names."""
    try:
        if isinstance(value, list):
            # Process each value in the list
            return [map_in_coda_at(v, id_to_name) for v in value]
        elif isinstance(value, str):
            # Extract ObjectId string if in format ObjectId("...")
            match = re.search(r'ObjectId\("([a-fA-F0-9]+)"\)', value)
            if match:
                object_id_str = match.group(1)  # Extract the ObjectId part
                return id_to_name.get(object_id_str, value)  # Map to name or return the original string
            return id_to_name.get(value, value)  # If not formatted, try normal mapping
        elif isinstance(value, dict):  # For MongoDB references stored as dict
            return id_to_name.get(value.get('$oid', ''), str(value))
        elif isinstance(value, ObjectId):
            return id_to_name.get(str(value), str(value))
        elif pd.notna(value):
            return id_to_name.get(str(value), str(value))
        else:
            return value
    except Exception as e:
        print(f"Error mapping value {value}: {e}")
        return value
    
def calculate_in_coda(df):
            print("Assigning in coda")
            in_coda_values = []
            for i in range(len(df)):
                if i == 0:
                    in_coda_values.append("")  # La prima riga non ha una riga precedente
                else:
                    current_row = df.iloc[i]
                    prev_row = df.iloc[i - 1]
                    #print("CURR")
                    #print(current_row['orderId'])
                    current_row_status = current_row['phaseStatus']
                    print(current_row_status)
                    print(type(current_row_status))
                    prev_row_status = prev_row['phaseStatus']
                    # Convert phaseStatus to the largest integer if it contains multiple values (Diramazione)
                    def parse_phase_status(status):
                        if isinstance(status, str):
                            # Split string by commas and convert each part to an integer
                            parts = [int(x.strip()) for x in status.split(',') if x.strip().isdigit()]
                            return max(parts) if parts else 0
                        elif isinstance(status, list):
                            # Convert each element to an integer and take the max
                            return max(int(x) for x in status if isinstance(x, int))
                        else:
                            return int(status)
                        
                    current_row_status = parse_phase_status(current_row_status)
                    prev_row_status = parse_phase_status(prev_row_status)
                    current_row_entrata = current_row['entrataCodaFase']
                    prev_row_entrata = prev_row['entrataCodaFase']
                    
                    # Condizioni per determinare il valore "in coda"
                    if (
                        current_row_status < 4
                        and prev_row_status == 4
                        and current_row_entrata > prev_row_entrata
                    ) or (
                        current_row_status < 4
                        and current_row_entrata < prev_row_entrata
                    ):
                        in_coda_values.append("in coda")
                    else:
                        in_coda_values.append("")
            return in_coda_values
    
def parse_value(val, default=['']):
    """General value parser to handle None, NaN, string, and list/array types."""
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        if isinstance(val, str):
            try:
                parsed_val = ast.literal_eval(val)
                if not isinstance(parsed_val, list):
                    parsed_val = [parsed_val]
                return parsed_val
            except Exception:
                return default
        if isinstance(val, (list, np.ndarray)):
            return list(val) if isinstance(val, np.ndarray) else val
        return [val]
    except Exception:
        print("Error while parsing")
def map_in_coda_at_value(val, id_to_name):
    """Map 'inCodaAt' values during parsing."""
    return map_in_coda_at(val, id_to_name)

def map_in_lavorazione_at_value(val, uuid_to_name):
    """
    Map 'inLavorazioneAt' values (which could be UUIDs) to machine names.
    """
    if isinstance(val, list):
        # If the value is a list, apply the mapping to each item in the list
        return [map_in_lavorazione_at_value(v, uuid_to_name) for v in val]
    elif isinstance(val, str) and '-' in val:  # Check if the value is a UUID-like string
        # Return the mapped name from the uuid_to_name dictionary, or the original value if no match
        return uuid_to_name.get(val, val)
    elif isinstance(val, str):
        return uuid_to_name.get(val, val)
    return val  # Return the value as is if it doesn't match the expected types

def parse_entrata_coda_fase(val):
    """Handle 'entrataCodaFase' separately due to datetime parsing."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ['']
    if isinstance(val, str):
        try:
            entrata_coda_fase_str = val.replace('datetime.datetime', 'dt')
            parsed_val = eval(entrata_coda_fase_str, {"dt": datetime})
            return parsed_val if isinstance(parsed_val, list) else [parsed_val]
        except Exception:
            print("Exception while parsing dataEntrataCoda")
            return ['']
    return parse_value(val)

def create_new_row(row, phases, parsed_columns, columns_to_parse):
    """Create and return a new expanded row for each phase."""
    new_rows = []
    num_phases = len(phases)

    # Ensure all columns have the same length as 'phases'
    for col in columns_to_parse + ['entrataCodaFase']:
        col_values = parsed_columns[col]
        if len(col_values) < num_phases:
            # If column has fewer values, pad with default values (e.g., empty string)
            parsed_columns[col] = col_values + [''] * (num_phases - len(col_values))

    # Now create the new rows
    for i in range(num_phases):
        new_row = row.copy()
        
        # Handle 'phase' column: strip brackets and join list elements as a string
        phase_value = phases[i]
        if isinstance(phase_value, list):
            phase_value = ', '.join([str(v) for v in phase_value if v])
        
        for col in columns_to_parse + ['entrataCodaFase']:
            value = parsed_columns[col][i]
            
            # Join list values into a string to remove brackets and quotes
            if isinstance(value, list):
                value = ', '.join([str(v) for v in value if v])
            new_row['phase'] = phase_value 

            if col == 'entrataCodaFase' and isinstance(value, list):
                value = value[0] if value else ''
            if isinstance(value, datetime.datetime):
                value = value.strftime('%Y-%m-%d %H:%M')
            new_row[col] = value
        new_rows.append(new_row)
    
    return new_rows

def format_queue_entry_time(value):
    """Format 'Queue Entry Time' column."""
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y-%m-%d %H:%M')
    try:
        dt_value = pd.to_datetime(value)
        return dt_value.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return value

def parse_columns(row, columns_to_parse, id_to_name):
    """Parse specific columns and handle mappings."""
    print("Parsing columns")
    parsed_columns = {}
    for col in columns_to_parse:
        val = row.get(col)
        parsed_columns[col] = parse_value(val)
        
        # Handle specific column mappings
        if col == 'inCodaAt':
            parsed_columns[col] = [map_in_coda_at_value(v, id_to_name) for v in parsed_columns[col]]
        elif col == 'entrataCodaFase':  
            parsed_columns[col] = parse_entrata_coda_fase(val)
        elif col == 'inLavorazioneAt':
            parsed_columns[col] = [map_in_lavorazione_at_value(v, id_to_name) for v in parsed_columns[col]]
            
    return parsed_columns


# def export_data(self, db_name, collection_name):
#         print(f"Attempting to export data from {db_name}.{collection_name}...")    
#         try:
#             # Connect to MongoDB and fetch data
#             db = client[db_name]
#             collection = db[collection_name]
#             cursor = collection.find({})
#             data = list(cursor)

#             if data:
#                 df = pd.DataFrame(data)
#                 if '_id' in df.columns:
#                     df.drop('_id', axis=1, inplace=True)

#                 print("Available columns in the data:")
#                 print(df.columns.tolist())

#                 # Fetch machine names (map ObjectId to machine name)
#                 id_to_name = fetch_in_coda_at_names()
#                 # Fetch the UUID-to-name mapping
#                 uuid_to_name = fetch_in_lavorazione_at_names()

#                 # Ensure all required columns are present
#                 required_columns = ['phase', 'phaseStatus', 'assignedOperator', 'phaseLateMotivation', 'phaseEndTime', 'phaseRealTime', 'entrataCodaFase']
#                 missing_columns = [col for col in required_columns if col not in df.columns]
#                 if missing_columns:
#                     QMessageBox.critical(self, "Export Failed", f"Missing required columns: {', '.join(missing_columns)}")
#                     return

#                 # List of columns to parse
#                 columns_to_parse = ['phaseStatus', 'assignedOperator', 'phaseLateMotivation', 'phaseEndTime', 'phaseRealTime', 'inCodaAt', 'inLavorazioneAt', 'entrataCodaFase']

#                 # Store all expanded rows
#                 all_expanded_rows = []

#                 # Iterate over each row in the DataFrame
#                 for idx, row in df.iterrows():
#                     phases = parse_value(row['phase'])
#                     if not phases:
#                         print(f"Skipping row {idx}: 'phase' value is invalid.")
#                         continue

#                     # Parse columns
#                     parsed_columns = parse_columns(row, columns_to_parse, id_to_name)

#                     parsed_columns['inCodaAt'] = [map_in_coda_at_value(v, id_to_name) for v in parsed_columns['inCodaAt']]
                    
#                     if 'inLavorazioneAt' in parsed_columns:
#                         parsed_columns['inLavorazioneAt'] = [map_in_lavorazione_at_value(v, uuid_to_name) for v in parsed_columns['inLavorazioneAt']]
                        
#                     # Create new expanded rows based on phases
#                     new_rows = create_new_row(row, phases, parsed_columns, columns_to_parse)
#                     all_expanded_rows.extend(new_rows)

#                 if all_expanded_rows:
#                     final_expanded_df = pd.DataFrame(all_expanded_rows)

#                     # Add sequence number if needed
#                     if 'orderId' in final_expanded_df.columns:
#                         final_expanded_df['Sequenza'] = final_expanded_df.groupby('orderId').cumcount() + 1
#                     else:
#                         final_expanded_df['Sequenza'] = range(1, len(final_expanded_df) + 1)

#                     # Can only perform here since later the phaseStatis gets mapped to Strings
#                     final_expanded_df['in coda'] = calculate_in_coda(final_expanded_df)
                    
#                     # Map status columns
#                     if 'orderStatus' in final_expanded_df.columns:
#                         final_expanded_df['orderStatus'] = final_expanded_df['orderStatus'].apply(order_status_mapper)
#                     if 'phaseStatus' in final_expanded_df.columns:
#                         final_expanded_df['phaseStatus'] = final_expanded_df['phaseStatus'].apply(phase_status_mapper)

#                     # Rename columns
#                     final_expanded_df.rename(columns=column_mapping, inplace=True)

#                     # Format 'Queue Entry Time' column
#                     if 'Queue Entry Time' in final_expanded_df.columns:
#                         final_expanded_df['Queue Entry Time'] = final_expanded_df['Queue Entry Time'].apply(format_queue_entry_time)

#                     # Convert column to integers, coercing errors to NaN and filling NaN with 0
#                     final_expanded_df['Quantità'] = pd.to_numeric(final_expanded_df['Quantità'], errors='coerce').fillna(0).astype(int)
#                     final_expanded_df['Lead Time Fase'] = pd.to_numeric(final_expanded_df['Lead Time Fase'], errors='coerce').fillna(0).astype(int)
#                     final_expanded_df['Tempo Ciclo Performato'] = pd.to_numeric(final_expanded_df['Tempo Ciclo Performato'], errors='coerce').fillna(0).astype(int)
#                     final_expanded_df['Priorità'] = pd.to_numeric(final_expanded_df['Priorità'], errors='coerce').fillna(0).astype(int)
#                     final_expanded_df['Sequenza'] = pd.to_numeric(final_expanded_df['Sequenza'], errors='coerce').fillna(0).astype(int)

#                     # Save the DataFrame to Excel
#                     options = QFileDialog.Options()
#                     file_path, _ = QFileDialog.getSaveFileName(self, "Save Excel File", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
#                     if file_path:
#                         final_expanded_df.to_excel(file_path, index=False)
#                         QMessageBox.information(self, "Export Successful", "Data has been successfully exported to Excel.")
#                     else:
#                         print("No file path was selected.")
#                 else:
#                     QMessageBox.information(self, "No Data", "No rows were expanded. The output file was not created.")
#             else:
#                 QMessageBox.information(self, "No Data", "There is no data to export.")
#         except Exception as e:
#             print(f"Error exporting data: {e}")
#             QMessageBox.critical(self, "Export Failed", f"Failed to export data: {e}")