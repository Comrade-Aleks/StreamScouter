import requests
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv
import webbrowser
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import pygame
from tkinter import filedialog
import CheckForUpdate

CheckForUpdate.check_for_update()
load_dotenv()

first_run = True 
tray_icon = None
blinking = False

SETTINGS_FILE = "settings.txt"
ENV_FILE = ".env"

stop_tracking = threading.Event()

CLIENT_ID = os.getenv("YOUR_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("YOUR_CLIENT_SECRET", "")
ACCESS_TOKEN = os.getenv("YOUR_ACCESS_TOKEN", "")

def save_env():
    with open(ENV_FILE, "w") as f:
        f.write(f"YOUR_CLIENT_ID={CLIENT_ID}\n")
        f.write(f"YOUR_CLIENT_SECRET={CLIENT_SECRET}\n")
        f.write(f"YOUR_ACCESS_TOKEN={ACCESS_TOKEN}\n")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            lines = f.readlines()
            if len(lines) >= 7:
                return (
                    lines[0].strip(),       
                    int(lines[1].strip()),
                    lines[2].strip(),
                    lines[3].strip(),
                    lines[4].strip().lower() == "true",
                    lines[5].strip(),
                    float(lines[6].strip())
                )
    return "", 3, "300", "400", False, "default.wav", 0.5

def save_settings(game_name, streamer_count, width, height):
    with open(SETTINGS_FILE, "w") as f:
        f.write(f"{game_name}\n{streamer_count}\n{width}\n{height}\n")
        f.write(f"{notify_var.get()}\n{sound_file.get()}\n{volume_var.get()}\n")

def generate_access_token():
    global ACCESS_TOKEN
    if not CLIENT_ID or not CLIENT_SECRET:
        messagebox.showerror("Error", "Client ID and Client Secret must be set first!")
        return
    
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(url, params=params)
    data = response.json()
    
    if "access_token" in data:
        ACCESS_TOKEN = data["access_token"]
        os.environ["YOUR_ACCESS_TOKEN"] = ACCESS_TOKEN
        save_env()
        access_token_entry.delete(0, tk.END)
        access_token_entry.insert(0, ACCESS_TOKEN)
    else:
        messagebox.showerror("Error", "Failed to generate access token")

def save_client_info():
    global CLIENT_ID, CLIENT_SECRET
    CLIENT_ID = client_id_entry.get()
    CLIENT_SECRET = client_secret_entry.get()
    save_env()
    messagebox.showinfo("Success", "Client ID and Secret saved!")

def get_game_id(game_name):
    url = "https://api.twitch.tv/helix/games"
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers, params={"name": game_name})
    data = response.json()
    return data["data"][0]["id"] if data.get("data") else None

def get_top_streams(game_id, limit):
    url = "https://api.twitch.tv/helix/streams"
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers, params={"game_id": game_id, "first": limit})

    data = response.json()
    streamers = [(stream["user_name"], f"https://twitch.tv/{stream['user_name']}") for stream in data.get("data", [])]
    
    return streamers, len(streamers)



def open_link(event):
    selected_index = result_list.curselection()
    if selected_index:
        name = result_list.get(selected_index[0])
        webbrowser.open(stream_links[name])

tracking_thread = None
def update_streamers():
    global tracking_thread, stop_tracking
    stop_tracking.set()
    if tracking_thread and tracking_thread.is_alive():
        tracking_thread.join()

    stop_tracking.clear()

    game_name = game_entry.get()
    streamer_count = int(count_entry.get())
    
    if streamer_count > 100:
        streamer_count = 100
        count_entry.delete(0, tk.END)
        count_entry.insert(0, str(streamer_count))

    save_settings(game_name, streamer_count, root.winfo_width(), root.winfo_height())

    game_id = get_game_id(game_name)
    if not game_id:
        messagebox.showerror("Error", f"Could not find game '{game_name}' on Twitch.")
        return

    tracking_thread = threading.Thread(target=track_changes, args=(game_id, streamer_count), daemon=True)
    tracking_thread.start()

pygame.mixer.init()

def play_notification():
    file_to_play = sound_file.get()

    if not os.path.exists(file_to_play):
        print(f"Selected file '{file_to_play}' not found, using 'default.wav'")
        file_to_play = "default.wav"

    if not os.path.exists(file_to_play):
        print("Error: Notification sound file not found! No sound will play.")
        return  

    print(f"Playing notification sound: {file_to_play} at volume: {volume_var.get()}")

    def play_sound():
        try:
            pygame.mixer.init()
            sound = pygame.mixer.Sound(file_to_play)
            sound.set_volume(volume_var.get())  
            sound.play()
        except pygame.error as e:
            print(f"Error loading sound file: {e}")

    threading.Thread(target=play_sound, daemon=True).start()

seen_streamers = set()

linger_streamers = {}

def track_changes(game_id, streamer_count):
    global seen_streamers, minimized_at, first_run, linger_streamers
    stop_tracking.clear()

    while not stop_tracking.is_set():
        top_streams, _ = get_top_streams(game_id, streamer_count)
        current_streamers = set(name for name, _ in top_streams)
        new_streamers = current_streamers - seen_streamers
        dropped_streamers = seen_streamers - current_streamers

        for streamer in dropped_streamers:
            if streamer in linger_streamers:
                if linger_streamers[streamer] <= 1:
                    del linger_streamers[streamer]
                else:
                    linger_streamers[streamer] -= 1  
            else:
                linger_streamers[streamer] = 2

        for streamer in list(linger_streamers.keys()):
            if streamer in current_streamers:
                del linger_streamers[streamer]

        if notify_var.get() and new_streamers:
            if not first_run:
                if minimized_at == 0 or time.time() - minimized_at >= 30:
                    play_notification()
                    if root.state() == 'withdrawn':
                        start_blinking_icon()

        seen_streamers = current_streamers | set(linger_streamers.keys()) 

        root.after(0, result_list.delete, 0, tk.END)
        for name, link in top_streams:
            root.after(0, lambda n=name: result_list.insert(tk.END, n))
            stream_links[name] = link  

        first_run = False

        for i in range(30, 0, -1):
            if stop_tracking.is_set():
                return
            root.after(0, lambda t=i: timer_label.config(text=f"Next refresh in: {t}s"))
            time.sleep(1)

    root.after(0, lambda: timer_label.config(text="Tracking Stopped"))

tray_icon = None

root = tk.Tk()
root.title("StreamScouter")
default_game, default_count, default_width, default_height, default_notify, default_sound, default_volume = load_settings()

notify_var = tk.BooleanVar(value=default_notify)
sound_file = tk.StringVar(value=default_sound)
root.geometry(f"{default_width}x{default_height}")
root.minsize(200, 300)

tab_control = ttk.Notebook(root)
main_tab = ttk.Frame(tab_control)
settings_tab = ttk.Frame(tab_control)
tab_control.add(main_tab, text="Tracker")
tab_control.add(settings_tab, text="Settings")
tab_control.pack(expand=1, fill="both")

tk.Label(main_tab, text="Enter Game Name:").pack()
game_entry = tk.Entry(main_tab)
game_entry.insert(0, default_game)
game_entry.pack(fill=tk.X, padx=10)

tk.Label(main_tab, text="Number of Streamers to Track:").pack()
count_entry = tk.Entry(main_tab)
count_entry.insert(0, str(default_count))
count_entry.pack(fill=tk.X, padx=10)

tk.Button(main_tab, text="Track Streamers", command=update_streamers).pack()

timer_label = tk.Label(main_tab, text="Next refresh in: 30s", anchor="e")
timer_label.pack(fill=tk.X, padx=10, pady=5)

frame = tk.Frame(main_tab)
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
result_list = tk.Listbox(frame, width=50, height=20, yscrollcommand=scrollbar.set)
scrollbar.config(command=result_list.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
result_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
result_list.bind("<Double-Button-1>", open_link)
stream_links = {}

tk.Label(settings_tab, text="Client ID:").pack()
client_id_entry = tk.Entry(settings_tab)
client_id_entry.insert(0, CLIENT_ID)
client_id_entry.pack(fill=tk.X, padx=10)

tk.Label(settings_tab, text="Client Secret:").pack()
client_secret_entry = tk.Entry(settings_tab)
client_secret_entry.insert(0, CLIENT_SECRET)
client_secret_entry.pack(fill=tk.X, padx=10)

tk.Label(settings_tab, text="Access Token:").pack()
access_token_entry = tk.Entry(settings_tab)
access_token_entry.insert(0, ACCESS_TOKEN)
access_token_entry.pack(fill=tk.X, padx=10)

tk.Button(settings_tab, text="Save Client Info", command=save_client_info).pack(pady=5)
tk.Button(settings_tab, text="Generate Access Token", command=generate_access_token).pack(pady=5)

volume_var = tk.DoubleVar(value=default_volume)

def update_volume(value):
    save_settings(game_entry.get(), int(count_entry.get()), root.winfo_width(), root.winfo_height())

tk.Label(settings_tab, text="Notification Volume:").pack()
volume_slider = tk.Scale(settings_tab, from_=0, to=1, resolution=0.01, orient="horizontal", variable=volume_var, command=update_volume)
volume_slider.pack()


def toggle_notifications():
    save_settings(game_entry.get(), int(count_entry.get()), root.winfo_width(), root.winfo_height())
    with open(SETTINGS_FILE, "a") as f:
        f.write(f"{notify_var.get()}\n")

notify_checkbox = ttk.Checkbutton(
    settings_tab, text="Enable New Streamer Notification",
    variable=notify_var, command=toggle_notifications
)
notify_checkbox.pack(pady=5)

sound_file = tk.StringVar(value="default.wav")

def select_sound_file():
    file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav;*.mp3")])
    if file_path:
        sound_file.set(file_path)
        save_settings(game_entry.get(), int(count_entry.get()), root.winfo_width(), root.winfo_height())
        messagebox.showinfo("Success", f"Notification sound set to: {file_path}")

sound_button = tk.Button(settings_tab, text="Select Notification Sound", command=select_sound_file)
sound_button.pack(pady=5)

def create_icon(color=(0, 120, 215)):
    """Create a tray icon with a given color."""
    icon_size = (64, 64)
    image = Image.new("RGB", icon_size, (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 10, 54, 54), fill=color)
    return image

def show_window():
    """Restore the window and stop tray blinking."""
    global blinking, tray_icon
    blinking = False

    update_tray_icon((0, 120, 215)) 
    root.deiconify() 

    if tray_icon:  
        tray_icon.stop() 
        tray_icon = None

def quit_app():
    """Quit the app completely."""
    stop_tracking.set()
    save_settings(game_entry.get(), count_entry.get(), root.winfo_width(), root.winfo_height())
    tray_icon.stop()
    root.destroy()

minimized_at = 0

def on_close():
    """Minimize the app to the system tray instead of closing it."""
    global tray_icon, minimized_at
    root.withdraw()
    minimized_at = time.time()

    if tray_icon is None:
        tray_icon = pystray.Icon("twitch_tracker", create_icon((0, 120, 215)), "Twitch Tracker", menu=(
            item("Show", show_window),
            item("Exit", quit_app)
        ))

        def run_tray():
            tray_icon.run()

        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()
        update_tray_icon(0, 120, 215)

blinking = False
blink_thread = None

blinking = False
blink_thread = None

def update_tray_icon(color):
    """Update the tray icon color."""
    global tray_icon
    icon_size = (64, 64)
    image = Image.new("RGB", icon_size, color)
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 10, 54, 54), fill=color)
    tray_icon.icon = image

def start_blinking_icon():
    """Start blinking the tray icon when a new streamer appears."""
    global blinking, blink_thread
    if blinking:
        return

    blinking = True

    def blink():
        colors = [(255, 0, 0), (255, 255, 255)]
        while blinking:
            for color in colors:
                root.after(0, lambda: update_tray_icon(color))
                time.sleep(0.5)

    blink_thread = threading.Thread(target=blink, daemon=True)
    blink_thread.start()

def stop_blinking_icon():
    """Stop blinking and set the icon to solid red."""
    global blinking
    blinking = False
    root.after(0, lambda: update_tray_icon((255, 0, 0)))


if default_game:
    update_streamers()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
