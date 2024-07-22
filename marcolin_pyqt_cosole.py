import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QLabel, QTableWidget, \
    QTableWidgetItem, QFileDialog, QMessageBox, QLineEdit, QDialog, QGridLayout, QComboBox, QDialogButtonBox, QHBoxLayout
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
import pandas as pd
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from math import floor
from PIL import Image
from bson import ObjectId
import datetime
import json


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

def order_upload_to_mongodb(orders, db_url, db_name, collection_name):
        client = MongoClient(db_url)
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
            client = MongoClient('mongodb+srv://michael:stegish@jadclu-ster.d4ppdse.mongodb.net/', server_api=ServerApi('1'))
        elif username == "user2" and password == "password2":
            client = MongoClient('mongodb+srv://user2:password2@cluster2.mongodb.net/')
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
        fasi_column = 'Fasi'
        tempo_ciclo_column = 'Tempo ciclo [min]'
        codice_column = 'Codice'
        quantita_column = 'QTA'
        descrizione_column = 'Descrizione'
        
        orders = []

        unique_orders = {}
    # Process the DataFrame
        for index, row in data.iterrows():
            order_id = row[order_column]

            fasi = row[fasi_column]
            fasiArray = []
            phase_end_times = []
            if(row['FaseOperativo'] == 'Lavorazioni'):  
                for fase in fase.split("+"):
                    match fasi:
                        case "SB":
                            fasiArray.append([""])
                            phase_end_times.append(row[fasi_column])
                        case "S1":
                            fasiArray.append([""])
                            phase_end_times.append([""])
                        case "FZS":
                            fasiArray.append([""])
                            phase_end_times.append([""])
                        case "SV":
                            fasiArray.append([""])
                            phase_end_times.append([""])
                        case "FI":
                            fasiArray.append([""])
                            phase_end_times.append([""])
                        case "FO":
                            fasiArray.append([""])
                            phase_end_times.append([""])
                        case "TOR":
                            fasiArray.append([""])
                            phase_end_times.append([""])
                        case "S2":
                            fasiArray.append([""])
                            phase_end_times.append([""])
                        case "C":
                            fasiArray.append([""])
                            phase_end_times.append([""])
                        case "FR":
                            fasiArray.append([""])
                            phase_end_times.append([""])

            else:
                match fasi:
                    case "Smig":
                        fasiArray.append(["Saldatura"])
                        phase_end_times.append(["Saldatura"])
                    case "P":
                        fasiArray.append(["Pressopiega"])
                        phase_end_times.append(["Pressopiega"])
                    case "A":
                        fasiArray.append(["Assemblaggio"])
                        phase_end_times.append(["Assemblaggio"])
                    case "TO+D":
                        fasiArray.append(["Taglio"])
                        phase_end_times.append(["Taglio"])
                    case "Stig":
                        fasiArray.append(["Saldatura"])
                        phase_end_times.append(["Saldatura"])
                    case "ZF":
                        fasiArray.append(["Zincatura"])
                        phase_end_times.append(["Zincatura"])
                    case "Stig+Smig":
                        fasiArray.append(["Saldatura"])
                        phase_end_times.append(["Saldatura"])
                    case "TA+D":
                        fasiArray.append(["Taglio"])
                        phase_end_times.append(["Taglio"])
                    case "T+D":
                        fasiArray.append(["Taglio"])
                        phase_end_times.append(["Taglio"])
                    case "TTM":
                        fasiArray.append(["Piegatondini"])
                        phase_end_times.append(["Piegatondini"])
                    case "TTM+PTM":
                        fasiArray.append(["Piegatondini"])
                        phase_end_times.append(["Piegatondini"])
                    case "ZC":
                        fasiArray.append(["Zincatura"])
                        phase_end_times.append(["Zincatura"])

            tempo_ciclo = row[tempo_ciclo_column]
            codice = row[codice_column]
            quantita = row[quantita_column]
            descrizione = row[descrizione_column]
            orderDeadline = estrai_data_richiesta(dataOrders, order_id)

        # Create or update the order in the unique orders dict
            if order_id not in unique_orders:
                unique_orders[order_id] = {
                    "_id": ObjectId(),  # Generate new MongoDB ObjectId
                    "orderId": order_id,
                    "orderInsertDate": datetime.datetime.now(),
                    "codiceArticolo": codice,
                    "orderDescription": descrizione,
                    "quantita": quantita,
                    "orderStatus": 0,
                    "phaseStatus": [[0] for _ in fasiArray],
                    "assignedOperator": [[""] for _ in fasiArray],
                    "phase": [[ph] for ph in fasiArray],
                    "phaseLateMotivation": [["none"] for _ in fasiArray],
                    "phaseRealTime": [[0] for _ in fasiArray],
                    "priority": 0,
                    "inCodaAt": "",
                    "orderDeadline": orderDeadline,
                    "customerDeadline": orderDeadline,
                    "orderStartDate": [],
                    "phaseEndTime": [],
                    "entrataCodaFase": [[] for _ in fasiArray],
                    "dataInizioLavorazioni": datetime.now(),
                }
        # Append the current Fasi and its Tempo Ciclo to the order
            unique_orders[order_id]['phase'].append(fasi)
            unique_orders[order_id]['phaseEndTime'].append(tempo_ciclo)

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
        self.queue_button = QPushButton("Queue Data")
        self.clear_button = QPushButton("Clear Queued Data")
        self.upload_button = QPushButton("Upload Queued Data")
        self.upload_button.setStyleSheet("background-color: green; color: white;")
        self.wipe_button = QPushButton("Wipe Database")
        self.wipe_button.setStyleSheet("background-color: red; color: white;")
        self.export_button = QPushButton("Export Data")

        # Setup font
        font = QFont("Proxima Nova", 12)
        for button in [self.queue_button, self.clear_button, self.upload_button, self.wipe_button, self.export_button]:
            button.setFont(font)
            button.setFixedSize(350, 50)

        # Create layouts
        main_horizontal_layout = QHBoxLayout()
        left_layout = QHBoxLayout()
        center_layout = QHBoxLayout()
        right_layout = QHBoxLayout()

        # Add buttons to layouts
        center_layout.addWidget(self.queue_button)
        center_layout.addWidget(self.clear_button)

        center_layout.addWidget(self.upload_button)

        center_layout.addWidget(self.wipe_button)
        center_layout.addWidget(self.export_button)

        # Add stretches to center the center layout
        main_horizontal_layout.addLayout(left_layout)
        main_horizontal_layout.addLayout(center_layout)
        main_horizontal_layout.addLayout(right_layout)

        self.layout.addLayout(main_horizontal_layout)
        
        self.queue_button.clicked.connect(self.queue_data)
        self.clear_button.clicked.connect(self.clear_data)
        self.upload_button.clicked.connect(self.upload_queued_data)
        self.wipe_button.clicked.connect(self.wipe_database)
        self.export_button.clicked.connect(self.select_database_and_collection)

        self.upload_orders_button = QPushButton("Upload Orders")
        self.upload_orders_button.setFont(font)
        self.upload_orders_button.setFixedSize(350, 50)
        self.upload_orders_button.setStyleSheet("background-color: blue; color: white;")
        self.upload_orders_button.clicked.connect(self.upload_orders_data)

        center_layout.addWidget(self.upload_orders_button)
        # Table for CSV data
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        
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
        # Trigger the file dialog to select an Excel file
        filename, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel files (*.xlsx)")
        if filename:
            try:
                # Read data from Excel and create orders
                orders = create_orders_objects(filename)

                # Optionally save to JSON or upload to MongoDB
                # json_file_name = 'orders.json'
                # save_orders_to_json(orders, json_file_name)

                # Optionally upload to MongoDB
                order_upload_to_mongodb(orders, client, "orders_db", "ordini")

                QMessageBox.information(self, "Success", "Orders have been processed and uploaded.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to process orders: {e}")
                
    # def save_orders_to_json(orders, file_name):
    # # Convert the orders list to JSON format and write to a file
    #     with open(file_name, 'w') as f:
    #         json.dump(orders, f, indent=4, default=str)  # `default=str` to handle non-serializable data like ObjectId and datetime
    # print(f"Orders have been saved to {file_name}")
        
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
                db = client['processes_db']
                collection = db['macchinari']
                collection.delete_many({})
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

if __name__ == '__main__':
    app = QApplication(sys.argv)

    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        main_window = MainWindow(login.user_role)
        main_window.show()
        sys.exit(app.exec_())
