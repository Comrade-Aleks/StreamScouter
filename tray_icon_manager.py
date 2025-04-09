import threading
from pystray import Icon, MenuItem as item
from PIL import Image
import time
import os
import sys

class TrayIconManager:
    def __init__(self, root, on_show, on_quit):
        self.root = root
        self.on_show = on_show
        self.on_quit = on_quit
        self.tray_icon = None
        self.blinking = False
        self.blink_thread = None

        if hasattr(sys, "_MEIPASS"):
            self.icon_path = os.path.join(sys._MEIPASS, "TwitchScout.ico")
        else:
            self.icon_path = os.path.join(os.getcwd(), "dist", "TwitchScout.ico")

        self.default_icon = self.create_icon(self.icon_path)
        self.blink_icon = self.create_blink_icon()

    def create_icon(self, path):
        """Load the tray icon from the .ico file."""
        try:
            return Image.open(path)
        except Exception as e:
            print(f"Error loading icon: {e}")
            return None

    def create_blink_icon(self):
        """Create a red-tinted version of the tray icon for blinking."""
        try:
            icon = self.default_icon.convert("RGBA")
            red_tint = Image.new("RGBA", icon.size, (255, 0, 0, 0))
            blended_icon = Image.blend(icon, red_tint, alpha=0.5)
            return blended_icon
        except Exception as e:
            print(f"Error creating blink icon: {e}")
            return self.default_icon

    def minimize_to_tray(self):
        """Minimize the app to the system tray."""
        if not self.tray_icon:
            if self.default_icon:
                self.tray_icon = Icon(
                    "StreamScouter",
                    self.default_icon,
                    menu=(item("Show", self.on_show), item("Quit", self.on_quit)),
                )
                threading.Thread(target=self.tray_icon.run, daemon=True).start()
            else:
                print("Failed to load tray icon. Tray functionality will not work.")

    def start_blinking_icon(self):
        """Start blinking the tray icon."""
        if self.blinking or not self.tray_icon:
            return

        self.blinking = True

        def blink():
            for _ in range(10):
                if not self.blinking:
                    break
                self.tray_icon.icon = self.blink_icon
                time.sleep(0.5)
                self.tray_icon.icon = self.default_icon
                time.sleep(0.5)

            self.tray_icon.icon = self.blink_icon

        self.blink_thread = threading.Thread(target=blink, daemon=True)
        self.blink_thread.start()

    def stop_blinking_icon(self):
        """Stop blinking the tray icon and keep it red."""
        self.blinking = False
        if self.tray_icon:
            self.tray_icon.icon = self.blink_icon

    def stop_tray_icon(self):
        """Stop and remove the tray icon."""
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None