import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime
import time
import csv

load_dotenv()

client_id = os.getenv('TWITCH_CLIENT_ID')
client_secret = os.getenv('TWITCH_SECRET')
if not all([client_id, client_secret]):
    raise ValueError("Missing Twitch API Keys")

overwatch2_twitch_id = '515025'

def get_oauth_token():
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    response = requests.post(url, params=params)
    oauth_token = response.json()["access_token"]
    return oauth_token
    
oauth_token = get_oauth_token()

# Whitelist of overwatch streamers to get vods from
# High rank (GM or so), mostly comp overwatch (no stadium/variety), no sub-only vods, english (for OCR), no obstructive overlay
# note: hiimsky was added despite playing mostly 6v6, I think for this that should be fine
whitelist_streamers = [
    'August', 'mL7support', 'pge4', 'Rakattack', '6Cyx', 'chosen_ow', 'hadi_ow', 'kraandop', 'vulture_ow',
    'durpee82', 'Apply', 'PLAYTO_ow', 'LhCloudy27', 'ZBRA', 'Josh369', 'cartifan22_', 'Yeatle', 'hiimsky',
    'chazm', 'pirate_ow_', 'harbleu', 'Danteh', 'sugarfree', 'cuFFa', 'WMaimone', 'xomba_ow', 'astdesign',
    'romani_ow', 'Gurkmeister', 'scyle2', 'Bowie', 'NenWhy', 'kronikfps'
]

def get_user_id(username):
    r = requests.get(f"https://api.twitch.tv/helix/users?login={username}", 
                     headers={f"Client-ID":client_id, f"Authorization":f"Bearer {oauth_token}"})
    r.raise_for_status()
    j = json.loads(r.text)
    id = j['data'][0]['id']
    return id


# Returns list of (user_name, url, created_at) from the last 10 vods of user_id
def vod_info_from_id(user_id):
    r = requests.get(f"https://api.twitch.tv/helix/videos?user_id={user_id}&type=archive&first=10", 
                     headers={f"Client-ID":client_id, f"Authorization":f"Bearer {oauth_token}"})
    r.raise_for_status()
    j = json.loads(r.text)
    
    print(j['data'][0])
    
    return [(v['user_name'], v['url'], v['created_at']) for v in j['data']]

# Gets VOD info from random streams at least an hour in length, and in english (for OCR)
# Randomness from getting the most recent 1h+ vods on the site, viewership independent
# Returns VOD info in full for now
def get_random_overwatch_vods():
    all_filtered = []
    cursor = None
    pages_fetched = 0
    max_pages = 5
    target_number_of_vods = 50 # At least this many vods should be grabbed

    while pages_fetched < max_pages:
        url = f"https://api.twitch.tv/helix/videos?game_id={overwatch2_twitch_id}&type=archive&first=100"
        if cursor:
            url += f"&after={cursor}"

        r = requests.get(url, headers={"Client-ID": client_id, "Authorization": f"Bearer {oauth_token}"})
        r.raise_for_status()
        data = r.json()['data']

        #filtered = [v for v in data if v['created_at'] < one_hour_ago_iso]
        filtered = [v for v in data if 'h' in v['duration'] and 'en' in v['language']] # at least an hour long, in english
        all_filtered.extend(filtered)

        if not data:
            if len(all_filtered) > 0:
                print("Error in getting random twitch vods, no data")
            break
        
        if len(all_filtered) >= target_number_of_vods:
            break

        cursor = r.json().get('pagination', {}).get('cursor')
        if not cursor:
            if len(all_filtered) > 0:
                print("Error in getting random twitch vods, no cursor")
            break

        pages_fetched += 1
        time.sleep(0.25)

    return all_filtered

# Returns list of (user_name, url, created_at) from the last 20 vods of all user_id in (username, user_id) csv input between date range
def get_whitelist_overwatch_vods(csv_path, cutoff_start_date, cutoff_end_date):
    vods = []
    
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            user_id = row['user_id']
            r = requests.get(f"https://api.twitch.tv/helix/videos?user_id={user_id}&type=archive&first=20", 
                                headers={f"Client-ID":client_id, f"Authorization":f"Bearer {oauth_token}"})
            r.raise_for_status()
            for v in r.json()['data']:
                dt = datetime.fromisoformat(v['created_at'].replace('Z', '+00:00'))
                if cutoff_start_date <= dt <= cutoff_end_date:
                    vods.append((v['user_name'], v['url'], v['created_at']))
            time.sleep(0.25)

    return vods

# Getting user IDs for whitelisted streamers
if __name__ == "__main__":
    results = []
    for username in whitelist_streamers:
        try:
            user_id = get_user_id(username)
            if user_id:
                results.append({'username': username, 'user_id': user_id})
            time.sleep(0.5)  # optional, to avoid rate limits
        except Exception as e:
            print(f"Error fetching {username}: {e}")

    with open('whitelist.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['username', 'user_id'])
        writer.writeheader()
        writer.writerows(results)