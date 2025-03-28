class StreamerTracker:
    def __init__(self, twitch_api, notify_var, notification_manager):
        self.twitch_api = twitch_api
        self.notify_var = notify_var
        self.notification_manager = notification_manager
        self.seen_streamers = set()
        self.linger_streamers = {}

    def track_changes(self, game_id, streamer_count):
        top_streams = self.twitch_api.get_top_streams(game_id, streamer_count)
        current_streamer_ids = set(stream["id"] for stream in top_streams)
        dropped_streamer_ids = self.seen_streamers - current_streamer_ids

        for streamer_id in dropped_streamer_ids:
            if streamer_id in self.linger_streamers:
                if self.linger_streamers[streamer_id] <= 1:
                    del self.linger_streamers[streamer_id]
                else:
                    self.linger_streamers[streamer_id] -= 1
            else:
                self.linger_streamers[streamer_id] = 2

        for streamer_id in list(self.linger_streamers.keys()):
            if streamer_id in current_streamer_ids:
                del self.linger_streamers[streamer_id]

        self.seen_streamers = current_streamer_ids | set(self.linger_streamers.keys())

        streamer_ids = [stream["id"] for stream in top_streams]
        profile_pictures = self.twitch_api.get_profile_pictures(streamer_ids)

        results = [
            {
                "id": stream["id"],
                "name": stream["name"],
                "link": stream["link"],
                "profile_picture": profile_pictures.get(stream["id"], None),
            }
            for stream in top_streams
        ]

        return results