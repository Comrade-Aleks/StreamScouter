import requests
import tkinter as tk
from tkinter import messagebox

Version = "v1.0.0"
REPO_OWNER = "Comrade-Aleks"
REPO_NAME = "StreamScouter"

def get_latest_version():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        latest_release = response.json()
        return latest_release["tag_name"]
    else:
        return None

def check_for_update():
    latest_version = get_latest_version()
    if latest_version and latest_version != Version:
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        messagebox.showinfo("Update Available", f"A new version ({latest_version}) is available!")
        root.destroy()

if __name__ == "__main__":
    check_for_update()