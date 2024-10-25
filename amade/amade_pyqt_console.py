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
from functools import reduce
import numpy as np
import ast
import re  
from export_utils import order_status_mapper, phase_status_mapper, column_mapping, fetch_in_coda_at_names, map_in_lavorazione_at_value, fetch_in_lavorazione_at_names, map_in_coda_at, calculate_in_coda, parse_value, map_in_coda_at_value, parse_entrata_coda_fase, create_new_row, format_queue_entry_time, parse_columns
from order_insert_utils import calculate_phase_dates

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

# MongoDB Functions:

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
        elif username == "launch" and password == "launch":
            client = MongoClient(os.getenv("LAUNCH_URI"))
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

def fetchMacchinari():
    global client
    db = client['process_db']
    macchinari_collection = db['macchinari']
    
    # Fetch all macchinari names
    macchinari_names = macchinari_collection.find({}, {'_id': 0, 'name': 1})
    macchinari_list = [item['name'] for item in macchinari_names]
    
    return macchinari_list

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

def check_family_existance_db(familyName):
    process_db = client['process_db']
    famiglie_di_prodotto = process_db['famiglie_di_prodotto']
    
    family = famiglie_di_prodotto.find_one({"titolo": familyName})
    
    if family:
        return True

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

# Utils

# def subtract_workdays(end_date, workdays, open_time, close_time, holiday_list):
#     """
#     Subtracts the given number of workdays from the end date, skipping weekends and holidays.
#     """
#     while workdays > 0:
#         end_date -= datetime.timedelta(days=1)
        
#         # Skip weekends
#         if end_date.weekday() >= 5 or is_holiday(end_date, holiday_list):
#             continue

#         workdays -= 1

#     return end_date

# def is_holiday(date, holiday_list):
#     """
#     Check if the date falls on a holiday by comparing against the holiday_list.
#     """
#     # print('in holiday')
#     for holiday in holiday_list:
#         # print(f"Holiday data: {holiday}")  # Debug statement
#         # OLD CODE CAUSING ERRORS: 
#         # holiday_start = datetime.datetime.fromtimestamp(holiday['inizio']['$date']['$numberLong'] / 1000)
#         # holiday_end = datetime.datetime.fromtimestamp(holiday['fine']['$date']['$numberLong'] / 1000)
#         holiday_start = holiday['inizio']  # Assuming this is a datetime.datetime object
#         holiday_end = holiday['fine'] 
#         if holiday_start <= date <= holiday_end:
#             return True
#     return False

# Orders

def create_order_object(phases, articolo, quantity, order_id, end_date, order_description, settings):
    # Calculate phase dates
    print('Passing to calculate_phase_dates:')
    print('end_date:', end_date)
    print('phases:', phases)
    print('quantity:', quantity)
    print('settings:', settings)
    print('articolo:', articolo)
    phase_dates = calculate_phase_dates(client, end_date, phases, quantity, settings, articolo) #returns entrata coda fase
    
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
        
    order_object = {
        "orderId": str(order_id),
        "orderInsertDate": datetime.datetime.now(),
        "orderStartDate": start_date,  # Start date based on calculated phase dates ERA phase_dates[0]
        "assignedOperator": [[""] for _ in phases],  # Default empty assigned operator
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
    """ Creates Family Json object 

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
        infoAggiuntive = row['Info aggiuntive']

        if ordineId in existing_order_ids:
            skipped_orders.append(ordineId)
            continue  # Skip processing this order
        
        print('Trying to check data Rcihesta')
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

        print('Data Rcihesta is good: ', dataRichiesta)
        
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


## DEPRECATED

def map_phases(phase_string):
    # Define the mappings
    phase_mappings = {
        'lavmec': 'Filettatura/Foratura',
        'lav mecc': 'Filettatura/Foratura',
        'taglio': 'Taglio',
        'piega': 'Piega 1',
        'smerigliatura/insertaggio': 'Smerigliatura',
        'saldatura': 'Saldatura'
    }
    
    # Split the phase string into individual phases
    separators = ['-', '+']
    for sep in separators:
        if sep in phase_string:
            phases = phase_string.split(sep)
            break
    else:
        phases = [phase_string]  # If no separator is found, treat as a single phase
    
    # Map the phases using the predefined mappings
    mapped_phases = []
    for phase in phases:
        phase = phase.strip()
        for key in phase_mappings:
            if key in phase:
                mapped_phases.append(phase_mappings[key])
                break
    
    return mapped_phases
    

def check_missing_families(articoli_checks):
    missing_families = [check['Famiglia'] for check in articoli_checks if not check['FamigliaExists']]
    
    if missing_families:
        QMessageBox.warning(None, "Missing Families", "The following families are missing in the database:\n" + "\n".join(missing_families))


def create_order_object_with_dates(phases, codice_articolo, quantita, order_id, end_date, customer_deadline):
    ""
    DeprecationWarning
    ""
    
    settings = fetch_settings()
    
    open_time = settings.get('orariAzienda', {}).get('inizio', {'ore': 8, 'minuti': 0})
    close_time = settings.get('orariAzienda', {}).get('fine', {'ore': 18, 'minuti': 0})
    holiday_list = settings.get('ferieAziendali', [])
    pausa_pranzo = settings.get('pausaPranzo', {'inizio': {'ore': 12, 'minuti': 0}, 'fine': {'ore': 15, 'minuti': 0}})

    graph = {phase: [] for phase in phases}
    for i in range(len(phases) - 1):
        graph[phases[i]].append(phases[i + 1])

    phase_end_times = get_phase_end_times(phases)
    durations = dict(zip(phases, phase_end_times))

    entrata_coda_fase = []
    for phase in phases:
        # compute the delivery end time
        if isinstance(end_date, str):
            end_date = datetime.datetime(int(end_date.split("/")[2]), int(end_date.split("/")[1]), int(end_date.split("/")[0]), close_time['ore'], close_time['minuti'])
            print('End Date after parsing is: ', end_date)

        start_date = find_start_date_of_phase(end_date, phase, quantita, open_time, holiday_list, pausa_pranzo, graph, durations)
        print("Found start_date of equal to", phase, start_date)
        entrata_coda_fase.append([start_date])#(int(start_date.timestamp() * 1000)) if start_date else None)

    non_null_dates = [date for date in entrata_coda_fase if date is not None]
    # valore di default per evitare null
    order_start_date = datetime.datetime.fromtimestamp(datetime.datetime.now().timestamp() / 1000) - datetime.timedelta(days=10)
    if non_null_dates:
        order_start_date = min(non_null_dates)

    # sarebbe da mettere il controllo per vedere che non siano infattibili, ma credo si possa skippare
    # if start_date is not None and start_date < datetime.now(): return
    
    current_time = datetime.datetime.now()
    order_object = {
        "codiceArticolo": str(codice_articolo),
        # mancava order startDate
        "orderInsertDate": current_time, #datetime.datetime.fromtimestamp(current_time.timestamp() / 1000),
        # orderDeadline e customerDeadline sono la stessa cosa, col refactoring sistemiamo questa variabile
        "orderDeadline": datetime.datetime(int(customer_deadline.split("/")[2]), int(customer_deadline.split("/")[1]), int(customer_deadline.split("/")[0]), close_time['ore'], close_time['minuti']) if isinstance(customer_deadline, str) else customer_deadline,
        "customerDeadline": datetime.datetime(int(customer_deadline.split("/")[2]), int(customer_deadline.split("/")[1]), int(customer_deadline.split("/")[0]), close_time['ore'], close_time['minuti']) if isinstance(customer_deadline, str) else customer_deadline,
        "orderDescription": "",
        "orderStartDate": order_start_date[0],
        "orderStatus": 0,
        # sistemati tutti gli array
        "phaseStatus": [[0] for _ in phases],
        "assignedOperator": [[""] for _ in phases],
        "phase": [[ph] for ph in phases],
        "phaseEndTime": [[time] for time in phase_end_times],
        "phaseLateMotivation": [["none"] for _ in phases],
        "phaseRealTime": [[0] for _ in phases],
        "quantita": quantita,
        "entrataCodaFase": entrata_coda_fase,
        "orderId": order_id,
        "dataInizioLavorazioni": entrata_coda_fase[0][0], #datetime.datetime.fromtimestamp(current_time.timestamp() / 1000),
        "priority": 0,
        "inCodaAt": []
    }
    
    return order_object

def get_procedure_phases_by_prodId(prodId):
    ""
    # Not currently Used
    ""
    
    db = client['process_db']
    collection = db['famiglie_di_prodotto']
    
    # Search for the family containing the prodId in the catalogo array
    document = collection.find_one({"catalogo.prodId": prodId})
    
    if not document:
        # Print all documents for debugging purposes
        all_documents = list(collection.find())
        print("All documents in collection:")
        for doc in all_documents:
            print(doc)
        raise ValueError(f"No document found with prodId {prodId}")
    
    # Now find the specific item in the catalogo array
    catalog_item = next((item for item in document['catalogo'] if item['prodId'] == prodId), None)
    
    if not catalog_item:
        raise ValueError(f"No catalog item found with prodId {prodId}")
    
    # Extract the 'elements' array from the dashboard
    dashboard = document.get('dashboard', {})
    elements = dashboard.get('elements', [])
    
    if not elements:
        raise ValueError(f"No elements found in the dashboard for prodId {prodId}")
    
    # Extract the 'text' field from each element in the elements array (phases)
    phases = [element.get('text') for element in elements if 'text' in element]
    
    if not phases:
        raise ValueError(f"No phases found for prodId {prodId}")
    
    return phases

def show_family_upload_report(successful_families, failed_families, skipped_families):
        report_message = "Upload Report:\n\n"

        if successful_families:
            report_message += "Successfully uploaded Families:\n"
            report_message += "\n".join([str(family) for family in successful_families])
            report_message += "\n\n"

        if failed_families:
            report_message += "Failed to upload Families:\n"
            for failed in failed_families:
                report_message += f"Family ID: {failed['familyID']}, Codice: {failed['codice']}, Reason: {failed['reason']}\n"
                
        if skipped_families:
            report_message += "Skipped families (already in database):\n"
            report_message += "\n".join(skipped_families) + "\n\n"

        # Show the message in a popup dialog
        QMessageBox.information(None, "Upload Report", report_message)
        
        save_report_to_file(report_message, "families")

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
        self.upload_orders_button_amade = QPushButton("Upload Orders Amade")
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
        required_columns = {'Codice', 'FaseOperativo', 'LTFase', 'Tempo Ciclo', 'Descrizione'}
        if not required_columns.issubset(df.columns):
            missing_columns = required_columns - set(df.columns)
            QMessageBox.critical(self, "File Error", "Missing required columns: " + ", ".join(missing_columns))
            return

        output_directory = './output_jsons'

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
                    # Check for any phases in FaseOperativo that are not in macchinari_list
                    macchinari_list = fetchMacchinari()
                    missing_phases = [fase for fase in fasi if fase not in macchinari_list]

                    if missing_phases:
                        failed_families.append({'familyID': set(group['ID'].tolist()),'codice': f'{codice}', 'reason': f'Hai provato di inserire una famiglia che contiene delle Lavorazioni (Fasi) che non esistono nella Basi Dati di Operativo. {missing_phases}'})
                        error_count += 1
                        print(f"Questi fasi non sono nella lista di macchinari: {missing_phases}")
                        continue
                    
                    lowercase_fasi = [fase.lower() for fase in fasi]
                    if len(lowercase_fasi) != len(set(lowercase_fasi)):
                        print(f"Duplicate phases found (case-insensitive) for family {codice}: {fasi}")
                        failed_families.append({'codice': codice, 'reason': 'Duplicate phases found'})
                        error_count += 1
                        continue  # Skip this family if duplicate phases are found
                    
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
            # Connect to MongoDB and fetch data
            db = client[db_name]
            collection = db[collection_name]
            cursor = collection.find({})
            data = list(cursor)

            if data:
                df = pd.DataFrame(data)
                if '_id' in df.columns:
                    df.drop('_id', axis=1, inplace=True)

                print("Available columns in the data:")
                print(df.columns.tolist())

                # Fetch machine names (map ObjectId to machine name)
                id_to_name = fetch_in_coda_at_names(client)
                # Fetch the UUID-to-name mapping
                uuid_to_name = fetch_in_lavorazione_at_names(client)

                # Ensure all required columns are present
                required_columns = ['phase', 'phaseStatus', 'assignedOperator', 'phaseLateMotivation', 'phaseEndTime', 'phaseRealTime', 'entrataCodaFase']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    QMessageBox.critical(self, "Export Failed", f"Missing required columns: {', '.join(missing_columns)}")
                    return

                # List of columns to parse
                columns_to_parse = ['phaseStatus', 'assignedOperator', 'phaseLateMotivation', 'phaseEndTime', 'phaseRealTime', 'inCodaAt', 'inLavorazioneAt', 'entrataCodaFase']

                # Store all expanded rows
                all_expanded_rows = []

                # Iterate over each row in the DataFrame
                for idx, row in df.iterrows():
                    phases = parse_value(row['phase'])
                    if not phases:
                        print(f"Skipping row {idx}: 'phase' value is invalid.")
                        continue

                    # Parse columns
                    parsed_columns = parse_columns(row, columns_to_parse, id_to_name)

                    parsed_columns['inCodaAt'] = [map_in_coda_at_value(v, id_to_name) for v in parsed_columns['inCodaAt']]
                    
                    if 'inLavorazioneAt' in parsed_columns:
                        parsed_columns['inLavorazioneAt'] = [map_in_lavorazione_at_value(v, uuid_to_name) for v in parsed_columns['inLavorazioneAt']]
                        
                    # Create new expanded rows based on phases
                    new_rows = create_new_row(row, phases, parsed_columns, columns_to_parse)
                    all_expanded_rows.extend(new_rows)

                if all_expanded_rows:
                    final_expanded_df = pd.DataFrame(all_expanded_rows)

                    # Add sequence number if needed
                    if 'orderId' in final_expanded_df.columns:
                        print("Trying to add Seqeuenza column")
                        final_expanded_df['Sequenza'] = final_expanded_df.groupby('orderId').cumcount() + 1
                    else:
                        print("Else of sequenza")
                        final_expanded_df['Sequenza'] = range(1, len(final_expanded_df) + 1)

                    # Can only perform here since later the phaseStatis gets mapped to Strings
                    final_expanded_df['in coda'] = calculate_in_coda(final_expanded_df)
                    
                    # Map status columns
                    if 'orderStatus' in final_expanded_df.columns:
                        final_expanded_df['orderStatus'] = final_expanded_df['orderStatus'].apply(order_status_mapper)
                    if 'phaseStatus' in final_expanded_df.columns:
                        final_expanded_df['phaseStatus'] = final_expanded_df['phaseStatus'].apply(phase_status_mapper)

                    # Rename columns
                    final_expanded_df.rename(columns=column_mapping, inplace=True)

                    # Format 'Queue Entry Time' column
                    if 'Queue Entry Time' in final_expanded_df.columns:
                        final_expanded_df['Queue Entry Time'] = final_expanded_df['Queue Entry Time'].apply(format_queue_entry_time)

                    # Convert column to integers, coercing errors to NaN and filling NaN with 0
                    final_expanded_df['Quantità'] = pd.to_numeric(final_expanded_df['Quantità'], errors='coerce').fillna(0).astype(int)
                    final_expanded_df['Lead Time Fase'] = pd.to_numeric(final_expanded_df['Lead Time Fase'], errors='coerce').fillna(0).astype(int)
                    final_expanded_df['Tempo Ciclo Performato'] = pd.to_numeric(final_expanded_df['Tempo Ciclo Performato'], errors='coerce').fillna(0).astype(int)
                    final_expanded_df['Priorità'] = pd.to_numeric(final_expanded_df['Priorità'], errors='coerce').fillna(0).astype(int)
                    final_expanded_df['Sequenza'] = pd.to_numeric(final_expanded_df['Sequenza'], errors='coerce').fillna(0).astype(int)

                    # Save the DataFrame to Excel
                    options = QFileDialog.Options()
                    file_path, _ = QFileDialog.getSaveFileName(self, "Save Excel File", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
                    if file_path:
                        final_expanded_df.to_excel(file_path, index=False)
                        QMessageBox.information(self, "Export Successful", "Data has been successfully exported to Excel.")
                    else:
                        print("No file path was selected.")
                else:
                    QMessageBox.information(self, "No Data", "No rows were expanded. The output file was not created.")
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
                "descrizione": "",  # You can include additional info if needed
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



# def find_start_date_of_phase(end_date, duration, open_time, close_time, pausa_pranzo, holiday_list):
#     """
#     Recursively calculates the start date of a phase by moving backwards from the end date.
#     Accounts for working hours, lunch breaks, holidays, and weekends.
#     """
#     # Calculate the duration of a workday in minutes (excluding the lunch break)
#     workday_start = datetime.timedelta(hours=open_time['ore'], minutes=open_time['minuti'])
#     workday_end = datetime.timedelta(hours=close_time['ore'], minutes=close_time['minuti'])
#     lunch_start = datetime.timedelta(hours=pausa_pranzo['inizio']['ore'], minutes=pausa_pranzo['inizio']['minuti'])
#     lunch_end = datetime.timedelta(hours=pausa_pranzo['fine']['ore'], minutes=pausa_pranzo['fine']['minuti'])
    
#     # Total working time in a day excluding the lunch break
#     workday_duration = (workday_end - workday_start).total_seconds() / 60
#     lunch_duration = (lunch_end - lunch_start).total_seconds() / 60
#     effective_workday_minutes = workday_duration - lunch_duration
    
#     # Calculate how many full workdays are required
#     full_workdays_needed = duration // effective_workday_minutes
#     remaining_minutes = duration % effective_workday_minutes

#     # Move the end date back by the full workdays, skipping weekends and holidays
#     start_date = subtract_workdays(end_date, full_workdays_needed, open_time, close_time, holiday_list)
    
#     # Now handle the remaining minutes
#     while remaining_minutes > 0:
#         # If the current day is a weekend or holiday, skip it
#         if start_date.weekday() >= 5 or is_holiday(start_date, holiday_list):
#             start_date -= datetime.timedelta(days=1)
#             continue

#         # Define workday start and end times for the current day
#         workday_start_dt = start_date.replace(hour=open_time['ore'], minute=open_time['minuti'])
#         workday_end_dt = start_date.replace(hour=close_time['ore'], minute=close_time['minuti'])

#         # Check if we can fit the remaining minutes in the current workday
#         if remaining_minutes <= (workday_end_dt - workday_start_dt).total_seconds() / 60:
#             start_date -= datetime.timedelta(minutes=remaining_minutes)
#             remaining_minutes = 0
#         else:
#             # Subtract a full workday and continue
#             remaining_minutes -= effective_workday_minutes
#             start_date -= datetime.timedelta(days=1)
    
#     return start_date