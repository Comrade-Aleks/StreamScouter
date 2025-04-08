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
import logging



os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

root = tk.Tk()

CheckForUpdate.check_for_update_after_startup()

logging.basicConfig(
    filename="StreamScouter.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

SETTINGS_FILE = "settings.txt"
ENV_FILE = ".env"

settings_manager = SettingsManager(SETTINGS_FILE, ENV_FILE)
default_game, default_count, default_width, default_height, default_notify, default_sound, default_volume, default_launch_at_startup = settings_manager.load_settings()

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
    settings_manager.save_settings(game_name, streamer_count, width, height, notify_var, sound_file, volume_var, layout.launch_at_startup_var.get())

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
        tray_icon_manager.stop_tray_icon()
    root.destroy()
    sys.exit()

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
    global seen_streamers, minimized_at, first_run
    stop_tracking.clear()

    while not stop_tracking.is_set():
        game_id = twitch_api.get_game_id(game_name)
        if not game_id:
            show_error(f"Game '{game_name}' not found on Twitch.")
            return
        
        top_streams = tracker.get_top_streams(game_id, streamer_count)
        layout.total_streamers_count = len(top_streams)
        streamer_data = tracker.process_streamers(top_streams)

        handle_new_streamers(streamer_data)
        update_ui(streamer_data)
        first_run = False
        countdown_timer()

def show_error(message):
    root.after(0, lambda: messagebox.showerror("Error", message))

def handle_new_streamers(streamer_data):
    global seen_streamers, minimized_at, first_run
    current_ids = {stream["id"] for stream in streamer_data}
    new_streamer_ids = current_ids - seen_streamers

    if new_streamer_ids and not first_run:
        if minimized_at == 0 or time.time() - minimized_at >= 30:
            if notify_var.get():
                notification_manager.play_notification()
            if root.state() == 'withdrawn':
                tray_icon_manager.start_blinking_icon()
    
    seen_streamers = current_ids | set(tracker.linger_streamers.keys())

def update_ui(streamer_data):
    if root.state() != 'withdrawn':
        root.after(0, lambda: clear_canvas(layout.canvas_frame))
        for stream in streamer_data:
            root.after(0, lambda s=stream: layout.add_item_to_canvas(s["name"], s["link"], s["profile_picture"]))
            stream_links[stream["id"]] = stream["link"]

        shown_count = len(streamer_data)
        total_count = layout.total_streamers_count
        root.after(0, lambda: layout.streamer_count_label.config(
            text=f"{shown_count}/{total_count} streamers shown"
        ))

def countdown_timer():
    for i in range(30, 0, -1):
        if stop_tracking.is_set():
            return

        root.after(0, lambda t=i: layout.timer_label.config(text=f"Next refresh in: {t}s"))
        time.sleep(1)

    root.after(0, lambda: layout.timer_label.config(text="Refreshing streams..."))


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
    logging.debug("start_tracking_on_launch called")
    if tracking_thread and tracking_thread.is_alive():
        logging.debug("Tracking thread already running.")
        return
    if not default_game:
        logging.error("Default game is not set. Cannot start tracking.")
        return
    try:
        logging.debug(f"Starting tracking thread for game: {default_game}, count: {default_count}")
        tracking_thread = threading.Thread(
            target=track_changes, args=(default_game, default_count), daemon=True
        )
        tracking_thread.start()
    except Exception as e:
        logging.error(f"Error starting tracking thread: {e}")

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
    }
)

root.after(0, start_tracking_on_launch)

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
