from pymongo import MongoClient
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

global client

def get_procedure_phases_by_prodId(prodId):
    # Connect to the MongoDB database
    db = client['process_db']
    collection = db['catalogo']
    
    # Print debug info
    print(f"Searching for prodId: {prodId}")
    
    # Find the document with the matching prodId
    document = collection.find_one({"prodId": prodId})
    
    if not document:
        # Print all documents for debugging
        all_documents = list(collection.find())
        print("All documents in collection:")
        for doc in all_documents:
            print(doc)
        raise ValueError(f"No document found with prodId {prodId}")
    
    # Extract the 'elements' array from the 'dashboard' object
    dashboard = document.get('dashboard', {})
    elements = dashboard.get('elements', [])
    
    # Extract the 'text' field from each object in the 'elements' array
    phases = [element.get('text') for element in elements if 'text' in element]
    
    return phases


def get_phase_end_times(phases):
    # Connect to the MongoDB database
    db = client['process_db']
    collection = db['macchinari']
    
    # Fetch queueTargetTime for each phase
    phase_end_times = []
    for phase in phases:
        document = collection.find_one({"name": phase})
        if not document:
            raise ValueError(f"No document found for phase {phase}")
        phase_end_times.append(document.get('queueTargetTime'))
        print(document.get('queueTargetTime'))
    
    return phase_end_times

def fetch_settings():
    
    db = client['azienda']
    collection = db['settings']
    
    # Fetch the settings document
    settings = collection.find_one()
    
    if not settings:
        raise ValueError("No settings document found")
    
    return settings

from pymongo import MongoClient
import datetime

def get_phase_end_times(phases):
  
    db = client['process_db']
    collection = db['macchinari']
    
    phase_end_times = []
    for phase in phases:
        document = collection.find_one({"name": phase})
        if not document:
            raise ValueError(f"No document found for phase {phase}")
        phase_end_times.append(int(document.get('queueTargetTime', 0)))  # Ensure it's an int
    
    return phase_end_times

def fetch_settings():
    db = client['azienda']
    collection = db['settings']
    
    settings = collection.find_one()
    
    if not settings:
        raise ValueError("No settings document found")
    
    return settings

def find_start_date_of_phase(end_date, target_phase, quantity, open_time, holiday_list, pausa_pranzo, graph, durations):
    def traverse_backwards(current_id):
        if target_phase in current_id:
            return durations[current_id] * quantity
        if current_id not in reverse_graph:
            return None
        for prev_id in reverse_graph[current_id]:
            result = traverse_backwards(prev_id)
            if result is not None:
                return result + (durations[current_id] * quantity)
        return None

    reverse_graph = {k: [] for k in graph}
    for k, v in graph.items():
        for node in v:
            reverse_graph[node].append(k)

    pausa = datetime.timedelta(hours=pausa_pranzo['fine']['ore'], minutes=pausa_pranzo['fine']['minuti']) - \
            datetime.timedelta(hours=pausa_pranzo['inizio']['ore'], minutes=pausa_pranzo['inizio']['minuti'])
    minutes_in_day = datetime.timedelta(hours=end_date.hour, minutes=end_date.minute) - \
                     datetime.timedelta(hours=open_time['ore'], minutes=open_time['minuti']) - pausa

    end_nodes = [key for key, val in graph.items() if not val]
    for end_node in end_nodes:
        total_minutes = traverse_backwards(end_node)
        if total_minutes is not None:
            whole_days = total_minutes // minutes_in_day.total_seconds() // 60
            extra_minutes = total_minutes % minutes_in_day.total_seconds() // 60

            possible_date = end_date - datetime.timedelta(days=whole_days, minutes=extra_minutes)

            for day in (possible_date + datetime.timedelta(days=i) for i in range((end_date - possible_date).days + 1)):
                if day.weekday() >= 5:  # Saturday or Sunday
                    possible_date -= datetime.timedelta(days=1)
                for hol in holiday_list:
                    hol_start = datetime.datetime.fromtimestamp(hol['inizio']['$date']['$numberLong'] / 1000)
                    hol_end = datetime.datetime.fromtimestamp(hol['fine']['$date']['$numberLong'] / 1000)
                    if hol_start <= day <= hol_end:
                        possible_date -= datetime.timedelta(days=1)
            return possible_date
    return None

def create_order_object_with_dates(phases, codice_articolo, quantita, order_id, end_date, customer_deadline):
    settings = fetch_settings()
    
    open_time = settings.get('orariAzienda', {}).get('inizio', {'ore': 8, 'minuti': 0})
    holiday_list = settings.get('ferieAziendali', [])
    pausa_pranzo = settings.get('pausaPranzo', {'inizio': {'ore': 12, 'minuti': 0}, 'fine': {'ore': 15, 'minuti': 0}})

    graph = {phase: [] for phase in phases}
    for i in range(len(phases) - 1):
        graph[phases[i]].append(phases[i + 1])

    phase_end_times = get_phase_end_times(phases)
    durations = dict(zip(phases, phase_end_times))

    entrata_coda_fase = []
    for phase in phases:
        start_date = find_start_date_of_phase(end_date, phase, quantita, open_time, holiday_list, pausa_pranzo, graph, durations)
        entrata_coda_fase.append(datetime.datetime.now())#(int(start_date.timestamp() * 1000)) if start_date else None)
    
    current_time = datetime.datetime.now()
    order_object = {
        "codiceArticolo": codice_articolo,
        "orderDeadline": datetime.datetime.fromtimestamp((datetime.datetime.now() + datetime.timedelta(days=10)).timestamp() * 1000 / 1000),
        "customerDeadline":  customer_deadline,
        "orderDescription": "",
        "orderStartDate": datetime.datetime.fromtimestamp(current_time.timestamp() / 1000),
        "orderStatus":0,
        "phaseStatus": [0 for _ in phases],
        "assignedOperator": ["" for _ in phases],
        "phase": phases,
        "phaseEndTime": [time for time in phase_end_times],
        "phaseLateMotivation": ["none" for _ in phases],
        "phaseRealTime": [0 for _ in phases],
        "quantita": quantita,
        "entrataCodaFase": entrata_coda_fase,
        "orderId": order_id,
        "dataInizioLavorazioni":datetime.datetime.fromtimestamp(current_time.timestamp() / 1000),
        "priority": 0,
        "inCodaAt": ""
    }
    
    return order_object

def upload_order_to_db(order_object):
    db = client['orders_db']
    collection = db["newOrdini"]
    
    result = collection.insert_one(order_object)
    
    return result.inserted_id




# Example usage:
client = MongoClient(os.getenv("IMPORT_TEST_URI"))  

prodId = "583583357"
phases = get_procedure_phases_by_prodId(prodId)
print(phases)

phases = ["saldatura", "lucidatura"]
codice_articolo = "vent3XRed"
quantita = 5
order_id = "IMPORTED"
customer_deadline = datetime.datetime.now() + datetime.timedelta(days=40)  # Example customer deadline 40 days from now
end_date = datetime.datetime.now() + datetime.timedelta(days=30)  # Example end date 30 days from now
order_object = create_order_object_with_dates(phases, codice_articolo, quantita, order_id, end_date, customer_deadline)
print(order_object)

inserted_id = upload_order_to_db(order_object)
print(f"Order inserted with ID: {inserted_id}")