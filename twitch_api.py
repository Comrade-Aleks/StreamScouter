import requests

class TwitchAPI:
    def __init__(self, client_id, access_token):
        self.client_id = client_id
        self.access_token = access_token

    def get_game_id(self, game_name):
        url = "https://api.twitch.tv/helix/games"
        headers = {"Client-ID": self.client_id, "Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers, params={"name": game_name})
        data = response.json()
        return data["data"][0]["id"] if data.get("data") else None

    def get_top_streams(self, game_id, limit):
        url = "https://api.twitch.tv/helix/streams"
        headers = {"Client-ID": self.client_id, "Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers, params={"game_id": game_id, "first": limit})
        data = response.json()
        return [
            (stream["user_name"], f"https://twitch.tv/{stream['user_name']}")
            for stream in data.get("data", [])
        ]

    def generate_access_token(self, client_secret):
        """Generate an access token using the client ID and client secret."""
        url = "https://id.twitch.tv/oauth2/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Failed to generate access token: {response.status_code} - {response.text}")
            return None