import tkinter as tk
import CheckForUpdate
from tkinter import messagebox, filedialog
from dotenv import load_dotenv
from layout import Layout
from twitch_api import TwitchAPI
from notification_manager import NotificationManager
from streamer_tracker import StreamerTracker
from settings_manager import SettingsManager
from tray_icon_manager import TrayIconManager
import threading
import time

root = tk.Tk()

CheckForUpdate.check_for_update_after_startup()

load_dotenv()

SETTINGS_FILE = "settings.txt"
ENV_FILE = ".env"

settings_manager = SettingsManager(SETTINGS_FILE, ENV_FILE)
default_game, default_count, default_width, default_height, default_notify, default_sound, default_volume = settings_manager.load_settings()

notify_var = tk.BooleanVar(value=default_notify)
sound_file = tk.StringVar(value=default_sound)
volume_var = tk.DoubleVar(value=default_volume)
stream_links = {}

twitch_api = TwitchAPI(
    settings_manager.load_env_variable("YOUR_CLIENT_ID"),
    settings_manager.load_env_variable("YOUR_ACCESS_TOKEN")
)
notification_manager = NotificationManager(sound_file, volume_var)
tracker = StreamerTracker(twitch_api, notify_var, notification_manager)

stop_tracking = threading.Event()
seen_streamers = set()
linger_streamers = {}
first_run = True
minimized_at = 0
tracking_thread = None
is_updating = False

def save_settings(game_name, streamer_count, width, height):
    settings_manager.save_settings(game_name, streamer_count, width, height, notify_var, sound_file, volume_var)

def generate_access_token():
    client_id = layout.client_id_entry.get()
    client_secret = layout.client_secret_entry.get()

    settings_manager.save_env_variable("CLIENT_ID", client_id)
    settings_manager.save_env_variable("CLIENT_SECRET", client_secret)

    access_token = twitch_api.generate_access_token(client_secret)
    if access_token:
        settings_manager.save_env_variable("ACCESS_TOKEN", access_token)
        layout.access_token_entry.delete(0, tk.END)
        layout.access_token_entry.insert(0, access_token)
        messagebox.showinfo("Success", "Client info saved and access token generated!")
    else:
        messagebox.showerror("Error", "Failed to generate access token")

def save_client_info():
    client_id = layout.client_id_entry.get()
    client_secret = layout.client_secret_entry.get()
    settings_manager.save_env_variable("CLIENT_ID", client_id)
    settings_manager.save_env_variable("CLIENT_SECRET", client_secret)
    messagebox.showinfo("Success", "Client ID and Secret saved!")

def quit_app():
    save_settings(layout.game_entry.get(), layout.count_entry.get(), root.winfo_width(), root.winfo_height())
    if tray_icon_manager.tray_icon:
        tray_icon_manager.tray_icon.stop()
    root.destroy()

def on_close():
    root.withdraw()
    tray_icon_manager.minimize_to_tray()

def on_show():
    """Restore the application window and reset the tray icon."""
    root.deiconify()
    tray_icon_manager.stop_blinking_icon()
    if tray_icon_manager.tray_icon:
        tray_icon_manager.tray_icon.stop()
        tray_icon_manager.tray_icon = None
    
tray_icon_manager = TrayIconManager(root, on_show, lambda: quit_app())

def toggle_notifications():
    print(f"Notifications {'enabled' if notify_var.get() else 'disabled'}.")

def select_sound_file():
    file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3")])
    if file_path:
        sound_file.set(file_path)
        print(f"Selected sound file: {file_path}")

def update_volume(value):
    print(f"Volume updated to: {value}")

def track_changes(game_name, streamer_count):
    global seen_streamers, minimized_at, first_run, linger_streamers
    stop_tracking.clear()

    while not stop_tracking.is_set():
        game_id = twitch_api.get_game_id(game_name)
        if not game_id:
            root.after(0, lambda: messagebox.showerror("Error", f"Game '{game_name}' not found on Twitch."))
            return

        top_streams = tracker.track_changes(game_id, streamer_count)
        current_streamer_ids = set(stream["id"] for stream in top_streams)
        new_streamer_ids = current_streamer_ids - seen_streamers
        dropped_streamer_ids = seen_streamers - current_streamer_ids

        for streamer_id in dropped_streamer_ids:
            if streamer_id in linger_streamers:
                if linger_streamers[streamer_id] <= 1:
                    del linger_streamers[streamer_id]
                else:
                    linger_streamers[streamer_id] -= 1
            else:
                linger_streamers[streamer_id] = 2

        for streamer_id in list(linger_streamers.keys()):
            if streamer_id in current_streamer_ids:
                del linger_streamers[streamer_id]

        if new_streamer_ids:
            if not first_run:
                if minimized_at == 0 or time.time() - minimized_at >= 30:
                    if notify_var.get():
                        notification_manager.play_notification()
                    if root.state() == 'withdrawn':
                        tray_icon_manager.start_blinking_icon()

        seen_streamers = current_streamer_ids | set(linger_streamers.keys())

        if root.state() != 'withdrawn':
            root.after(0, lambda: clear_canvas(layout.canvas_frame))
            for stream in top_streams:
                root.after(
                    0,
                    lambda s=stream: layout.add_item_to_canvas(
                        s["name"], s["link"], s["profile_picture"]
                    ),
                )
                stream_links[stream["id"]] = stream["link"]

        first_run = False

        for i in range(30, 0, -1):
            if stop_tracking.is_set():
                return

            if i < 2:
                root.after(0, lambda: layout.track_button.config(state=tk.DISABLED))
            else:
                root.after(0, lambda: layout.track_button.config(state=tk.NORMAL))

            if root.state() != 'withdrawn':
                root.after(0, lambda t=i: layout.timer_label.config(text=f"Next refresh in: {t}s"))

            time.sleep(1)

        if root.state() != 'withdrawn':
            root.after(0, lambda: layout.timer_label.config(text="Refreshing streams..."))
            if i == 30:
                root.after(0, lambda: layout.track_button.config(state=tk.NORMAL))

def clear_canvas(canvas_frame):
    """Clear all items from the canvas."""
    for widget in canvas_frame.winfo_children():
        widget.destroy()

def update_streamers():
    global tracking_thread, stop_tracking, is_updating

    if is_updating:
        return

    is_updating = True

    layout.track_button.config(state=tk.DISABLED)

    try:
        if tracking_thread and tracking_thread.is_alive():
            stop_tracking.set() 
            tracking_thread.join()

        stop_tracking.clear()

        root.after(0, lambda: layout.timer_label.config(text="Next refresh in: 30s"))

        game_name = layout.game_entry.get()
        streamer_count = int(layout.count_entry.get())

        if streamer_count > 100:
            streamer_count = 100
            layout.count_entry.delete(0, tk.END)
            layout.count_entry.insert(0, str(streamer_count))

        save_settings(game_name, streamer_count, root.winfo_width(), root.winfo_height())

        def start_tracking():
            global tracking_thread
            tracking_thread = threading.Thread(
                target=track_changes, args=(game_name, streamer_count), daemon=True
            )
            tracking_thread.start()

        root.after(0, start_tracking)
    finally:
        root.after(1000, lambda: layout.track_button.config(state=tk.NORMAL))
        root.after(1000, lambda: set_is_updating(False))


def set_is_updating(value):
    global is_updating
    is_updating = value

if default_game:
    tracking_thread = threading.Thread(
        target=track_changes, args=(default_game, default_count), daemon=True
    )
    tracking_thread.start()

layout = Layout(
    root,
    config={
        "default_game": default_game,
        "default_count": default_count,
        "default_width": default_width,
        "default_height": default_height,
        "CLIENT_ID": settings_manager.load_env_variable("YOUR_CLIENT_ID"), 
        "CLIENT_SECRET": settings_manager.load_env_variable("YOUR_CLIENT_SECRET"),
        "ACCESS_TOKEN": settings_manager.load_env_variable("YOUR_ACCESS_TOKEN"), 
        "volume_var": volume_var,
        "notify_var": notify_var,
    },
    callbacks={
        "update_streamers": update_streamers,
        "stop_tracking": lambda: stop_tracking.set(), 
        "generate_access_token": generate_access_token,
        "toggle_notifications": toggle_notifications,
        "select_sound_file": select_sound_file,
        "update_volume": update_volume,
    }
)
root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
