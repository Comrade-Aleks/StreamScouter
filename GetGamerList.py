import requests
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv
import webbrowser

load_dotenv()

SETTINGS_FILE = "settings.txt"
ENV_FILE = ".env"
tracking_thread = None
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
            if len(lines) >= 4:
                return lines[0].strip(), int(lines[1].strip()), lines[2].strip(), lines[3].strip()
    return "", 3, "300", "400"

def save_settings(game_name, streamer_count, width, height):
    with open(SETTINGS_FILE, "w") as f:
        f.write(f"{game_name}\n{streamer_count}\n{width}\n{height}\n")

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
    return [(stream["user_name"], f"https://twitch.tv/{stream['user_name']}") for stream in response.json().get("data", [])]

def open_link(event):
    selected_index = result_list.curselection()
    if selected_index:
        name = result_list.get(selected_index[0])
        webbrowser.open(stream_links[name])

def update_streamers():
    global tracking_thread, stop_tracking
    stop_tracking.set()
    if tracking_thread and tracking_thread.is_alive():
        tracking_thread.join()
    stop_tracking.clear()

    game_name = game_entry.get()
    streamer_count = int(count_entry.get())
    save_settings(game_name, streamer_count, root.winfo_width(), root.winfo_height())

    game_id = get_game_id(game_name)
    if not game_id:
        messagebox.showerror("Error", f"Could not find game '{game_name}' on Twitch.")
        return
    
    def track_changes():
        last_streamers = []
        while not stop_tracking.is_set():
            top_streams = get_top_streams(game_id, streamer_count)
            if top_streams != last_streamers:
                result_list.delete(0, tk.END)
                stream_links.clear()
                for name, link in top_streams:
                    result_list.insert(tk.END, name)
                    stream_links[name] = link
                last_streamers[:] = top_streams
            for i in range(30, 0, -1):
                if stop_tracking.is_set():
                    return
                timer_label.config(text=f"Next refresh in: {i}s")
                time.sleep(1)

    tracking_thread = threading.Thread(target=track_changes, daemon=True)
    tracking_thread.start()

root = tk.Tk()
root.title("Twitch Stream Tracker")
default_game, default_count, default_width, default_height = load_settings()
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

def on_close():
    stop_tracking.set()
    save_settings(game_entry.get(), count_entry.get(), root.winfo_width(), root.winfo_height())
    root.destroy()
root.protocol("WM_DELETE_WINDOW", on_close)

if default_game:
    update_streamers()

root.mainloop()
