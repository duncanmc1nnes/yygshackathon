from datetime import datetime

def get_restaurant_database() -> list:
    pass

def get_party_database() -> list:
    pass

def get_filtered_party_database(earliest : datetime, latest : datetime, cuisine : str) -> list:
    parties : list = get_party_database()