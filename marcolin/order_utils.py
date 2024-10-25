import datetime


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

def fetch_settings():
    global client
    db = client['azienda']
    collection = db['settings']
    
    # Fetch the settings document
    settings = collection.find_one()
    
    if not settings:
        raise ValueError("No settings document found")
    
    return settings

def calculate_phase_dates(end_date, phases, quantity, settings, codiceArticolo):
    # settings = fetch_settings()
    
    # Existing time-related calculations
    open_time = settings.get('orariAzienda', {}).get('inizio', {'ore': 8, 'minuti': 0})
    close_time = settings.get('orariAzienda', {}).get('fine', {'ore': 19, 'minuti': 0})
    holiday_list = settings.get('ferieAziendali', [])
    pausa_pranzo = settings.get('pausaPranzo', {'inizio': {'ore': 12, 'minuti': 0}, 'fine': {'ore': 13, 'minuti': 0}})

    phase_durations = get_phase_end_times(phases, codiceArticolo)
    
    # Process the phases sequentially based on the graph structure
    entrata_coda_fase = []
    current_end_date = end_date  # Initialize with the overall end date (the deadline)

    # Traverse phases in reverse (starting from the last phase)
    for i in reversed(range(len(phases))):
        phase = phases[i]
        duration = phase_durations[i] * quantity
        graph, reverse_graph, durations, queues, indegree, dashboard = fetch_flowchart_data(codiceArticolo)

        # Calculate the start date for the current phase based on the current end date
        start_date = find_start_date_of_phase(
            current_end_date,
            phase,
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
        
        if start_date:
            print(f"Phase {phase}: Calculated start_date = {start_date}")
            possible_start_date = start_date
            if isinstance(possible_start_date, pd.Timestamp):
                possible_start_date = possible_start_date.to_pydatetime()

            # Append the start date to the phase dates list
            entrata_coda_fase.insert(0, possible_start_date)  # Insert at the beginning to maintain correct order
        else:
            entrata_coda_fase.insert(0, None)

        # Update the end date for the next (previous) phase
        current_end_date = start_date if start_date else current_end_date

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
            return queues[current_id]  # Only queue time should be accumulated
        
        if current_id not in reverse_graph:
            print('Target phase not in reverse_graph: returning None', current_id)
            return None
        
        for prev_id in reverse_graph[current_id]:
            print(f"Traversing to previous node: {prev_id}")
            result = traverse_backwards(prev_id)
            if result is not None:
                print(f"Found path from {current_id} to {prev_id}: {result}")
                return result + queues[current_id]  # Accumulate total queue time
                
        print(f"No valid path found for node: {current_id}")
        return None

    # Get all end nodes (those with no outgoing edges)
    end_nodes = [node_id for node_id, edges in graph.items() if not edges]
    
    print('End nodes: ', end_nodes)

    # Traverse from end nodes backward to accumulate queue times
    for end_node in end_nodes:
        print("Trying to traverse_backwards")
        total_lead_time = traverse_backwards(end_node)
        print('Finished traverse_backwards, total_lead_time:', total_lead_time)

        if total_lead_time is not None:
            # Calculate possible start date by subtracting the total lead time (queue time)
            possible_start_date = subtract_working_minutes(
                end_date,
                total_lead_time,
                open_time,
                close_time,
                holiday_list,
                pausa_pranzo
            )
            print('Found possible_start_date', possible_start_date)

            # Return the possible start date twice (as in Flutter)
            return possible_start_date

    return None

# Utils

def subtract_working_minutes(end_date, minutes_to_subtract, open_time, close_time, holiday_list, pausa_pranzo):
    current_date = end_date
    minutes_remaining = minutes_to_subtract

    pausa_duration = (datetime.timedelta(hours=pausa_pranzo['fine']['ore'], minutes=pausa_pranzo['fine']['minuti']) - 
                      datetime.timedelta(hours=pausa_pranzo['inizio']['ore'], minutes=pausa_pranzo['inizio']['minuti']))
    working_minutes_per_day = (datetime.timedelta(hours=close_time['ore'], minutes=close_time['minuti']) - 
                               datetime.timedelta(hours=open_time['ore'], minutes=open_time['minuti']) - 
                               pausa_duration).total_seconds() / 60

    while minutes_remaining > 0:
        # Move to the previous day
        current_date -= datetime.timedelta(days=1)

        # Skip weekends (Saturday=5, Sunday=6)
        if current_date.weekday() in [5, 6]:
            continue

        # Skip holidays
        if any(holiday['inizio'].date() <= current_date.date() <= holiday['fine'].date() for holiday in holiday_list):
            continue

        if minutes_remaining >= working_minutes_per_day:
            minutes_remaining -= working_minutes_per_day
        else:
            # Subtract the remaining minutes for the current day
            current_date = current_date.replace(hour=open_time['ore'], minute=open_time['minuti'])
            current_date = current_date + timedelta(minutes=minutes_remaining)
            minutes_remaining = 0
            return current_date

    current_date = current_date.replace(hour=open_time['ore'], minute=open_time['minuti'])
    return current_date


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
    
    # # Check if phase_dates is sorted in increasing order
    # if phase_dates != sorted(phase_dates): 
    #     # If not sorted (increasing order), reverse the array (because the starting date is at the end)
    #     phase_dates.reverse()
    #     print('Phase dates after sorting check:', phase_dates)

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
        "entrataCodaFase": [[date if not isinstance(date, pd.Timestamp) else date.to_pydatetime()] for date in phase_dates],
        "priority": 0,  # Default priority
        "inCodaAt": [],  
        "inLavorazioneAt": [[""] for _ in phases],
    }
    
    return order_object