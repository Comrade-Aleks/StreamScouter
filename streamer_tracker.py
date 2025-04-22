class StreamerTracker:
    linger_duration = 10

    def __init__(self, twitch_api, notify_var, notification_manager):
        self.twitch_api = twitch_api
        self.notify_var = notify_var
        self.notification_manager = notification_manager
        self.seen_streamers = []
        self.linger_streamers = []
    def get_top_streams(self, game_id, streamer_count):
        top_streams = self.twitch_api.get_top_streams(game_id, streamer_count)
        streamer_ids = [stream["id"] for stream in top_streams]
        profile_pictures = self.twitch_api.get_profile_pictures(streamer_ids)
        return [
            {
                "id": stream["id"],
                "name": stream["name"],
                "link": stream["link"],
                "profile_picture": profile_pictures.get(stream["id"], None),
            }
            for stream in top_streams
        ]

    def process_streamers(self, top_streams):
        current_streamer_ids = {stream["id"] for stream in top_streams}
        dropped_streamer_ids = {s["id"] for s in self.seen_streamers} - current_streamer_ids

        self.update_linger_streamers(dropped_streamer_ids, current_streamer_ids)
        self.seen_streamers = top_streams + [
            s for s in self.linger_streamers if s["countdown"] > 0
        ]
        return top_streams


    def update_linger_streamers(self, dropped_streamers, current_streamers):
        self.linger_streamers = [
            lingering for lingering in self.linger_streamers
            if lingering["id"] not in current_streamers and lingering["countdown"] > 0
        ]

        for lingering in self.linger_streamers:
            lingering["countdown"] -= 1

        for streamer_id in dropped_streamers:
            if streamer_id not in current_streamers and not any(s["id"] == streamer_id for s in self.linger_streamers):
                streamer_data = next((s for s in self.seen_streamers if s["id"] == streamer_id), None)
                if streamer_data:
                    self.linger_streamers.append({
                        "id": streamer_data["id"],
                        "name": streamer_data["name"],
                        "link": streamer_data["link"],
                        "profile_picture": streamer_data["profile_picture"],
                        "countdown": self.linger_duration
                    })