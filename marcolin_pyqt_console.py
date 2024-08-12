import os
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
from bson import ObjectId
import datetime
import json
from dotenv import load_dotenv
import qrcode

load_dotenv()
# Initialize global variable
queued_df = pd.DataFrame()
client = None  # Initialize client variable
login_logo = Image.open(r".\OPERATIVO_L_Main_Color.png")
login_logo_width = 1654
login_logo_length = 1246

original_logo = Image.open(r".\OPERATIVO_L_Main_Color.png") 
original_logo_width = 1654
original_logo_length = 1246

window_width = 1600
window_height = 1600

def create_json_for_flowchart(codice, phases, cycle_times, description, phaseTargetQueue):
        element_ids = [str(ObjectId()) for _ in phases]
        dashboard_elements = []
        for i, (phase, time, phaseTargetQueue) in enumerate(zip(phases, cycle_times, phaseTargetQueue)):
            element = {
                "positionDx": 101.2 + 200 * i,
                "positionDy": 240.2,
                "size.width": 100.0, 
                "size.height": 50.0,
                "text": phase,
                "phaseTargetQueue": phaseTargetQueue,
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
                "phaseDuration": int(time)
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
    

def order_upload_to_mongodb(orders, db_url, db_name, collection_name):
        db = client[db_name]
        collection = db[collection_name]
        result = collection.insert_many(orders)
        print(f"Inserted Order IDs: {result.inserted_ids}")
        client.close()

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
        else:
            print("Invalid credentials")
            return False
        print("Connected to MongoDB")
        return True
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return False
    
def trova_riga_per_id_legame(df, id_legame):
    riga_trovata = df[df['ID legame'] == id_legame]
    return riga_trovata

def estrai_data_richiesta(df, id_legame):
    riga = trova_riga_per_id_legame(df, id_legame)
    if not riga.empty:
        data_richiesta = riga['Data richiesta'].values[0]
        return pd.to_datetime(data_richiesta)
    return None
    
def create_orders_objects(file_path):
    # Load the data from Excel
        dataOrders = pd.read_excel(file_path)
        global queued_df
        data = queued_df
    # Define the columns to use
        order_column = 'ID'
        fasi_column = 'FaseOperativo'
        tempo_ciclo_column = 'Tempo Ciclo'
        codice_column = 'Codice'
        quantita_column = 'Qta'
        descrizione_column = 'Descrizione'
        accessori_column = 'Accessori'
        lead_time_column = 'LTFase'
        deadline_column = 'Data richiesta'
        
        orders = []

        unique_orders = {}
    # Process the DataFrame
        for index, row in dataOrders.iterrows():
            order_id = row[order_column]

            fasi = row[fasi_column]

            tempo_ciclo = row[tempo_ciclo_column]
            codice = row[codice_column]
            quantita = row[quantita_column]
            descrizione = str(row[accessori_column]) + " " + row[descrizione_column] if str(row[accessori_column]) != "nan" else row[descrizione_column]
            lead_time_fase = row[lead_time_column]
            orderDeadline = row[deadline_column] #row[deadline_column] #datetime.datetime.now() #estrai_data_richiesta(dataOrders, order_id)

        # Create or update the order in the unique orders dict
            if order_id not in unique_orders:
                unique_orders[order_id] = {
                    # chiave da eliminare per memorizzare i sabati e domeniche da saltare in seguito
                    "count": 0,
                    "_id": ObjectId(),  # Generate new MongoDB ObjectId
                    "orderId": str(order_id),
                    "orderInsertDate": datetime.datetime.now(),
                    "codiceArticolo": codice,
                    "orderDescription": descrizione,
                    "quantita": quantita,
                    "orderStatus": 0,
                    "priority": 0,
                    "inCodaAt": "",
                    # DUPLICATO
                    "orderDeadline": orderDeadline,
                    "customerDeadline": orderDeadline,
                    # DUPLICATO
                    # questi due campi vengono settati alla deadline e poi per ogni fase
                    # viene rimosso il lead time di ogni fase per capire quando l'ordine
                    # entrerà in coda in ogni macchinario
                    "orderStartDate": orderDeadline,
                    "dataInizioLavorazioni": orderDeadline,
                    "phase": [],
                    "phaseStatus": [],
                    "assignedOperator": [],
                    "phaseLateMotivation": [],
                    "phaseEndTime": [],
                    "phaseRealTime": [],
                    "entrataCodaFase": [],
                }
        # Append the current Fasi and its Tempo Ciclo to the order
            unique_orders[order_id]['phase'].append([fasi])
            unique_orders[order_id]['phaseStatus'].append([1]) # NO UFFICIO ACQUISTI
            unique_orders[order_id]['assignedOperator'].append([""])
            unique_orders[order_id]['phaseLateMotivation'].append(["none"])
            unique_orders[order_id]['phaseEndTime'].append([tempo_ciclo] if fasi != "Zincatura" else [0])
            unique_orders[order_id]['phaseRealTime'].append([0])

            possible_date = unique_orders[order_id]['dataInizioLavorazioni'] - datetime.timedelta(days=lead_time_fase + unique_orders[order_id]['count'])
            if possible_date.weekday() >= 5:
                unique_orders[order_id]['count'] = unique_orders[order_id]['count'] + 1

            unique_orders[order_id]['dataInizioLavorazioni'] = unique_orders[order_id]['dataInizioLavorazioni'] - datetime.timedelta(days=lead_time_fase + unique_orders[order_id]['count'])
            unique_orders[order_id]['orderStartDate'] = unique_orders[order_id]['orderStartDate'] - datetime.timedelta(days=lead_time_fase + unique_orders[order_id]['count'])
            # Entrata coda fase è il datetime che rappresenta quando una fase deve cominciare
            # usando dataInizioLavorazioni in ogni iterazione so esattamente quando ogni fase
            # deve cominciare, ma l'array dovrà essere rovesciato. Infatti, guardando l'excel,
            # le fasi sono scritte in ordine dalla prima all'ultima
            unique_orders[order_id]['entrataCodaFase'].append([unique_orders[order_id]['dataInizioLavorazioni']])

        for ordine in unique_orders:
            unique_orders[ordine]['entrataCodaFase'] = unique_orders[ordine]['entrataCodaFase'][::-1]
            unique_orders[ordine].pop('count', None)

    # Convert unique orders dictionary to a list for MongoDB insertion
        orders.extend(unique_orders.values())

        return orders    
    

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super(LoginWindow, self).__init__(parent)
        
        self.user_role = None  
        self.setWindowTitle("Login")
        self.setFixedSize(800, 600)

        layout = QVBoxLayout()

        # Add company logo
        self.logo_label = QLabel(self)
        self.pixmap = QPixmap(r".\OPERATIVO_L_Main_Color.png")
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
            self.user_role = get_user_role(username)
            self.accept()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid username or password")
            
def get_user_role(username):
    # This is a placeholder function. You should implement the actual logic to retrieve the user role
    # For demonstration:
    if username == "marcolin":
        return "marcolin_role"
    else:
        return "regular_role"
    

class MainWindow(QMainWindow):
    def __init__(self, user_role):
        super(MainWindow, self).__init__()
        self.user_role = user_role
        self.setWindowTitle("Data Uploader")
        self.setGeometry(75, 75, window_width, window_height)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.adjust_sizes()

        self.logo_layout = QHBoxLayout()

            
        self.qr_save_path = "./QRs" 
        # Add company logo
        self.logo_label = QLabel(self)
        self.pixmap = QPixmap(r".\OPERATIVO_L_Main_Color.png")
        self.logo_label.setPixmap(self.pixmap.scaled(2400, 600, Qt.KeepAspectRatio))
        self.logo_layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

        # Add new logo
        self.new_logo_label = QLabel(self)
        self.new_pixmap = QPixmap(r"marcolin_logo.png")  # Adjust the path as necessary
        self.new_logo_label.setPixmap(self.new_pixmap.scaled(2400, 600, Qt.KeepAspectRatio))  # Adjust size as needed
        self.logo_layout.addWidget(self.new_logo_label, alignment=Qt.AlignCenter)

        # Add the logo layout to the main layout
        self.layout.addLayout(self.logo_layout)

        # Buttons
        # self.queue_button = QPushButton("Queue Data")
        # self.clear_button = QPushButton("Clear Queued Data")
        # self.upload_button = QPushButton("Upload Queued Data")
        # self.upload_button.setStyleSheet("background-color: green; color: white;")
        self.wipe_button = QPushButton("Wipe Flussi Database")
        self.export_button = QPushButton("Export Data")
        self.family_upload_button = QPushButton("Upload Famiglie (Flussi)")
        self.utenti_qr_code_button = QPushButton("Generate Operatori QR Codes")
        self.order_qr_code_button = QPushButton("Generate Orders QR Codes")
        self.upload_orders_button = QPushButton("Upload Orders")


        # Setup font
        font = QFont("Proxima Nova", 12)
        for button in [self.wipe_button, self.export_button, self.family_upload_button, self.order_qr_code_button, self.utenti_qr_code_button, self.upload_orders_button]:
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

        center_layout.addWidget(self.wipe_button)
        center_layout.addWidget(self.export_button)
        center_layout.addWidget(self.family_upload_button)
        center_layout.addWidget(self.utenti_qr_code_button)
        center_layout.addWidget(self.order_qr_code_button)
        center_layout.addWidget(self.upload_orders_button)
        
        # Add stretches to center the center layout
        main_horizontal_layout.addLayout(left_layout)
        main_horizontal_layout.addLayout(center_layout)
        main_horizontal_layout.addLayout(right_layout)

        self.layout.addLayout(main_horizontal_layout)
        
        # Special Styling
        self.wipe_button.setStyleSheet("background-color: red; color: white;") # RED WIPE BUTTON
        self.upload_orders_button.setStyleSheet("background-color: blue; color: white;") # BLUE UPLOAD BUTTON
        
        
        # BUTTON CONNECTIVITY TO FUNCTIONS
        
        # self.queue_button.clicked.connect(self.queue_data)
        # self.clear_button.clicked.connect(self.clear_data)
        # self.upload_button.clicked.connect(self.upload_queued_data)
        self.wipe_button.clicked.connect(self.wipe_database)
        self.export_button.clicked.connect(self.select_database_and_collection)
        self.family_upload_button.clicked.connect(self.marcolin_import_famiglie)
        self.utenti_qr_code_button.clicked.connect(self.generate_and_save_qr_codes)
        self.order_qr_code_button.clicked.connect(self.generate_order_qr_codes)
        self.upload_orders_button.clicked.connect(self.upload_orders_data)

        # Table for CSV data REDUNDANT - TO REMOVE
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        
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
                qr_data = f"{name}||{surname}||{password}"  # Format the data as required by the new QR code system
                filename = f"{name}_{surname}.png"
                self.generate_qr(qr_data, filename, name, surname)  # Pass the name and surname to the QR generation function
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
        font = ImageFont.load_default()  # You can specify a different font here
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
    
    def initialize_ui(self):
        # Common setup code here

        # Now, apply user-specific configurations:
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

    def queue_data(self):
        global queued_df
        filename, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV files (*.csv)")
        if filename:
            queued_df = pd.read_csv(filename)
            self.display_data()

    def display_data(self):
        self.table.clear()
        if not queued_df.empty:
            self.table.setRowCount(queued_df.shape[0])
            self.table.setColumnCount(queued_df.shape[1])
            self.table.setHorizontalHeaderLabels(queued_df.columns)
            for i in range(queued_df.shape[0]):
                for j in range(queued_df.shape[1]):
                    self.table.setItem(i, j, QTableWidgetItem(str(queued_df.iat[i, j])))
                    
    def upload_orders_data(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel files (*.xlsx)")
        if filename:
            try:
                orders = create_orders_objects(filename)
                success_count = 0
                error_count = 0
                errors = []
                for order in orders:
                    try:
                        order_upload_to_mongodb([order], client, "orders_db", "ordini")
                        print(f"Order {order['orderId']} was uploaded successfully")
                        success_count += 1
                    except Exception as e:
                        print(f"Error encountered with order {order['orderId']}: {e}")
                        errors.append(order['orderId'])
                        error_count += 1

                summary_message = f"{success_count} orders uploaded successfully, {error_count} failed: {', '.join(errors)}"
                QMessageBox.information(self, "Upload Summary", summary_message)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to process orders: {e}")
                
    def upload_queued_data(self):
        global queued_df
        print("Attempting to upload data...")
        if not queued_df.empty:
            reply = QMessageBox.question(self, "Confirm Upload", "Are you sure you want to upload the queued data?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    data_to_upload = queued_df.to_dict('records')
                    db = client['processes_db']
                    collection = db['macchinari']
                    collection.insert_many(data_to_upload)
                    QMessageBox.information(self, "Upload Complete", "Data has been successfully uploaded.")
                    self.clear_data()
                except Exception as e:
                    print(f"Error uploading data: {e}")
                    QMessageBox.critical(self, "Upload Failed", f"Failed to upload data: {e}")

    def clear_data(self):
        self.table.clear()

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
                db = client['process_db']
                collection = db['famiglie_di_prodotto']
                
                print("Deleting documents in the collection...")
                result = collection.delete_many({})
                print(f"Deleted {result.deleted_count} documents.")
                self.clear_data()
                QMessageBox.information(self, "Success", "The database has been wiped.")
            except Exception as e:
                print(f"Error wiping database: {e}")
                QMessageBox.critical(self, "Wipe Failed", f"Failed to wipe database: {e}")

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
            
    def marcolin_import_famiglie(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel files (*.xlsx)")
        if not file_path:
            QMessageBox.warning(self, "File Selection", "No file selected.")
            return

        if not file_path.endswith('.xlsx'):
            QMessageBox.critical(self, "File Error", "The selected file is not an Excel file.")
            return

        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to read the Excel file: {e}")
            return

        required_columns = {'Codice', 'FaseOperativo', 'LTFase', 'Tempo Ciclo', 'Qta', 'Descrizione', 'Accessori'}
        if not required_columns.issubset(df.columns):
            missing_columns = required_columns - set(df.columns)
            QMessageBox.critical(self, "File Error", "Missing required columns: " + ", ".join(missing_columns))
            return

        output_directory = './output_jsons'
        
        db_name = 'process_db'
        collection_name = 'famiglie_di_prodotto'
        db = client[db_name]
        collection = db[collection_name]

        print("Reading the Excel file...")
        df = pd.read_excel(file_path)

        processed_data = {
            'Codice': [],
            'Fasi': [],
            'LT Fase Array': [],
            'Tempo Ciclo Array': [],
            'QTA': [],
            'Description': [],
        }

        print("Processing data...")
        success_count = 0
        error_count = 0
        errors = []
        for codice, group in df.groupby('Codice'):
            try:
                fasi = group['FaseOperativo'].tolist()
                lt_fase = group['LTFase'].tolist()
                tempo_ciclo = group['Tempo Ciclo'].tolist()
                qta = group['Qta'].iloc[0]
                description = group['Descrizione'].iloc[0] + " " + " ".join(map(str, group['Accessori'].dropna().unique()))

                print(f"Creating and uploading JSON for Codice: {codice}")
                json_object = create_json_for_flowchart(codice, fasi, tempo_ciclo, description, lt_fase)

                processed_data['Codice'].append(codice)
                processed_data['Fasi'].append(fasi)
                processed_data['LT Fase Array'].append(lt_fase)
                processed_data['Tempo Ciclo Array'].append(tempo_ciclo)
                processed_data['QTA'].append(qta)
                processed_data['Description'].append(description)

                collection.insert_one(json_object)
                print(f"Family {codice} was uploaded successfully")
                success_count += 1
            except Exception as e:
                print(f"Error encountered with family {codice}: {e}")
                errors.append(codice)
                error_count += 1

        summary_message = f"{success_count} families uploaded successfully, {error_count} failed: {', '.join(errors)}"
        QMessageBox.information(self, "Upload Summary", summary_message)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        main_window = MainWindow(login.user_role)
        main_window.show()
        sys.exit(app.exec_())
