import tkinter as tk
from tkinter import ttk
import sys
import os
import webbrowser
from PIL import Image, ImageTk
import requests
from io import BytesIO
import threading
import CheckForUpdate
from threading import Timer

class Layout:
    def __init__(self, root, config, callbacks, twitch_api):
        self.root = root
        self.config = config
        self.callbacks = callbacks
        self.twitch_api = twitch_api
        self.total_streamers_count = 0
        self.dropdown_window = None
        self.search_timer = None
        self.initialize_layout()

    def initialize_layout(self):
        """Initialize the layout for the StreamScouter application."""
        self.root.title(f"StreamScouter - Version {CheckForUpdate.Version}")
        self.root.geometry(f"{self.config['default_width']}x{self.config['default_height']}")
        self.root.minsize(274, 361)

        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "TwitchScout.ico")
        try:
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error setting icon: {e}")

        # Tab control
        self.tab_control = ttk.Notebook(self.root)
        self.main_tab = ttk.Frame(self.tab_control)
        self.settings_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.main_tab, text="Tracker")
        self.tab_control.add(self.settings_tab, text="Settings")
        self.tab_control.pack(expand=1, fill="both")

        # Main tab layout
        tk.Label(self.main_tab, text="Enter Game Name:").pack()
        self.game_entry = tk.Entry(self.main_tab)
        self.game_entry.insert(0, self.config['default_game'] or "") 
        self.game_entry.pack(fill=tk.X, padx=10)
        self.game_entry.bind("<KeyRelease>", self.search_categories)

        self.dropdown_frame = tk.Frame(self.main_tab)
        self.dropdown_frame.pack(fill=tk.X, padx=10)

        tk.Label(self.main_tab, text="Number of Streamers to Track:").pack()
        self.count_entry = tk.Entry(self.main_tab)
        self.count_entry.insert(0, str(self.config['default_count'] or ""))
        self.count_entry.pack(fill=tk.X, padx=10)

        self.track_button = tk.Button(
            self.main_tab, 
            text="Track Streamers", 
            command=self.callbacks['update_streamers'], 
            state=tk.DISABLED
        )
        self.track_button.pack()

        tk.Button(self.main_tab, text="Stop Tracking", command=self.callbacks['stop_tracking']).pack()

        info_frame = tk.Frame(self.main_tab, bg="#2e2e2e")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        # streamer count label for debugging mostly
        self.streamer_count_label = tk.Label(
            info_frame, text="0/0 streamers shown", anchor="w", bg="#2e2e2e", fg="#ffffff"
        )
        self.streamer_count_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        #refresh timer label
        self.timer_label = tk.Label(
            info_frame, text="Next refresh in: 10s", anchor="e", bg="#2e2e2e", fg="#ffffff"
        )
        self.timer_label.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        frame = tk.Frame(self.main_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Frame to hold canvas
        canvas_container = tk.Frame(frame, bg="#815ac0", highlightthickness=1, highlightbackground="#815ac0")
        canvas_container.grid(row=0, column=0, sticky="nsew")

        # Create the Canvas inside the bordered container
        self.result_canvas = tk.Canvas(
            canvas_container,
            bg="#2e2e2e",
            highlightthickness=0
        )
        self.result_canvas.pack(fill=tk.BOTH, expand=True)

        # Frame inside the Canvas
        self.canvas_frame = tk.Frame(self.result_canvas, bg="#2e2e2e", padx=5, pady=5)
        self.canvas_window = self.result_canvas.create_window((0, 0), window=self.canvas_frame, anchor="nw")

        # add scrolling functionality
        self.canvas_frame.bind(
            "<Configure>",
            lambda e: self.result_canvas.configure(scrollregion=self.result_canvas.bbox("all"))
        )
        
        # Add the Frame to the Canvas
        self.canvas_window = self.result_canvas.create_window((0, 0), window=self.canvas_frame, anchor="nw")

        # Create a vertical scrollbar
        style = ttk.Style()
        style.theme_use("default")
        style.configure("#815ac0.Vertical.TScrollbar",
                        gripcount=0,
                        background="#815ac0",
                        troughcolor="#2e2e2e",
                        bordercolor="#4caf50",
                        arrowcolor="#ffffff")
        style.map("#815ac0.Vertical.TScrollbar",
                  background=[("disabled", "#815ac0")])

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.result_canvas.yview, style="#815ac0.Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Configure the Canvas to use the scrollbar
        self.result_canvas.configure(yscrollcommand=scrollbar.set)

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # tab layout
        tk.Label(self.settings_tab, text="Client ID:").pack()
        self.client_id_entry = tk.Entry(self.settings_tab)
        self.client_id_entry.insert(0, self.config['CLIENT_ID'] or "")
        self.client_id_entry.pack(fill=tk.X, padx=10)

        tk.Label(self.settings_tab, text="Client Secret:").pack()
        self.client_secret_entry = tk.Entry(self.settings_tab)
        self.client_secret_entry.insert(0, self.config['CLIENT_SECRET'] or "")
        self.client_secret_entry.pack(fill=tk.X, padx=10)

        tk.Label(self.settings_tab, text="Access Token:").pack()
        self.access_token_entry = tk.Entry(self.settings_tab)
        self.access_token_entry.insert(0, self.config['ACCESS_TOKEN'] or "")
        self.access_token_entry.pack(fill=tk.X, padx=10)

        tk.Button(self.settings_tab, text="Generate Access Token", command=self.callbacks['generate_access_token']).pack(pady=5)

        tk.Label(self.settings_tab, text="Notification Volume:").pack()
        self.volume_slider = tk.Scale(
            self.settings_tab, from_=0, to=1, resolution=0.01, orient="horizontal",
            variable=self.config['volume_var'], command=self.callbacks['update_volume']
        )
        self.volume_slider.pack()

        # Add "Launch at Startup" checkbox
        self.launch_at_startup_var = tk.BooleanVar(value=self.config.get('launch_at_startup', False))
        self.launch_at_startup_checkbox = tk.Checkbutton(
            self.settings_tab,
            text="Launch at Startup",
            variable=self.launch_at_startup_var,
            command=self.callbacks['toggle_launch_at_startup'],
            bg="#2e2e2e", fg="#ffffff", selectcolor="#815ac0",
            activebackground="#2e2e2e", activeforeground="#ffffff"
        )
        self.launch_at_startup_checkbox.pack(pady=5)

        # dark mode!!!!
        self.enable_dark_mode()

    def enable_dark_mode(self):
        """Apply dark mode styling to the application."""
        dark_bg = "#2e2e2e"
        dark_fg = "#ffffff"
        accent_color = "#815ac0"
        border_color = "#815ac0"

        # Root window
        self.root.configure(bg=dark_bg)
        self.root.option_add("*Background", dark_bg)
        self.root.option_add("*Foreground", dark_fg)

        # Tab styling
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=dark_bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=accent_color, foreground=dark_fg, padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", dark_bg)], foreground=[("selected", dark_fg)])

        self.tab_control.configure(style="TNotebook")

        style.configure("Dark.TFrame", background=dark_bg)
        self.main_tab.configure(style="Dark.TFrame")
        self.settings_tab.configure(style="Dark.TFrame")

        # Main tab
        for widget in self.main_tab.winfo_children():
            if isinstance(widget, tk.Label):
                widget.configure(bg=dark_bg, fg=dark_fg)
            elif isinstance(widget, tk.Entry):
                widget.configure(bg=dark_bg, fg=dark_fg, insertbackground=dark_fg, highlightbackground=border_color, highlightcolor=border_color, highlightthickness=1)
            elif isinstance(widget, tk.Button):
                widget.configure(bg=accent_color, fg=dark_fg, activebackground=dark_fg, activeforeground=dark_bg)
            elif isinstance(widget, tk.Frame):
                widget.configure(bg=dark_bg)

        # Settings tab
        for widget in self.settings_tab.winfo_children():
            if isinstance(widget, tk.Label):
                widget.configure(bg=dark_bg, fg=dark_fg)
            elif isinstance(widget, tk.Entry):
                widget.configure(bg=dark_bg, fg=dark_fg, insertbackground=dark_fg, highlightbackground=border_color, highlightcolor=border_color, highlightthickness=1)
            elif isinstance(widget, tk.Button):
                widget.configure(bg=accent_color, fg=dark_fg, activebackground=dark_fg, activeforeground=dark_bg)
            elif isinstance(widget, tk.Scale):
                widget.configure(
                    bg=dark_bg, 
                    fg=dark_fg, 
                    troughcolor=accent_color, 
                    highlightbackground=border_color,
                    highlightcolor=border_color,
                    highlightthickness=1
                )
            elif isinstance(widget, ttk.Checkbutton):
                widget.configure(style="Dark.TCheckbutton")
            elif isinstance(widget, tk.Frame):
                widget.configure(bg=dark_bg)

        # Checkbutton styling
        style.configure("Dark.TCheckbutton", background=dark_bg, foreground=dark_fg)
        style.map("Dark.TCheckbutton", background=[("active", dark_bg)], foreground=[("active", dark_fg)])

        self.notify_checkbox = tk.Checkbutton(
            self.settings_tab, text="Enable New Streamer Notification",
            variable=self.config['notify_var'], command=self.callbacks['toggle_notifications'],
            bg=dark_bg, fg=dark_fg, selectcolor=accent_color, activebackground=dark_bg, activeforeground=dark_fg
        )
        self.notify_checkbox.pack(pady=5)

        tk.Button(
            self.settings_tab, 
            text="Select Notification Sound", 
            command=self.callbacks['select_sound_file'],
            bg=accent_color, 
            fg=dark_fg, 
            activebackground=dark_fg, 
            activeforeground=dark_bg
        ).pack(pady=5)

    def add_item_to_canvas(self, text, link=None, image_url=None, linger_duration=None, remaining_linger=None):
        if linger_duration and remaining_linger is not None and linger_duration > 0:
            color1 = (129, 90, 192)  # purple
            color2 = (255, 0, 0)  # red
            ratio = max(0, min(remaining_linger / linger_duration, 1))
            r = int(color2[0] * (1 - ratio) + color1[0] * ratio)
            g = int(color2[1] * (1 - ratio) + color1[1] * ratio)
            b = int(color2[2] * (1 - ratio) + color1[2] * ratio)
            bg_color = f"#{r:02x}{g:02x}{b:02x}"
        else:
            bg_color = "#2e2e2e"

        existing_widgets = {
            getattr(widget, "streamer_id", None): widget
            for widget in self.canvas_frame.winfo_children()
            if widget.winfo_exists()
        }

        streamer_id = text
        if remaining_linger == 0:
            widget = existing_widgets[streamer_id]
            widget.destroy()

        if streamer_id in existing_widgets:
            widget = existing_widgets[streamer_id]
            widget.pack_forget()
            widget.pack(fill=tk.X)
            widget.configure(bg=bg_color)
            for child in widget.winfo_children():
                if hasattr(child, "configure"):
                    child.configure(bg=bg_color)
        else:
            item_frame = tk.Frame(self.canvas_frame, bg=bg_color)
            item_frame.pack(fill=tk.X)
            item_frame.streamer_id = streamer_id

            def load_image():
                try:
                    response = requests.get(image_url, timeout=5)
                    response.raise_for_status()
                    img_data = BytesIO(response.content)
                    img = Image.open(img_data).resize((30, 30))
                    tk_img = ImageTk.PhotoImage(img)

                    def update_ui():
                        img_label = tk.Label(item_frame, image=tk_img, bg=bg_color, cursor="hand2" if link else "arrow")
                        img_label.image = tk_img
                        img_label.pack(side=tk.LEFT)

                        if link:
                            img_label.bind("<Button-1>", lambda e: webbrowser.open(link))

                        text_label = tk.Label(item_frame, text=text, bg=bg_color, fg="#ffffff", anchor="w", cursor="hand2" if link else "arrow")
                        text_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

                        if link:
                            text_label.bind("<Button-1>", lambda e: webbrowser.open(link))

                    self.root.after(0, update_ui)
                except Exception as e:
                    self.root.after(0, lambda: self.add_text_only_item(item_frame, text, link, bg_color))

            if image_url:
                threading.Thread(target=load_image, daemon=True).start()
            else:
                self.add_text_only_item(item_frame, text, link, bg_color)

    def add_text_only_item(self, item_frame, text, link, bg_color):
        text_label = tk.Label(item_frame, text=text, bg=bg_color, fg="#ffffff", anchor="w", cursor="hand2" if link else "arrow")
        text_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        if link:
            text_label.bind("<Button-1>", lambda e: webbrowser.open(link))

    def search_categories(self, event):
        """Search for categories based on the live input in the game entry field."""
        if self.search_timer:
            self.search_timer.cancel() 

        query = self.game_entry.get().strip()
        if not query:
            self.clear_dropdown()
            return

        # Set a timer to delay the search
        self.search_timer = Timer(0.3, lambda: self.perform_search(query))
        self.search_timer.start()

    def perform_search(self, query):
        """Perform the actual search for categories."""
        categories = self.twitch_api.search_categories(query)
        self.show_dropdown(categories)

    def show_dropdown(self, categories):
        """Display the dropdown menu as a floating window."""
        if not categories:
            self.clear_dropdown()
            return

        if not self.dropdown_window:
            # Create the dropdown window if it doesn't exist
            self.dropdown_window = tk.Toplevel(self.root)
            self.dropdown_window.wm_overrideredirect(True)

        # Update the dropdown position and size
        self.dropdown_window.geometry(self.get_dropdown_position(categories))

        # Clear existing buttons
        for widget in self.dropdown_window.winfo_children():
            widget.destroy()

        # Add buttons for the new categories
        for category in categories:
            button = tk.Button(
                self.dropdown_window,
                text=category["name"],
                command=lambda name=category["name"]: self.select_category(name),
                anchor="w"
            )
            button.pack(fill=tk.X)

    def on_global_click(self, event):
        """Close the dropdown menu if clicking outside of it."""
        if self.dropdown_window:
            # Check if the click is outside the dropdown window
            x1 = self.dropdown_window.winfo_rootx()
            y1 = self.dropdown_window.winfo_rooty()
            x2 = x1 + self.dropdown_window.winfo_width()
            y2 = y1 + self.dropdown_window.winfo_height()

            if not (x1 <= event.x_root <= x2 and y1 <= event.y_root <= y2):
                self.clear_dropdown()
                self.root.unbind("<Button-1>")

    def get_dropdown_position(self, categories):
        """Calculate the position of the dropdown window relative to the entry field."""
        x = self.game_entry.winfo_rootx()
        y = self.game_entry.winfo_rooty() + self.game_entry.winfo_height()

        # Update the dropdown position dynamically when the application moves
        self.root.bind("<Configure>", lambda e: self.update_dropdown_position(categories))

        if self.dropdown_window:
            x = self.game_entry.winfo_rootx()
            y = self.game_entry.winfo_rooty() + self.game_entry.winfo_height()
            width = self.game_entry.winfo_width()
            height = len(categories) * 26
            self.dropdown_window.geometry(f"{int(width)}x{int(height)}+{int(x)}+{int(y)}")
        width = self.game_entry.winfo_width()
        height = len(categories) * 26
        return f"{int(width)}x{int(height)}+{int(x)}+{int(y)}"

    def select_category(self, category_name):
        """Auto-fill the game entry field with the selected category and clear the dropdown."""
        self.game_entry.delete(0, tk.END)
        self.game_entry.insert(0, category_name)
        self.clear_dropdown()

    def clear_dropdown(self):
        """Destroy the dropdown window if it exists."""
        if self.dropdown_window:
            self.dropdown_window.destroy()
            self.dropdown_window = None
    
    def update_dropdown_position(self, categories):
        """Update the position of the dropdown window when the application moves."""
        if self.dropdown_window:
            x = self.game_entry.winfo_rootx()
            y = self.game_entry.winfo_rooty() + self.game_entry.winfo_height()
            width = self.game_entry.winfo_width()
            height = len(categories) * 26
            self.dropdown_window.geometry(f"{int(width)}x{int(height)}+{int(x)}+{int(y)}")