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
import os
import winreg
import sys
from screeninfo import get_monitors

os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

root = tk.Tk()

CheckForUpdate.check_for_update_after_startup()

load_dotenv()

SETTINGS_FILE = "settings.txt"
ENV_FILE = ".env"

settings_manager = SettingsManager(SETTINGS_FILE, ENV_FILE)

def validate_window_position(x, y, width, height):
    monitors = get_monitors()

    for monitor in monitors:
        if (
            monitor.x <= x < monitor.x + monitor.width and
            monitor.y <= y < monitor.y + monitor.height
        ):
            if x + int(width) > monitor.x + monitor.width:
                x = monitor.x + monitor.width - int(width)
            if y + int(height) > monitor.y + monitor.height:
                y = monitor.y + monitor.height - int(height)
            return x, y
    primary_monitor = monitors[0]
    return primary_monitor.x + 100, primary_monitor.y + 100

default_game, default_count, default_width, default_height, default_notify, default_sound, default_volume, default_launch_at_startup, default_x, default_y = settings_manager.load_settings()

# This is for setting and validating window position
default_x, default_y = validate_window_position(default_x, default_y, default_width, default_height)
root.geometry(f"{default_width}x{default_height}+{default_x}+{default_y}")

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
cached_game_id = None

def save_settings(game_name, streamer_count, width, height):
    x = root.winfo_x()
    y = root.winfo_y()
    settings_manager.save_settings(
        game_name, streamer_count, width, height, notify_var, sound_file, volume_var, layout.launch_at_startup_var.get(), x, y
    )

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

tray_icon_manager = TrayIconManager(
    root=root,
    on_quit=lambda: tray_icon_manager.quit_app(save_settings, layout)
)

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
    global seen_streamers, minimized_at, first_run
    stop_tracking.clear()

    while not stop_tracking.is_set():
        global cached_game_id
        if not cached_game_id:
            cached_game_id = twitch_api.get_game_id(game_name)
            if not cached_game_id:
                show_error(f"Game '{game_name}' not found on Twitch.")
                return
        
        top_streams = tracker.get_top_streams(cached_game_id, streamer_count)
        layout.total_streamers_count = len(top_streams)
        streamer_data = tracker.process_streamers(top_streams)

        process_streamers_and_update_ui(streamer_data)
        first_run = False
        countdown_timer()

def show_error(message):
    root.after(0, lambda: messagebox.showerror("Error", message))

def process_streamers_and_update_ui(streamer_data):
    global seen_streamers, minimized_at, first_run

    current_ids = {stream["id"] for stream in streamer_data}
    new_streamer_ids = current_ids - {s["id"] for s in seen_streamers}

    if root.state() != 'withdrawn':
        for stream in streamer_data:
            root.after(0, lambda s=stream: layout.add_item_to_main_canvas(
                s["name"], s["link"], s["profile_picture"], linger_duration=None, remaining_linger=None
            ))
            stream_links[stream["id"]] = stream["link"]
        
        for lingering in tracker.linger_streamers:
            root.after(0, lambda s=lingering: layout.add_item_to_main_canvas(
                s["name"], s["link"], s["profile_picture"], StreamerTracker.linger_duration, remaining_linger=s["countdown"]
            ))

        shown_count = len(streamer_data) + len(tracker.linger_streamers)
        total_count = layout.total_streamers_count
        root.after(0, lambda: layout.streamer_count_label.config(
            text=f"{shown_count}/{total_count} streamers shown"
        ))
    
    if new_streamer_ids and not first_run:
        if minimized_at == 0 or time.time() - minimized_at >= 10:
            if notify_var.get():
                notification_manager.play_notification()
            if root.state() == 'withdrawn':
                tray_icon_manager.start_blinking_icon()

    seen_streamers = streamer_data + tracker.linger_streamers

def countdown_timer():
    for i in range(10, 0, -1):
        if stop_tracking.is_set():
            return

        if i <= 1:
            root.after(0, lambda: layout.track_button.config(state=tk.DISABLED))
        if i > 1:
            root.after(0, lambda: layout.track_button.config(state=tk.NORMAL))

        root.after(0, lambda t=i: layout.timer_label.config(text=f"Next refresh in: {t}s"))
        time.sleep(1)

    root.after(0, lambda: layout.timer_label.config(text="Refreshing streams..."))

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
        global cached_game_id
        cached_game_id = None

        root.after(0, lambda: layout.timer_label.config(text="Next refresh in: 10s"))

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

def toggle_launch_at_startup():
    """Enable or disable launching the app at startup."""
    app_name = "StreamScouter"
    app_path = os.path.abspath(sys.argv[0])
    startup_key = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_key, 0, winreg.KEY_ALL_ACCESS) as key:
            if layout.launch_at_startup_var.get():
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            else:
                winreg.DeleteValue(key, app_name)
    except FileNotFoundError:
        if layout.launch_at_startup_var.get():
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, startup_key) as key:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)

def start_tracking_on_launch():
    global tracking_thread
    if tracking_thread and tracking_thread.is_alive():
        return
    if not default_game:
        root.after(1000, lambda: layout.track_button.config(state=tk.NORMAL))
        return
    try:
        tracking_thread = threading.Thread(
            target=track_changes, args=(default_game, default_count), daemon=True
        )
        tracking_thread.start()
    except Exception as e:
        pass

def on_close():
    """Save settings and close the application."""
    save_settings(
        layout.game_entry.get(),
        layout.count_entry.get(),
        root.winfo_width(),
        root.winfo_height()
    )
    tray_icon_manager.quit_app(save_settings, layout)

root.protocol("WM_DELETE_WINDOW", on_close)

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
        "launch_at_startup": default_launch_at_startup,
    },
    callbacks={
        "update_streamers": update_streamers,
        "stop_tracking": lambda: stop_tracking.set(), 
        "generate_access_token": generate_access_token,
        "toggle_notifications": toggle_notifications,
        "select_sound_file": select_sound_file,
        "update_volume": update_volume,
        "toggle_launch_at_startup": toggle_launch_at_startup,
    },
    twitch_api=twitch_api
)

root.after(0, start_tracking_on_launch)

root.bind("<Unmap>", lambda event: tray_icon_manager.on_minimize() if root.state() == "iconic" else None)
root.mainloop()
