import datetime
from datetime import timedelta

def find_start_date_of_phase(
    end_date,
    target_phase,
    quantity,
    open_time,
    close_time,
    holiday_list,
    pausa_pranzo,
    graph,
    reverse_graph,
    queues,
    dashboard,
    durations,
    duration=-1,
):
    """
    Find the start date of a phase by traversing backwards from the end nodes.
    """
    print("Trying to find Start date of phase for", target_phase)

    start_work = datetime.time(open_time["ore"], open_time["minuti"])
    end_work = datetime.time(close_time["ore"], close_time["minuti"])
    lunch_start = datetime.time(
        pausa_pranzo["inizio"]["ore"], pausa_pranzo["inizio"]["minuti"]
    )
    lunch_end = datetime.time(
        pausa_pranzo["fine"]["ore"], pausa_pranzo["fine"]["minuti"]
    )
    # pausa_pranzo = lunch_end - lunch_start

    # Create a mapping of phase names to node IDs
    phase_name_to_id = {
        node["text"]: node["id"] for node in dashboard.get("elements", [])
    }

    # Check if the target_phase exists in the mapping
    if target_phase not in phase_name_to_id:
        raise ValueError(f"Target phase '{target_phase}' not found in the dashboard.")

    # Get the node ID corresponding to the target phase
    target_phase_id = phase_name_to_id[target_phase]
    print(f"Target phase '{target_phase}' corresponds to node ID: {target_phase_id}")

    # Function to traverse the graph backwards from the end nodes to find the target phase
    def traverse_backwards(current_id):
        print(
            f"Traversing node: {current_id}, looking for target phase: {target_phase_id}"
        )
        if current_id == target_phase_id:
            print(f"Found target phase: {current_id}")
            return [
                queues[current_id],
                duration if duration >= 0 else durations[current_id] * quantity,
            ]

        if current_id not in reverse_graph:
            print("Target phase not in reverse_graph: returning None", current_id)
            return None

        for prev_id in reverse_graph[current_id]:
            print(f"Traversing to previous node: {prev_id}")
            result = traverse_backwards(prev_id)
            if result:
                print(f"Found path from {current_id} to {prev_id}: {result}")
                return [
                    result[0] + queues[current_id],
                    result[1]
                    + (duration if duration >= 0 else durations[current_id] * quantity),
                ]

        print(f"No valid path found for node: {current_id}")
        return None

    # Calculate time durations
    pausa_duration = datetime.timedelta(
        hours=pausa_pranzo["fine"]["ore"], minutes=pausa_pranzo["fine"]["minuti"]
    ) - datetime.timedelta(
        hours=pausa_pranzo["inizio"]["ore"], minutes=pausa_pranzo["inizio"]["minuti"]
    )

    print("Found pausa_duration equal to", pausa_duration)

    minutes_in_day = (
        datetime.timedelta(hours=close_time["ore"], minutes=close_time["minuti"])
        - datetime.timedelta(hours=open_time["ore"], minutes=open_time["minuti"])
        - pausa_duration
    ).total_seconds() / 60

    print("Found minutes_in_day equal to", minutes_in_day)

    print("Check the structure of reverse_graph ", reverse_graph)

    end_nodes = [node_id for node_id, edges in graph.items() if not edges]

    print("End nodes: ", end_nodes)

    def adjust_to_work_hours(possible_date):

        print("Company Hours:")
        print(start_work)
        print(end_work)
        print(lunch_start)
        print(lunch_end)

        # Check for holidays
        if any(
            holiday["inizio"].date() <= possible_date.date() <= holiday["fine"].date()
            for holiday in holiday_list
        ):
            possible_date -= timedelta(days=1)
            possible_date = possible_date.replace(
                hour=start_work.hour, minute=start_work.minute
            )
            return adjust_to_work_hours(possible_date)

        # Adjust time if before or after working hours
        if possible_date.time() < start_work:
            possible_date = possible_date.replace(
                hour=start_work.hour, minute=start_work.minute
            )
        elif possible_date.time() > end_work:
            possible_date = possible_date + timedelta(days=1)
            possible_date = possible_date.replace(
                hour=start_work.hour, minute=start_work.minute
            )

        # Adjust if within lunch break
        if lunch_start <= possible_date.time() <= lunch_end:
            possible_date = possible_date.replace(
                hour=lunch_end.hour, minute=lunch_end.minute
            )

        return possible_date

    # Calculate time respecting working hours and holidays
    def calculate_possible_date(total_minutes, end_date):
        """
        Old Function used to calculate possible dates, deprecated for now, replaced with subtractWorkingMinutes

        """
        print("Calculating possible date")
        possible_date = end_date - timedelta(
            days=total_minutes // minutes_in_day, minutes=total_minutes % minutes_in_day
        )
        print("Possible date before adjusting", possible_date)
        possible_date = adjust_to_work_hours(possible_date)
        print("Possible date after adjusting", possible_date)

        # Check for weekends and holidays
        while possible_date.weekday() in [5, 6]:  # Saturday (5) or Sunday (6)
            possible_date -= timedelta(days=2)
            possible_date = adjust_to_work_hours(possible_date)

        print("Possible date found: ", possible_date)
        return possible_date

    for end_node in end_nodes:
        print("Trying to traverse_backwards")
        total_minutes = traverse_backwards(end_node)  # totalLeadTime
        print("Finished traverse_backwards, total_minutes:", total_minutes)
        if total_minutes:
            # possible_queue_date = calculate_possible_date(total_minutes[0], end_date) # was 1
            # possible_cycle_date = calculate_possible_date(total_minutes[1], end_date) # was 0
            possible_queue_date = subtractWorkingMinutes(
                end_date,
                total_minutes[0],
                start_work,
                end_work,
                holiday_list,
                lunch_start,
                lunch_end,
                pausa_duration,
            )  # was 0
            possible_cycle_date = subtractWorkingMinutes(
                end_date,
                total_minutes[1],
                start_work,
                end_work,
                holiday_list,
                lunch_start,
                lunch_end,
                pausa_duration,
            )  # was 0

            print(
                "Found possible_queue_date and possible_cycle_date",
                possible_queue_date,
                possible_cycle_date,
            )

            return [[possible_queue_date], [possible_cycle_date]]

    return None


def calculate_phase_dates(client, end_date, phases, quantity, settings, codiceArticolo):

    print("Calculating Phase Dates")
    open_time = settings.get("orariAzienda", {}).get("inizio", {"ore": 8, "minuti": 0})
    close_time = settings.get("orariAzienda", {}).get("fine", {"ore": 18, "minuti": 0})
    holiday_list = settings.get("ferieAziendali", [])
    pausa_pranzo = settings.get(
        "pausaPranzo",
        {"inizio": {"ore": 12, "minuti": 0}, "fine": {"ore": 15, "minuti": 0}},
    )

    print("Open Time:", open_time)
    print("Close Time:", close_time)
    print("Holiday Time:", holiday_list)
    print("Pausa Time:", pausa_pranzo)

    # phase_durations = get_phase_end_times(phases, codiceArticolo) # Not needed with new alg

    # print('Got Phase durations (Tempo ciclo):', phase_durations)

    entrata_coda_fase = []

    for i, phase in enumerate(phases):
        # Calculate phase duration based on quantity
        # duration = phase_durations[i] * quantity

        graph, reverse_graph, durations, queues, indegree, dashboard = (
            fetch_flowchart_data(client, codiceArticolo)
        )  # durations not needed anymore

        print("checking end_date type", type(end_date))
        print("checking end_date value", end_date)
        # Calculate start date for the phase, taking into account work hours, breaks, and holidays
        start_date = find_start_date_of_phase(
            end_date,
            phase,  # target phase
            quantity,
            open_time,
            close_time,
            holiday_list,
            pausa_pranzo,
            graph,
            reverse_graph,
            queues,
            dashboard,
            durations,
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
        # end_date = start_date[0][0] if start_date else end_date

    print("Entrata coda phase:", entrata_coda_fase)
    return entrata_coda_fase


def fetch_flowchart_data(client, codiceArticolo):
    db = client["process_db"]
    collection = db["famiglie_di_prodotto"]

    # Fetch the family document from the collection
    family = collection.find_one({"catalogo.prodId": codiceArticolo})

    print("Found Family:", family["titolo"])

    if not family or "dashboard" not in family:
        raise ValueError("No valid dashboard found for the given family ID.")

    dashboard = family["dashboard"]
    graph = {}
    reverse_graph = {}
    durations = {}
    queues = {}
    indegree = {}

    elements = dashboard.get("elements", [])
    for node in elements:
        node_id = node["id"]
        duration = node.get("phaseDuration", 0)
        # queue = node.get('phaseTargetQueue', duration) Old method to get queue from family dashboard
        queue = get_lead_time_from_macchinari(
            client, node.get("text")
        )  # pass nome fase + client for db fetching
        # Initialize the node in the graph
        durations[node_id] = duration
        queues[node_id] = queue
        graph[node_id] = []

        # Ensure every node is initialized in the reverse_graph (even without incoming edges)
        if node_id not in reverse_graph:
            reverse_graph[node_id] = []

        # Process connections (outgoing edges)
        for next_node in node.get("next", []):
            dest_id = next_node["destElementId"]
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


def get_lead_time_from_macchinari(client, fase):
    process_db = client["process_db"]
    macchinari = process_db["macchinari"]

    mach = macchinari.find_one({"name": fase})
    mach_lead_time = 0
    if mach:
        mach_lead_time = mach.get("queueTargetTime")

    return mach_lead_time


def subtractWorkingMinutes(
    end_date,
    total_minutes,
    start_work,
    end_work,
    holiday,
    lunch_start,
    lunch_end,
    pausa_duration,
):
    # total_minutes is totalLeadTime

    current_date = end_date
    minutes_remaining = total_minutes

    working_minutes_per_day = (
        datetime.timedelta(hours=end_work.hour, minutes=end_work.minute)
        - datetime.timedelta(hours=start_work.hour, minutes=start_work.minute)
        - pausa_duration
    ).total_seconds() / 60

    print("Found working mins per day", working_minutes_per_day)

    while minutes_remaining > 0:
        # Move to previous day
        current_date -= timedelta(days=1)

        # Skip weekends (Saturday=5, Sunday=6 in Python's weekday())
        if current_date.weekday() >= 5:
            continue

        # Skip holidays
        is_holiday = False
        for hol in holiday:
            if hol["inizio"].date() <= current_date.date() <= hol["fine"].date():
                is_holiday = True
                break
        if is_holiday:
            continue

        # Subtract working minutes of the day
        if minutes_remaining >= working_minutes_per_day:
            minutes_remaining -= working_minutes_per_day
        else:
            # Remaining minutes less than a day's work
            minutes_to_subtract_today = minutes_remaining

            # Set the time to open time
            current_date = current_date.replace(
                hour=start_work.hour, minute=start_work.minute, second=0, microsecond=0
            )

            # Add the remaining minutes to current_date
            current_date += timedelta(minutes=minutes_to_subtract_today)

            minutes_remaining = 0

            # Return the calculated date
            return current_date

        # After subtracting all the minutes, set the time to open time
        current_date = current_date.replace(
            hour=start_work.hour, minute=start_work.minute, second=0, microsecond=0
        )

    return current_date
