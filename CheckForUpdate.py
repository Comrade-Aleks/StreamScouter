import requests
import tkinter as tk
from tkinter import messagebox
import os
import threading

Version = "v2.6.0"
REPO_OWNER = "Comrade-Aleks"
REPO_NAME = "StreamScouter"
MUTE_FILE = "mute_update_notifications.txt"

def get_all_releases():
    """Fetch all releases from the GitHub repository."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return []

def is_muted(version):
    """Check if a specific version is muted."""
    if not os.path.exists(MUTE_FILE):
        return False
    with open(MUTE_FILE, "r") as f:
        muted_versions = f.read().splitlines()
    return version in muted_versions

def mute_notifications(versions):
    """Mute specific update notifications."""
    with open(MUTE_FILE, "w") as f:
        f.write("\n".join(versions))

def unmute_notifications():
    """Unmute all update notifications."""
    if os.path.exists(MUTE_FILE):
        os.remove(MUTE_FILE)

def clean_mute_file(current_version):
    """Remove versions from the mute file that are older than or equal to the current version."""
    if not os.path.exists(MUTE_FILE):
        return
    current_parts = list(map(int, current_version.lstrip("v").split(".")))
    with open(MUTE_FILE, "r") as f:
        muted_versions = f.read().splitlines()
    valid_versions = []
    for version in muted_versions:
        version_parts = list(map(int, version.lstrip("v").split(".")))
        if version_parts > current_parts:
            valid_versions.append(version)
    if valid_versions:
        mute_notifications(valid_versions)
    else:
        unmute_notifications() 

def compare_versions(current, latest):
    """Compare version numbers and determine if it's a major or minor update."""
    current_parts = list(map(int, current.lstrip("v").split(".")))
    latest_parts = list(map(int, latest.lstrip("v").split(".")))

    if latest_parts[0] > current_parts[0]:
        return "major"
    elif latest_parts[1] > current_parts[1]:
        return "minor"
    elif latest_parts[2] > current_parts[2]:
        return "minor"
    return "none"

def show_update_popup():
    """Show the update notification popup."""
    releases = get_all_releases()
    if not releases:
        return 

    clean_mute_file(Version)

    root = tk.Tk()
    root.withdraw()

    muted_versions = []
    if os.path.exists(MUTE_FILE):
        with open(MUTE_FILE, "r") as f:
            muted_versions = f.read().splitlines()

    updates_to_notify = []
    current_parts = list(map(int, Version.lstrip("v").split(".")))
    for release in releases:
        version = release["tag_name"]
        version_parts = list(map(int, version.lstrip("v").split(".")))
        if version_parts > current_parts and version not in muted_versions:
            updates_to_notify.append((version, release.get("body", "No changelog available.")))

    updates_to_notify.sort(key=lambda x: list(map(int, x[0].lstrip("v").split("."))), reverse=True)

    if updates_to_notify:
        update_message = ""
        for version, changelog in updates_to_notify:
            update_type = compare_versions(Version, version)
            update_message += f"{update_type.capitalize()} Update ({version}):\n{changelog}\n\n"

        def mute_all():
            for version, _ in updates_to_notify:
                muted_versions.append(version)
            mute_notifications(muted_versions)
            popup.destroy()

        popup = tk.Toplevel(root)
        popup.title("Update Notifications")
        tk.Label(popup, text=update_message, justify="left", wraplength=400).pack(pady=10, padx=10)

        mute_button = tk.Button(popup, text="Mute All", command=mute_all)
        mute_button.pack(side="left", padx=10, pady=10)

        close_button = tk.Button(popup, text="Close Without Muting", command=popup.destroy)
        close_button.pack(side="right", padx=10, pady=10)

        popup.mainloop()

    if not updates_to_notify and os.path.exists(MUTE_FILE):
        unmute_notifications()

    root.destroy()

def check_for_update_after_startup():
    """Run the update checker after the main application starts."""
    threading.Thread(target=show_update_popup, daemon=True).start()

if __name__ == "__main__":
    check_for_update_after_startup()