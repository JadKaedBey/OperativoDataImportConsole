import pandas as pd

def create_orders_objects(file_path):
    # Load the data from Excel
    data = pd.read_excel(file_path)

    # Define the columns to use
    order_column = 'ID'
    fasi_column = 'Fase'
    tempo_ciclo_column = 'Tempo ciclo [min]'
    codice_column = 'Codice'
    quantita_column = 'QTA'
    descrizione_column = 'Descrizione'

    # Create a dictionary to hold the orders
    orders = {}

    # Process the DataFrame
    for index, row in data.iterrows():
        order_id = row[order_column]
        fasi = row[fasi_column]
        tempo_ciclo = row[tempo_ciclo_column]
        codice = row[codice_column]
        quantita = row[quantita_column]
        descrizione = row[descrizione_column]

        # Check if the order ID already exists in the dictionary
        if order_id not in orders:
            orders[order_id] = {
                'Quantità': quantita,
                'Codice': codice,
                'Descrizione': descrizione,
                'Fasi': [],
                'Tempo Ciclo': []
            }

        # Append the current Fasi and its Tempo Ciclo to the order
        orders[order_id]['Fasi'].append(fasi)
        orders[order_id]['Tempo Ciclo'].append(tempo_ciclo)

    # Displaying the Orders object
    for order_id, details in orders.items():
        print(f"Order {order_id}: Quantità: {details['Quantità']} Codice: {details['Codice']}, "
              f"Descrizione: {details['Descrizione']} [Fasi = {details['Fasi']}, "
              f"Tempo Ciclo = {details['Tempo Ciclo']}]")

# Example usage of the function
# Replace 'your_excel_file.xlsx' with the path to your actual Excel file
file_path = 'marcolin/excel.xlsx'
create_orders_objects(file_path)
