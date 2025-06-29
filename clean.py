import pandas as pd
from rapidfuzz import fuzz, process

overwatch_maps = [
    # Control Maps
    "ANTARCTIC PENINSULA", "BUSAN", "ILIOS", "LIJIANG TOWER", "NEPAL", "SAMOA", "OASIS",
    # Escort Maps
    "CIRCUIT ROYAL", "DORADO", "HAVANA", "JUNKERTOWN", "SHAMBALI MONASTERY", "RIALTO", "ROUTE 66", "WATCHPOINT: GIBRALTAR",
    # Flashpoint Maps
    "SURAVASA", "NEW JUNK CITY", "AATLIS",
    # Hybrid Maps
    "BLIZZARD WORLD", "EICHENWALDE", "HOLLYWOOD", "KING'S ROW", "MIDTOWN", "NUMBANI", "PARAÍSO",
    # Push Maps
    "COLOSSEO", "ESPERANÇA", "NEW QUEEN STREET", "RUNASAPI"
]

# Fuzzy match map_name
def fix_map_name(map_name, valid_maps, threshold=80):
    if pd.isnull(map_name) or not map_name.strip():
        return None

    match, score, _ = process.extractOne(map_name, valid_maps, scorer=fuzz.ratio)
    if score >= threshold:
        return match
    return None

# Cleans map_vote data, saves to output_file and returns df
def clean_vote_data(input_file, output_file):
    # Read input file
    column_names = ['user_name', 'url', 'created_at', 'map1', 'votes1', 'map2', 'votes2', 'map3', 'votes3']
    df = pd.read_csv(input_file, names=column_names, header=None)

    # For votes columns, get the first character, and if it isnt a number, remove the whole row
    for col in ['votes1', 'votes2', 'votes3']:
        df[col] = df[col].apply(lambda x: x[0] if str(x)[0].isdigit() else None)
    df = df.dropna(subset=['votes1', 'votes2', 'votes3'])
    
    # Convert maps to uppercase
    for col in ['map1', 'map2', 'map3']:
        df[col] = df[col].str.upper()
    
    # Fix names to fuzzy match overwatch_maps
    for col in ['map1', 'map2', 'map3']:
        df[col] = df[col].apply(lambda x: fix_map_name(x, overwatch_maps))
    
    # Drop rows with NaN in map columns
    df = df.dropna(subset=['map1', 'map2', 'map3'])
    
    # Convert created_at to datetime, and only keep the date part
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['created_at'] = df['created_at'].dt.date
    
    # Remove duplicate votes from same created_at date
    df = df.drop_duplicates(subset=['map1', 'votes1', 'map2', 'votes2', 'map3', 'votes3', 'created_at'], keep='first')
    
    df.to_csv(output_file, index=False)
    return df