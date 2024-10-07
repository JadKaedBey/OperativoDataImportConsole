import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QLabel, QTableWidget, \
    QTableWidgetItem, QFileDialog, QMessageBox, QLineEdit, QDialog, QGridLayout, QComboBox, QDialogButtonBox, QHBoxLayout
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
import pandas as pd
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from math import floor
from PIL import Image, ImageDraw, ImageFont
import qrcode
import os
import datetime
from bson import ObjectId
from dotenv import load_dotenv
from datetime import timedelta
from functools import reduce

queued_df = pd.DataFrame()
client = None  # Initialize MongoDB client variable
try:
    login_logo = Image.open(r".\img\OPERATIVO_L_Main_Color.png")
except FileNotFoundError:
    print("Image not found. Continuing with the rest of the script.")
    login_logo = None
        
logo_width = 1654
logo_length = 1246

original_logo = login_logo

window_width = 1600
window_height = 1600

load_dotenv()  # Load environment variables from .env file

def connect_to_mongodb(username, password):
    global client
    print(f"Attempting to connect with username: {username} and password: {password}")
    try:
        if username == "1" and password == "1":
            client = MongoClient(os.getenv("IMPORT_TEST_URI"))
        elif username == "amade" and password == "amade":
            client = MongoClient(os.getenv("AMADE_URI"))
        elif username == "marcolin" and password == "marcolin":
            client = MongoClient(os.getenv("MARCOLIN_URI"))
        elif username == "demo" and password == "demo":
            client = MongoClient(os.getenv("DEMO_URI"))
        elif username == "demoveloce" and password == "demoveloce":
            client = MongoClient(os.getenv("DEMO_VELOCE_URI"))
        else:
            print("Invalid credentials")
            return False
        print("Connected to MongoDB")
        return True
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return False

# Getters from DB

def fetch_settings():
    global client
    db = client['azienda']
    collection = db['settings']
    
    # Fetch the settings document
    settings = collection.find_one()
    
    if not settings:
        raise ValueError("No settings document found")
    
    return settings

def get_phase_end_times(phases, codiceArticolo):
    # Initialize the list to store phase end times
    end_times = []
    
    # Access the database and collection
    process_db = client['process_db']
    famiglie_di_prodotto = process_db['famiglie_di_prodotto']
    
    # Find the correct family document based on codiceArticolo
    family = famiglie_di_prodotto.find_one({"catalogo.prodId": codiceArticolo})
    
    # If the family document is found
    if family:
        for phase in phases:
            # Loop through each element in the family 'dashboard' to find the phase by name
            for element in family.get('dashboard', {}).get('elements', []):
                if element.get('text') == phase:
                    # Get the phase duration
                    phase_duration = element.get('phaseDuration', 0)
                    
                    # Check if phase_duration is a dictionary and has '$numberInt', else use it as-is
                    if isinstance(phase_duration, dict):
                        phase_duration = phase_duration.get('$numberInt', 0)
                    
                    end_times.append(int(phase_duration))
                    break
            else:
                # If the phase is not found, append 0 as the duration
                end_times.append(0)
    else:
        # If the family or article isn't found, return 0 for each phase
        end_times = [0] * len(phases)
    
    return end_times

def get_phase_queue_times(phases, codiceArticolo):
    # Initialize the list to store phase end times
    queue_times = []
    
    # Access the database and collection
    process_db = client['process_db']
    famiglie_di_prodotto = process_db['famiglie_di_prodotto']
    
    # Find the correct family document based on codiceArticolo
    family = famiglie_di_prodotto.find_one({"catalogo.prodId": codiceArticolo})
    
    # If the family document is found
    if family:
        for phase in phases:
            # Loop through each element in the family 'dashboard' to find the phase by name
            for element in family.get('dashboard', {}).get('elements', []):
                if element.get('text') == phase:
                    # Get the phase duration
                    phase_duration = element.get('phaseTargetQueue', 0)
                    
                    # Check if phase_duration is a dictionary and has '$numberInt', else use it as-is
                    if isinstance(phase_duration, dict):
                        phase_duration = phase_duration.get('$numberInt', 0)
                    
                    queue_times.append(int(phase_duration))
                    break
            else:
                # If the phase is not found, append 0 as the duration
                queue_times.append(0)
    else:
        # If the family or article isn't found, return 0 for each phase
        queue_times = [0] * len(phases)
    
    return queue_times

# Phase Calculation functions:

def get_queue_times(phases, codiceArticolo):
    process_db = client['process_db']
    famiglie_di_prodotto = process_db['famiglie_di_prodotto']
    
    family = famiglie_di_prodotto.find_one({"catalogo.prodId": codiceArticolo})
    queues = {}
    
    if family:
        for phase in phases:
            # Fetch queue time for each phase from the family dashboard
            for element in family.get('dashboard', {}).get('elements', []):
                if element.get('text') == phase:
                    queues[phase] = int(element.get('phaseTargetQueue', 0))  
                    break
    return queues

def check_family_existance_db(familyName):
    process_db = client['process_db']
    famiglie_di_prodotto = process_db['famiglie_di_prodotto']
    
    family = famiglie_di_prodotto.find_one({"titolo": familyName})
    
    if family:
        return True

def get_phase_durations(phases, codiceArticolo):
    process_db = client['process_db']
    famiglie_di_prodotto = process_db['famiglie_di_prodotto']
    
    family = famiglie_di_prodotto.find_one({"catalogo.prodId": codiceArticolo})
    durations = {}
    
    if family:
        for phase in phases:
            # Fetch duration time for each phase from the family dashboard
            for element in family.get('dashboard', {}).get('elements', []):
                if element.get('text') == phase:
                    durations[phase] = int(element.get('phaseDuration', 0)) 
                    break
    return durations

def fetch_flowchart_data(codiceArticolo):
    global client
    db = client['process_db']
    collection = db['famiglie_di_prodotto']

    # Fetch the family document from the collection
    family = collection.find_one({"catalogo.prodId": codiceArticolo})

    print('Found Family:', family['titolo'])
    
    if not family or 'dashboard' not in family:
        raise ValueError("No valid dashboard found for the given family ID.")
    
    dashboard = family['dashboard']
    graph = {}
    reverse_graph = {}
    durations = {}
    queues = {}
    indegree = {}

    elements = dashboard.get('elements', [])
    for node in elements:
        node_id = node['id']
        duration = node.get('phaseDuration', 0)
        queue = node.get('phaseTargetQueue', duration)

        # Initialize the node in the graph
        durations[node_id] = duration
        queues[node_id] = queue
        graph[node_id] = []

        # Ensure every node is initialized in the reverse_graph (even without incoming edges)
        if node_id not in reverse_graph:
            reverse_graph[node_id] = []

        # Process connections (outgoing edges)
        for next_node in node.get('next', []):
            dest_id = next_node['destElementId']
            graph[node_id].append(dest_id)

            # Increment the indegree for reverse graph construction
            indegree[dest_id] = indegree.get(dest_id, 0) + 1

            # Add to reverse graph (dest_id -> node_id)
            if dest_id not in reverse_graph:
                reverse_graph[dest_id] = []
            reverse_graph[dest_id].append(node_id)

    # Debugging print statements to verify structures
    print("Graph:", graph)
    print("Reverse Graph:", reverse_graph)
    print("Durations:", durations)
    print("Queues:", queues)
    print("Indegree:", indegree)

    return graph, reverse_graph, durations, queues, indegree, dashboard

def calculate_phase_dates(end_date, phases, quantity, settings, codiceArticolo):
    
    settings = fetch_settings()
    
    print('Calculating Phase Dates')
    open_time = settings.get('orariAzienda', {}).get('inizio', {'ore': 8, 'minuti': 0})
    close_time = settings.get('orariAzienda', {}).get('fine', {'ore': 18, 'minuti': 0})
    holiday_list = settings.get('ferieAziendali', [])
    pausa_pranzo = settings.get('pausaPranzo', {'inizio': {'ore': 12, 'minuti': 0}, 'fine': {'ore': 15, 'minuti': 0}})

    print('Open Time:', open_time)
    print('Close Time:', close_time)
    print('Holiday Time:', holiday_list)
    print('Pausa Time:', pausa_pranzo)
    
    phase_durations = get_phase_end_times(phases, codiceArticolo)
    
    print('Got Phase durations (Tempo ciclo):', phase_durations)
    
    entrata_coda_fase = []
    
    for i, phase in enumerate(phases):
        # Calculate phase duration based on quantity
        duration = phase_durations[i] * quantity
        
        graph, reverse_graph, durations, queues, indegree, dashboard = fetch_flowchart_data(codiceArticolo)
    
        print('checking end_date type', type(end_date))
        # Calculate start date for the phase, taking into account work hours, breaks, and holidays
        start_date = find_start_date_of_phase(
            end_date, 
            phase, #target phase
            quantity, 
            open_time, 
            close_time, 
            holiday_list, 
            pausa_pranzo, 
            graph,
            reverse_graph, 
            queues, 
            dashboard,
            durations
        )
        print("Found start_date of equal to", phase, start_date)
        
        if start_date:
            # Append the queue or cycle start date as a single-layer array
            if start_date[0][0] < start_date[1][0]:
                entrata_coda_fase.append(start_date[0][0])  # Queue start is earlier
            else:
                entrata_coda_fase.append(start_date[1][0])  # Cycle start is earlier
        else:
            # Default handling if None is returned
            entrata_coda_fase.append(None)
        
        
        
        # Update end_date to the start date of the current phase for the next iteration
        end_date = start_date[0][0] if start_date else end_date
    
    print('Entrata coda phase:', entrata_coda_fase)
    return entrata_coda_fase

def get_graph_layers_from_end(graph, reverse_graph):
    local_reverse_graph = reverse_graph.copy()
    layers = []
    visited = set()
    queue = []

    # Identify all end nodes (nodes with no outgoing edges)
    for node_id, edges in graph.items():
        if not edges:
            queue.append(node_id)
            visited.add(node_id)

    # Start from end nodes and traverse backwards
    while queue:
        current_layer = []
        layer_size = len(queue)

        for _ in range(layer_size):
            node_id = queue.pop(0)
            current_layer.append(node_id)

            # Traverse to all nodes pointing to the current node (predecessors)
            if node_id in local_reverse_graph:
                for predecessor in local_reverse_graph[node_id]:
                    if predecessor not in visited:
                        queue.append(predecessor)
                        visited.add(predecessor)

        layers.insert(0, current_layer)

    return layers

def find_start_date_of_phase(end_date, target_phase, quantity, open_time, close_time, holiday_list, pausa_pranzo, graph, reverse_graph, queues, dashboard, durations, duration=-1):
    """
    Find the start date of a phase by traversing backwards from the end nodes.
    """
    print('Trying to find Start date of phase for', target_phase)
    
    # Create a mapping of phase names to node IDs
    phase_name_to_id = {node['text']: node['id'] for node in dashboard.get('elements', [])}
    
    # Check if the target_phase exists in the mapping
    if target_phase not in phase_name_to_id:
        raise ValueError(f"Target phase '{target_phase}' not found in the dashboard.")
    
    # Get the node ID corresponding to the target phase
    target_phase_id = phase_name_to_id[target_phase]
    print(f"Target phase '{target_phase}' corresponds to node ID: {target_phase_id}")
    
    # Function to traverse the graph backwards from the end nodes to find the target phase
    def traverse_backwards(current_id):
        print(f"Traversing node: {current_id}, looking for target phase: {target_phase_id}")
        if current_id == target_phase_id:
            print(f"Found target phase: {current_id}")    
            return [queues[current_id], duration if duration >= 0 else durations[current_id] * quantity]
        
        if current_id not in reverse_graph:
            print('Target phase not in reverse_graph: returning None', current_id)
            return None
        
        for prev_id in reverse_graph[current_id]:
            print(f"Traversing to previous node: {prev_id}")
            result = traverse_backwards(prev_id)
            if result:
                print(f"Found path from {current_id} to {prev_id}: {result}")
                return [result[0] + queues[current_id], result[1] + (duration if duration >= 0 else durations[current_id] * quantity)]
            
        print(f"No valid path found for node: {current_id}")
        return None

    # Calculate time durations
    pausa_duration = (datetime.timedelta(hours=pausa_pranzo['fine']['ore'], minutes=pausa_pranzo['fine']['minuti']) -
                      datetime.timedelta(hours=pausa_pranzo['inizio']['ore'], minutes=pausa_pranzo['inizio']['minuti']))
    
    print('Found pausa_duration equal to', pausa_duration)
    
    minutes_in_day = (datetime.timedelta(hours=close_time['ore'], minutes=close_time['minuti']) -
                      datetime.timedelta(hours=open_time['ore'], minutes=open_time['minuti']) -
                      pausa_duration).total_seconds() / 60
    
    print('Found minutes_in_day equal to', minutes_in_day)
    
    print("Check the structure of reverse_graph ", reverse_graph)  
    
    end_nodes = [node_id for node_id, edges in graph.items() if not edges]
    
    print('End nodes: ', end_nodes)
    
    def adjust_to_work_hours(possible_date):
        start_work = datetime.time(open_time['ore'], open_time['minuti'])
        end_work = datetime.time(close_time['ore'], close_time['minuti'])
        lunch_start = datetime.time(pausa_pranzo['inizio']['ore'], pausa_pranzo['inizio']['minuti'])
        lunch_end = datetime.time(pausa_pranzo['fine']['ore'], pausa_pranzo['fine']['minuti'])
        
        print('Company Hours:')
        print(start_work)
        print(end_work)
        print(lunch_start)
        print(lunch_end)

        # Check for holidays
        if any(holiday['inizio'].date() <= possible_date.date() <= holiday['fine'].date() for holiday in holiday_list):
            possible_date -= timedelta(days=1)
            possible_date = possible_date.replace(hour=start_work.hour, minute=start_work.minute)
            return adjust_to_work_hours(possible_date)

        # Adjust time if before or after working hours
        if possible_date.time() < start_work:
            possible_date = possible_date.replace(hour=start_work.hour, minute=start_work.minute)
        elif possible_date.time() > end_work:
            possible_date = possible_date + timedelta(days=1)
            possible_date = possible_date.replace(hour=start_work.hour, minute=start_work.minute)

        # Adjust if within lunch break
        if lunch_start <= possible_date.time() <= lunch_end:
            possible_date = possible_date.replace(hour=lunch_end.hour, minute=lunch_end.minute)
        
        return possible_date

    # Calculate time respecting working hours and holidays
    def calculate_possible_date(total_minutes, end_date):
        print('Calculating possible date')
        possible_date = end_date - timedelta(days=total_minutes // minutes_in_day, minutes=total_minutes % minutes_in_day)
        possible_date = adjust_to_work_hours(possible_date)
        
        # Check for weekends and holidays
        while possible_date.weekday() in [5, 6]:  # Saturday (5) or Sunday (6)
            possible_date -= timedelta(days=2)
            possible_date = adjust_to_work_hours(possible_date)
            
        print('Possible date found: ', possible_date)
        return possible_date

    for end_node in end_nodes:
        print("Trying to traverse_backwards")
        total_minutes = traverse_backwards(end_node)
        print('Finished traverse_backwards, total_minutes:', total_minutes)
        if total_minutes:
            possible_queue_date = calculate_possible_date(total_minutes[1], end_date)
            possible_cycle_date = calculate_possible_date(total_minutes[0], end_date)
            
            print('Found possible_queue_date and possible_cycle_date', possible_queue_date, possible_cycle_date)

            return [[possible_queue_date], [possible_cycle_date]]

    return None

# Utils

def subtract_workdays(end_date, workdays, open_time, close_time, holiday_list):
    """
    Subtracts the given number of workdays from the end date, skipping weekends and holidays.
    """
    while workdays > 0:
        end_date -= datetime.timedelta(days=1)
        
        # Skip weekends
        if end_date.weekday() >= 5 or is_holiday(end_date, holiday_list):
            continue

        workdays -= 1

    return end_date

def is_holiday(date, holiday_list):
    """
    Check if the date falls on a holiday by comparing against the holiday_list.
    """
    # print('in holiday')
    for holiday in holiday_list:
        # print(f"Holiday data: {holiday}")  # Debug statement
        # OLD CODE CAUSING ERRORS: 
        # holiday_start = datetime.datetime.fromtimestamp(holiday['inizio']['$date']['$numberLong'] / 1000)
        # holiday_end = datetime.datetime.fromtimestamp(holiday['fine']['$date']['$numberLong'] / 1000)
        holiday_start = holiday['inizio']  # Assuming this is a datetime.datetime object
        holiday_end = holiday['fine'] 
        if holiday_start <= date <= holiday_end:
            return True
    return False


# Orders

def create_order_object(phases, articolo, quantity, order_id, end_date, order_description, settings):
    # Calculate phase dates
    print('Passing to calculate_phase_dates:')
    print('end_date:', end_date)
    print('phases:', phases)
    print('quantity:', quantity)
    print('settings:', settings)
    print('articolo:', articolo)
    phase_dates = calculate_phase_dates(end_date, phases, quantity, settings, articolo) #returns entrata coda fase
    
    # Check if phase_dates is sorted in increasing order
    if phase_dates != sorted(phase_dates): 
        # If not sorted (increasing order), reverse the array (because the starting date is at the end)
        phase_dates.reverse()
        print('Phase dates after sorting check:', phase_dates)

    # Print or return phase_dates as needed
    print("Phase dates (entrara coda fase) array:", phase_dates)
    
    filtered_dates = [date for date in phase_dates if date is not None]
    # reduce to find the earliest date
    if filtered_dates:
        start_date = min(filtered_dates) # Earliest Date
        print('Order Start Date is: ', start_date)
    else:
        start_date = None
        print('Order Start Date could not be calculated')
        
    # Align order structure with Flutter
    order_object = {
        "orderId": str(order_id),
        "orderInsertDate": datetime.datetime.now(),
        "orderStartDate": start_date,  # Start date based on calculated phase dates ERA phase_dates[0]
        "assignedOperator": [[""] for _ in phases],
        "orderStatus": 0,  # Initial status
        "orderDescription": order_description or '',
        "codiceArticolo": articolo,
        "orderDeadline": end_date,
        "customerDeadline": end_date,
        "quantita": int(quantity),
        "phase": [[p] for p in phases],  # List of phases
        "phaseStatus": [[1] for _ in phases],  # Default status
        "phaseEndTime": [[et * quantity] for et in get_phase_end_times(phases, articolo)], 
        "phaseLateMotivation": [["none"] for _ in phases],  # Default empty motivation
        "phaseRealTime": [[0] for _ in phases],  # Default real-time
        "entrataCodaFase": [[date] for date in phase_dates],  # Queue entry dates
        "priority": 0,  # Default priority
        "inCodaAt": [],  
        "inLavorazioneAt": [[""] for _ in phases],
    }
    
    return order_object



def create_json_for_flowchart(codice, phases, cycle_times, queueTargetTimes, description):
    """  Creates Family Json object 

    Args:
        codice (_type_): _description_
        phases (_type_): _description_
        cycle_times (_type_): _description_
        description (_type_): _description_

    Returns:
        _type_: _description_
    """
    element_ids = [str(ObjectId()) for _ in phases]
    dashboard_elements = []
    for i, (phase, time, targetTime) in enumerate(zip(phases, cycle_times, queueTargetTimes)):
        element = {
            "positionDx": 101.2 + 200 * i,
            "positionDy": 240.2,
            "size.width": 100.0, 
            "size.height": 50.0,
            "text": phase,
            "textColor": 4278190080,
            "fontFamily": None,
            "textSize": 12.0,
            "textIsBold": False,
            "id": element_ids[i],
            "kind": 0,
            "handlers": [3, 2],
            "handlerSize": 15.0,
            "backgroundColor": 4294967295,
            "borderColor": 4293336434,
            "borderThickness": 3.0,
            "elevation": 4.0,
            "next": [],
            "phaseDuration": int(time),
            "phaseTargetQueue": targetTime
        }
        if i < len(phases) - 1:
            element['next'].append({
                "destElementId": element_ids[i + 1],
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
            })
        dashboard_elements.append(element)
    json_output = {
        "_id": ObjectId(),
        "titolo": codice,
        "descrizione": description,
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
                "gridColor": 520093696
            },
            "blockDefaultZoomGestures": False,
            "minimumZoomFactor": 0.25,
            "arrowStyle": 0
        },
        "catalogo": [{
            "_id": ObjectId(),
            "prodId": codice,  
            "prodotto": codice, 
            "descrizione": description,
            "famiglia": codice,
            "elements": [
                {
                    "pId": element_ids[i],
                    "property": "Example property", # Placeholder
                    "duration": int(time)
                } for i, time in enumerate(cycle_times)
            ]
        }]
    }
    return json_output
    

def excel_date_parser(date_str):
    return pd.to_datetime(date_str, dayfirst=True, errors='coerce')
        
def upload_orders_from_xlsx_amade(self):
    # Fetch necessary data from MongoDB
    db = client
    collection_famiglie = db['process_db']['famiglie_di_prodotto']
    collection_orders = db['orders_db']['ordini']
    
    # Open file dialog to select Excel file
    file_path, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel files (*.xlsx)")
    if not file_path:
        QMessageBox.warning(self, "File Selection", "No file selected.")
        return

    if not file_path.endswith('.xlsx'):
        QMessageBox.critical(self, "File Error", "The selected file is not an Excel file.")
        return
    
    # Fetch existing order IDs from the 'ordini' collection
    existing_order_ids = set()
    
    skipped_orders = []

    order_cursor = collection_orders.find({}, {'orderId': 1})
    for order in order_cursor:
        existing_order_ids.add(order['orderId'])

    try:
        # Read the Excel file
        xls = pd.ExcelFile(file_path)
        orders_df = pd.read_excel(
            xls,
            sheet_name='Ordini',
            dtype={'Id Ordine': str, 'Codice Articolo': str, 'Info aggiuntive': str},
            parse_dates=['Data Richiesta'],
            date_parser=excel_date_parser

        )
    except Exception as e:
        QMessageBox.critical(self, "File Error", f"Failed to read the Excel file: {e}")
        return

    # Check if required columns are present
    required_columns = {'Id Ordine', 'Codice Articolo', 'QTA', 'Data Richiesta', 'Info aggiuntive'}
    if not required_columns.issubset(orders_df.columns):
        missing_columns = required_columns - set(orders_df.columns)
        QMessageBox.critical(self, "File Error", "Missing required columns: " + ", ".join(missing_columns))
        return

    # Drop rows where 'Codice Articolo' is NaN
    orders_df = orders_df.dropna(subset=['Codice Articolo'])

    # Initialize counters and lists for reporting
    successful_orders = []
    failed_orders = []

    

    # Create a dictionary to map 'prodId' to catalog item and family information
    famiglia_cursor = collection_famiglie.find({}, {'catalogo': 1, 'dashboard': 1})
    prodId_to_catalog_info = {}
    for famiglia in famiglia_cursor:
        catalogo = famiglia.get('catalogo', [])
        phases_elements = famiglia.get('dashboard', {}).get('elements', [])
        phase_names = [element.get('text', '') for element in phases_elements]
        for item in catalogo:
            prodId_to_catalog_info[item['prodId']] = {
                'catalog_item': item,
                'phases': phase_names,
                'family': famiglia
            }
            
    settings = fetch_settings() 
    print('got settings')

    # Process each order
    for idx, row in orders_df.iterrows():
        ordineId = row['Id Ordine']
        codiceArticolo = row['Codice Articolo']
        qta = row['QTA']
        dataRichiesta = row['Data Richiesta']
        infoAggiuntive = row['Info aggiuntive'] or ''
        
        # Double check that infoaggiuntive will not cause crash
        if pd.isna(infoAggiuntive) or infoAggiuntive.strip() == "":
            infoAggiuntive = "0"

        if ordineId in existing_order_ids:
            skipped_orders.append(ordineId)
            continue  # Skip processing this order
        
        print('Trying to check data Richesta')
        # Validate dataRichiesta
        if pd.isnull(dataRichiesta):
            failed_orders.append({'ordineId': ordineId, 'codiceArticolo': codiceArticolo, 'reason': 'Data Richiesta is null'})
            continue

        if not isinstance(dataRichiesta, datetime.datetime):
            try:
                # Try to parse the date
                dataRichiesta = pd.to_datetime(dataRichiesta, dayfirst=True)
            except Exception as e:
                failed_orders.append({'ordineId': ordineId, 'codiceArticolo': codiceArticolo, 'reason': f'Invalid date: {dataRichiesta}'})
                continue

        print('Data Richesta is good: ', dataRichiesta)
        
        # Check if the 'codiceArticolo' exists in 'catalogo'
        catalog_info = prodId_to_catalog_info.get(codiceArticolo)
        if not catalog_info:
            failed_orders.append({'ordineId': ordineId, 'codiceArticolo': codiceArticolo, 'reason': f'No document found with prodId {codiceArticolo}'})
            continue

        catalog_item = catalog_info['catalog_item']
        phases = catalog_info['phases']
        articolo = catalog_item  
        quantity = qta
        order_id = ordineId
        end_date = dataRichiesta
        order_description = infoAggiuntive

        print('Trying to create order object')
        # Create the order object using the provided function
        try:
            order_document = create_order_object(
                phases=phases,
                articolo=codiceArticolo,
                quantity=quantity,
                order_id=order_id,
                end_date=end_date,
                order_description=order_description,
                settings=settings
            )
        except Exception as e:
            failed_orders.append({'ordineId': ordineId, 'codiceArticolo': codiceArticolo, 'reason': f'Error creating order object: {e}'})
            continue
        print('Order object created')

        # Insert the order into the 'orders' collection
        try:
            collection_orders.insert_one(order_document)
            successful_orders.append(ordineId)
        except Exception as e:
            failed_orders.append({'ordineId': ordineId, 'codiceArticolo': codiceArticolo, 'reason': str(e)})

    summary_message = f"{len(successful_orders)} orders processed successfully, {len(failed_orders)} errors, {len(skipped_orders)} orders skipped (already in database)."

     # Create the report content
    report_message = "Orders Upload Report:\n\n"
    report_message += summary_message + "\n\n"

    if successful_orders:
        report_message += "Successfully processed orders:\n"
        report_message += "\n".join(successful_orders) + "\n\n"

    if failed_orders:
        report_message += "Errors encountered:\n"
        for error in failed_orders:
            error_detail = f"{error.get('ordineId', error.get('codiceArticolo'))}: {error['reason']}"
            report_message += error_detail + "\n"

    # Show a report of the upload process
    show_upload_report(successful_orders, failed_orders, skipped_orders)

# Reporting Functions

def show_upload_report(successful_orders, failed_orders, skipped_orders):
    report_message = "Upload Report:\n\n"

    if successful_orders:
        report_message += "Successfully uploaded orders:\n"
        report_message += "\n".join([str(order) for order in successful_orders])
        report_message += "\n\n"

    if failed_orders:
        report_message += "Failed to upload orders:\n"
        for failed in failed_orders:
            codice_articolo = failed.get('codiceArticolo', 'Unknown')
            report_message += f"Order ID: {failed['ordineId']}, Codice Articolo: {codice_articolo}, Reason: {failed['reason']}\n"
            
    if skipped_orders:
        report_message += "Skipped orders (already in database):\n"
        report_message += "\n".join(skipped_orders) + "\n\n"

    # Show the message in a popup dialog
    QMessageBox.information(None, "Upload Report", report_message)
    
    save_report_to_file(report_message, "orders")
    
def show_family_upload_report(successful_families, failed_families, skipped_families):
    report_message = "Upload Report:\n\n"

    if successful_families:
        report_message += "Successfully uploaded Families:\n"
        report_message += "\n".join([str(family) for family in successful_families])
        report_message += "\n\n"

    if failed_families:
        report_message += "Failed to upload Families:\n"
        for failed in failed_families:
            family_name = failed.get('familyName', 'Unknown')
            report_message += f"Family ID: {failed['familyID']}, Codice: {family_name}, Reason: {failed['reason']}\n"
            
    if skipped_families:
        report_message += "Skipped families (already in database):\n"
        report_message += "\n".join(skipped_families) + "\n\n"

    # Show the message in a popup dialog
    QMessageBox.information(None, "Upload Report", report_message)
    
    save_report_to_file(report_message, "families")

def save_report_to_file(report_content, report_type):
    if not os.path.exists('./reports'):
        os.makedirs('./reports')

    # Generate a timestamped filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report_type}_report_{timestamp}.txt"
    file_path = os.path.join('reports', filename)

    # Write the report content to the file
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(report_content)
        print(f"Report saved to {file_path}")
    except Exception as e:
        print(f"Failed to save report: {e}")

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super(LoginWindow, self).__init__(parent)
        
        self.user_role = None  
        self.setWindowTitle("Login")
        self.setFixedSize(800, 600)
        
        layout = QVBoxLayout()

        # Add company logo
        self.logo_label = QLabel(self)
        self.pixmap = QPixmap(r".\img\OPERATIVO_L_Main_Color.png")
        self.logo_label.setPixmap(self.pixmap.scaled(1200, 300, Qt.KeepAspectRatio))
        layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

        # Username and Password fields
        self.username_label = QLabel("Username:", self)
        self.username_input = QLineEdit(self)
        self.password_label = QLabel("Password:", self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)

        font = QFont("Proxima Nova", 12)
        self.username_label.setFont(font)
        self.username_input.setFont(font)
        self.password_label.setFont(font)
        self.password_input.setFont(font)

        # Layout for username and password
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.username_label, 0, 0)
        grid_layout.addWidget(self.username_input, 0, 1)
        grid_layout.addWidget(self.password_label, 1, 0)
        grid_layout.addWidget(self.password_input, 1, 1)
        layout.addLayout(grid_layout)

        # Login button
        self.login_button = QPushButton("Login", self)
        self.login_button.setFont(font)
        self.login_button.clicked.connect(self.on_login)
        layout.addWidget(self.login_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def on_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if connect_to_mongodb(username, password):
            self.accept()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid username or password")

class MainWindow(QMainWindow):
    def __init__(self, user_role):
        super(MainWindow, self).__init__()
        self.user_role = user_role
        self.setWindowTitle("Data Uploader")
        self.setGeometry(75, 75, window_width, window_height)
        
        self.qr_save_path = "./QRs" 
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.adjust_sizes()

        # Add company logo
        self.logo_label = QLabel(self)
        self.pixmap = QPixmap(r".\img\OPERATIVO_L_Main_Color.png")
        self.logo_label.setPixmap(self.pixmap.scaled(2400, 600, Qt.KeepAspectRatio))
        self.layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

        # Buttons
        # self.queue_button = QPushButton("Queue Data")
        # self.clear_button = QPushButton("Clear Queued Data")
        # self.upload_button = QPushButton("Upload Queued Data")
        # self.upload_button.setStyleSheet("background-color: green; color: white;")
        self.upload_orders_button_amade = QPushButton("Upload Orders")
        self.upload_famiglie_button = QPushButton("Upload Flussi (Famiglie)")
        self.upload_famiglie_button.setStyleSheet("background-color: red; color: white;")
        self.export_button = QPushButton("Export Data")
        self.utenti_qr_code_button = QPushButton("Generate Operatori QR Codes")
        self.order_qr_button = QPushButton("Generate Order QR Codes")
        self.upload_articoli_button = QPushButton("Upload Articoli")  

        # Setup font
        font = QFont("Proxima Nova", 12)
        for button in [self.upload_famiglie_button, self.export_button, self.upload_orders_button_amade, self.upload_famiglie_button, 
                       self.export_button, self.utenti_qr_code_button, self.upload_articoli_button]:
            button.setFont(font)
            button.setFixedSize(350, 50)

        # Create layouts
        main_horizontal_layout = QHBoxLayout()
        left_layout = QHBoxLayout()
        center_layout = QHBoxLayout()
        right_layout = QHBoxLayout()

        # Add buttons to layouts
        # center_layout.addWidget(self.queue_button)
        # center_layout.addWidget(self.clear_button)
        # center_layout.addWidget(self.upload_button)
        center_layout.addWidget(self.upload_famiglie_button)
        center_layout.addWidget(self.export_button)
        center_layout.addWidget(self.upload_orders_button_amade)
        center_layout.addWidget(self.utenti_qr_code_button)
        center_layout.addWidget(self.order_qr_button)
        center_layout.addWidget(self.upload_articoli_button)  


        # Add stretches to center the center layout
        main_horizontal_layout.addLayout(left_layout)
        main_horizontal_layout.addLayout(center_layout)
        main_horizontal_layout.addLayout(right_layout)
        self.layout.addLayout(main_horizontal_layout)
        
        # BUTTON CONNECTIONS TO FUNCTIONS
        
        # self.queue_button.clicked.connect(self.queue_data)
        # self.clear_button.clicked.connect(self.clear_data)
        # self.upload_button.clicked.connect(self.upload_queued_data)
        self.upload_famiglie_button.clicked.connect(self.marcolin_import_famiglie)
        self.export_button.clicked.connect(self.select_database_and_collection)
        self.utenti_qr_code_button.clicked.connect(self.generate_and_save_qr_codes)
        self.order_qr_button.clicked.connect(self.generate_order_qr_codes)
        self.upload_orders_button_amade.clicked.connect(self.upload_orders_amade)
        self.upload_articoli_button.clicked.connect(self.upload_articoli)
        
        # Table for CSV data - REDUNDANT TO BE REMOVED
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        
    def initialize_ui(self):
        if self.user_role == "special_role":
            self.setup_special_user_ui()
        else:
            self.setup_regular_user_ui()
        
    def adjust_sizes(self):
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()

        # Set window size to 50% of the screen size
        self.window_width = floor(self.screen_width * 0.5)
        self.window_height = floor(self.screen_height * 0.5)
        self.resize(self.window_width, self.window_height)

        # Set image size to 30% of the window size
        self.image_width = self.window_width * 0.3
        self.image_height = self.window_height * 0.3


    def generate_and_save_qr_codes(self):
        if not os.path.exists(self.qr_save_path):
            os.makedirs(self.qr_save_path)
        try:
            db = client['azienda']  
            collection = db['utenti']
            for document in collection.find():
                name = document.get('nome', 'UnknownName')
                surname = document.get('cognome', 'UnknownSurname')
                password = document.get('password', 'NoPassword')  
                qr_data = f"{name}||{surname}||{password}"  
                filename = f"{name}_{surname}.png"
                self.generate_qr(qr_data, filename, name, surname)  
            QMessageBox.information(self, "QR Codes Generated", "QR codes have been successfully generated and saved in " + self.qr_save_path)
        except Exception as e:
            QMessageBox.critical(self, "Operation Failed", f"Failed to generate QR codes: {e}")

    def generate_qr(self, data, filename, name, surname):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')

        # Convert to a format that allows drawing
        img = img.convert("RGB")

        # Define font and get a drawing context
        font = ImageFont.load_default() 
        draw = ImageDraw.Draw(img)

        # Text to add
        text = f"{name} {surname}"

        # Calculate text size and position
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        img_width, img_height = img.size
        x = (img_width - text_width) // 2
        y = img_height - text_height - 10  # 10 pixels above the bottom edge

        # Create a new image with extra space for the text
        new_img_height = img_height + text_height + 20  # Adding some padding
        new_img = Image.new("RGB", (img_width, new_img_height), "white")
        new_img.paste(img, (0, 0))

        # Draw the text on the new image
        draw = ImageDraw.Draw(new_img)
        draw.text((x, img_height + 10), text, font=font, fill="black")

        # Save the image
        full_path = os.path.join(self.qr_save_path, filename)
        new_img.save(full_path)
        

    def generate_order_qr_codes(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            QMessageBox.warning(self, "No Folder Selected", "Please select a valid folder to save QR codes.")
            return

        try:
            db = client['orders_db']
            collection = db['ordini']
            for document in collection.find():
                order_id = document.get('orderId', 'UnknownOrderID')
                codice_articolo = document.get('codiceArticolo', 'UnknownCode')
                quantita = document.get('quantita', 'UnknownQuantity')  # Assuming this field exists

                # Correctly extracting the date part from the orderDeadline string
                order_deadline = str(document.get('orderDeadline', 'UnknownDeadline'))
                date_part = order_deadline.split('T', 1)[0]  # Split the string at 'T' and take the first part
                sanitized_date_part = date_part.replace(':', '-')
                #Constructing filename using the sanitized date part of the order deadline
                filename = f"{order_id}_{codice_articolo}_{sanitized_date_part}.png"
                full_path = os.path.join(folder, filename)

                # Generate QR code with text
                self.generate_order_qr_with_text(order_id, full_path, order_id, codice_articolo, quantita)

            QMessageBox.information(self, "QR Codes Generated", f"Order QR codes have been successfully generated and saved in {folder}")
        except Exception as e:
            QMessageBox.critical(self, "Operation Failed", f"Failed to generate order QR codes: {e}")

    def generate_order_qr_with_text(self, data, full_path, order_id, codice_articolo, quantita):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')

        # Convert to a format that allows drawing
        img = img.convert("RGB")

        # Define font and get a drawing context
        font = ImageFont.load_default()  
        draw = ImageDraw.Draw(img)

        # Text to add
        text = f"Order ID: {order_id}\nCodice: {codice_articolo}\nQuantita: {quantita}"

        # Calculate text size and position
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        img_width, img_height = img.size
        x = (img_width - text_width) // 2
        y = img_height + 10  # 10 pixels below the QR code

        # Create a new image with extra space for the text
        new_img_height = img_height + text_height + 20  # Adding some padding
        new_img = Image.new("RGB", (img_width, new_img_height), "white")
        new_img.paste(img, (0, 0))

        # Draw the text on the new image
        draw = ImageDraw.Draw(new_img)
        draw.text((x, img_height + 10), text, font=font, fill="black")

        # Save the image
        new_img.save(full_path)

    def init_placeholder(self):
        self.table.setRowCount(1)
        self.table.setColumnCount(1)
        self.table.setItem(0, 0, QTableWidgetItem("Upload a csv file to visualize the data"))

    def wipe_database(self):
        print("Attempting to wipe database...")
        reply = QMessageBox.question(self, "Confirm Wipe", "Are you sure you want to wipe the database?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                db = client['processes_db']
                collection = db['macchinari']
                collection.delete_many({})
                self.clear_data()
                QMessageBox.information(self, "Success", "The database has been wiped.")
            except Exception as e:
                print(f"Error wiping database: {e}")
                QMessageBox.critical(self, "Wipe Failed", f"Failed to wipe database: {e}")
                
    
    # today

    def upload_orders_amade(self):
        # filename, _ = QFileDialog.getOpenFileName(self, "Open XLSX File", "", "Excel files (*.xlsx)")
        # if filename:
             upload_orders_from_xlsx_amade(self)
        #     QMessageBox.information(self, "Upload Complete", "Order upload process completed.")
        # else:
        #     QMessageBox.warning(self, "No File Selected", "Please select an Excel file to upload.")
    
    def marcolin_import_famiglie(self):
        # Prompt the user to select an Excel file
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel files (*.xlsx)")
        if not file_path:
            QMessageBox.warning(self, "File Selection", "No file selected.")
            return

        if not file_path.endswith('.xlsx'):
            QMessageBox.critical(self, "File Error", "The selected file is not an Excel file.")
            return

        try:
            # Reading the Excel file
            df = pd.read_excel(file_path, sheet_name='Famiglie')
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to read the Excel file: {e}")
            return
        successful_families = []
        failed_families = []
        skipped_families = []

        # Check if required columns are present in the DataFrame
        required_columns = {'Codice', 'FaseOperativo', 'LTFase', 'Tempo Ciclo', 'Descrizione', 'Accessori'}
        if not required_columns.issubset(df.columns):
            missing_columns = required_columns - set(df.columns)
            QMessageBox.critical(self, "File Error", "Missing required columns: " + ", ".join(missing_columns))
            return

         # Convert `Tempo Ciclo` to a decimal number (float) and round it (for marcolin who will insert TC/Qta)
        try:
            df['Tempo Ciclo'] = pd.to_numeric(df['Tempo Ciclo'], errors='coerce').round()
        except Exception as e:
            QMessageBox.critical(self, "Conversion Error", f"Failed to convert and round 'Tempo Ciclo': {e}")
            return
        
        # Fill any NaN values resulting from conversion,
        df['Tempo Ciclo'].fillna(0, inplace=True)

        db_name = 'process_db'
        collection_name = 'famiglie_di_prodotto'
        db = client[db_name]
        collection = db[collection_name]

        print("Processing data...")
        success_count = 0
        error_count = 0
        errors = []
        for codice, group in df.groupby('Codice'):
            if check_family_existance_db(codice):
                print(f'Family: {codice} already presnt in DB')
                skipped_families.append(codice)
                error_count += 1
            else:
                try:
                    fasi = group['FaseOperativo'].tolist()
                    lt_fase = group['LTFase'].tolist()
                    tempo_ciclo = group['Tempo Ciclo'].tolist()
                    
                    if group['Accessori'].dropna().unique():
                        description = group['Descrizione'].iloc[0] + " " + " ".join(group['Accessori'].dropna().unique())
                    else:
                        description = group['Descrizione'].iloc[0]
                    
                    print(f"Creating and uploading JSON for Codice: {codice}")
                    json_object = create_json_for_flowchart(codice, fasi, tempo_ciclo, lt_fase, description)

                    # Upload JSON object directly to MongoDB
                    collection.insert_one(json_object)
                    print(f"Uploaded JSON for Codice: {codice} to MongoDB")
                    successful_families.append(codice)
                    success_count += 1
                except Exception as e:
                    print(f"Error encountered with family {codice}: {e}")
                    failed_families.append(codice)
                    error_count += 1

        summary_message = f"{success_count} families uploaded successfully, {error_count} failed: {', '.join(errors)}"
        QMessageBox.information(self, "Upload Summary", summary_message)
                
        report_message = "Orders Upload Report:\n\n"
        report_message += summary_message + "\n\n"

        if successful_families:
            report_message += "Successfully processed families:\n"
            report_message += "\n".join(successful_families) + "\n\n"

        if failed_families:
            report_message += "Errors encountered:\n"
            for error in failed_families:
                error_detail = f"{error.get('codice', error.get('codice'))}: {error['reason']}"
                report_message += error_detail + "\n"

        # Show a report of the upload process
        show_family_upload_report(successful_families, failed_families, skipped_families)

    def select_database_and_collection(self):
        databases = client.list_database_names()

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Database and Collection")
        dialog.setFixedSize(400, 300)

        layout = QVBoxLayout()

        db_label = QLabel("Select Database:")
        db_combo = QComboBox()
        db_combo.addItems(databases)

        coll_label = QLabel("Select Collection:")
        coll_combo = QComboBox()

        def on_db_select():
            selected_db = db_combo.currentText()
            collections = client[selected_db].list_collection_names()
            coll_combo.clear()
            coll_combo.addItems(collections)

        db_combo.currentIndexChanged.connect(on_db_select)

        layout.addWidget(db_label)
        layout.addWidget(db_combo)
        layout.addWidget(coll_label)
        layout.addWidget(coll_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            selected_db = db_combo.currentText()
            selected_coll = coll_combo.currentText()
            if selected_db and selected_coll:
                self.export_data(selected_db, selected_coll)
            else:
                QMessageBox.critical(self, "Error", "Please select both database and collection.")

    def export_data(self, db_name, collection_name):
        print(f"Attempting to export data from {db_name}.{collection_name}...")
        try:
            db = client[db_name]
            collection = db[collection_name]
            cursor = collection.find({})
            data = list(cursor)
            if data:
                df = pd.DataFrame(data)
                if '_id' in df.columns:
                    df.drop('_id', axis=1, inplace=True)
                file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV files (*.csv)")
                if file_path:
                    df.to_csv(file_path, index=False)
                    QMessageBox.information(self, "Export Successful", "Data has been successfully exported to CSV.")
            else:
                QMessageBox.information(self, "No Data", "There is no data to export.")
        except Exception as e:
            print(f"Error exporting data: {e}")
            QMessageBox.critical(self, "Export Failed", f"Failed to export data: {e}")
            
    def upload_articoli(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel files (*.xlsx)")
        if not file_path:
            QMessageBox.warning(self, "File Selection", "No file selected.")
            return

        if not file_path.endswith('.xlsx'):
            QMessageBox.critical(self, "File Error", "The selected file is not an Excel file.")
            return

        try:
            # Read the Excel file
            xls = pd.ExcelFile(file_path)
            articoli_df = pd.read_excel(xls, sheet_name='Articoli')
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to read the Excel file: {e}")
            return

        # Check if required columns are present
        required_columns = {'Codice Articolo', 'Descrizione articolo', 'Famiglia di prodotto', 'Fase Operativo', 'Tempo Ciclo', 'Info lavorazione'}
        if not required_columns.issubset(articoli_df.columns):
            missing_columns = required_columns - set(articoli_df.columns)
            QMessageBox.critical(self, "File Error", "Missing required columns: " + ", ".join(missing_columns))
            return

        # Fetch all families from MongoDB
        db = client['process_db']
        collection = db['famiglie_di_prodotto']
        families = list(collection.find())
        # Create a dictionary for quick lookup
        family_dict = {}
        for family in families:
            family_dict[family['titolo']] = family

        # Initialize counters
        success_count = 0
        error_count = 0
        errors = []
        processed_articoli = []


        # Process each row in articoli_df
        for idx, row in articoli_df.iterrows():
            codice_articolo = row['Codice Articolo']
            descrizione_articolo = row['Descrizione articolo']
            famiglia_di_prodotto = row['Famiglia di prodotto']
            fase_operativo = row['Fase Operativo']
            tempo_ciclo = row['Tempo Ciclo']
            info_lavorazione = row['Info lavorazione']

             # Find the family in the database
            if famiglia_di_prodotto not in family_dict:
                error_message = f'Famiglia di prodotto "{famiglia_di_prodotto}" not found in database.'
                errors.append({'Codice Articolo': codice_articolo, 'Reason': error_message})
                error_count += 1
                continue

            family = family_dict[famiglia_di_prodotto]

            # Check if 'codice_articolo' is already in 'catalogo'
            catalogo = family.get('catalogo', [])
            if any(item['prodId'] == codice_articolo for item in catalogo):
                # Article already exists in catalogo
                continue

            # Create 'elements' array
            # For simplicity, create empty dictionaries, or match with family's dashboard elements
            dashboard_elements = family.get('dashboard', {}).get('elements', [])
            elements = [{} for _ in dashboard_elements]

            # Create the new catalog item
            catalog_item = {
                "_id": ObjectId(),
                "prodId": codice_articolo,
                "prodotto": descrizione_articolo,
                "descrizione": "",  
                "famiglia": famiglia_di_prodotto,
                "elements": elements
            }

            # Add the new catalog item to 'catalogo'
            catalogo.append(catalog_item)

            # Update the family in the dictionary
            family['catalogo'] = catalogo
            family_dict[famiglia_di_prodotto] = family

            processed_articoli.append(codice_articolo)
            success_count += 1

        # After processing all articles, update the database with the modified families
        for famiglia, family in family_dict.items():
            # Update the family document in the database
            try:
                collection.update_one({'_id': family['_id']}, {'$set': {'catalogo': family['catalogo']}})
            except Exception as e:
                errors.append({'Famiglia di prodotto': famiglia, 'Reason': f'Error updating database: {e}'})
                error_count += 1

        # Prepare the summary message
        summary_message = f"{success_count} articoli processed successfully, {error_count} errors."
        if errors:
            error_messages = "\n".join([f"{error.get('Codice Articolo', error.get('Famiglia di prodotto'))}: {error['Reason']}" for error in errors])
            QMessageBox.information(self, "Processing Summary", summary_message + "\nErrors:\n" + error_messages)
        else:
            QMessageBox.information(self, "Processing Summary", summary_message)

        # Create the report content
        report_message = "Articoli Upload Report:\n\n"
        report_message += summary_message + "\n\n"

        if processed_articoli:
            report_message += "Successfully processed articoli:\n"
            report_message += "\n".join(processed_articoli) + "\n\n"

        if errors:
            report_message += "Errors encountered:\n"
            for error in errors:
                error_detail = f"{error.get('Codice Articolo', error.get('Famiglia di prodotto'))}: {error['Reason']}"
                report_message += error_detail + "\n"

        # Write the report to a .txt file
        save_report_to_file(report_message, "articoli")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        main_window = MainWindow(login.user_role)
        main_window.show()
        sys.exit(app.exec_())
