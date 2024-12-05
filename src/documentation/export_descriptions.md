# Function Descriptions

## Utility Functions for Exporting Data

### `order_status_mapper(status)`

**Description:**

Maps numerical order status codes to their corresponding human-readable strings.

**Functionality:**

- Checks if the input `status` is a list and extracts the first element if it is.
- Converts the status to an integer.
- Returns a string representing the order status based on the mapping:
  - `0`: "Non iniziato" (Not started)
  - `1`: "In corso" (In progress)
  - `4`: "Completato" (Completed)
- If the status code is not in the predefined mapping, it returns the string representation of the status.
- Handles exceptions for invalid or missing values.

---

### `phase_status_mapper(status_list)`

**Description:**

Maps numerical phase status codes to their corresponding human-readable strings, handling lists of statuses.

**Functionality:**

- Checks if the input `status_list` is a list.
  - If it is, recursively applies the mapping to each element in the list.
  - If it is not, maps the single status code.
- Converts each status code to an integer and maps it based on:
  - `0`: "attesa di materiale" (Waiting for material)
  - `1`: "Non iniziato" (Not started)
  - `2`: "In corso" (In progress)
  - `3`: "In ritardo" (Delayed)
  - `4`: "Completato" (Completed)
- If the status code is not in the predefined mapping, it returns the string representation of the status.
- Handles exceptions for invalid or missing values.

---

### `column_mapping`

**Description:**

A dictionary that maps internal column names to their corresponding column names in the exported Excel file.

**Mapping:**

- `'orderId'`: `'Order ID'`
- `'orderInsertDate'`: `'Order Insert Date'`
- `'codiceArticolo'`: `'Codice Articolo'` (Article Code)
- `'orderDescription'`: `'Order Description'`
- `'quantita'`: `'Quantità'` (Quantity)
- `'orderStatus'`: `'Order Status'`
- `'priority'`: `'Priorità'` (Priority)
- `'inCodaAt'`: `'In Coda At'`
- `'orderDeadline'`: `'Order Deadline'`
- `'customerDeadline'`: `'Customer Deadline'`
- `'orderStartDate'`: `'Order Start Date'`
- `'dataInizioLavorazioni'`: `'Work Start Date'`
- `'phase'`: `'Fase'` (Phase)
- `'phaseStatus'`: `'Stato Fase'` (Phase Status)
- `'assignedOperator'`: `'Operatore Assegnato'` (Assigned Operator)
- `'phaseLateMotivation'`: `'Motivazione Ritardo Fase'` (Phase Delay Motivation)
- `'phaseEndTime'`: `'Lead Time Fase'` (Phase Lead Time)
- `'phaseRealTime'`: `'Tempo Ciclo Performato'` (Performed Cycle Time)
- `'entrataCodaFase'`: `'Entrata Coda Fase'` (Phase Queue Entry)
- `'Sequenza'`: `'Sequenza'` (Sequence)

---

### `fetch_in_coda_at_names(client)`

**Description:**

Fetches a mapping from machine Object IDs to machine names from the MongoDB database.

**Functionality:**

- Connects to the `process_db` database and accesses the `macchinari` (machines) collection.
- Iterates over each document (machine) in the collection.
- Constructs a dictionary `id_to_name` mapping each machine's `_id` (as a string) to its `name`.
- Prints the mapping for verification.
- Returns the `id_to_name` dictionary.

---

### `fetch_in_lavorazione_at_names(client)`

**Description:**

Fetches a mapping from tablet UUIDs to machine names from the MongoDB database.

**Functionality:**

- Connects to the `process_db` database and accesses the `macchinari` collection.
- Iterates over each machine document.
- For each machine, checks if the `tablet` field exists and is a list.
- Iterates over the `tablet` UUIDs and maps each UUID to the machine's `name`.
- Prints the mapping for verification.
- Returns the `uuid_to_name` dictionary.

---

### `map_in_coda_at(value, id_to_name)`

**Description:**

Maps `inCodaAt` values, which can be Object IDs, to their corresponding machine names.

**Functionality:**

- Handles different types of input:
  - If `value` is a list, recursively applies the mapping to each element.
  - If `value` is a string, attempts to extract an Object ID using a regular expression.
    - If an Object ID is found, maps it to the machine name.
    - If not, tries a direct mapping.
  - If `value` is a dictionary (e.g., a MongoDB reference), extracts the `$oid` and maps it.
  - If `value` is an `ObjectId`, converts it to a string and maps it.
- Returns the machine name or the original value if no mapping is found.
- Handles exceptions and prints errors if mapping fails.

---

### `calculate_in_coda(df)`

**Description:**

Calculates the "in coda" (in queue) status for each row in the DataFrame based on specific conditions.

**Functionality:**

- Initializes an empty list `in_coda_values`.
- Iterates over each row in the DataFrame `df`.
- For each row (starting from the second one), compares the current and previous row's:
  - `phaseStatus`
  - `entrataCodaFase` (queue entry time)
- Parses the `phaseStatus` to handle lists and strings containing multiple statuses.
- Determines the "in coda" status based on the following conditions:
  - If the current phase is not completed (`current_row_status < 4`).
  - If the previous phase is completed (`prev_row_status == 4`).
  - If the current entry time is greater than the previous one.
- Appends "in coda" or an empty string to `in_coda_values` based on the conditions.
- Returns the list `in_coda_values`.

---

### `parse_value(val, default=[''])`

**Description:**

Parses a value that could be `None`, `NaN`, a string representation of a list, or an actual list/array, and returns a list.

**Functionality:**

- Checks if `val` is `None` or `NaN` and returns the `default` value.
- If `val` is a string, attempts to evaluate it using `ast.literal_eval` to parse it into a Python object.
  - If parsing fails, returns the `default` value.
- If `val` is a NumPy array, converts it to a list.
- If `val` is already a list, returns it as is.
- If `val` is a single value, wraps it in a list.
- Handles exceptions and prints an error message if parsing fails.

---

### `map_in_coda_at_value(val, id_to_name)`

**Description:**

Maps a single `inCodaAt` value to a machine name using `map_in_coda_at`.

**Functionality:**

- Calls `map_in_coda_at` with the provided `val` and `id_to_name` mapping.
- Used during data parsing to map machine IDs to names.

---

### `map_in_lavorazione_at_value(val, uuid_to_name)`

**Description:**

Maps `inLavorazioneAt` values (which could be UUIDs) to machine names.

**Functionality:**

- If `val` is a list, recursively applies the mapping to each element.
- If `val` is a string that resembles a UUID (contains a hyphen), attempts to map it using `uuid_to_name`.
- Returns the machine name or the original value if no mapping is found.
- If `val` is not a string or list, returns it as is.

---

### `parse_entrata_coda_fase(val)`

**Description:**

Parses the `entrataCodaFase` (phase queue entry) value, handling datetime parsing.

**Functionality:**

- Checks if `val` is `None` or `NaN`, returns a list with an empty string.
- If `val` is a string, attempts to:
  - Replace `datetime.datetime` with `dt` to safely evaluate it.
  - Evaluate the string using `eval` with a restricted dictionary (`{"dt": datetime}`).
  - Returns the parsed value as a list.
- If evaluation fails, prints an error message and returns a list with an empty string.
- For other types, uses `parse_value` to parse the value.

---

### `create_new_row(row, phases, parsed_columns, columns_to_parse)`

**Description:**

Creates and returns new expanded rows for each phase, effectively flattening nested data structures.

**Functionality:**

- Initializes an empty list `new_rows`.
- Determines the number of phases (`num_phases`).
- Ensures all parsed columns have the same length as the number of phases, padding with default values if necessary.
- Iterates over each phase index:
  - Copies the original `row` to `new_row`.
  - For each column in `columns_to_parse` and `'entrataCodaFase'`:
    - Retrieves the value corresponding to the current phase.
    - If the value is a list, joins its elements into a string.
    - Handles specific formatting for `'entrataCodaFase'` and datetime values.
    - Updates `new_row` with the parsed and formatted value.
  - Adds `new_row` to `new_rows`.
- Returns the list `new_rows`.

---

### `format_queue_entry_time(value)`

**Description:**

Formats the `Queue Entry Time` value into a human-readable datetime string.

**Functionality:**

- Checks if `value` is a `datetime` object and formats it as `'YYYY-MM-DD HH:MM'`.
- If not, attempts to parse `value` into a datetime using `pandas.to_datetime`.
- If parsing succeeds, formats the datetime.
- If parsing fails, returns the original `value`.

---

### `parse_columns(row, columns_to_parse, id_to_name)`

**Description:**

Parses specific columns in a row and handles mappings for machine IDs and other special cases.

**Functionality:**

- Initializes an empty dictionary `parsed_columns`.
- Iterates over each column in `columns_to_parse`:
  - Retrieves the value from `row`.
  - Parses the value using `parse_value`.
  - If the column is `'inCodaAt'`, maps the values to machine names using `map_in_coda_at_value`.
  - If the column is `'entrataCodaFase'`, parses it using `parse_entrata_coda_fase`.
  - If the column is `'inLavorazioneAt'`, maps the values using `map_in_lavorazione_at_value`.
- Returns the `parsed_columns` dictionary.

---