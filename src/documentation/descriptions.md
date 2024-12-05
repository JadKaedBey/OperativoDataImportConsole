# Function Descriptions

## Global Functions

### `connect_to_mongodb(username, password)`

**Description:**

Authenticates a user and establishes a connection to the MongoDB instance. It accesses the company's collection based on the provided username and retrieves the actual connection details to connect to the company's database.

**Functionality:**

- Constructs an initial connection string using the provided `username` and `password`.
- Connects to the `loginaziende` MongoDB cluster.
- Fetches the document corresponding to the `username` to retrieve the actual connection string (`stringaConn`).
- Replaces placeholders in the connection string with actual credentials.
- Establishes a global MongoDB client connection (`client`) to the company's database.
- Returns `True` if the connection is successful, otherwise `False`.

---

### `fetchSettings()`

**Description:**

Retrieves the settings document from the MongoDB database.

**Functionality:**

- Accesses the `settings` collection in the `azienda` database.
- Fetches the first settings document.
- Raises a `ValueError` if no settings document is found.
- Returns the settings document.

---

### `fetchMacchinari()`

**Description:**

Fetches the list of machine names (`macchinari`) from the MongoDB database.

**Functionality:**

- Accesses the `macchinari` collection in the `process_db` database.
- Retrieves all machine documents, fetching only the `name` field.
- Returns a list of machine names.

---

### `get_phase_end_times(phases, codiceArticolo)`

**Description:**

Retrieves the duration of each phase for a given product code (`codiceArticolo`).

**Functionality:**

- Accesses the `famiglie_di_prodotto` collection in the `process_db` database.
- Finds the product family document that contains the given `codiceArticolo`.
- For each phase in the provided `phases` list:
  - Searches the family's dashboard elements to find the phase by name.
  - Retrieves the `phaseDuration` for the phase.
  - Appends the duration to the `end_times` list.
- If the family or phase is not found, appends `0` as the duration.
- Returns the list of phase end times.

---

### `check_family_existance_db(familyName)`

**Description:**

Checks whether a product family exists in the database.

**Functionality:**

- Accesses the `famiglie_di_prodotto` collection in the `process_db` database.
- Searches for a document with the title (`titolo`) matching `familyName`.
- Returns `True` if the family exists.

---

### `create_order_object(phases, articolo, quantity, order_id, end_date, order_description, settings)`

**Description:**

Creates an order object suitable for insertion into the MongoDB database, using the provided parameters.

**Functionality:**

- Calculates the phase dates by calling `calculate_phase_dates`, which computes the entry dates for each phase queue (`entrata coda fase`).
- Ensures the phase dates are sorted correctly.
- Determines the earliest start date (`start_date`) from the phase dates.
- Constructs an order data dictionary with all necessary fields:
  - `orderId`, `orderStartDate`, `assignedOperator`, `orderStatus`, `orderDescription`, `codiceArticolo`, `orderDeadline`, `customerDeadline`, `quantita`, `phase`, `phaseStatus`, `phaseEndTime`, `phaseLateMotivation`, `phaseRealTime`, `entrataCodaFase`, `priority`, `inCodaAt`, `inLavorazioneAt`.
- Uses a Pydantic model `OrderModel` to validate the order data.
- Returns the validated order data as a dictionary.
- If validation fails, prints the validation error and returns `None`.

---

### `create_json_for_flowchart(codice, phases, cycle_times, queueTargetTimes, description)`

**Description:**

Creates a JSON object representing a product family flowchart, suitable for insertion into the MongoDB database.

**Functionality:**

- Generates unique IDs for each phase element.
- Constructs the dashboard elements for the flowchart, including position, size, text (phase name), phase duration, and phase target queue time.
- Links the phases sequentially by adding `next` pointers.
- Assembles the final JSON object representing the product family, including:
  - `titolo`, `descrizione`, `image`, `dashboard`, and `catalogo`.
- Returns the JSON object.

---

### `excel_date_parser(date_str)`

**Description:**

Parses a date string from an Excel file into a `datetime` object.

**Functionality:**

- Uses `pandas.to_datetime` with `dayfirst=True` and `errors='coerce'` to parse the date string.
- Returns the parsed date or `NaT` (Not a Time) if parsing fails.

---

### `upload_orders_from_xlsx(self)`

**Description:**

Uploads orders from an Excel file into the MongoDB database.

**Functionality:**

- Prompts the user to select an Excel file using a file dialog.
- Reads the 'Ordini' sheet from the Excel file into a DataFrame.
- Checks if required columns are present in the DataFrame.
- Drops rows where 'Codice Articolo' is missing.
- Fetches existing order IDs from the database to avoid duplicates.
- Processes each order in the DataFrame:
  - Validates and parses the data, including date parsing.
  - Checks if the product code (`codiceArticolo`) exists in the database.
  - Retrieves the phases for the product code.
  - Creates an order object using `create_order_object`.
  - Inserts the order into the `orders_db` database.
- Keeps track of successful orders, failed orders, and skipped orders.
- Shows an upload report by calling `show_upload_report`.

---

### `show_upload_report(successful_orders, failed_orders, skipped_orders)`

**Description:**

Displays a report of the orders upload process.

**Functionality:**

- Constructs a report message summarizing the number of successful, failed, and skipped orders.
- Displays the report in a popup dialog using `QMessageBox`.
- Calls `save_report_to_file` to save the report to a file.

---

### `save_report_to_file(report_content, report_type)`

**Description:**

Saves a report to a text file in the 'reports' directory.

**Functionality:**

- Creates a 'reports' directory if it does not exist.
- Generates a timestamped filename based on the `report_type` and current datetime.
- Writes the `report_content` to the file.
- Handles any exceptions during file writing.

---

### `show_family_upload_report(successful_families, failed_families, skipped_families)`

**Description:**

Displays a report of the product families upload process.

**Functionality:**

- Constructs a report message summarizing the number of successful, failed, and skipped families.
- Displays the report in a popup dialog using `QMessageBox`.
- Calls `save_report_to_file` to save the report to a file.

---

## Classes

### `LoginWindow(QDialog)`

**Description:**

Represents the login window where the user enters their username and password.

#### Methods:

- `__init__(self, parent=None)`

  **Description:**

  Initializes the login window, sets up the UI elements (username and password fields, login button), and connects the login button to the `on_login` method.

- `on_login(self)`

  **Description:**

  Handles the login process when the login button is clicked.

  **Functionality:**

  - Retrieves the entered `username` and `password`.
  - Calls `connect_to_mongodb` with the credentials.
  - If the connection is successful, accepts the dialog and proceeds to the main window.
  - If the connection fails, shows an error message.

---

### `MainWindow(QMainWindow)`

**Description:**

Represents the main application window after successful login, providing various functionalities.

#### Methods:

- `__init__(self, user_role)`

  **Description:**

  Initializes the main window, sets up UI elements (buttons, layouts), and connects buttons to their respective functions.

  **Functionality:**

  - Sets up the window title, geometry, and central widget.
  - Adjusts the window and image sizes based on the screen size.
  - Adds the company logo to the layout.
  - Creates buttons for various functionalities:
    - Upload Orders
    - Upload Flussi (Famiglie)
    - Export Data
    - Generate Operatori QR Codes
    - Generate Order QR Codes
    - Upload Articoli
  - Adds the buttons to the layout and connects them to their respective methods.

---

- `initialize_ui(self)`

  **Description:**

  Initializes the UI based on the user's role.

  **Functionality:**

  - Checks the `user_role` attribute.
  - Calls `setup_special_user_ui` or `setup_regular_user_ui` based on the role.

---

- `adjust_sizes(self)`

  **Description:**

  Adjusts the window and image sizes based on the screen size.

  **Functionality:**

  - Retrieves the primary screen's geometry.
  - Calculates the window size as 50% of the screen size.
  - Sets the window size.
  - Calculates the image size as 30% of the window size.

---

- `generate_and_save_qr_codes(self)`

  **Description:**

  Generates QR codes for operators and saves them to files.

  **Functionality:**

  - Checks if the QR codes save path exists; if not, creates it.
  - Connects to the `utenti` collection in the `azienda` database.
  - Iterates over each user document in the collection.
  - For each user:
    - Constructs the QR data as `name||surname||password`.
    - Generates the QR code by calling `generate_qr`.
  - Shows a success message or an error message.

---

- `generate_qr(self, data, filename, name, surname)`

  **Description:**

  Generates a QR code with the given data and adds the operator's name as text below the QR code.

  **Functionality:**

  - Creates a QR code with the specified data.
  - Converts the QR code image to RGB format.
  - Adds the operator's name and surname as text below the QR code.
  - Saves the image to the specified filename.

---

- `generate_order_qr_codes(self)`

  **Description:**

  Generates QR codes for orders and saves them to files.

  **Functionality:**

  - Prompts the user to select a folder to save the QR codes.
  - Connects to the `ordini` collection in the `orders_db` database.
  - Iterates over each order document in the collection.
  - For each order:
    - Constructs the QR data as the order ID.
    - Generates the QR code by calling `generate_order_qr_with_text`.
  - Shows a success message or an error message.

---

- `generate_order_qr_with_text(self, data, full_path, order_id, codice_articolo, quantita)`

  **Description:**

  Generates a QR code for an order and adds order details as text below the QR code.

  **Functionality:**

  - Creates a QR code with the specified data (order ID).
  - Converts the QR code image to RGB format.
  - Adds the order details (`Order ID`, `Codice`, `Quantita`) as text below the QR code.
  - Saves the image to the specified full path.

---

- `init_placeholder(self)`

  **Description:**

  Initializes a placeholder message in the table widget.

  **Functionality:**

  - Sets the table widget's row and column count to 1.
  - Adds a message to the table indicating that a CSV file needs to be uploaded.

---

- `wipe_database(self)`

  **Description:**

  Provides functionality to wipe the database (not recommended).

  **Functionality:**

  - Prompts the user for confirmation.
  - If confirmed, deletes all documents in the `macchinari` collection in the `processes_db` database.
  - Clears any data.
  - Shows a success message or an error message.

---

- `upload_orders(self)`

  **Description:**

  Initiates the process of uploading orders from an Excel file.

  **Functionality:**

  - Calls `upload_orders_from_xlsx` to upload orders from an Excel file.
  - Shows an information message upon completion.

---

- `importFamiglie(self)`

  **Description:**

  Imports product families from an Excel file into the database.

  **Functionality:**

  - Prompts the user to select an Excel file.
  - Reads the 'Famiglie' sheet from the Excel file into a DataFrame.
  - Checks if required columns are present.
  - Fetches existing families from the database.
  - Processes each family group in the DataFrame:
    - Checks for duplicate phases.
    - Validates the phases against the machine list.
    - Creates a JSON object for the flowchart using `create_json_for_flowchart`.
    - Inserts the family into the `famiglie_di_prodotto` collection.
  - Keeps track of successful, failed, and skipped families.
  - Shows an upload report by calling `show_family_upload_report`.

---

- `select_database_and_collection(self)`

  **Description:**

  Prompts the user to select a database and collection for exporting data.

  **Functionality:**

  - Retrieves the list of databases and collections from MongoDB.
  - Displays a dialog with dropdowns for selecting the database and collection.
  - When a database is selected, updates the collection list.
  - Upon confirmation, calls `export_data` with the selected database and collection.

---

- `export_data(self, db_name, collection_name)`

  **Description:**

  Exports data from the selected database and collection to an Excel file.

  **Functionality:**

  - Connects to the specified database and collection.
  - Fetches all documents from the collection.
  - Converts the data to a DataFrame.
  - Performs data processing:
    - Parses columns that contain lists of lists.
    - Expands the rows based on phases.
    - Maps IDs to names for machines and operators.
    - Calculates additional columns.
    - Renames columns according to a mapping.
  - Prompts the user to select a file path for saving the Excel file.
  - Saves the processed data to an Excel file.
  - Shows a success message or an error message.

---

- `upload_articoli(self)`

  **Description:**

  Uploads articles from an Excel file into the database.

  **Functionality:**

  - Prompts the user to select an Excel file.
  - Reads the 'Articoli' sheet from the Excel file into a DataFrame.
  - Checks if required columns are present.
  - Fetches existing families from the database.
  - Processes each article in the DataFrame:
    - Validates the family of the article.
    - Checks if the article already exists in the family's catalog.
    - Creates a new catalog item for the article.
    - Updates the family document in the database.
  - Keeps track of successful articles and errors.
  - Shows a processing summary and writes a report to a file.

---

## Main Execution Block

At the end of the script, the main execution block initializes the application and displays the login window. If the login is successful, it proceeds to show the main window.

```python
if __name__ == "__main__":
    app = QApplication(sys.argv)

    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        main_window = MainWindow(login.user_role)
        main_window.show()
        sys.exit(app.exec_())
```

---