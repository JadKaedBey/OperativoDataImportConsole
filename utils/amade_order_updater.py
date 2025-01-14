from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
import re
import os
import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename

load_dotenv()

def update_phase_status(similar_order_id, codice_articolo, current_phase):
    # Connect to MongoDB
    client = MongoClient(os.getenv("AMADE_URI"))
    db = client['orders_db']
    collection = db["newOrdini"]

    # Append a wildcard to the similar_order_id to match any suffix
    regex_order_id = f"{re.escape(similar_order_id)}."

    # Debug statement to show the regex being used
    print(f"Using regex for orderId: {regex_order_id}")

    # Find the order by orderId
    order = collection.find_one({
        "orderId": similar_order_id,
        "codiceArticolo": codice_articolo
    })

    # Debug statement to show the query result
    print(f"Query result for orderId: {similar_order_id}, codiceArticolo: {codice_articolo}: {order}")

    if not order:
        print(f"No order found with orderId similar to: {similar_order_id} and codiceArticolo: {codice_articolo}")
        return

    # Get the index of the current phase in the phase array
    phase_index = None
    for i, phase_list in enumerate(order['phase']):
        if current_phase in phase_list:
            phase_index = i
            break

    if phase_index is None:
        print(f"No phase found with name: {current_phase}")
        return

    # Update the phaseStatus array of arrays
    updated_phase_status = order['phaseStatus']
    for i in range(len(updated_phase_status)):
        if i < phase_index:
            updated_phase_status[i] = [4]
        elif i == phase_index:
            updated_phase_status[i] = [1]
        else:
            updated_phase_status[i] = [1]

    # Update the document in the database
    result = collection.update_one(
        {"_id": order['_id']},
        {"$set": {"phaseStatus": updated_phase_status}}
    )

    if result.modified_count > 0:
        print(f"Order {order['orderId']} updated successfully.")
    else:
        print(f"No updates made to the order {order['orderId']}.")

def process_excel_file(file_path):
    # Read the Excel file
    df = pd.read_excel(file_path)

    # Iterate through each row in the DataFrame
    for _, row in df.iterrows():
        similar_order_id = str(row['Numero Ordine'])
        codice_articolo = str(row['Codice'])
        current_phase = row['Fase Attuale'] if pd.notna(row['Fase Attuale']) else ""

        # Debug statement to show current processing row
        print(f"Processing orderId: {similar_order_id}, codiceArticolo: {codice_articolo}, currentPhase: {current_phase}")

        # Call the update function
        update_phase_status(similar_order_id, codice_articolo, current_phase)

def select_excel_file():
    # Hide the root window
    Tk().withdraw()

    # Show the file dialog to select an Excel file
    file_path = askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    
    if file_path:
        process_excel_file(file_path)
    else:
        print("No file selected.")

# Example usage
select_excel_file()
