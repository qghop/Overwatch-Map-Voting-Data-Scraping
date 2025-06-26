import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

client_id = os.getenv('TWITCH_CLIENT_ID')
client_secret = os.getenv('TWITCH_SECRET')

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
