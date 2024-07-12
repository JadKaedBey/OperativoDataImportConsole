import pandas as pd

def save_to_csv(dataframe, filename):
    """
    Saves the given DataFrame to a CSV file.

    Args:
        dataframe (pd.DataFrame): The DataFrame to save.
        filename (str): The name of the file to save the data to.
    """
    try:
        dataframe.to_csv(filename, index=False)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Failed to save data to {filename}. Error: {e}")


def extract_second_kind_of_data_and_fasi(file_path):
    data = pd.read_excel(file_path)

    # Define static, dynamic, and conditional columns
    static_columns = ['Codice', 'LT', 'QtaFasi']
    dynamic_columns = ['T', 'TO', 'TA', 'D', 'P', 'FI', 'FO', 'FZS', 'L', 'S1', 'S2', 'SB', 'SV', 'TOR', 'PTM', 'TTM', 'FR', 'Stig', 'Smig', 'A', 'C', 'PA', 'VE']
    conditional_columns = ['ZF', 'ZC']

    data_frames = []
    seen_codice = set()

    for index, row in data.iterrows():
        if row['Codice'] not in seen_codice:
            # Check dynamic columns for non-zero values
            non_zero_columns = [col for col in dynamic_columns if row[col] != 0]

            # Include conditional columns based on specific values
            for col in conditional_columns:
                if row[col] == 'Si':
                    non_zero_columns.append(col)

            # Prepare row data with static and dynamic values
            row_data = {col: row[col] for col in static_columns if col in row}
            row_data.update({col: row[col] for col in non_zero_columns if col in row})

            # Debug: Print to see what's being captured
            print(f"Processing Codice: {row['Codice']}")
            print(f"Fasi detected: {non_zero_columns}")

            # Append phases to row data
            row_data['fasi'] = non_zero_columns

            # Convert to DataFrame and store
            data_frames.append(pd.DataFrame([row_data]))
            seen_codice.add(row['Codice'])

    # Concatenate all data frames
    final_data = pd.concat(data_frames, ignore_index=True)

    return final_data

# Path for testing
test_file_path = '20240612_Legami_KB_Officina.xlsx'
res = extract_second_kind_of_data_and_fasi(test_file_path)

save_to_csv(res, "print.csv")
# Print the result for testing
print(res)

