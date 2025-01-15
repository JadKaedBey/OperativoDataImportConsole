import datetime
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from bson import ObjectId

from date_utils import subtractWorkingMinutes

def fetch_flowchart_data(client: MongoClient, codice_articolo: str):
    """
    Recupera il flowchart (dashboard) della famiglia di prodotto
    associata al 'codice_articolo'. Ritorna:
      - graph:       mappa { id_nodo -> [nodi successivi] }
      - reverse_graph: mappa inversa { id_nodo -> [nodi precedenti] }
      - durations:   mappa { id_nodo -> durata base (in minuti) }
      - queues:      mappa { id_nodo -> tempo di coda (lead time) }
      - indegree:    mappa { id_nodo -> numero di archi in entrata }
      - dashboard:   il JSON completo salvato nella famiglia
    """
    db = client["process_db"]
    collection_famiglie = db["famiglie_di_prodotto"]
    collection_macchinari = db["macchinari"]

    # Trova la famiglia associata al codice_articolo
    family = collection_famiglie.find_one({"catalogo.prodId": codice_articolo})
    if not family:
        raise ValueError(f"Nessuna famiglia trovata per l'articolo {codice_articolo}")

    if "dashboard" not in family:
        raise ValueError("Dashboard non presente nel documento di famiglia.")

    dashboard = family["dashboard"]
    elements = dashboard.get("elements", [])

    # Scarica tutti i macchinari in un dizionario per associazione rapida
    macchinari = {
        m["name"].strip().lower(): m.get("queueTargetTime", 0)
        for m in collection_macchinari.find()
    }

    graph = {}
    reverse_graph = {}
    durations = {}
    queues = {}
    indegree = {}

    # Inizializzo i dict
    for node in elements:
        node_id = node.get("id", "")
        if not node_id:
            continue

        # Durata base della fase (in minuti)
        base_duration = node.get("phaseDuration", 0)
        durations[node_id] = base_duration

        # Recupero il tempo di coda dal dizionario macchinari
        # Recupero il nome di fase come "text"
        raw_phase_name = node.get("text", "")
        phase_name = raw_phase_name.strip().lower()

        queue_time = macchinari.get(phase_name, 0)
        queues[node_id] = queue_time


        # Ogni nodo ha i next
        next_nodes = []
        if "next" in node:
            for nxt in node["next"]:
                dest_id = nxt["destElementId"]
                next_nodes.append(dest_id)
                # Aggiorno indegree
                indegree[dest_id] = indegree.get(dest_id, 0) + 1

                # Costruisco reverse_graph
                if dest_id not in reverse_graph:
                    reverse_graph[dest_id] = []
                reverse_graph[dest_id].append(node_id)

        graph[node_id] = next_nodes

        # Se non c'è una voce in reverse_graph per node_id, la creo vuota
        if node_id not in reverse_graph:
            reverse_graph[node_id] = []

    return graph, reverse_graph, durations, queues, indegree, dashboard


def traverse_backwards(
    end_node: str,
    reverse_graph: Dict[str, List[str]],
    durations: Dict[str, int],
    queues: Dict[str, int],
    quantity: int,
    dashboard: Dict[str, Any],
) -> Optional[List[int]]:
    """
    Esempio semplificato di funzione che risale (backtracking)
    la catena di nodi partendo da 'end_node' per calcolare:
      - Tempo di coda complessivo
      - Tempo di ciclo complessivo
    Restituisce [queueTime, cycleTime] in minuti, oppure None se non trova nulla.

    L'idea è simile alla 'traverse_backwards' che hai nel tuo script,
    ma semplificata per questa demo.
    """

    visited = set()

    def dfs(node_id: str) -> Optional[List[int]]:
        # queueTime + cycleTime del nodo attuale
        my_queue = queues.get(node_id, 0)  # tempo di coda
        my_cycle = durations.get(node_id, 0) * quantity  # tempo di ciclo x quantita

        if node_id not in reverse_graph or not reverse_graph[node_id]:
            # Nodo senza predecessori: base case
            return [my_queue, my_cycle]

        # Se ha predecessori, li visito tutti e sommo
        total_queue = my_queue
        total_cycle = my_cycle

        for prev in reverse_graph[node_id]:
            if prev in visited:
                # Se l'ho già visitato, evito loop
                continue
            visited.add(prev)
            result = dfs(prev)
            if result:
                total_queue += result[0]
                total_cycle += result[1]

        return [total_queue, total_cycle]

    return dfs(end_node)


def get_family_title(client: MongoClient, codice_articolo: str) -> Optional[str]:
    """
    Restituisce il titolo della famiglia di prodotto legata a 'codice_articolo'.
    Nel tuo esempio, la chiave era 'titolo' o 'title'. Adattalo se necessario.
    """
    db = client["process_db"]
    collection = db["famiglie_di_prodotto"]
    family = collection.find_one({"catalogo.prodId": codice_articolo})

    if not family:
        raise ValueError("famiglia non trovata")
    return family.get("titolo", None)

def get_phase_text_from_dashboard(dashboard: dict, node_id: str) -> str:
    """Restituisce il 'text' dell'elemento con id == node_id, oppure stringa vuota."""
    node_element = next(
        (el for el in dashboard.get("elements", []) if el.get("id") == node_id),
        None
    )
    if node_element:
        return node_element.get("text", "")
    return ""


def build_order_new_model_backwards(
    client: MongoClient,
    codice_articolo: str,
    descrizione: str,
    quantity: int,
    order_id: str,
    customer_deadline: datetime,
    open_time: dict,
    close_time: dict,
    holiday_list: list,
    pausa_pranzo: dict,
) -> dict:
    """
    Esegue un calcolo "backwards" identico (o molto simile) alla logica in Dart:
      - Per ogni fase finale, finishDate = customerDeadline
        e queueInsertDate = finishDate - (queueTime) (in ore lavorative).
      - Per le fasi intermedie: finishDate = min(queueInsertDate dei figli),
        queueInsertDate = finishDate - (queueTime).
      - Infine crea l'ordine (nuovo modello) con campi come `Phases`, `startPhasesList`, ecc.
    """

    # ----- 1) Scarico il flowchart (grafo) -----
    graph, reverse_graph, durations, queues, indegree, dashboard = fetch_flowchart_data(
        client, codice_articolo
    )

    # ----- 2) Preparo strutture di appoggio per salvare date per ogni nodo -----
    finish_date_map = {}
    queue_insert_map = {}

    # I nodi finali (end_nodes) sono quelli senza successori
    end_nodes = [nid for nid, nxts in graph.items() if not nxts]

    # ----- 3) Preparo code/strutture per un BFS "all'indietro" -----
    #    - outdegree ci serve per sapere quanti figli ha un nodo;
    #      quando scende a 0 significa che tutti i figli sono già calcolati.
    outdegree = {}
    for nid, nxts in graph.items():
        outdegree[nid] = len(nxts)

    from collections import deque
    queue_bfs = deque()

    # ----- 4) Inizializzo le fasi finali -----
    # Per ciascun end_node: finishDate = customerDeadline
    # queueInsertDate = subtractWorkingMinutes(customerDeadline, queue)
    for end_node in end_nodes:
        finish_date_map[end_node] = customer_deadline  # per l'ultima fase
        cycle_time = durations.get(end_node, 0) * quantity
        raw_phase_name = get_phase_text_from_dashboard(dashboard, end_node)
        phase_name_key = raw_phase_name.strip().lower()
        queue_time = queues.get(phase_name_key, 0)


        queue_insert = subtractWorkingMinutes(
            customer_deadline,
            queue_time,
            time(open_time["ore"], open_time["minuti"]),
            time(close_time["ore"], close_time["minuti"]),
            holiday_list,
            time(pausa_pranzo["inizio"]["ore"], pausa_pranzo["inizio"]["minuti"]),
            time(pausa_pranzo["fine"]["ore"], pausa_pranzo["fine"]["minuti"]),
            timedelta(
                hours=pausa_pranzo["fine"]["ore"],
                minutes=pausa_pranzo["fine"]["minuti"],
            )
            - timedelta(
                hours=pausa_pranzo["inizio"]["ore"],
                minutes=pausa_pranzo["inizio"]["minuti"],
            ),
        )
        queue_insert_map[end_node] = queue_insert
        # Metto in coda BFS
        queue_bfs.append(end_node)

    # ----- 5) BFS all'indietro: una volta calcolate le date di tutti i figli, aggiorno il padre -----
    visited = set(end_nodes)

    while queue_bfs:
        current = queue_bfs.popleft()
        # Prendo i predecessori di current
        preds = reverse_graph.get(current, [])
        for pred in preds:
            if pred not in visited:
                # Decremento l'outdegree del pred --> ho "consumato" un figlio
                outdegree[pred] -= 1
                # Se outdegree[pred] == 0, significa che TUTTI i figli di pred sono calcolati
                if outdegree[pred] == 0:
                    # 1) finishDate[pred] = min(queueInsertMap[child] for child in graph[pred])
                    children = graph[pred]
                    if children:
                        # prendo la minima fra le queueInsertDate dei figli
                        min_queue = min(queue_insert_map[ch] for ch in children)
                        finish_date_map[pred] = min_queue
                    else:
                        # se non ha figli (potrebbe essere end_node, ma in teoria
                        # lo avremmo già fatto sopra)
                        finish_date_map[pred] = customer_deadline

                    # 2) queueInsertDate[pred] = finishDate[pred] - (queueTime)
                    cycle_time = durations.get(pred, 0) * quantity
                    queue_time = queues.get(phase_name_key, 0)

                    queue_insert = subtractWorkingMinutes(
                        finish_date_map[pred],
                        cycle_time + queue_time,
                        time(open_time["ore"], open_time["minuti"]),
                        time(close_time["ore"], close_time["minuti"]),
                        holiday_list,
                        time(pausa_pranzo["inizio"]["ore"], pausa_pranzo["inizio"]["minuti"]),
                        time(pausa_pranzo["fine"]["ore"], pausa_pranzo["fine"]["minuti"]),
                        timedelta(
                            hours=pausa_pranzo["fine"]["ore"],
                            minutes=pausa_pranzo["fine"]["minuti"],
                        )
                        - timedelta(
                            hours=pausa_pranzo["inizio"]["ore"],
                            minutes=pausa_pranzo["inizio"]["minuti"],
                        ),
                    )
                    queue_insert_map[pred] = queue_insert
                    # Aggiungo pred alla coda BFS
                    visited.add(pred)
                    queue_bfs.append(pred)

    # ----- 6) Ora ho queueInsertMap[node] e finishDateMap[node] per tutti i nodi -----
    # Costruisco le "Phases"
    phases_list = []
    now_ts = datetime.now()

    # Creo i campi necessari
    for node_id in graph.keys():
        cycle_time = durations.get(node_id, 0) * quantity
        # queue_time = queues.get(node_id, 0)
        finish_date = finish_date_map.get(node_id, customer_deadline)
        queue_insert_date = queue_insert_map.get(node_id, customer_deadline)

        # Recupera il nome della fase dal campo "text" del dashboard
        phase_name = next(
            (el["text"] for el in dashboard.get("elements", []) if str(el.get("id")) == str(node_id) and "text" in el),
            f"Fase_{node_id}"  # Fallback se non trovato
        )



        # Predecessori e successori
        prev_phases = reverse_graph.get(node_id, [])
        next_phases = graph.get(node_id, [])

        phase_dict = {
            "phaseId": node_id,
            "phaseName": phase_name,
            "phaseStatus": 1,
            "phaseRealTime": 0,
            "cycleTime": cycle_time,
            "queueInsertDate": queue_insert_date,
            "queueRealInsertDate": None,
            "finishDate": finish_date,
            "realFinishDate": None,
            "phaseLateMotivation": "",
            "operators": [],
            "inCodaAt": [],
            "inLavorazioneAt": "",
            "previousPhases": prev_phases,
            "nextPhases": next_phases,
        }
        phases_list.append(phase_dict)

    # ----- 7) Identifico le fasi "iniziali" (senza predecessori) -----
    start_phases_list = [
        p["phaseId"] for p in phases_list if not p["previousPhases"]
    ]

    # ----- 8) Calcolo orderStartDate e orderDeadline -----
    # In base ai valori calcolati (min di queueInsertDate, max di finishDate)
    if not phases_list:
        order_start_date = now_ts
        order_deadline = customer_deadline
    else:
        order_start_date = min(p["queueInsertDate"] for p in phases_list)
        order_deadline = max(p["finishDate"] for p in phases_list)

    # ----- 9) Recupero il nome/famiglia di prodotto (opzionale) -----
    famiglia_di_prodotto = get_family_title(client, codice_articolo)

    new_order_document = {
        "_id": ObjectId(),
        "orderId": order_id,
        "codiceArticolo": codice_articolo,
        "famigliaDiProdotto": famiglia_di_prodotto,
        "orderDescription": descrizione,
        "orderStatus": 0,
        "orderInsertDate": now_ts,
        "orderStartDate": order_start_date,
        "orderDeadline": order_deadline,
        "customerDeadline": customer_deadline,
        "realOrderFinishDate": None,
        "priority": 0,
        "quantity": quantity,
        "Phases": phases_list,
        "startPhasesList": start_phases_list,
        "selectedPhase": None,
    }

    return new_order_document


def build_order_new_model(
    client: MongoClient,
    codice_articolo: str,
    descrizione: str,
    quantity: int,
    order_id: str,
    customer_deadline: datetime,
    open_time: dict,
    close_time: dict,
    holiday_list: list,
    pausa_pranzo: dict,
) -> dict:
    """
    Costruisce un nuovo ordine (dizionario) con il formato
    del nuovo modello Dart (Ordine + Phase).
    """

    # 1) Recupero il flowchart
    graph, reverse_graph, durations, queues, indegree, dashboard = fetch_flowchart_data(
        client, codice_articolo
    )

    # 2) Individuo i nodi finali (senza successori)
    end_nodes = [node_id for node_id, edges in graph.items() if not edges]

    # Esempio: calcolo i tempi totali di coda/ciclo (sommati) partendo dai nodi finali
    # Nota che nel Dart si fa un calcolo più dettagliato per ogni singola fase.
    # Qui, per semplificare, mostriamo come potresti usare traverse_backwards.
    for end_node in end_nodes:
        total_minutes = traverse_backwards(
            end_node,
            reverse_graph,
            durations,
            queues,
            quantity,
            dashboard
        )
        # total_minutes = [queueTime, cycleTime]
        # Se volessi, potresti convertire questi in date di inizio / fine della "fase finale"
        # e poi proseguire a ritroso per ogni nodo, salvando i dati.
        # Nel Dart usi 'calculate_phase_dates' o simili. Qui è un esempio base.

    # 3) Creiamo la lista di TUTTE le fasi
    #    In uno scenario reale, calcoleresti 'queueInsertDate' e 'finishDate'
    #    per ciascun nodo con la logica simile a "calculate_phase_dates".
    all_nodes = list(graph.keys())

    # Per un esempio funzionante, qui assumiamo di NON fare un calcolo di date
    # specifico per ogni nodo, ma solo di impostare valori di base.
    # In un contesto reale, useresti la stessa logica del Dart
    # (o una portata in Python) per ogni nodo.
    phases_list = []
    now_ts = datetime.now()

    # Ricavo orari in Python 'time' e pausa
    start_work = time(open_time["ore"], open_time["minuti"])
    end_work = time(close_time["ore"], close_time["minuti"])
    lunch_start = time(pausa_pranzo["inizio"]["ore"], pausa_pranzo["inizio"]["minuti"])
    lunch_end = time(pausa_pranzo["fine"]["ore"], pausa_pranzo["fine"]["minuti"])
    pausa_duration = (datetime.combine(now_ts, lunch_end) - datetime.combine(now_ts, lunch_start))

    for node_id in all_nodes:
        node_cycle_time = durations.get(node_id, 0) * quantity
        node_queue_time = queues.get(node_id, 0)

        # Esempio: fingo di calcolare la finishDate come
        # (customer_deadline - cycle_time in minuti) e la queueInsertDate
        # come (finishDate - queue_time in minuti).
        # In verità, potresti dover fare un calcolo più “multilivello” come
        # nel tuo Dart, ma qui diamo un’idea.
        finish_date = subtractWorkingMinutes(
            customer_deadline,
            node_cycle_time,
            start_work,
            end_work,
            holiday_list,
            lunch_start,
            lunch_end,
            pausa_duration
        )
        queue_insert_date = subtractWorkingMinutes(
            finish_date,
            node_queue_time,
            start_work,
            end_work,
            holiday_list,
            lunch_start,
            lunch_end,
            pausa_duration
        )

        phase_name = f"Fase_{node_id}"

        # Raccogli i predecessori e successori
        prev_phases = reverse_graph.get(node_id, [])
        next_phases = graph.get(node_id, [])

        # Assemblo il dizionario Phase
        phase_dict = {
            "phaseId": node_id,
            "phaseName": phase_name,
            "phaseStatus": 1,
            "phaseRealTime": 0,
            "cycleTime": node_cycle_time,
            "queueInsertDate": queue_insert_date,
            "queueRealInsertDate": None,
            "finishDate": finish_date,
            "realFinishDate": None,
            "phaseLateMotivation": "",
            "operators": [],
            "inCodaAt": [],
            "inLavorazioneAt": "",
            "previousPhases": prev_phases,  # ["idA", "idB", ...]
            "nextPhases": next_phases,      # ["idC", "idD", ...]
        }
        phases_list.append(phase_dict)

    # Identifico le fasi di “ingresso” (senza predecessori)
    start_phases_list = [
        p["phaseId"] for p in phases_list if not p["previousPhases"]
    ]

    # Calcolo orderStartDate e orderDeadline
    # min queueInsertDate e max finishDate tra le fasi (come suggerito in Dart)
    if len(phases_list) == 0:
        order_start_date = now_ts
        order_deadline = customer_deadline
    else:
        order_start_date = min(p["queueInsertDate"] for p in phases_list)
        order_deadline = max(p["finishDate"] for p in phases_list)

    famiglia_di_prodotto = get_family_title(client, codice_articolo) or "???"

    new_order_document = {
        "_id": ObjectId(),
        "orderId": order_id,
        "codiceArticolo": codice_articolo,
        "famigliaDiProdotto": famiglia_di_prodotto,
        "orderDescription": descrizione,
        "orderStatus": 0,
        "orderInsertDate": now_ts,
        "orderStartDate": order_start_date,
        "orderDeadline": order_deadline,
        "customerDeadline": customer_deadline,
        "realOrderFinishDate": None,
        "priority": 0,
        "quantity": quantity,
        "Phases": phases_list,
        "startPhasesList": start_phases_list,
        "selectedPhase": None,
    }

    return new_order_document