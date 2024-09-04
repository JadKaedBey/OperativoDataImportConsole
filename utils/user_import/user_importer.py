import pandas as pd
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import os

def main():
    file_path = './OESSE_base_dati_rev0.xlsx'  # Updated to the actual file path
    sheet_name = 'matrice competenze operativo'  # Specified sheet name
    db_name = 'azienda'
    collection_name = 'utenti'

    df = read_excel(file_path, sheet_name)
    transformed_data = transform_data(df)
    upload_to_mongodb(transformed_data, db_name, collection_name)
    print("Data uploaded successfully.")

def transform_data(df):
    users = []
    # Iterate over each column (person), df.columns will have the names directly
    for name in df.columns:
        parts = name.split()
        first_name = ' '.join(parts[:-1])
        last_name = parts[-1]
        user_data = {
            "_id": ObjectId(),
            "nome": first_name,
            "cognome": last_name,
            "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
            "password": "123456789",
            "id": ''.join([part[0].upper() for part in parts]),
            "skills": {},
            "isLogged": False,
            "loggedAt": "",
            "image": "https://storage.needpix.com/rsynced_images/blank-profile-picture-973460_1280.png"
        }
        # Iterate over the index (skills)
        for skill in df.index:
            skill_value = df.at[skill, name]  # Access the skill value directly
            if isinstance(skill_value, str) and '%' in skill_value:
                percentage_value = int(skill_value.strip('%'))
            else:
                # Log unexpected format but continue processing
                print(f"Unexpected format for skill '{skill}' for '{name}': {skill_value}")
                continue
            user_data["skills"][skill] = {"$numberInt": str(percentage_value)}
        users.append(user_data)
    return users



def read_excel(file_path, sheet_name):
    # Load a specific sheet by name, use the first column as the index
    df = pd.read_excel(file_path, sheet_name=sheet_name, index_col=0)
    return df


def upload_to_mongodb(data, db_name, collection_name):
    client = MongoClient(os.getenv("AMADE_URI"))
 # Adjust the connection string as needed
  # Modify as needed
    db = client[db_name]
    collection = db[collection_name]
    collection.insert_many(data)

if __name__ == "__main__":
    main()
