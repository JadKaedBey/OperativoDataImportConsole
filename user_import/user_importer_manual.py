import pandas as pd
from pymongo import MongoClient
from bson import ObjectId

def main():
    db_name = 'azienda'
    collection_name = 'utenti'
    transformed_data = create_manual_data()
    upload_to_mongodb(transformed_data, db_name, collection_name)
    print("Data uploaded successfully.")

def create_manual_data():
    names = ["Amato Daniela", "De Grandis Cristian", "Amato Federico", "Basso Basset Chiara", 
             "Khan Naheed", "Scodeller Fabio", "Moldan Ramon Delis", "Ciesse BouBou", "Colautti Nicola"]
    skills = [
        "Piega", "Taglio", "Saldatura", "CNC", "Fresatura/Foratura", "Taglio profilati", 
        "Calandra", "Filettatrice", "Smerigliatura", "Imballaggio", "Spedizioni - Trasporti"
    ]
    percentages = [
        [100, 100, 17, 75, 100, 58, 33, 33, 25],
        [100, 100, 100, 33, 33, 17, 17, 17, 33],
        [50, 100, 63, 0, 63, 100, 88, 50, 0],
        [100, 50, 50, 0, 0, 25, 25, 0, 25],
        [100, 100, 100, 75, 100, 100, 100, 100, 75],
        [100, 100, 100, 0, 100, 100, 100, 100, 100],
        [100, 100, 75, 0, 50, 100, 100, 75, 50],
        [100, 100, 100, 100, 100, 100, 100, 100, 100],
        [100, 100, 100, 75, 100, 100, 100, 100, 50],
        [100, 100, 100, 100, 100, 100, 100, 100, 100],
        [100, 100, 0, 50, 50, 0, 100, 0, 100]
    ]

    users = []
    for index, name in enumerate(names):
        first_name, last_name = name.split(' ', 1)
        user_data = {
            "_id": ObjectId(),
            "nome": first_name,
            "cognome": last_name,
            "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
            "password": "123456789",
            "id": ''.join([part[0].upper() for part in name.split()]),
            "skills": {skill: {"$numberInt": str(percentages[skill_index][index])} for skill_index, skill in enumerate(skills)},
            "isLogged": False,
            "loggedAt": "",
            "image": "https://storage.needpix.com/rsynced_images/blank-profile-picture-973460_1280.png"
        }
        users.append(user_data)
    return users

def upload_to_mongodb(data, db_name, collection_name):
    client = MongoClient('mongodb+srv://amade_serverless:UH0GEayED87@amadeserverlesscluster.xavtarq.mongodb.net/?retryWrites=true&w=majority&appName=AMADEServerlessCluster')
    db = client[db_name]
    collection = db[collection_name]
    collection.insert_many(data)

if __name__ == "__main__":
    main()
