class StreamerTracker:
    def __init__(self, twitch_api, notify_var, notification_manager):
        self.twitch_api = twitch_api
        self.notify_var = notify_var
        self.notification_manager = notification_manager
        self.seen_streamers = set()
        self.linger_streamers = {}

    def get_top_streams(self, game_id, streamer_count):
        return self.twitch_api.get_top_streams(game_id, streamer_count)

    def process_streamers(self, top_streams):
        current_streamer_ids = {stream["id"] for stream in top_streams}
        dropped_streamer_ids = self.seen_streamers - current_streamer_ids

        self.update_linger_streamers(dropped_streamer_ids, current_streamer_ids)
        self.seen_streamers = current_streamer_ids | set(self.linger_streamers.keys())
        
        return self.build_streamer_data(top_streams)

    def update_linger_streamers(self, dropped_streamers, current_streamers):
        for streamer_id in dropped_streamers:
            if streamer_id in self.linger_streamers:
                self.linger_streamers[streamer_id] -= 1
                if self.linger_streamers[streamer_id] <= 0:
                    del self.linger_streamers[streamer_id]
            else:
                self.linger_streamers[streamer_id] = 2

        for streamer_id in list(self.linger_streamers.keys()):
            if streamer_id in current_streamers:
                del self.linger_streamers[streamer_id]

    def build_streamer_data(self, top_streams):
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
