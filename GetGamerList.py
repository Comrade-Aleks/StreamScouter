import requests

CLIENT_ID = "YOUR_CLIENT_ID"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
GAME_NAME = "Minecraft"  # Change this to the game you want to track

def get_game_id(game_name):
    url = "https://api.twitch.tv/helix/games"
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    params = {"name": game_name}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    if data.get("data"):
        return data["data"][0]["id"]
    else:
        return None

def get_live_streams(game_id):
    url = "https://api.twitch.tv/helix/streams"
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    params = {"game_id": game_id, "first": 10}  # Get the top 10 streamers
    response = requests.get(url, headers=headers, params=params)
    return response.json()

game_id = get_game_id(GAME_NAME)
if game_id:
    streams = get_live_streams(game_id)
    for stream in streams["data"]:
        print(f"{stream['user_name']} is live: https://twitch.tv/{stream['user_name']}")
