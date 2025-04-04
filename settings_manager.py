import os

class SettingsManager:
    def __init__(self, settings_file, env_file):
        self.settings_file = settings_file
        self.env_file = env_file

    def save_settings(self, game_name, streamer_count, width, height, notify_var, sound_file, volume_var, launch_at_startup=False):
        with open(self.settings_file, "w") as f:
            f.write(f"{game_name}\n{streamer_count}\n{width}\n{height}\n")
            f.write(f"{notify_var.get()}\n{sound_file.get()}\n{volume_var.get()}\n")
            f.write(f"{launch_at_startup}\n")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                lines = f.readlines()
                if len(lines) >= 8:
                    return (
                        lines[0].strip(),
                        int(lines[1].strip()),
                        lines[2].strip(),
                        lines[3].strip(),
                        lines[4].strip().lower() == "true",
                        lines[5].strip(),
                        float(lines[6].strip()),
                        lines[7].strip().lower() == "true"
                    )
        return "", 3, "300", "400", False, "default.wav", 0.5, False

    def load_setting(self, key, default):
        """Load a specific setting by key."""
        settings = self.load_settings()
        keys = ["game_name", "streamer_count", "width", "height", "notify", "sound_file", "volume", "launch_at_startup"]
        if key in keys:
            return settings[keys.index(key)]
        return default

    def save_env_variable(self, key, value):
        """Save an environment variable to the .env file with the correct naming convention."""
        key_mapping = {
            "CLIENT_ID": "YOUR_CLIENT_ID",
            "CLIENT_SECRET": "YOUR_CLIENT_SECRET",
            "ACCESS_TOKEN": "YOUR_ACCESS_TOKEN"
        }
        correct_key = key_mapping.get(key, key)
        os.environ[correct_key] = value

        env_lines = []
        if os.path.exists(self.env_file):
            with open(self.env_file, "r") as f:
                env_lines = f.readlines()

        updated = False
        with open(self.env_file, "w") as f:
            for line in env_lines:
                if line.startswith(f"{correct_key}="):
                    f.write(f"{correct_key}={value}\n")
                    updated = True
                else:
                    f.write(line)
            if not updated:
                f.write(f"{correct_key}={value}\n")

    def load_env_variable(self, key):
        """Load an environment variable from the .env file or the system."""
        if key in os.environ:
            return os.environ[key]
        if os.path.exists(self.env_file):
            with open(self.env_file, "r") as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        return line.strip().split("=", 1)[1]
                    if line.startswith(f"YOUR_{key}="):
                        return line.strip().split("=", 1)[1]
        return None