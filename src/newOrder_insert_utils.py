import datetime
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from bson import ObjectId

from date_utils import subtractWorkingMinutes

def fetch_flowchart_data(client: MongoClient, codice_articolo: str):
    # Controllo preliminare sul parametro codice_articolo
    if not codice_articolo or not isinstance(codice_articolo, str):
        raise ValueError("Il codice_articolo deve essere una stringa non vuota.")
    
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

    for node in elements:
        node_id = node.get("id", "")
        if not node_id:
            continue

        # Utilizza il campo 'phaseDuration' (se presente) altrimenti 0
        base_duration = node.get("phaseDuration", 0)
        durations[node_id] = base_duration

        raw_phase_name = node.get("text", "")
        phase_name = raw_phase_name.strip().lower()
        queue_time = macchinari.get(phase_name, 0)
        queues[node_id] = queue_time

        next_nodes = []
        if "next" in node:
            for nxt in node["next"]:
                dest_id = nxt["destElementId"]
                next_nodes.append(dest_id)
                indegree[dest_id] = indegree.get(dest_id, 0) + 1
                reverse_graph.setdefault(dest_id, []).append(node_id)
        graph[node_id] = next_nodes
        if node_id not in reverse_graph:
            reverse_graph[node_id] = []

    return graph, reverse_graph, durations, queues, indegree, dashboard


def get_family_title(client: MongoClient, codice_articolo: str) -> Optional[str]:
    # Controllo preliminare sul parametro codice_articolo
    if not codice_articolo or not isinstance(codice_articolo, str):
        raise ValueError("Il codice_articolo deve essere una stringa non vuota.")

    db = client["process_db"]
    collection = db["famiglie_di_prodotto"]
    family = collection.find_one({"catalogo.prodId": codice_articolo})
    if not family:
        raise ValueError(f"Nessuna famiglia trovata per l'articolo {codice_articolo}")
    return family.get("titolo", None)



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
    # ----- 1) Scarico il flowchart (grafo) -----
    graph, reverse_graph, durations, queues, indegree, dashboard = fetch_flowchart_data(
        client, codice_articolo
    )
    # DEBUG: stampo l'intero grafo per verificare i next
    print(f"[DEBUG] Graph (next nodes per nodo): {graph}")

    # ----- 2) Preparo strutture per salvare le date per ogni nodo -----
    finish_date_map = {}
    queue_insert_map = {}

    # I nodi finali (end_nodes) sono quelli senza successori
    end_nodes = [nid for nid, nxts in graph.items() if not nxts]

    # ----- 3) Preparo struttura per la BFS "all'indietro" -----
    outdegree = {nid: len(nxts) for nid, nxts in graph.items()}
    from collections import deque
    queue_bfs = deque()

    # ----- 4) Inizializzo le fasi finali -----
    for end_node in end_nodes:
        finish_date_map[end_node] = customer_deadline
        queue_time = queues.get(end_node, 0)
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
            ) - timedelta(
                hours=pausa_pranzo["inizio"]["ore"],
                minutes=pausa_pranzo["inizio"]["minuti"],
            ),
        )
        queue_insert_map[end_node] = queue_insert
        queue_bfs.append(end_node)

    # ----- 5) BFS all'indietro per aggiornare le date dei nodi -----
    visited = set(end_nodes)
    while queue_bfs:
        current = queue_bfs.popleft()
        for pred in reverse_graph.get(current, []):
            if pred not in visited:
                outdegree[pred] -= 1
                if outdegree[pred] == 0:
                    children = graph[pred]
                    finish_date_map[pred] = (
                        min(queue_insert_map[ch] for ch in children)
                        if children
                        else customer_deadline
                    )
                    queue_time = queues.get(pred, 0)
                    queue_insert = subtractWorkingMinutes(
                        finish_date_map[pred],
                        queue_time,
                        time(open_time["ore"], open_time["minuti"]),
                        time(close_time["ore"], close_time["minuti"]),
                        holiday_list,
                        time(pausa_pranzo["inizio"]["ore"], pausa_pranzo["inizio"]["minuti"]),
                        time(pausa_pranzo["fine"]["ore"], pausa_pranzo["fine"]["minuti"]),
                        timedelta(
                            hours=pausa_pranzo["fine"]["ore"],
                            minutes=pausa_pranzo["fine"]["minuti"],
                        ) - timedelta(
                            hours=pausa_pranzo["inizio"]["ore"],
                            minutes=pausa_pranzo["inizio"]["minuti"],
                        ),
                    )
                    queue_insert_map[pred] = queue_insert
                    visited.add(pred)
                    queue_bfs.append(pred)

    # ----- 6) Costruisco le fasi (inserendo "phaseDescription" se presente) -----
    phases_list = []
    now_ts = datetime.now()
    for node_id in graph.keys():
        cycle_time = durations.get(node_id, 0) * quantity
        finish_date = finish_date_map.get(node_id, customer_deadline)
        queue_insert_date = queue_insert_map.get(node_id, customer_deadline)

        # Recupera il nome della fase dalla dashboard (campo "text")
        phase_name = next(
            (el["text"] for el in dashboard.get("elements", [])
             if str(el.get("id")) == str(node_id) and "text" in el),
            f"Fase_{node_id}"
        )
        # Recupera la descrizione della fase dalla dashboard (campo "phaseDescription")
        phase_description = next(
            (el.get("phaseDescription") for el in dashboard.get("elements", [])
             if str(el.get("id")) == str(node_id) and el.get("phaseDescription")),
            None
        )
        prev_phases = reverse_graph.get(node_id, [])
        next_phases = graph.get(node_id, [])
        
        # DEBUG: verifico il contenuto di nextPhases per il nodo corrente
        print(f"[DEBUG] Nodo {node_id}: nextPhases = {next_phases}")

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
        if phase_description is not None:
            phase_dict["phaseDescription"] = phase_description
        phases_list.append(phase_dict)

    start_phases_list = [p["phaseId"] for p in phases_list if not p["previousPhases"]]
    order_start_date = min((p["queueInsertDate"] for p in phases_list), default=now_ts)
    order_deadline = max((p["finishDate"] for p in phases_list), default=customer_deadline)
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
