import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QDialog,
    QGridLayout,
    QComboBox,
    QDialogButtonBox,
    QHBoxLayout,
)
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
from family_insert_utils import create_json_for_flowchart, safe_parse_literal, show_family_upload_report


# -------------- NUOVE IMPORTAZIONI -------------
# (Assumendo che i file "newOrder_insert_utils.py" e "newOrder_model.py" siano nel path)
from newOrder_insert_utils import build_order_new_model_backwards  # <-- Nuova funzione di calcolo/inserimento
from models.newOrder_model import NewOrderModel, PhaseModel      # <-- Nuovi modelli
from report_utils import save_report_to_file
from report_utils import show_upload_report

# Se serve ancora qualche funzione per import (tipo "subtractWorkingMinutes" ecc.),
# le importerai da newOrder_insert_utils
# ------------------------------------------------

from export_utils import (
    order_status_mapper,
    phase_status_mapper,
    column_mapping,
    fetch_in_coda_at_names,
    map_in_lavorazione_at_value,
    fetch_in_lavorazione_at_names,
    map_in_coda_at_value,
    parse_entrata_coda_fase,
    create_new_row,
    format_queue_entry_time,
    parse_columns,
    calculate_in_coda,
    parse_value,
)
# ATTENZIONE: "order_insert_utils.py" era il vecchio file, ora sostituito da newOrder_insert_utils?
# Elimina (o commenta) se non lo usi più.
# from order_insert_utils import calculate_phase_dates

# Non importiamo più il vecchio OrderModel
# from models.order_model import OrderModel  # <-- RIMOSSO

from models.codiceArticoloModel import codiceArticolo
from models.famigliaModel import (
    DashboardElement,
    Dashboard,
    GridBackgroundParams,
    CatalogElement,
    Catalog,
    NextElement,
    ArrowParams,
    FamilyModel,
)
from pydantic import ValidationError

queued_df = pd.DataFrame()
client = None

try:
    logo = Image.open(r".\resources\OPERATIVO_L_Main_Color.png")
except FileNotFoundError:
    print("Image not found. Continuing with the rest of the script.")
    logo = None

logo_width = 1654
logo_length = 1246

window_width = 1600
window_height = 1600

load_dotenv()  # Load environment variables from .env file

uri = "mongodb+srv://OperativoLogin:<db_password>@loginaziende.4fpi2ex.mongodb.net/?retryWrites=true&w=majority&appName=loginAziende"

def fetchMacchinari():
    db = client["process_db"]
    macchinari_collection = db["macchinari"]
    macchinari_names = macchinari_collection.find({}, {"_id": 0, "name": 1})
    macchinari_list = [item["name"] for item in macchinari_names]
    return macchinari_list

def check_family_existance_db(familyName):
    process_db = client["process_db"]
    famiglie_di_prodotto = process_db["famiglie_di_prodotto"]
    family = famiglie_di_prodotto.find_one({"titolo": familyName})
    return bool(family)

def connect_to_mongodb(username, password):
    global client
    print(f"Attempting to connect with username: {username} and password: {password}")

    initial_uri = f"mongodb+srv://{username}:{password}@loginaziende.4fpi2ex.mongodb.net/?retryWrites=true&w=majority&appName=loginAziende"

    try:
        temp_client = MongoClient(initial_uri)
        db = temp_client.get_database("aziende")
        collection = db[username]

        user_doc = collection.find_one({"nome": username})

        if user_doc is None:
            print("No matching document found for connection details.")
            return False

        conn_string = user_doc.get("stringaConn")
        print(conn_string)
        if conn_string:
            conn_string = conn_string.replace("<username>", user_doc["usernameConn"])
            conn_string = conn_string.replace("<password>", user_doc["passwordConn"])
            conn_string = conn_string.split("/<database>")[0] + "/"
            client = MongoClient(conn_string)
            print("Connected to MongoDB with updated credentials")
            return True
        else:
            print("Connection string not found in document.")
            return False

    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return False

def fetchSettings():
    global client
    db = client["azienda"]
    collection = db["settings"]
    settings = collection.find_one()
    if not settings:
        raise ValueError("No settings document found")
    return settings



def excel_date_parser(date_str):
    return pd.to_datetime(date_str, dayfirst=True, errors="coerce")


def upload_orders_from_xlsx(self):
    """ 
    Funzione principale che carica l'Excel e inserisce ordini
    usando **le nuove funzioni** dal file `newOrder_insert_utils`.
    """
    collection_orders = client["orders_db"]["newOrdini"]

    file_path, _ = QFileDialog.getOpenFileName(
        self, "Open Excel File", "", "Excel files (*.xlsx)"
    )
    if not file_path:
        QMessageBox.warning(self, "File Selection", "No file selected.")
        return

    if not file_path.endswith(".xlsx"):
        QMessageBox.critical(self, "File Error", "The selected file is not an Excel file.")
        return

    # Carichiamo già tutti gli orderId esistenti (per evitare duplicati)
    existing_order_ids = set(
        doc["orderId"] for doc in collection_orders.find({}, {"orderId": 1})
    )

    skipped_orders = []
    successful_orders = []
    failed_orders = []

    try:
        xls = pd.ExcelFile(file_path)
        orders_df = pd.read_excel(
            xls,
            sheet_name="Ordini",
            dtype={"Id Ordine": str, "Codice Articolo": str, "Info aggiuntive": str},
            parse_dates=["Data Richiesta"],
            date_parser=excel_date_parser,
        )
    except Exception as e:
        QMessageBox.critical(self, "File Error", f"Failed to read the Excel file: {e}")
        return

    required_columns = {
        "Id Ordine",
        "Codice Articolo",
        "QTA",
        "Data Richiesta",
        "Info aggiuntive",
    }
    if not required_columns.issubset(orders_df.columns):
        missing_columns = required_columns - set(orders_df.columns)
        QMessageBox.critical(
            self,
            "File Error",
            "Missing required columns: " + ", ".join(missing_columns),
        )
        return

    # Rimuovo le righe con Codice Articolo = NaN
    orders_df.dropna(subset=["Codice Articolo"], inplace=True)

    settings = fetchSettings()

    # Importiamo le info sugli orari dal settings
    open_time = settings.get("orariAzienda", {}).get("inizio", {"ore": 8, "minuti": 0})
    close_time = settings.get("orariAzienda", {}).get("fine", {"ore": 18, "minuti": 0})
    holiday_list = settings.get("ferieAziendali", [])
    pausa_pranzo = settings.get(
        "pausaPranzo",
        {"inizio": {"ore": 12, "minuti": 0}, "fine": {"ore": 13, "minuti": 0}},
    )

    # Per evitare di rifare query su famiglie di prodotto, costruiamo una mappa
    collection_famiglie = client["process_db"]["famiglie_di_prodotto"]
    famiglia_cursor = collection_famiglie.find({}, {"catalogo": 1, "dashboard": 1})
    # Mappa: { "codice_articolo": { "family": docMongo, "dashboard": docMongo['dashboard'], "catalog_item": ... } }
    prodId_to_catalog_info = {}
    for fam in famiglia_cursor:
        dash = fam.get("dashboard", {})
        cat = fam.get("catalogo", [])
        phases_elements = dash.get("elements", [])
        phase_names = [element.get("text", "") for element in phases_elements]
        # Per ogni item in catalogo, aggancio "famiglia" e "dashboard"
        for item in cat:
            cod = item["prodId"]
            prodId_to_catalog_info[cod] = {
                "family": fam,
                "dashboard": dash,
                "catalog_item": item,
                "phases": phase_names,
            }

    for idx, row in orders_df.iterrows():
        ordineId = row["Id Ordine"]
        codiceArticolo = row["Codice Articolo"]
        qta = row["QTA"]
        dataRichiesta = row["Data Richiesta"]
        infoAggiuntive = row["Info aggiuntive"]

        if ordineId in existing_order_ids:
            skipped_orders.append(ordineId)
            continue

        # Validazione data
        if pd.isnull(dataRichiesta) or not isinstance(dataRichiesta, datetime.datetime):
            try:
                dataRichiesta = pd.to_datetime(dataRichiesta, dayfirst=True)
            except:
                failed_orders.append({
                    "ordineId": ordineId,
                    "codiceArticolo": codiceArticolo,
                    "reason": f"Invalid date: {dataRichiesta}",
                })
                continue

        # Verifico se esiste la "famiglia" associata al codice
        # (almeno in prodId_to_catalog_info)
        if codiceArticolo not in prodId_to_catalog_info:
            failed_orders.append({
                "ordineId": ordineId,
                "codiceArticolo": codiceArticolo,
                "reason": f"No doc found with prodId {codiceArticolo}",
            })
            continue

        try:
            new_order_doc = build_order_new_model_backwards(
                client=client,
                codice_articolo=codiceArticolo,
                descrizione=infoAggiuntive or "",
                quantity=int(qta),
                order_id=ordineId,
                customer_deadline=dataRichiesta,
                open_time=open_time,
                close_time=close_time,
                holiday_list=holiday_list,
                pausa_pranzo=pausa_pranzo,
            )
        except Exception as e:
            failed_orders.append({
                "ordineId": ordineId,
                "codiceArticolo": codiceArticolo,
                "reason": f"build_order_new_model_backwards error: {e}",
            })
            continue

        # Provo a inserire in DB
        try:
            collection_orders.insert_one(new_order_doc)
            successful_orders.append(ordineId)
        except Exception as e:
            failed_orders.append({
                "ordineId": ordineId,
                "codiceArticolo": codiceArticolo,
                "reason": str(e),
            })

    summary_message = (
        f"{len(successful_orders)} orders processed successfully, "
        f"{len(failed_orders)} errors, "
        f"{len(skipped_orders)} orders skipped."
    )
    show_upload_report(successful_orders, failed_orders, skipped_orders)


class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super(LoginWindow, self).__init__(parent)
        self.user_role = None
        self.setWindowTitle("Login")
        self.setFixedSize(800, 600)

        layout = QVBoxLayout()
        self.logo_label = QLabel(self)
        self.pixmap = QPixmap(r".\resources\OPERATIVO_L_Main_Color.png")
        self.logo_label.setPixmap(self.pixmap.scaled(1200, 300, Qt.KeepAspectRatio))
        layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

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

        grid_layout = QGridLayout()
        grid_layout.addWidget(self.username_label, 0, 0)
        grid_layout.addWidget(self.username_input, 0, 1)
        grid_layout.addWidget(self.password_label, 1, 0)
        grid_layout.addWidget(self.password_input, 1, 1)
        layout.addLayout(grid_layout)

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

        self.logo_label = QLabel(self)
        self.pixmap = QPixmap(r".\resources\OPERATIVO_L_Main_Color.png")
        self.logo_label.setPixmap(self.pixmap.scaled(2400, 600, Qt.KeepAspectRatio))
        self.layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

        self.upload_orders_button = QPushButton("Upload Orders")
        self.upload_famiglie_button = QPushButton("Upload Flussi (Famiglie)")
        self.upload_famiglie_button.setStyleSheet("background-color: red; color: white;")
        self.upload_articoli_button = QPushButton("Upload Articoli")
        self.export_button = QPushButton("Export Data")
        self.utenti_qr_code_button = QPushButton("Generate Operatori QR Codes")
        self.order_qr_button = QPushButton("Generate Order QR Codes")

        font = QFont("Proxima Nova", 12)
        for button in [
            self.upload_famiglie_button,
            self.upload_orders_button,
            self.upload_articoli_button,
            self.export_button,
            self.order_qr_button,
        ]:
            button.setFont(font)
            button.setFixedSize(350, 50)

        self.utenti_qr_code_button.setFixedSize(380, 50)

        main_horizontal_layout = QHBoxLayout()
        left_layout = QHBoxLayout()
        center_layout = QHBoxLayout()
        right_layout = QHBoxLayout()

        center_layout.addWidget(self.upload_famiglie_button)
        center_layout.addWidget(self.upload_orders_button)
        center_layout.addWidget(self.upload_articoli_button)
        center_layout.addWidget(self.export_button)
        center_layout.addWidget(self.utenti_qr_code_button)
        center_layout.addWidget(self.order_qr_button)

        main_horizontal_layout.addLayout(left_layout)
        main_horizontal_layout.addLayout(center_layout)
        main_horizontal_layout.addLayout(right_layout)
        self.layout.addLayout(main_horizontal_layout)

        self.upload_famiglie_button.clicked.connect(self.uploadFamiglie)
        self.upload_orders_button.clicked.connect(self.upload_orders)
        self.upload_articoli_button.clicked.connect(self.upload_articoli)
        self.export_button.clicked.connect(self.select_database_and_collection)
        self.utenti_qr_code_button.clicked.connect(self.generate_and_save_qr_codes)
        self.order_qr_button.clicked.connect(self.generate_order_qr_codes)

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
        self.window_width = floor(self.screen_width * 0.5)
        self.window_height = floor(self.screen_height * 0.5)
        self.resize(self.window_width, self.window_height)
        self.image_width = self.window_width * 0.3
        self.image_height = self.window_height * 0.3

    def generate_and_save_qr_codes(self):
        if not os.path.exists(self.qr_save_path):
            os.makedirs(self.qr_save_path)
        try:
            db = client["azienda"]
            collection = db["utenti"]
            for document in collection.find():
                name = document.get("nome", "UnknownName")
                surname = document.get("cognome", "UnknownSurname")
                password = document.get("password", "NoPassword")
                qr_data = f"{name}||{surname}||{password}"
                filename = f"{name}_{surname}.png"
                self.generate_qr(qr_data, filename, name, surname)
            QMessageBox.information(
                self,
                "QR Codes Generated",
                "QR codes have been successfully generated and saved in " + self.qr_save_path,
            )
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
        img = qr.make_image(fill="black", back_color="white").convert("RGB")

        font = ImageFont.load_default()
        draw = ImageDraw.Draw(img)
        text = f"{name} {surname}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        img_width, img_height = img.size
        x = (img_width - text_width) // 2
        new_img_height = img_height + text_height + 20
        new_img = Image.new("RGB", (img_width, new_img_height), "white")
        new_img.paste(img, (0, 0))
        draw = ImageDraw.Draw(new_img)
        draw.text((x, img_height + 10), text, font=font, fill="black")
        full_path = os.path.join(self.qr_save_path, filename)
        new_img.save(full_path)

    def generate_order_qr_codes(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            QMessageBox.warning(
                self, "No Folder Selected", "Please select a valid folder to save QR codes."
            )
            return
        try:
            db = client["orders_db"]
            collection = db["newOrdini"]
            for document in collection.find():
                order_id = document.get("orderId", "UnknownOrderID")
                codice_articolo = document.get("codiceArticolo", "UnknownCode")
                quantita = document.get("quantita", "UnknownQuantity")
                order_deadline = str(document.get("orderDeadline", "UnknownDeadline"))
                date_part = order_deadline.split("T", 1)[0]
                sanitized_date_part = date_part.replace(":", "-")
                filename = f"{order_id}_{codice_articolo}_{sanitized_date_part}.png"
                full_path = os.path.join(folder, filename)
                self.generate_order_qr_with_text(order_id, full_path, order_id, codice_articolo, quantita)
            QMessageBox.information(
                self, "QR Codes Generated", f"Order QR codes successfully generated in {folder}"
            )
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
        img = qr.make_image(fill="black", back_color="white").convert("RGB")

        font = ImageFont.load_default()
        draw = ImageDraw.Draw(img)
        text = f"Order ID: {order_id}\nCodice: {codice_articolo}\nQuantita: {quantita}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        img_width, img_height = img.size
        x = (img_width - text_width) // 2
        new_img_height = img_height + text_height + 20
        new_img = Image.new("RGB", (img_width, new_img_height), "white")
        new_img.paste(img, (0, 0))
        draw = ImageDraw.Draw(new_img)
        draw.text((x, img_height + 10), text, font=font, fill="black")
        new_img.save(full_path)

    def init_placeholder(self):
        self.table.setRowCount(1)
        self.table.setColumnCount(1)
        self.table.setItem(0, 0, QTableWidgetItem("Upload a csv file to visualize the data"))

    def upload_orders(self):
        upload_orders_from_xlsx(self)

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
                QMessageBox.critical(
                    self, "Error", "Please select both database and collection."
                )

    def export_data(self, db_name, collection_name):
        print(f"Attempting to export data from {db_name}.{collection_name}...")
        try:
            db = client[db_name]
            collection = db[collection_name]
            cursor = collection.find({})
            data = list(cursor)
            if data:
                df = pd.DataFrame(data)
                if "_id" in df.columns:
                    df.drop("_id", axis=1, inplace=True)

                print("Available columns in the data:")
                print(df.columns.tolist())

                id_to_name = fetch_in_coda_at_names(client)
                uuid_to_name = fetch_in_lavorazione_at_names(client)
                required_columns = [
                    "phase",
                    "phaseStatus",
                    "assignedOperator",
                    "phaseLateMotivation",
                    "phaseEndTime",
                    "phaseRealTime",
                    "entrataCodaFase",
                ]
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    QMessageBox.critical(
                        self,
                        "Export Failed",
                        f"Missing required columns: {', '.join(missing_columns)}",
                    )
                    return

                columns_to_parse = [
                    "phaseStatus",
                    "assignedOperator",
                    "phaseLateMotivation",
                    "phaseEndTime",
                    "phaseRealTime",
                    "inCodaAt",
                    "inLavorazioneAt",
                    "entrataCodaFase",
                ]
                all_expanded_rows = []

                for idx, row in df.iterrows():
                    phases = parse_value(row["phase"])
                    if not phases:
                        print(f"Skipping row {idx}: 'phase' value is invalid.")
                        continue

                    parsed_columns = parse_columns(row, columns_to_parse, id_to_name)
                    parsed_columns["inCodaAt"] = [
                        map_in_coda_at_value(v, id_to_name) for v in parsed_columns["inCodaAt"]
                    ]
                    if "inLavorazioneAt" in parsed_columns:
                        parsed_columns["inLavorazioneAt"] = [
                            map_in_lavorazione_at_value(v, uuid_to_name)
                            for v in parsed_columns["inLavorazioneAt"]
                        ]

                    new_rows = create_new_row(row, phases, parsed_columns, columns_to_parse)
                    all_expanded_rows.extend(new_rows)

                if all_expanded_rows:
                    final_expanded_df = pd.DataFrame(all_expanded_rows)
                    final_expanded_df["orderId"] = final_expanded_df["orderId"].astype(str)
                    final_expanded_df["phase"] = final_expanded_df["phase"].astype(str)
                    final_expanded_df["Sequenza"] = 0

                    current_order_id = None
                    sequence = 0
                    for idx, row in final_expanded_df.iterrows():
                        if row["orderId"] != current_order_id:
                            current_order_id = row["orderId"]
                            sequence = 1
                        else:
                            sequence += 1
                        final_expanded_df.at[idx, "Sequenza"] = sequence

                    final_expanded_df["in coda"] = calculate_in_coda(final_expanded_df)

                    if "orderStatus" in final_expanded_df.columns:
                        final_expanded_df["orderStatus"] = final_expanded_df["orderStatus"].apply(order_status_mapper)
                    if "phaseStatus" in final_expanded_df.columns:
                        final_expanded_df["phaseStatus"] = final_expanded_df["phaseStatus"].apply(phase_status_mapper)

                    final_expanded_df.rename(columns=column_mapping, inplace=True)

                    if "Queue Entry Time" in final_expanded_df.columns:
                        final_expanded_df["Queue Entry Time"] = final_expanded_df["Queue Entry Time"].apply(format_queue_entry_time)

                    final_expanded_df["Quantità"] = (
                        pd.to_numeric(final_expanded_df["Quantità"], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )
                    final_expanded_df["Lead Time Fase"] = (
                        pd.to_numeric(final_expanded_df["Lead Time Fase"], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )
                    final_expanded_df["Tempo Ciclo Performato"] = (
                        pd.to_numeric(final_expanded_df["Tempo Ciclo Performato"], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )
                    final_expanded_df["Priorità"] = (
                        pd.to_numeric(final_expanded_df["Priorità"], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )

                    options = QFileDialog.Options()
                    file_path, _ = QFileDialog.getSaveFileName(
                        self,
                        "Save Excel File",
                        "",
                        "Excel Files (*.xlsx);;All Files (*)",
                        options=options,
                    )
                    if file_path:
                        final_expanded_df.to_excel(file_path, index=False)
                        QMessageBox.information(
                            self, "Export Successful", "Data has been successfully exported to Excel."
                        )
                    else:
                        print("No file path was selected.")
                else:
                    QMessageBox.information(self, "No Data", "No rows were expanded.")
            else:
                QMessageBox.information(self, "No Data", "No documents in the collection.")
        except Exception as e:
            print(f"Error exporting data: {e}")
            QMessageBox.critical(self, "Export Failed", f"Failed to export data: {e}")

    def uploadFamiglie(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Excel File", "", "Excel files (*.xlsx)"
        )
        if not file_path:
            QMessageBox.warning(self, "File Selection", "No file selected.")
            return
        if not file_path.endswith(".xlsx"):
            QMessageBox.critical(self, "File Error", "The selected file is not an Excel file.")
            return
        try:
            df = pd.read_excel(file_path, sheet_name="Famiglie")
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to read the Excel file: {e}")
            return

        successful_families = []
        skipped_families = []
        failed_families = []

        required_columns = {
            "ID fase",
            "FaseOperativo",
            "ID fase successiva",
            "Fase successiva",
            "Codice",
            "FaseOperativo",
            "Tempo Ciclo",
            "Descrizione",
        }
        if not required_columns.issubset(df.columns):
            missing_columns = required_columns - set(df.columns)
            QMessageBox.critical(
                self,
                "File Error",
                "Missing required columns: " + ", ".join(missing_columns),
            )
            return

        try:
            for codice, group in df.groupby("Codice"):
                try:
                    codice = str(codice)
                except Exception:
                    raise ValueError(f"'nome' non convertibile in stringa, ricevuto: {type(codice)}")
                if check_family_existance_db(codice):
                    print(f"Family: {codice} already present in DB")
                    skipped_families.append(codice)
                    continue
                else:
                    try:
                        fasi = group["FaseOperativo"].tolist()
                        macchinari_list = fetchMacchinari()
                        missing_phases = [fase for fase in fasi if fase not in macchinari_list]
                        if missing_phases:
                            failed_families.append({
                                "Family": f"{codice}",
                                "Reason": f"Fasi non presenti in DB macchinari: {missing_phases}"
                            })
                            continue
                        else:
                            # Controlla che ci sia un solo valore nella colonna "Descrizione" per questo gruppo
                            if group["Descrizione"].nunique() > 1:
                                failed_families.append({
                                    "Family": f"{codice}",
                                    "Reason": f"Ci sono più descrizioni diverse nel gruppo per '{codice}'."
                                })
                                continue

                            # Prendi il primo (e unico) valore
                            descrizione_value = group["Descrizione"].iloc[0]

                            json_object = create_json_for_flowchart(group, codice, descrizione_value)
                            db_name = "process_db"
                            collection_name = "famiglie_di_prodotto"
                            db = client[db_name]
                            collection = db[collection_name]
                            collection.insert_one(json_object)
                            successful_families.append(codice)
                    except Exception as e:
                        print(f"Error encountered with family {codice}: {e}")
                        failed_families.append({"Family": codice, "Reason": str(e)})

            show_family_upload_report(successful_families, failed_families, skipped_families)

        except Exception as e:
            print(f"Error encountered: {e}")
            failed_families.append(f"Failed to process: {e}")


    def upload_articoli(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Excel File", "", "Excel files (*.xlsx)"
        )
        if not file_path:
            QMessageBox.warning(self, "File Selection", "No file selected.")
            return

        if not file_path.endswith(".xlsx"):
            QMessageBox.critical(self, "File Error", "The selected file is not an Excel file.")
            return

        try:
            articoli_df = pd.read_excel(file_path, sheet_name="Articoli")
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to read the Excel file: {e}")
            return

        required_columns = {
            "Codice Articolo", "Descrizione articolo", "Famiglia di prodotto",
            "Fase Operativo", "Tempo Ciclo", "Info lavorazione"
        }
        
        if not required_columns.issubset(articoli_df.columns):
            missing_columns = required_columns - set(articoli_df.columns)
            QMessageBox.critical(self, "File Error", f"Missing required columns: {', '.join(missing_columns)}")
            return

        client = MongoClient()
        db = client["process_db"]
        collection = db["famiglie_di_prodotto"]
        family_dict = {family["titolo"]: family for family in collection.find()}

        success_count, error_count = 0, 0
        errors, processed_articoli = [], []

        for idx, row in articoli_df.iterrows():
            try:
                codice_articolo = str(row["Codice Articolo"])
                descrizione_articolo = str(row["Descrizione articolo"])
                famiglia_di_prodotto = str(row["Famiglia di prodotto"])
            except Exception as e:
                errors.append({"Row": idx + 1, "Reason": f"Data conversion error: {e}"})
                error_count += 1
                continue

            if famiglia_di_prodotto not in family_dict:
                errors.append({"Codice Articolo": codice_articolo, "Reason": f'Famiglia di prodotto "{famiglia_di_prodotto}" not found in database.'})
                error_count += 1
                continue

            family = family_dict[famiglia_di_prodotto]
            catalogo = family.setdefault("catalogo", [])

            if any(item["prodId"] == codice_articolo for item in catalogo):
                continue  # Skip duplicate

            elements = [{} for _ in family.get("dashboard", {}).get("elements", [])]
            catalogo.append({
                "_id": ObjectId(),
                "prodId": codice_articolo,
                "prodotto": descrizione_articolo,
                "descrizione": "",
                "famiglia": famiglia_di_prodotto,
                "elements": elements,
            })
            success_count += 1
            processed_articoli.append(codice_articolo)

        for famiglia, family in family_dict.items():
            try:
                collection.update_one({"_id": family["_id"]}, {"$set": {"catalogo": family["catalogo"]}})
            except Exception as e:
                errors.append({"Famiglia di prodotto": famiglia, "Reason": f"Error updating database: {e}"})
                error_count += 1

        summary_message = f"{success_count} articoli processed successfully, {error_count} errors."
        if errors:
            error_messages = "\n".join([f"{error.get('Codice Articolo', error.get('Famiglia di prodotto'))}: {error['Reason']}" for error in errors])
            QMessageBox.information(self, "Processing Summary", summary_message + "\nErrors:\n" + error_messages)
        else:
            QMessageBox.information(self, "Processing Summary", summary_message)

        report_message = "Articoli Upload Report:\n\n" + summary_message + "\n\n"
        if processed_articoli:
            report_message += "Successfully processed articoli:\n" + "\n".join(processed_articoli) + "\n\n"
        if errors:
            report_message += "Errors encountered:\n" + "\n".join([f"{error.get('Codice Articolo', error.get('Famiglia di prodotto'))}: {error['Reason']}" for error in errors])

        save_report_to_file(report_message, "articoli")


    def wipe_database(self):
        print("Attempting to wipe database...")
        reply = QMessageBox.question(
            self,
            "Confirm Wipe",
            "Are you sure you want to wipe the database?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply == QMessageBox.Yes:
            try:
                db = client["processes_db"]
                collection = db["macchinari"]
                collection.delete_many({})
                self.clear_data()
                QMessageBox.information(self, "Success", "The database has been wiped.")
            except Exception as e:
                print(f"Error wiping database: {e}")
                QMessageBox.critical(
                    self, "Wipe Failed", f"Failed to wipe database: {e}"
                )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        main_window = MainWindow(login.user_role)
        main_window.show()
        sys.exit(app.exec_())
