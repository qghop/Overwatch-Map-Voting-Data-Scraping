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

control_maps = ["ANTARCTIC PENINSULA", "BUSAN", "ILIOS", "LIJIANG TOWER", "NEPAL", "SAMOA", "OASIS"]
escort_maps = ["CIRCUIT ROYAL", "DORADO", "HAVANA", "JUNKERTOWN", "SHAMBALI MONASTERY", "RIALTO", "ROUTE 66", "WATCHPOINT: GIBRALTAR"]
flashpoint_maps = ["SURAVASA", "NEW JUNK CITY", "AATLIS"]
hybrid_maps = ["BLIZZARD WORLD", "EICHENWALDE", "HOLLYWOOD", "KING'S ROW", "MIDTOWN", "NUMBANI", "PARAÍSO"]
push_maps = ["COLOSSEO", "ESPERANÇA", "NEW QUEEN STREET", "RUNASAPI"]

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

    # if any vote column is just "VOTE" add 1 to the front
    for col in ['votes1', 'votes2', 'votes3']:
        df[col] = df[col].apply(lambda x: '1' + str(x) if str(x) == 'VOTE' else x)

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
    
    # Get total votes, remove row if below 2 or above 10
    df['total_votes'] = df[['votes1', 'votes2', 'votes3']].apply(lambda x: sum(int(v) for v in x if str(v).isdigit()), axis=1)
    df = df[df['total_votes'] > 1]
    df = df[df['total_votes'] <= 10]
    
    # Add columns percent1-3 = votes1-3 / total_votes
    df['percent1'] = df['votes1'].astype(int) / df['total_votes']
    df['percent2'] = df['votes2'].astype(int) / df['total_votes']
    df['percent3'] = df['votes3'].astype(int) / df['total_votes']

    # Calculate winner (majority votes)
    df['winner'] = df.apply(lambda row: row['map1'] if row['votes1'] > row['votes2'] and row['votes1'] > row['votes3'] 
                            else (row['map2'] if row['votes2'] > row['votes1'] and row['votes2'] > row['votes3'] 
                                else (row['map3'] if row['votes3'] > row['votes1'] and row['votes3'] > row['votes2'] 
                                        else 'draw')), axis=1)
    
    df.to_csv(output_file, index=False)
    return df

# Tiers based on half standard deviations
def get_tier(p):
    if p >= 0.84:
        return "S"
    elif p >= 0.69:
        return "A"
    elif p >= 0.5:
        return "B"
    elif p >= 0.31:
        return "C"
    elif p >= 0.16:
        return "D"
    else:
        return "F"

# Takes in cleaned_df (from clean_vote_data)
# Returns Dataframe with columns Map Name, Appearances, Total Votes, Total Percent of Votes
def summarize_vote_data(df):
    # Melt the dataframe to long format
    maps = df[['map1', 'votes1', 'percent1']].rename(columns={'map1': 'Map Name', 'votes1': 'Votes', 'percent1': 'Percent'})
    maps2 = df[['map2', 'votes2', 'percent2']].rename(columns={'map2': 'Map Name', 'votes2': 'Votes', 'percent2': 'Percent'})
    maps3 = df[['map3', 'votes3', 'percent3']].rename(columns={'map3': 'Map Name', 'votes3': 'Votes', 'percent3': 'Percent'})

    all_maps = pd.concat([maps, maps2, maps3], ignore_index=True)
    
    # Add map type column
    all_maps['Map Type'] = all_maps['Map Name'].apply(lambda x: 'Control' if x in control_maps else
                                                                'Escort' if x in escort_maps else
                                                                'Flashpoint' if x in flashpoint_maps else
                                                                'Hybrid' if x in hybrid_maps else
                                                                'Push' if x in push_maps else
                                                                'Unknown')

    # Ensure correct types
    all_maps['Votes'] = pd.to_numeric(all_maps['Votes'], errors='coerce')
    all_maps['Percent'] = pd.to_numeric(all_maps['Percent'], errors='coerce')
    all_maps = all_maps.dropna(subset=['Map Name', 'Votes', 'Percent'])

    # Group and aggregate
    summary = all_maps.groupby(['Map Name', 'Map Type']).agg(
        Appearances=('Map Name', 'count'),
        Total_Votes=('Votes', 'sum'),
        Total_Percent_of_Votes=('Percent', 'sum')
    ).reset_index()
    
    # Add columns votes per appearance and percent per appearance
    summary['Votes_per_Appearance'] = summary['Total_Votes'] / summary['Appearances']
    summary['Percent_per_Appearance'] = summary['Total_Percent_of_Votes'] / summary['Appearances']

    # Calculate tiers
    percentiles = summary["Votes_per_Appearance"].rank(pct=True)
    summary["Tier"] = percentiles.apply(get_tier)

    # Count wins (based on majority votes)
    win_counts = df[df['winner'] != 'draw']['winner'].value_counts()
    summary['Total_Wins'] = summary['Map Name'].map(win_counts).fillna(0).astype(int)
    summary['Win_Percentage'] = (summary['Total_Wins'] / summary['Appearances']).round(3)
    
    return summary
    

# Run on whitelisted data
if __name__ == "__main__":
    clean_vote_data('vote_data_whitelisted.csv', 'vote_data_whitelisted_cleaned.csv')