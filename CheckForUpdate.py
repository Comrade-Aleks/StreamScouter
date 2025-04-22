import requests
import tkinter as tk
from tkinter import messagebox
import os
import threading
import shutil
import zipfile
import sys
import subprocess

Version = "v2.7.0"
REPO_OWNER = "Comrade-Aleks"
REPO_NAME = "StreamScouter"
MUTE_FILE = "mute_update_notifications.txt"
UPDATE_ZIP_NAME = "StreamScouter.zip"
UPDATE_FOLDER_NAME = "StreamScouter"

def get_all_releases():
    """Fetch all releases from the GitHub repository."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
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
    """Compare version numbers and determine if an update is available."""
    current_parts = list(map(int, current.lstrip("v").split(".")))
    latest_parts = list(map(int, latest.lstrip("v").split(".")))

    for current_part, latest_part in zip(current_parts, latest_parts):
        if latest_part > current_part:
            return True
        elif latest_part < current_part:
            return False

    return len(latest_parts) > len(current_parts)

def schedule_update(temp_dir):
    """Schedule the update to replace files after the application exits."""
    current_folder = os.path.dirname(os.path.abspath(sys.argv[0]))
    updater_script = os.path.join(temp_dir, "update_script.bat")
    exe_name = os.path.basename(sys.argv[0])

    # This creates a batch script that will run after the application closes
    # It will update the program and whatnot
    with open(updater_script, "w") as f:
        f.write(f"""
        @echo off
        echo Updating StreamScouter...
        timeout /t 2 >nul
        taskkill /f /im "{exe_name}" >nul 2>&1
        xcopy "{temp_dir}\\StreamScouter\\*" "{current_folder}" /E /H /C /Y >nul
        rmdir /S /Q "{temp_dir}\\StreamScouter" >nul 2>&1
        rmdir /S /Q "{temp_dir}" >nul 2>&1
        del /Q "{updater_script}" >nul
        start "" "{os.path.join(current_folder, exe_name)}"
        exit
        """)
    subprocess.Popen(updater_script, shell=True)
    sys.exit()

def download_and_extract_update(download_url):
    """Download and prepare the update zip file."""
    try:
        # Downloads the zip file
        response = requests.get(download_url, stream=True)
        with open(UPDATE_ZIP_NAME, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        temp_dir = "temp_update"
        os.makedirs(temp_dir, exist_ok=True)
        with zipfile.ZipFile(UPDATE_ZIP_NAME, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        schedule_update(temp_dir)

    except Exception as e:
        messagebox.showerror("Update Failed", f"An error occurred during the update: {e}")
    finally:
        if os.path.exists(UPDATE_ZIP_NAME):
            os.remove(UPDATE_ZIP_NAME)

def show_update_popup():
    """Show the update notification popup if an update is available."""
    releases = get_all_releases()
    if not releases:
        return

    clean_mute_file(Version)

    muted_versions = []
    if os.path.exists(MUTE_FILE):
        with open(MUTE_FILE, "r") as f:
            muted_versions = f.read().splitlines()

    latest_release = releases[0]
    latest_version = latest_release["tag_name"].strip()

    if compare_versions(Version, latest_version) and latest_version not in muted_versions:
        download_url = None
        for asset in latest_release["assets"]:
            if asset["name"] == "StreamScouter.zip":
                download_url = asset["browser_download_url"]
                break

        if not download_url:
            messagebox.showerror("Update Error", "No update file found in the latest release.")
            return

        root = tk.Tk()
        root.withdraw()

        def update_now():
            popup.destroy()
            download_and_extract_update(download_url)

        def mute_until_next_update():
            muted_versions.append(latest_version)
            mute_notifications(muted_versions)
            popup.destroy()

        def open_github_page():
            import webbrowser
            webbrowser.open(f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases")

        popup = tk.Toplevel(root)
        popup.title("Update Available")
        tk.Label(popup, text=f"A new version ({latest_version}) is available!", font=("Arial", 14)).pack(pady=10)
        tk.Label(popup, text=f"Changelog:\n{latest_release.get('body', 'No changelog available.')}", justify="left", wraplength=400).pack(pady=10, padx=10)

        update_button = tk.Button(popup, text="Update Now", command=update_now)
        update_button.pack(side="left", padx=10, pady=10)

        mute_button = tk.Button(popup, text="Mute Until Next Update", command=mute_until_next_update)
        mute_button.pack(side="left", padx=10, pady=10)

        manual_update_button = tk.Button(popup, text="Manual Update", command=open_github_page)
        manual_update_button.pack(side="right", padx=10, pady=10)

        popup.mainloop()

def check_for_update_after_startup():
    """Run the update checker after the main application starts."""
    threading.Thread(target=show_update_popup, daemon=True).start()

if __name__ == "__main__":
    check_for_update_after_startup()