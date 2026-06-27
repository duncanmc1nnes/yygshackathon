from datetime import datetime
from models import db, Party

def get_restaurant_database() -> list:
    pass

def get_party_database() -> list:
    parties = Party.query.all()
    return parties

def get_filtered_party_database(earliest : datetime, latest : datetime, cuisine : str) -> list:
    parties : list = get_party_database()
    final_parties : list = []
    for i in parties:
        if i.date >= earliest and i.date <= latest and similar_cuisine(cuisine1=i.cuisine, cuisine2=cuisine):
            final_parties.append(i)
    return final_parties

def similar_cuisine(cuisine1, cuisine2) -> bool:
    return cuisine1 == cuisine2