import tkinter as tk
from tkinter import ttk
import sys
import os

class Layout:
    def __init__(self, root, config, callbacks):
        self.root = root
        self.config = config
        self.callbacks = callbacks
        self.initialize_layout()

    def initialize_layout(self):
        """Initialize the layout for the StreamScouter application."""
        self.root.title("StreamScouter")
        self.root.geometry(f"{self.config['default_width']}x{self.config['default_height']}")
        self.root.minsize(200, 300)

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

        tk.Label(self.main_tab, text="Number of Streamers to Track:").pack()
        self.count_entry = tk.Entry(self.main_tab)
        self.count_entry.insert(0, str(self.config['default_count'] or ""))
        self.count_entry.pack(fill=tk.X, padx=10)

        self.track_button = tk.Button(self.main_tab, text="Track Streamers", command=self.callbacks['update_streamers'])
        self.track_button.pack()

        tk.Button(self.main_tab, text="Stop Tracking", command=self.callbacks['stop_tracking']).pack()

        self.timer_label = tk.Label(self.main_tab, text="Next refresh in: 30s", anchor="e")
        self.timer_label.pack(fill=tk.X, padx=10, pady=5)

        frame = tk.Frame(self.main_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create the Listbox
        self.result_list = tk.Listbox(frame, width=50, height=20)
        self.result_list.grid(row=0, column=0, sticky="nsew")

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

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.result_list.yview, style="#815ac0.Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Sets the scrollbar to the listbox
        self.result_list.configure(yscrollcommand=scrollbar.set)

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

        # Listbox
        self.result_list.configure(
            bg=dark_bg, 
            fg=dark_fg, 
            selectbackground=accent_color, 
            selectforeground=dark_bg,
            highlightbackground=border_color,
            highlightcolor=border_color
        )

        style.configure("Dark.TFrame", background=dark_bg)

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