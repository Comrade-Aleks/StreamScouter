class StreamerTracker:
    def __init__(self, twitch_api, notify_var, notification_manager):
        self.twitch_api = twitch_api
        self.notify_var = notify_var
        self.notification_manager = notification_manager
        self.seen_streamers = set()
        self.linger_streamers = {}

    def track_changes(self, game_id, streamer_count):
        top_streams = self.twitch_api.get_top_streams(game_id, streamer_count)
        current_streamers = set(name for name, _ in top_streams)
        new_streamers = current_streamers - self.seen_streamers
        dropped_streamers = self.seen_streamers - current_streamers

        for streamer in dropped_streamers:
            if streamer in self.linger_streamers:
                if self.linger_streamers[streamer] <= 1:
                    del self.linger_streamers[streamer]
                else:
                    self.linger_streamers[streamer] -= 1  
            else:
                self.linger_streamers[streamer] = 2

        for streamer in list(self.linger_streamers.keys()):
            if streamer in current_streamers:
                del self.linger_streamers[streamer]

        if self.notify_var.get() and new_streamers:
            self.notification_manager.play_notification()

        self.seen_streamers = current_streamers | set(self.linger_streamers.keys())
        return top_streams