# ui_app.py
# Battleship Project - Tkinter app + screen manager
# Created: 2026-02-06

import tkinter as tk  # Tkinter GUI framework
from tkinter import filedialog, messagebox, ttk, font as tkfont  # File picker + simple alerts
from app.app_models import GameState  # Shared game state object
from app.ui_screen import WelcomeScreen, PlacementScreen, BattleScreen, WinScreen  # All screen classes
from pathlib import Path  # For file path handling

try:
    from PIL import Image, ImageTk
except ImportError:  # Pillow is optional; the app still runs without wallpaper support.
    Image = None
    ImageTk = None


WINDOW_PRESETS = {
    "compact": {"label": "Compact", "width_ratio": 0.74, "height_ratio": 0.80},
    "balanced": {"label": "Balanced", "width_ratio": 0.84, "height_ratio": 0.88},
    "large": {"label": "Large", "width_ratio": 0.93, "height_ratio": 0.94},
    "fullscreen": {"label": "Full Screen"},
}
WINDOW_PRESET_ORDER = ("compact", "balanced", "large", "fullscreen")
DEFAULT_WINDOW_PRESET = "balanced"

BASE_LAYOUT_WIDTH = 1500
BASE_LAYOUT_HEIGHT = 960
MIN_LAYOUT_SCALE = 0.65
MAX_LAYOUT_SCALE = 1.18

MIN_WINDOW_WIDTH = 760
MIN_WINDOW_HEIGHT = 620

FONT_SPECS = {
    "title": ("Helvetica", 46, "bold"),
    "section": ("Helvetica", 22, "bold"),
    "status": ("Helvetica", 19, "bold"),
    "body": ("Helvetica", 13, "normal"),
    "small": ("Helvetica", 11, "normal"),
    "button": ("Helvetica", 12, "bold"),
    "result": ("Helvetica", 28, "bold"),
    "board_title": ("Helvetica", 18, "bold"),
    "board_label": ("Helvetica", 12, "bold"),
    "battle_cell": ("Helvetica", 14, "bold"),
}


'''
This file defines the main Tkinter application class, App, which acts as the screen manager. 
It creates the root window, initializes the shared GameState, and loads all screens (WelcomeScreen, PlacementScreen, and BattleScreen) 
into a single container frame. The app controls which screen is visible using tkraise(), allowing smooth screen transitions without destroying widgets. 
It also configures fullscreen behavior and provides a single place for screens to access shared state.
'''

class App(tk.Tk):  # Main application window inherits from Tk
    def __init__(self):
        super().__init__()  # Initialize Tk base class
        self.title("Battleship")  # Set window title
        self.state = GameState()  # Create shared game state object
        self._current_screen_name = None
        self._current_window_preset = DEFAULT_WINDOW_PRESET
        self._last_layout_scale = None
        self._style = ttk.Style(self)
        self.ui_fonts = {}
        self.screens = {}  # Dictionary to store screen instances

        self._build_ui_fonts()

        # Use a moderate default font so windowed mode still fits cleanly.
        self.option_add("*Font", self.ui_font("body"))
        self._style.configure("TCombobox", font=self.ui_font("body"))

        # --- Wallpaper / background setup ---
        self._bg_original = None      # PIL.Image (original)
        self._bg_photo = None         # ImageTk.PhotoImage (resized)
        self._bg_label = tk.Label(self, bd=0, bg="#0b1f33")
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self._on_resize)  # auto-resize wallpaper when window changes

        # Container frame to hold all screens (kept above wallpaper)
        self._container = tk.Frame(self, bg="")
        self._container.pack(fill="both", expand=True)  # Make container fill window
        self._container.lift()  # keep screens above the wallpaper

        self._container.grid_rowconfigure(0, weight=1)  # Allow vertical expansion
        self._container.grid_columnconfigure(0, weight=1)  # Allow horizontal expansion

        # Create and register each screen
        for Screen in (WelcomeScreen, PlacementScreen, BattleScreen, WinScreen):
            self._add_screen(Screen)

        self.show_screen("WelcomeScreen")  # Show welcome screen first

        min_width = min(MIN_WINDOW_WIDTH, max(760, self.winfo_screenwidth() - 120))
        min_height = min(MIN_WINDOW_HEIGHT, max(580, self.winfo_screenheight() - 160))
        self.minsize(min_width, min_height)
        self.resizable(True, True)
        self.set_window_preset(DEFAULT_WINDOW_PRESET)

        self.bind("<Escape>", self._on_escape)  # ESC exits fullscreen
        self.bind("<F11>", self.toggle_fullscreen)  # F11 toggles fullscreen

        # Wallpaper picker: Cmd/Ctrl+O to choose an image
        self.bind_all("<Command-o>", lambda e: self.choose_wallpaper())
        self.bind_all("<Control-o>", lambda e: self.choose_wallpaper())

        # Optional menu (works even in fullscreen on some platforms)
        menubar = tk.Menu(self)
        menubar.add_command(label="Forfeit", command=self.forfeit)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Choose Wallpaper…", command=self.choose_wallpaper)
        view_menu.add_command(label="Clear Wallpaper", command=self.clear_wallpaper)
        size_menu = tk.Menu(view_menu, tearoff=0)
        for preset_name in WINDOW_PRESET_ORDER:
            size_menu.add_command(
                label=self.window_preset_option_label(preset_name),
                command=lambda name=preset_name: self.set_window_preset(name),
            )
        view_menu.add_separator()
        view_menu.add_cascade(label="Window Size", menu=size_menu)
        view_menu.add_command(label="Toggle Full Screen (F11)", command=self.toggle_fullscreen)
        menubar.add_cascade(label="View", menu=view_menu)
        self.config(menu=menubar)

        # Try to load a default wallpaper if it exists in the project root
        default_wallpaper = "assets/HD-wallpaper-battleship-oceans-clouds-sea.jpg"
        try:
            self.set_wallpaper(default_wallpaper)
        except Exception:
            pass

    def _build_ui_fonts(self):
        for name, (family, size, weight) in FONT_SPECS.items():
            self.ui_fonts[name] = tkfont.Font(self, family=family, size=size, weight=weight)

    def ui_font(self, name: str) -> tkfont.Font:
        return self.ui_fonts[name]

    def window_preset_label(self, name: str) -> str:
        return WINDOW_PRESETS[name]["label"]

    def current_window_preset(self) -> str:
        return self._current_window_preset

    def current_window_preset_label(self) -> str:
        return self.window_preset_label(self._current_window_preset)

    def window_preset_dimensions(self, preset_name: str) -> tuple[int, int]:
        if preset_name == "fullscreen":
            return self.winfo_screenwidth(), self.winfo_screenheight()
        return self._preset_window_size(preset_name)

    def window_preset_option_label(self, preset_name: str) -> str:
        width, height = self.window_preset_dimensions(preset_name)
        return f"{self.window_preset_label(preset_name)} - {width} x {height}"

    def current_window_size_text(self) -> str:
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        if width == 1 or height == 1:
            width, height = self.window_preset_dimensions(self._current_window_preset)
        return f"{width} x {height}"

    def _center_window(self, width: int, height: int):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _preset_window_size(self, preset_name: str) -> tuple[int, int]:
        """Translate a named preset into a centered window size that fits the monitor."""
        preset = WINDOW_PRESETS[preset_name]
        screen_w = max(820, self.winfo_screenwidth() - 80)
        screen_h = max(620, self.winfo_screenheight() - 120)
        width = max(MIN_WINDOW_WIDTH, int(screen_w * preset["width_ratio"]))
        height = max(MIN_WINDOW_HEIGHT, int(screen_h * preset["height_ratio"]))
        width = min(width, screen_w)
        height = min(height, screen_h)
        return width, height

    def set_window_preset(self, preset_name: str):
        """Apply a preset and then let each screen recompute its own responsive layout."""
        if preset_name not in WINDOW_PRESETS:
            return

        self._current_window_preset = preset_name

        if preset_name == "fullscreen":
            self.attributes("-fullscreen", True)
        else:
            self.attributes("-fullscreen", False)
            width, height = self._preset_window_size(preset_name)
            self._center_window(width, height)

        self.after_idle(self._update_ui_scale_from_window)
        self.after_idle(self._notify_layout_change)

    def toggle_fullscreen(self, _event=None):
        if self._current_window_preset == "fullscreen":
            self.set_window_preset(DEFAULT_WINDOW_PRESET)
        else:
            self.set_window_preset("fullscreen")
        return "break"

    def _on_escape(self, _event=None):
        if self._current_window_preset == "fullscreen":
            self.set_window_preset("large")
            return "break"
        return None

    def forfeit(self):
        """Called when the user picks the Forfeit menu item.

        The current player gives up and the opponent is declared the winner.
        If called outside of battle (no ships placed yet) it simply returns.
        """
        from tkinter import messagebox

        s = self.state
        # only meaningful during battle phase
        if s.num_ships is None or not any(s.p1_ships) or not any(s.p2_ships):
            return

        # confirm with user
        if not messagebox.askyesno("Forfeit", "Are you sure you want to forfeit the game?"):
            return

        other = 2 if s.current_turn == 1 else 1
        win_screen = self.screens.get("WinScreen")
        if win_screen:
            win_screen.set_winner(f"PLAYER {other} WINS BY FORFEIT!")
            win_screen.set_stats()
            self.show_screen("WinScreen")

    def _add_screen(self, ScreenClass):
        screen = ScreenClass(parent=self._container, app=self)  # Create screen instance
        self.screens[ScreenClass.__name__] = screen  # Store by class name
        screen.grid(row=0, column=0, sticky="nsew")  # Stack screens on top of each other

    def show_screen(self, name: str):
        if self._current_screen_name and self._current_screen_name != name:
            current = self.screens.get(self._current_screen_name)
            if current and hasattr(current, "on_hide"):
                current.on_hide()

        self._current_screen_name = name
        self.screens[name].tkraise()  # Bring selected screen to the front

    def new_game(self):
        n = self.state.num_ships  # Remember selected ship count

        self.state.reset_for_new_game()  # Reset all boards, hits, shots, turns

        self.state.num_ships = n  # Restore ship count

        # Reset placement phase variables
        self.state.placing_player = 1       # Player 1 starts placement again
        self.state.placing_orientation = "H"  # Default orientation
        self.state.placing_ship_len = 1     # First ship size starts at 1

        self.show_screen("WelcomeScreen")  # Return to welcome screen

    def choose_wallpaper(self):
        """Open a file picker so the user can choose a wallpaper image."""
        if Image is None or ImageTk is None:
            messagebox.showinfo(
                "Wallpaper Unavailable",
                "Wallpaper support requires Pillow. Install it to enable custom backgrounds.",
            )
            return

        path = filedialog.askopenfilename(
            title="Choose a wallpaper image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            self.set_wallpaper(path)
        except Exception as e:
            messagebox.showerror("Wallpaper Error", f"Could not load that image.\n\n{e}")

    def set_wallpaper(self, path: str):
        """Load wallpaper from a path.

        - Absolute paths (from the file picker) work as-is.
        - Relative paths (repo assets like 'assets/..') resolve from the project root.
        """
        if Image is None or ImageTk is None:
            raise RuntimeError("Pillow is not installed.")

        p = Path(path)

        # If a relative path is provided, resolve it from the project root (Battleship/)
        if not p.is_absolute():
            project_root = Path(__file__).resolve().parents[1]  # .../Battleship/
            p = project_root / p

        img = Image.open(p)
        self._bg_original = img
        self._render_wallpaper()

    def clear_wallpaper(self):
        """Remove the wallpaper."""
        self._bg_original = None
        self._bg_photo = None
        self._bg_label.config(image="")

    def _on_resize(self, event):
        # Only respond to root window resize events
        if event.widget is not self:
            return
        self._update_ui_scale_from_window()
        if self._bg_original is not None:
            self._render_wallpaper()

    def _update_ui_scale_from_window(self):
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        scale = min(width / BASE_LAYOUT_WIDTH, height / BASE_LAYOUT_HEIGHT)
        scale = max(MIN_LAYOUT_SCALE, min(MAX_LAYOUT_SCALE, scale))
        self._apply_layout_scale(scale)

    def _apply_layout_scale(self, scale: float):
        if self._last_layout_scale is not None and abs(scale - self._last_layout_scale) < 0.03:
            return

        self._last_layout_scale = scale
        for name, (_, base_size, _) in FONT_SPECS.items():
            self.ui_fonts[name].configure(size=max(8, round(base_size * scale)))

        self._style.configure("TCombobox", font=self.ui_font("body"))
        self._notify_layout_change()

    def _notify_layout_change(self):
        for screen in self.screens.values():
            callback = getattr(screen, "on_layout_change", None)
            if callable(callback):
                callback(self._last_layout_scale or 1.0)

    def _render_wallpaper(self):
        """Resize the original wallpaper to the current window size and apply it."""
        if self._bg_original is None or Image is None or ImageTk is None:
            return

        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())

        # Use high-quality resizing
        if hasattr(Image, "Resampling"):
            resample = Image.Resampling.LANCZOS
        else:
            resample = Image.LANCZOS
        resized = self._bg_original.resize((w, h), resample)
        self._bg_photo = ImageTk.PhotoImage(resized)
        self._bg_label.config(image=self._bg_photo)
        self._bg_label.lower()         # keep it behind
        self._container.lift()         # keep screens above

        welcome = self.screens.get("WelcomeScreen")
        if welcome and hasattr(welcome, "refresh_wallpaper"):
            welcome.refresh_wallpaper()
