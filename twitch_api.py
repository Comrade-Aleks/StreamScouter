import requests
import time

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
            {"id": stream["user_id"], "name": stream["user_name"], "link": f"https://twitch.tv/{stream['user_name']}"}
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
    
    def get_profile_pictures(self, user_ids, output_file="profile_pictures.txt"):
        """Fetch profile pictures for a list of Twitch user IDs and save them to a text file."""
        url = "https://api.twitch.tv/helix/users"
        headers = {"Client-ID": self.client_id, "Authorization": f"Bearer {self.access_token}"}
        profile_pictures = {}
        batch_size = 100

        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]
            params = [("id", user_id) for user_id in batch]

            try:
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 429:
                    time.sleep(1)
                    continue
                if response.status_code != 200:
                    print(f"Error fetching profile pictures: {response.status_code} - {response.text}")
                    continue

                data = response.json()
                fetched_users = {user["id"]: user["profile_image_url"] for user in data.get("data", [])}
                profile_pictures.update(fetched_users)

            except requests.RequestException as e:
                print(f"Request failed: {e}")
                time.sleep(1)

            time.sleep(0.5)

        with open(output_file, "w") as file:
            for user_id, profile_picture in profile_pictures.items():
                file.write(f"{user_id}: {profile_picture}\n")

        return profile_pictures




