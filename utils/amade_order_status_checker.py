from pymongo import MongoClient
from dotenv import load_dotenv
import os
import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
import re

load_dotenv()

def get_actual_phase(order_id, codice_articolo):
    # Connect to MongoDB
    client = MongoClient(os.getenv("AMADE_URI"))
    db = client['orders_db']
    collection = db["newOrdini"]

    # Append a wildcard to the similar_order_id to match any suffix
    regex_order_id = f"{re.escape(order_id)}.*$"

    # Find the order by orderId
    order = collection.find_one({
        "orderId": order_id,
        # "codiceArticolo": codice_articolo
    })

    if not order:
        print(f"No order found with orderId similar to: {order_id} and codiceArticolo: {codice_articolo}")
        return None

    # Find the actual phase with status = 2
    for i, status_list in enumerate(order['phaseStatus']):
        if 2 in status_list:
            return order['phase'][i][0]  # Return the actual phase name

    return None

def process_excel_file(file_path):
    # Read the Excel file
    df = pd.read_excel(file_path)

    # Create a list to store the results
    results = []

    # Iterate through each row in the DataFrame
    for _, row in df.iterrows():
        order_id = str(row['Numero Ordine'])
        codice_articolo = str(row['Codice'])
        expected_phase = row['Fase Attuale'] if pd.notna(row['Fase Attuale']) else ""

        # Get the actual phase from the database
        actual_phase = get_actual_phase(order_id, codice_articolo)

        # Determine if they match
        match = "Match" if expected_phase == actual_phase else "Mismatch"

        # Append the result to the list
        results.append({
            "Order ID": order_id,
            "Codice Articolo": codice_articolo,
            "Expected Phase": expected_phase,
            "Actual Phase": actual_phase,
            "Match": match
        })

    # Create a DataFrame from the results
    results_df = pd.DataFrame(results)

    # Save the results to an Excel file
    save_results_to_excel(results_df)

def save_results_to_excel(df):
    # Hide the root window
    Tk().withdraw()

    # Show the file dialog to select where to save the Excel file
    file_path = asksaveasfilename(
        title="Save Results As",
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )

    if file_path:
        df.to_excel(file_path, index=False)
        print(f"Results saved to {file_path}")
    else:
        print("No file selected.")

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
