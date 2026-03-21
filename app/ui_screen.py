# ui_screen.py
# Battleship Project - UI screens
# Created: 2026-02-06

'''
This is the largest and most important UI file, containing all three game screens and nearly all player interaction.

WelcomeScreen lets the user choose how many ships to play with and initializes the game state accordingly.

PlacementScreen handles ship placement for both players, enforcing turn order, ship sizes, orientation toggling, overlap rules, and allowing ships to be removed by clicking them again.

BattleScreen manages the actual gameplay: selecting targets, firing shots, displaying hits/misses/sinks, switching turns with a delay, updating the scoreboard, and detecting win conditions.

This file focuses on UI behavior and flow, while delegating rule enforcement (hits, sinks, remaining ships) to the game.rules module

'''

import tkinter as tk
from tkinter import ttk, messagebox
from collections import Counter
from game.board import generate_random_fleet
from game.rules import fire_shot, fire_area_shot, ships_remaining, ship_hit_counters, sunk_ship_cells, UNKNOWN, MISS, HIT  # type: ignore
from game.coords import col_to_letter, row_to_number
from game.ships import get_classic_fleet, get_placement_fleet


MIN_SHIPS = 1
MAX_SHIPS = 5
GRID_SIZE = 10

SCREEN_BG = "#071a2f"
CARD_BG = "#10263d"
PANEL_BG = "#12324f"
PANEL_BORDER = "#2f6489"
TEXT_DARK = "#eef8ff"
TEXT_MUTED = "#8fb5cf"
TEXT_SOFT = "#6489a7"

ACTIVE_BG = "#214b70"
COVER_BG = "#05101a"
CELL_EDGE = "#9bc4e3"
SUNK_EDGE = "#ffd166"

P1_SHIP_BG = "#1dd1a1"
P2_SHIP_BG = "#ff9f43"

MISS_BG = "#6c8295"
HIT_BG = "#ff5d73"
SUNK_BG = "#b4374a"

HIGHLIGHT_BG = "#4cc9f0"
PREVIEW_VALID_BG = "#ffb703"
PREVIEW_INVALID_BG = "#ef476f"
TURN_DELAY_MS = 3000

BUTTON_WIDTH = 16
BATTLE_BUTTON_WIDTH = 10
PLACEMENT_CELL_SIZE = 28
BATTLE_CELL_SIZE = 28

PRIMARY_BTN_BG = "#1d74c9"
SECONDARY_BTN_BG = "#168c88"
ACCENT_BTN_BG = "#f77f00"
BUTTON_FG = "#ffffff"
BUTTON_DISABLED_BG = "#24394f"
BUTTON_DISABLED_FG = "#7090a8"
TURN_BADGE_BG = "#163d5b"

RESULT_COLORS = {
    "neutral": TEXT_DARK,
    "good": "#7ae582",
    "warn": "#ffd166",
    "bad": "#ff6b6b",
}


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _blend(color: str, target: str, amount: float) -> str:
    r1, g1, b1 = _hex_to_rgb(color)
    r2, g2, b2 = _hex_to_rgb(target)
    r = round(r1 + (r2 - r1) * amount)
    g = round(g1 + (g2 - g1) * amount)
    b = round(b1 + (b2 - b1) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def make_action_button(parent, text, command, bg, width, font=None):
    if font is None:
        font = parent.winfo_toplevel().ui_font("button")

    button = tk.Label(
        parent,
        text=text,
        width=width,
        font=font,
        bg=bg,
        fg=BUTTON_FG,
        cursor="hand2",
        padx=12,
        pady=10,
        bd=0,
        highlightthickness=1,
        highlightbackground=_blend(bg, "#ffffff", 0.18),
        highlightcolor=_blend(bg, "#ffffff", 0.18),
    )
    button._command = command
    button._enabled = True
    button._default_bg = bg
    button._hover_bg = _blend(bg, "#ffffff", 0.12)

    def on_click(_event):
        if button._enabled and button._command:
            button._command()

    def on_enter(_event):
        if button._enabled:
            button.config(bg=button._hover_bg)

    def on_leave(_event):
        if button._enabled:
            button.config(bg=button._default_bg)
        else:
            button.config(bg=BUTTON_DISABLED_BG)

    button.bind("<Button-1>", on_click)
    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
    return button


def set_button_enabled(button, enabled: bool):
    if hasattr(button, "_enabled"):
        button._enabled = enabled
        button.config(
            bg=button._default_bg if enabled else BUTTON_DISABLED_BG,
            fg=BUTTON_FG if enabled else BUTTON_DISABLED_FG,
            cursor="hand2" if enabled else "arrow",
        )
        return

    button.config(state="normal" if enabled else "disabled")


def style_panel(frame, bg):
    frame.config(
        bg=bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=PANEL_BORDER,
        highlightcolor=PANEL_BORDER,
    )


class WelcomeScreen(tk.Frame):  # Screen 1: pick number of ships, then move to placement
    def __init__(self, parent, app):
        super().__init__(parent, bg=SCREEN_BG)  # Initialize Tkinter Frame base class
        self.app = app  # Store reference to the main App (lets us access state + screen switching)

        self.bg_label = tk.Label(self, bd=0, bg="#0b1f33")
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.refresh_wallpaper()

        inner = tk.Frame(self, bg=CARD_BG, padx=28, pady=22)
        style_panel(inner, CARD_BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")
        self.inner_card = inner

        self.command_lbl = tk.Label(
            inner,
            text="TACTICAL NAVAL COMMAND",
            font=self.app.ui_font("small"),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            justify="center",
        )
        self.command_lbl.pack(pady=(0, 10))

        self.title_lbl = tk.Label(
            inner,
            text="Battleship",
            font=self.app.ui_font("title"),
            bg=CARD_BG,
            fg=TEXT_DARK,
        )
        self.title_lbl.pack(pady=(0, 8))

        self.subtitle_lbl = tk.Label(
            inner,
            text="Set up your game, then choose who you want to play with.",
            font=self.app.ui_font("body"),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            justify="center",
        )
        self.subtitle_lbl.pack(pady=(0, 14))

        self.choice_var = tk.IntVar(value=MAX_SHIPS)  # Stores the selected number of boats

        content = tk.Frame(inner, bg=CARD_BG)
        content.pack(fill="x")
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        self.content = content

        self.setup_card = tk.Frame(content, bg=PANEL_BG, padx=18, pady=16)
        style_panel(self.setup_card, PANEL_BG)
        self.setup_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.mode_card = tk.Frame(content, bg=PANEL_BG, padx=18, pady=16)
        style_panel(self.mode_card, PANEL_BG)
        self.mode_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.setup_title_lbl = tk.Label(
            self.setup_card,
            text="Game Setup",
            font=self.app.ui_font("section"),
            bg=PANEL_BG,
            fg=TEXT_DARK,
        )
        self.setup_title_lbl.pack(pady=(0, 8))

        row = tk.Frame(self.setup_card, bg=PANEL_BG)  # Row container for label + dropdown
        row.pack(pady=(0, 8))
        self.ships_lbl = tk.Label(
            row,
            text="Boats:",
            font=self.app.ui_font("body"),
            bg=PANEL_BG,
            fg=TEXT_DARK,
        )
        self.ships_lbl.pack(side="left", padx=8)

        self.ship_count_dropdown = ttk.Combobox(  # Dropdown for ship count selection
            row,
            textvariable=self.choice_var,  # Connected to choice_var so we can read selected value
            values=list(range(MIN_SHIPS, MAX_SHIPS + 1)),  # Options [1..5]
            state="readonly",  # User must pick from list (no typing random values)
            width=5,  # Visual width of dropdown
            justify="center",  # Center the selected value text
        )
        self.ship_count_dropdown.pack(side="left")  # Place dropdown next to the label
        self.ship_count_dropdown.bind("<<ComboboxSelected>>", self.on_ship_count_changed)

        self.ship_info_lbl = tk.Label(  # Small explanation text about ship sizes
            self.setup_card,
            text="",
            font=self.app.ui_font("small"),
            fg=TEXT_MUTED,
            bg=PANEL_BG,
            justify="center",  # Center align multi-line text
        )
        self.ship_info_lbl.pack(pady=(0, 12))  # Add spacing below text

        size_section = tk.Frame(self.setup_card, bg=PANEL_BG)
        size_section.pack(fill="x")
        self.size_section = size_section

        self.size_heading_lbl = tk.Label(
            size_section,
            text="Window Size",
            font=self.app.ui_font("small"),
            bg=PANEL_BG,
            fg=TEXT_DARK,
        )
        self.size_heading_lbl.pack(pady=(0, 6))

        self.size_help_lbl = tk.Label(
            size_section,
            text="Choose the size that fits your screen best.",
            font=self.app.ui_font("small"),
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            justify="center",
        )
        self.size_help_lbl.pack(pady=(0, 8))

        size_controls = tk.Frame(size_section, bg=PANEL_BG)
        size_controls.pack()
        self.size_choice_var = tk.StringVar()
        self.size_option_names = {}
        self.size_dropdown = ttk.Combobox(
            size_controls,
            textvariable=self.size_choice_var,
            values=[],
            state="readonly",
            width=24,
            justify="center",
        )
        self.size_dropdown.pack(side="left")
        self.size_dropdown.bind("<<ComboboxSelected>>", self.on_window_preset_selected)

        self.size_status_lbl = tk.Label(
            size_section,
            text="",
            font=self.app.ui_font("small"),
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            justify="center",
        )
        self.size_status_lbl.pack(pady=(8, 0))

        self.mode_title_lbl = tk.Label(
            self.mode_card,
            text="Start Playing",
            font=self.app.ui_font("section"),
            bg=PANEL_BG,
            fg=TEXT_DARK,
        )
        self.mode_title_lbl.pack(pady=(0, 8))

        self.local_mode_title = tk.Label(
            self.mode_card,
            text="Play With Another Person",
            font=self.app.ui_font("board_title"),
            bg=PANEL_BG,
            fg=TEXT_DARK,
        )
        self.local_mode_title.pack(pady=(0, 6))

        self.local_mode_desc = tk.Label(
            self.mode_card,
            text="Two people share one computer and take turns.",
            font=self.app.ui_font("small"),
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            justify="center",
        )
        self.local_mode_desc.pack(pady=(0, 10))

        make_action_button(
            self.mode_card,
            text="2 Players",
            width=16,
            font=self.app.ui_font("button"),
            bg=PRIMARY_BTN_BG,
            command=self.on_continue,
        ).pack(pady=(0, 12))

        self.mode_divider = tk.Frame(self.mode_card, bg=PANEL_BORDER, height=1)
        self.mode_divider.pack(fill="x", pady=(0, 12))

        self.ai_mode_title = tk.Label(
            self.mode_card,
            text="Play Against The Computer",
            font=self.app.ui_font("board_title"),
            bg=PANEL_BG,
            fg=TEXT_DARK,
        )
        self.ai_mode_title.pack(pady=(0, 6))

        self.ai_mode_desc = tk.Label(
            self.mode_card,
            text="Pick Easy, Medium, or Hard. Easy is best for beginners.",
            font=self.app.ui_font("small"),
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            justify="center",
        )
        self.ai_mode_desc.pack(pady=(0, 10))

        self.ai_buttons_row = tk.Frame(self.mode_card, bg=PANEL_BG)
        self.ai_buttons_row.pack()
        make_action_button(
            self.ai_buttons_row,
            text="Easy",
            width=10,
            font=self.app.ui_font("button"),
            bg=SECONDARY_BTN_BG,
            command=lambda: self.on_ai_mode("easy"),
        ).pack(side="left", padx=4)

        make_action_button(
            self.ai_buttons_row,
            text="Medium",
            width=10,
            font=self.app.ui_font("button"),
            bg=ACCENT_BTN_BG,
            command=lambda: self.on_ai_mode("medium"),
        ).pack(side="left", padx=4)

        make_action_button(
            self.ai_buttons_row,
            text="Hard",
            width=10,
            font=self.app.ui_font("button"),
            bg="#d64b4b",
            command=lambda: self.on_ai_mode("hard"),
        ).pack(side="left", padx=4)
        self.refresh_ship_info()

    def tkraise(self, aboveThis=None):
        self.refresh_wallpaper()
        self.refresh_window_size_status()
        super().tkraise(aboveThis)

    def refresh_wallpaper(self):
        photo = getattr(self.app, "_bg_photo", None)
        self.bg_label.config(image=photo if photo else "", bg=SCREEN_BG)
        self.bg_label.image = photo
        self.bg_label.lower()

    def on_layout_change(self, _scale=1.0):
        wrap = max(320, min(620, self.winfo_width() - 180))
        self.subtitle_lbl.config(wraplength=wrap)
        self.ship_info_lbl.config(wraplength=wrap)
        self.size_help_lbl.config(wraplength=wrap)
        self.size_status_lbl.config(wraplength=wrap)
        mode_wrap = max(320, wrap - 40)
        self.local_mode_desc.config(wraplength=mode_wrap)
        self.ai_mode_desc.config(wraplength=mode_wrap)
        self.refresh_window_size_status()

    def on_ship_count_changed(self, _event=None):
        self.refresh_ship_info()

    def refresh_ship_info(self):
        count = int(self.choice_var.get())
        fleet = get_classic_fleet(count)
        summary = ", ".join(f"{ship.name} ({ship.length})" for ship in fleet)
        self.ship_info_lbl.config(text=f"Classic fleet: {summary}")

    def refresh_window_size_status(self):
        self.size_option_names = {}
        labels = []
        for preset_name in ("compact", "balanced", "large", "fullscreen"):
            label = self.app.window_preset_option_label(preset_name)
            labels.append(label)
            self.size_option_names[label] = preset_name

        self.size_dropdown.config(values=labels)
        current_preset = self.app.current_window_preset()
        current = self.app.window_preset_option_label(current_preset)
        self.size_choice_var.set(current)
        self.size_status_lbl.config(
            text=f"Current: {self.app.current_window_size_text()}. Drag the edges for a custom size.",
        )

    def on_window_preset_selected(self, _event=None):
        self.apply_selected_window_preset()

    def apply_selected_window_preset(self):
        preset_name = self.size_option_names.get(self.size_choice_var.get())
        if preset_name is None:
            return
        self.app.set_window_preset(preset_name)
        self.refresh_window_size_status()

    def on_continue(self):
        n = int(self.choice_var.get())  # Read selected ship count from dropdown variable

        if not (MIN_SHIPS <= n <= MAX_SHIPS):  # Safety check (should always pass due to readonly combobox)
            messagebox.showerror("Invalid", "Pick a number from 1 to 5.")  # Show error popup
            return  # Stop if invalid

        self.app.state.reset_for_new_game()  # Clear old boards/ships/hits/turns (fresh start)
        self.app.state.num_ships = n  # Save ship count into shared GameState
        # normal two‑player placement follows
        self.app.show_screen("PlacementScreen")  # Go to placement phase

    def on_ai_mode(self, mode: str):
        """Start a new game where player 2 is controlled by an AI of given difficulty.

        `mode` must be "easy" or "medium".
        """
        n = int(self.choice_var.get())
        if not (MIN_SHIPS <= n <= MAX_SHIPS):
            messagebox.showerror("Invalid", "Pick a number from 1 to 5.")
            return

        self.app.state.reset_for_new_game()
        self.app.state.num_ships = n
        self.app.state.p2_ai_mode = mode
        self.app.show_screen("PlacementScreen")


class PlacementScreen(tk.Frame):  # Screen 2: both players place ships before battle
    """
    Two 10x10 grids:
    - Left = Player 1 placement
    - Right = Player 2 placement

    Player 1 places first, clicks Ready.
    Player 2 places next, clicks Ready.
    Then we move to BattleScreen (placeholder for now).
    """

    def __init__(self, parent, app):
        super().__init__(parent, bg=SCREEN_BG)  # Initialize Tkinter Frame base class
        self.app = app  # Store reference to the main App (state + screen switching)
        self._transition_job = None
        self._board_layout_mode = None
        self._placement_cell_size = None
        self._placement_cell_images = {}
        self._hover_target = None
        self._preview_state = None

        root = tk.Frame(self, bg=SCREEN_BG)  # Root container for this screen
        root.pack(fill="both", expand=True, padx=16, pady=10)  # Fill screen with padding
        self.root = root

        top = tk.Frame(root, bg=SCREEN_BG)  # Top bar container (status + buttons)
        top.pack(fill="x", pady=(0, 8))  # Stretch horizontally + spacing below
        self.top_bar = top
        style_panel(top, CARD_BG)
        top.config(padx=14, pady=10)

        self.status_lbl = tk.Label(
            top,
            text="",
            font=self.app.ui_font("status"),
            bg=CARD_BG,
            fg=TEXT_DARK,
            justify="left",
        )
        self.status_lbl.pack(fill="x")

        controls = tk.Frame(root, bg=SCREEN_BG)
        self.controls_bar = controls
        style_panel(controls, CARD_BG)
        controls.config(padx=12, pady=8)

        controls_left = tk.Frame(controls, bg=CARD_BG)
        controls_left.pack(side="left")

        self.controls_lbl = tk.Label(
            controls_left,
            text="Boat Direction",
            font=self.app.ui_font("small"),
            bg=CARD_BG,
            fg=TEXT_MUTED,
        )
        self.controls_lbl.pack(side="left", padx=(0, 8))

        self.orient_btn = make_action_button(  # Button to toggle horizontal/vertical placement
            controls_left,
            text=self._orientation_button_text("H"),
            command=self.toggle_orientation,  # Calls toggle function
            width=16,  # Button width
            font=self.app.ui_font("button"),
            bg=PRIMARY_BTN_BG,
        )
        self.orient_btn.pack(side="left")

        self.randomize_btn = make_action_button(
            controls_left,
            text="Randomize Boats",
            command=self.on_randomize_fleet,
            width=15,
            font=self.app.ui_font("button"),
            bg=ACCENT_BTN_BG,
        )
        self.randomize_btn.pack(side="left", padx=(10, 0))

        self.ready_btn = make_action_button(  # Button to finish current player's placement
            controls,
            text="Ready",
            command=self.on_ready,  # Calls ready handler
            width=10,
            font=self.app.ui_font("button"),
            bg=SECONDARY_BTN_BG,
        )
        self.ready_btn.pack(side="right")  # Align right

        self.hint_lbl = tk.Label(
            root,
            text="Place the classic fleet one boat at a time.",
            font=self.app.ui_font("small"),
            bg=SCREEN_BG,
            fg=TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.hint_lbl.pack(fill="x", pady=(0, 4))

        controls.pack(fill="x", pady=(0, 6))

        self.fleet_strip = tk.Frame(root, bg=CARD_BG, padx=10, pady=6)
        style_panel(self.fleet_strip, CARD_BG)
        self.fleet_strip.pack(fill="x", pady=(0, 6))
        self.fleet_badges = []

        boards = tk.Frame(root, bg=SCREEN_BG)  # Container holding both player grids
        boards.pack(fill="both", expand=True)  # Let boards take remaining space
        self.boards_container = boards

        # Player 1 panel (left side)
        self.p1_panel = tk.Frame(boards, bg=PANEL_BG, padx=8, pady=4, highlightthickness=3)
        style_panel(self.p1_panel, PANEL_BG)
        self.p1_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))  # Left with spacing to middle
        self.p1_title = tk.Label(self.p1_panel, text="Player 1 Fleet", font=self.app.ui_font("board_title"), bg=PANEL_BG, fg=TEXT_DARK)
        self.p1_title.pack(pady=(0, 1))
        self.p1_hint = tk.Label(self.p1_panel, text="", font=self.app.ui_font("small"), bg=PANEL_BG, fg=TEXT_MUTED)
        self.p1_hint.pack(pady=(0, 3))
        self.p1_grid = tk.Frame(self.p1_panel, bg=PANEL_BG)  # Grid frame for Player 1 cells
        self.p1_grid.pack()  # Pack the grid frame

        # Player 2 panel (right side)
        self.p2_panel = tk.Frame(boards, bg=PANEL_BG, padx=8, pady=4, highlightthickness=3)
        style_panel(self.p2_panel, PANEL_BG)
        self.p2_panel.pack(side="left", fill="both", expand=True, padx=(12, 0))  # Right with spacing from middle
        self.p2_title = tk.Label(self.p2_panel, text="Player 2 Fleet", font=self.app.ui_font("board_title"), bg=PANEL_BG, fg=TEXT_DARK)
        self.p2_title.pack(pady=(0, 1))
        self.p2_hint = tk.Label(self.p2_panel, text="", font=self.app.ui_font("small"), bg=PANEL_BG, fg=TEXT_MUTED)
        self.p2_hint.pack(pady=(0, 3))
        self.p2_grid = tk.Frame(self.p2_panel, bg=PANEL_BG)  # Grid frame for Player 2 cells
        self.p2_grid.pack()  # Pack the grid frame

        self.p1_buttons = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]  # Store Player 1 cell widgets
        self.p2_buttons = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]  # Store Player 2 cell widgets

        self._make_grid(player=1)  # Build Player 1 grid widgets + bindings
        self._make_grid(player=2)  # Build Player 2 grid widgets + bindings
        self.after_idle(self._update_responsive_layout)

    def tkraise(self, aboveThis=None):
        self._cancel_transition()
        self._hover_target = None
        self._preview_state = None
        # Re-enable buttons in case they were disabled in previous game
        set_button_enabled(self.ready_btn, True)      # Allow pressing Ready again
        set_button_enabled(self.orient_btn, True)     # Allow toggling orientation again
        set_button_enabled(self.randomize_btn, True)  # Allow random placement again

        self._update_responsive_layout()
        self.refresh_ui()                          # Redraw board + update status text
        self._bind_orientation_keys()

        super().tkraise(aboveThis)                 # Bring this screen to front

    def on_hide(self):
        self._cancel_transition()
        self._unbind_orientation_keys()
        self._hover_target = None
        self._preview_state = None

    def on_layout_change(self, _scale=1.0):
        wrap = max(420, self.winfo_width() - 100)
        self.hint_lbl.config(wraplength=wrap)
        self._update_responsive_layout()

    def _update_responsive_layout(self):
        self._apply_placement_board_layout()
        self._apply_placement_cell_size()
        self._apply_placement_grid_visibility()
        self._update_placement_text_wraps()
        self._render_fleet_badges()

    def _apply_placement_board_layout(self):
        ai_game = self.app.state.p2_ai_mode is not None
        if ai_game:
            mode = "ai_only"
        else:
            mode = "stacked"
        if mode == self._board_layout_mode:
            return

        self._board_layout_mode = mode
        self.p1_panel.pack_forget()
        self.p2_panel.pack_forget()

        if mode == "ai_only":
            self.p1_panel.pack(fill="both", expand=True)
        elif mode == "stacked":
            self.p1_panel.pack(fill="x", expand=False, pady=(0, 10))
            self.p2_panel.pack(fill="x", expand=False)
        else:
            self.p1_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))
            self.p2_panel.pack(side="left", fill="both", expand=True, padx=(12, 0))

    def _apply_placement_cell_size(self):
        width = self.winfo_width()
        height = self.winfo_height()
        if self.app.state.p2_ai_mode is not None or self.app.state.placing_player == 1:
            panel = self.p1_panel
            title_widget = self.p1_title
            hint_widget = self.p1_hint
        else:
            panel = self.p2_panel
            title_widget = self.p2_title
            hint_widget = self.p2_hint
        panel_height = panel.winfo_height()
        panel_width = panel.winfo_width()

        if panel_height > 1 and panel_width > 1:
            title_height = title_widget.winfo_height() + hint_widget.winfo_height()
            usable_height = max(180, panel_height - title_height - 28)
            usable_width = max(180, panel_width - 80)
            size_from_height = max(18, min(PLACEMENT_CELL_SIZE, (usable_height - 26) // GRID_SIZE))
            size_from_width = max(18, min(PLACEMENT_CELL_SIZE, (usable_width - 44) // GRID_SIZE))
            cell_size = min(size_from_height, size_from_width)
        elif width < 920 or height < 760:
            cell_size = 20
        elif width < 1240 or height < 920:
            cell_size = 24
        else:
            cell_size = PLACEMENT_CELL_SIZE

        if cell_size == self._placement_cell_size:
            return

        self._placement_cell_size = cell_size
        image = self._placement_cell_image(cell_size)

        for cells in (self.p1_buttons, self.p2_buttons):
            for row in cells:
                for cell in row:
                    cell.config(image=image)
                    cell.image = image
                    cell.grid_configure(padx=0, pady=0)

    def _set_grid_visibility(self, grid: tk.Widget, visible: bool):
        is_visible = bool(grid.winfo_manager())
        if visible and not is_visible:
            grid.pack()
        elif not visible and is_visible:
            grid.pack_forget()

    def _apply_placement_grid_visibility(self):
        if self.app.state.p2_ai_mode is not None:
            self._set_grid_visibility(self.p1_grid, True)
            self._set_grid_visibility(self.p2_grid, False)
            return

        if self._board_layout_mode != "stacked":
            self._set_grid_visibility(self.p1_grid, True)
            self._set_grid_visibility(self.p2_grid, True)
            return

        active_player = getattr(self.app.state, "placing_player", 1)
        self._set_grid_visibility(self.p1_grid, active_player == 1)
        self._set_grid_visibility(self.p2_grid, active_player == 2)

    def _update_placement_text_wraps(self):
        width = self.winfo_width()
        self.status_lbl.config(wraplength=max(260, width - 80))
        if width < 980:
            self.controls_lbl.config(text="Direction")
            self.orient_btn.config(width=14)
            self.randomize_btn.config(width=13)
            self.ready_btn.config(width=9)
        else:
            self.controls_lbl.config(text="Boat Direction")
            self.orient_btn.config(width=16)
            self.randomize_btn.config(width=15)
            self.ready_btn.config(width=10)

    def _fleet_specs(self):
        s = self.app.state
        if s.num_ships is None:
            return []
        return get_placement_fleet(s.num_ships)

    def _required_ship_count(self) -> int:
        return len(self._fleet_specs())

    def _next_required_ship(self, player: int):
        fleet = self._fleet_specs()
        if not fleet:
            return None

        placed_counts = Counter(len(ship) for ship in self._ships_list_for_player(player))
        required_counts = Counter()

        for spec in fleet:
            required_counts[spec.length] += 1
            if placed_counts[spec.length] < required_counts[spec.length]:
                return spec

        return None

    def _render_fleet_badges(self):
        for badge in self.fleet_badges:
            badge.destroy()
        self.fleet_badges.clear()

        fleet = self._fleet_specs()
        if not fleet:
            return

        player = self.app.state.placing_player
        placed_counts = Counter(len(ship) for ship in self._ships_list_for_player(player))
        required_counts = Counter()
        width = self.winfo_width()
        if width >= 1180:
            columns = len(fleet)
        elif width >= 980:
            columns = min(3, len(fleet))
        else:
            columns = min(2, len(fleet))

        for index, spec in enumerate(fleet):
            required_counts[spec.length] += 1
            if placed_counts[spec.length] >= required_counts[spec.length]:
                bg = P1_SHIP_BG
                fg = TEXT_DARK
                badge_bg = _blend(P1_SHIP_BG, CARD_BG, 0.84)
                badge_edge = P1_SHIP_BG
                state_text = "Placed"
                state_bg = P1_SHIP_BG
                state_fg = "#052325"
            elif self._next_required_ship(player) == spec:
                bg = PREVIEW_VALID_BG
                fg = TEXT_DARK
                badge_bg = _blend(PREVIEW_VALID_BG, CARD_BG, 0.86)
                badge_edge = PREVIEW_VALID_BG
                state_text = "Next"
                state_bg = PREVIEW_VALID_BG
                state_fg = "#2b1400"
            else:
                bg = ACTIVE_BG
                fg = TEXT_DARK
                badge_bg = CARD_BG
                badge_edge = CELL_EDGE
                state_text = ""
                state_bg = CARD_BG
                state_fg = TEXT_DARK

            badge = tk.Frame(
                self.fleet_strip,
                bg=badge_bg,
                padx=6,
                pady=4,
                bd=0,
                highlightthickness=2 if state_text else 1,
                highlightbackground=badge_edge,
                highlightcolor=badge_edge,
            )
            title_row = tk.Frame(badge, bg=badge_bg)
            title_row.pack(side="left", padx=(0, 8))

            title = tk.Label(
                title_row,
                text=f"{spec.name} ({spec.length})",
                font=self.app.ui_font("small"),
                bg=badge_bg,
                fg=fg,
            )
            title.pack(side="left")

            if state_text:
                state_lbl = tk.Label(
                    title_row,
                    text=state_text,
                    font=self.app.ui_font("small"),
                    bg=state_bg,
                    fg=state_fg,
                    padx=6,
                    pady=1,
                )
                state_lbl.pack(side="left", padx=(8, 0))

            preview = tk.Frame(badge, bg=badge_bg)
            preview.pack(side="left")
            for cell_index in range(spec.length):
                mini = tk.Label(
                    preview,
                    text="",
                    width=2,
                    height=1,
                    bg=bg,
                    bd=0,
                    relief="flat",
                    highlightthickness=1,
                    highlightbackground=CELL_EDGE,
                    highlightcolor=CELL_EDGE,
                )
                mini.grid(row=0, column=cell_index, padx=1, pady=1)
            badge.grid(row=index // columns, column=index % columns, padx=4, pady=3, sticky="w")
            self.fleet_badges.append(badge)

        for col in range(columns):
            self.fleet_strip.grid_columnconfigure(col, weight=1)

    def _orientation_button_text(self, orientation: str) -> str:
        return f"Direction: {orientation}"

    def _placement_cell_image(self, size: int):
        image = self._placement_cell_images.get(size)
        if image is None:
            image = tk.PhotoImage(width=size, height=size)
            self._placement_cell_images[size] = image
        return image


    def _make_grid(self, player: int):
        frame = self.p1_grid if player == 1 else self.p2_grid  # Choose correct grid frame
        cells = self.p1_buttons if player == 1 else self.p2_buttons  # Choose correct button matrix

        tk.Label(frame, text="", width=4, bg=PANEL_BG).grid(row=0, column=0)  # Top-left empty corner

        # Column headers (A–J)
        for c in range(GRID_SIZE):
            tk.Label(
                frame,
                text=col_to_letter(c),  # Convert column index to letter
                font=self.app.ui_font("board_label"),
                bg=PANEL_BG,
                fg=TEXT_DARK,
            ).grid(row=0, column=c + 1)

        # Row headers + actual grid cells
        image = self._placement_cell_image(PLACEMENT_CELL_SIZE)
        for r in range(GRID_SIZE):
            tk.Label(
                frame,
                text=row_to_number(r),  # Convert row index to 1–10
                font=self.app.ui_font("board_label"),
                bg=PANEL_BG,
                fg=TEXT_DARK,
            ).grid(row=r + 1, column=0)

            for c in range(GRID_SIZE):
                cell = tk.Label(
                    frame,
                    text="",
                    image=image,
                    compound="center",
                    font=self.app.ui_font("body"),
                    bg=ACTIVE_BG,  # Default active color
                    relief="flat",
                    borderwidth=0,
                    highlightthickness=2,
                    highlightbackground=CELL_EDGE,
                    highlightcolor=CELL_EDGE,
                    padx=0,
                    pady=0,
                    fg=TEXT_DARK,
                    cursor="hand2",
                )
                cell.image = image
                cell.grid(row=r + 1, column=c + 1, padx=0, pady=0)

                # Click handler wrapper to preserve loop variables
                def handler(event, rr=r, cc=c, pp=player):
                    self.on_cell_click(pp, rr, cc)

                def hover_handler(_event, rr=r, cc=c, pp=player):
                    self.on_cell_hover(pp, rr, cc)

                def leave_handler(_event, rr=r, cc=c, pp=player):
                    self.on_cell_leave(pp, rr, cc)

                cell._click_handler = handler  # Store handler reference
                cell._hover_handler = hover_handler
                cell._leave_handler = leave_handler
                cell.bind("<Button-1>", cell._click_handler)  # Bind click event
                cell.bind("<Enter>", cell._hover_handler)
                cell.bind("<Motion>", cell._hover_handler)
                cell.bind("<Leave>", cell._leave_handler)

                cells[r][c] = cell  # Save widget reference in matrix

    def toggle_orientation(self):
        s = self.app.state
        s.placing_orientation = "V" if s.placing_orientation == "H" else "H"
        self.orient_btn.config(text=self._orientation_button_text(s.placing_orientation))
        self.refresh_ui()

    def on_cell_hover(self, player: int, row: int, col: int):
        s = self.app.state
        if player != s.placing_player:
            return
        if self._hover_target == (player, row, col):
            return
        self._clear_preview_overlay()
        self._hover_target = (player, row, col)
        self._paint_preview_overlay(player)

    def on_cell_leave(self, player: int, row: int, col: int):
        if self._hover_target != (player, row, col):
            return
        self._hover_target = None
        self._clear_preview_overlay()

    def on_randomize_fleet(self):
        s = self.app.state

        if s.num_ships is None:
            return

        ships_list = self._ships_list_for_player(s.placing_player)
        if ships_list and not messagebox.askyesno(
            "Randomize Fleet",
            "Replace the current fleet layout with a random one?",
        ):
            return

        self._set_random_fleet_for_player(s.placing_player)
        self.refresh_ui()

    def on_cell_click(self, player: int, row: int, col: int):
        s = self.app.state

        if player != s.placing_player:  # Prevent clicking wrong player's board
            return

        if s.num_ships is None:  # Safety check
            return

        board = self._board_for_player(player)  # Get correct board array
        ships_list = self._ships_list_for_player(player)  # Get correct ship list

        # If clicking an occupied cell → remove entire ship
        if board[row][col] == 1:
            for i, ship in enumerate(ships_list):
                if (row, col) in ship:
                    for rr, cc in ship:  # Clear all ship cells from board
                        board[rr][cc] = 0
                    ships_list.pop(i)  # Remove ship from list
                    self._hover_target = None
                    self._clear_preview_overlay()
                    self.refresh_ui()
                    return

        # Otherwise place the next required ship
        next_ship = self._next_required_ship(player)
        if next_ship is None:
            return

        length = next_ship.length
        orient = s.placing_orientation  # Current orientation

        if not self.can_place(board, row, col, length, orient):  # Validate placement
            messagebox.showerror("Invalid placement", "That ship doesn't fit there or overlaps another ship.")
            return

        coords = self.place_ship(board, row, col, length, orient)  # Place ship
        ships_list.append(coords)  # Add ship coordinates to state
        self._hover_target = None
        self._clear_preview_overlay()
        self.refresh_ui()


    def can_place(self, board, row, col, length, orient) -> bool:
        if orient == "H":
            if col + length - 1 >= GRID_SIZE:  # Right boundary check
                return False
            cells = [(row, col + i) for i in range(length)]
        else:
            if row + length - 1 >= GRID_SIZE:  # Bottom boundary check
                return False
            cells = [(row + i, col) for i in range(length)]

        return all(board[r][c] == 0 for r, c in cells)  # Overlap check


    def place_ship(self, board, row, col, length, orient):
        coords = []  # Will store ship coordinates

        if orient == "H":
            for i in range(length):
                board[row][col + i] = 1  # Mark board
                coords.append((row, col + i))  # Store coordinate
        else:
            for i in range(length):
                board[row + i][col] = 1
                coords.append((row + i, col))

        return coords  # Return full ship coordinate list

    def _bind_orientation_keys(self):
        try:
            self.app.bind_all("<Key-h>", lambda e: self.toggle_orientation())
            self.app.bind_all("<Key-H>", lambda e: self.toggle_orientation())
            self.app.bind_all("<Key-v>", lambda e: self.toggle_orientation())
            self.app.bind_all("<Key-V>", lambda e: self.toggle_orientation())
        except Exception:
            pass

    def _unbind_orientation_keys(self):
        try:
            self.app.unbind_all("<Key-h>")
            self.app.unbind_all("<Key-H>")
            self.app.unbind_all("<Key-v>")
            self.app.unbind_all("<Key-V>")
        except Exception:
            pass

    def _cancel_transition(self):
        if self._transition_job is not None:
            try:
                self.after_cancel(self._transition_job)
            except Exception:
                pass
            self._transition_job = None

    def _set_panel_state(self, panel, title, hint, active: bool, accent: str, text: str):
        border = accent if active else PANEL_BORDER
        panel.config(highlightbackground=border, highlightcolor=border)
        title.config(fg=accent if active else TEXT_DARK)
        hint.config(text=text, fg=TEXT_DARK if active else TEXT_MUTED)

    def _start_battle_transition(self):
        s = self.app.state
        ai_game = s.p2_ai_mode is not None

        if ai_game:
            self.status_lbl.config(text="Computer fleet ready. Starting battle.")
            self.hint_lbl.config(
                text="The computer placed its fleet automatically.",
                fg=TEXT_DARK,
            )
        else:
            self.status_lbl.config(text="All fleets locked in. Battle starts in 3 seconds.")
            self.hint_lbl.config(
                text="Pass the device to the next player while both boards are hidden.",
                fg=TEXT_DARK,
            )

        set_button_enabled(self.ready_btn, False)
        set_button_enabled(self.orient_btn, False)
        set_button_enabled(self.randomize_btn, False)

        self._render_board(self.p1_buttons, s.p1_board, show_ships=False, ship_color=P1_SHIP_BG, covered=True)
        self._render_board(self.p2_buttons, s.p2_board, show_ships=False, ship_color=P2_SHIP_BG, covered=True)
        self._set_active(self.p1_buttons, active=False)
        self._set_active(self.p2_buttons, active=False)
        self._unbind_orientation_keys()
        self._cancel_transition()
        delay = 400 if ai_game else 3000
        self._transition_job = self.after(delay, lambda: self.app.show_screen("BattleScreen"))


    def on_ready(self):
        s = self.app.state

        if s.num_ships is None:  # Safety check
            return

        ships_list = self._ships_list_for_player(s.placing_player)  # Get current player's ships

        # Ensure all required ships are placed
        required_ships = self._required_ship_count()
        if len(ships_list) < required_ships:
            remaining = required_ships - len(ships_list)
            messagebox.showinfo("Not ready", f"Place all ships first. Remaining: {remaining}")
            return

        if s.placing_player == 1:
            # If player 2 is AI, skip the human placement step entirely
            if s.p2_ai_mode is not None:
                self._place_ai_ships()           # generate random ships for the AI
                s.placing_player = 2             # pretend the AI just finished placing
                # fall through to the "player 2 finished" logic below
            else:
                # Switch to Player 2 placement phase for human opponent
                s.placing_player = 2
                s.placing_ship_len = 1  # Reset ship length tracker
                s.placing_orientation = "H"  # Reset orientation
                self.orient_btn.config(text=self._orientation_button_text("H"))  # Reset button label
                self.refresh_ui()
                return

        self._start_battle_transition()
        return
    

    def refresh_ui(self):
        s = self.app.state

        if s.num_ships is None:
            self.status_lbl.config(text="Placement")
            return

        ai_game = s.p2_ai_mode is not None
        player_label = "Your Fleet" if ai_game else f"Player {s.placing_player}"
        next_ship = self._next_required_ship(s.placing_player)

        if next_ship is not None:
            self.status_lbl.config(
                text=(
                    f"Placement — {player_label}: "
                    f"place {next_ship.name} ({next_ship.length} cells)"
                )
            )
            self.hint_lbl.config(
                text=(
                    "Big boats first. Hover to preview. H/V changes direction. Orange fits. Pink blocks."
                ),
                fg=TEXT_MUTED,
            )
        else:
            self.status_lbl.config(
                text=f"Placement — {player_label}: all ships placed. Click Ready."
            )
            self.hint_lbl.config(
                text="Check your fleet, then press Ready.",
                fg=TEXT_MUTED,
            )

        # Determine which board is active
        p1_turn = (s.placing_player == 1)
        p2_turn = (s.placing_player == 2) and not ai_game

        if ai_game:
            self.p1_title.config(text="Your Fleet")
            self.p2_title.config(text="Computer Fleet")
            p1_panel_text = "Your AI opponent will choose its fleet after you click Ready."
            p2_panel_text = "The computer fleet is chosen automatically."
        else:
            self.p1_title.config(text="Player 1 Fleet")
            self.p2_title.config(text="Player 2 Fleet")
            p1_panel_text = "Place boats now." if p1_turn else "Wait for Player 1."
            p2_panel_text = "Place boats now." if p2_turn else "Wait for Player 2."

        # Render boards
        self._render_board(self.p1_buttons, s.p1_board, show_ships=True,
                           ship_color=P1_SHIP_BG, covered=not p1_turn)

        self._render_board(self.p2_buttons, s.p2_board, show_ships=True,
                           ship_color=P2_SHIP_BG, covered=not p2_turn)
        self._preview_state = None
        self._render_placement_preview(player=1, cells=self.p1_buttons, board=s.p1_board, active=p1_turn)
        self._render_placement_preview(player=2, cells=self.p2_buttons, board=s.p2_board, active=p2_turn)

        # Enable/disable click interaction per board
        self._set_active(self.p1_buttons, active=p1_turn)
        self._set_active(self.p2_buttons, active=p2_turn)

        self._set_panel_state(
            self.p1_panel,
            self.p1_title,
            self.p1_hint,
            active=p1_turn,
            accent=P1_SHIP_BG,
            text=p1_panel_text,
        )
        self._set_panel_state(
            self.p2_panel,
            self.p2_title,
            self.p2_hint,
            active=p2_turn,
            accent=P2_SHIP_BG,
            text=p2_panel_text,
        )
        self._render_fleet_badges()


    def _render_board(self, cells, board, show_ships: bool, ship_color: str, covered: bool):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):

                if covered:  # Hide entire board when not player's turn
                    cells[r][c].config(bg=COVER_BG)
                    continue

                if board[r][c] == 1 and show_ships:
                    cells[r][c].config(bg=ship_color)  # Show ship color
                else:
                    cells[r][c].config(bg=ACTIVE_BG)  # Default empty cell color

    def _preview_cells(self, player: int):
        if self._hover_target is None or self._hover_target[0] != player:
            return [], None

        next_ship = self._next_required_ship(player)
        if next_ship is None:
            return [], None

        _, row, col = self._hover_target
        board = self._board_for_player(player)
        if board[row][col] == 1:
            return [], None

        orient = self.app.state.placing_orientation
        if orient == "H":
            if col + next_ship.length - 1 >= GRID_SIZE:
                return [(row, col)], False
            cells = [(row, col + i) for i in range(next_ship.length)]
        else:
            if row + next_ship.length - 1 >= GRID_SIZE:
                return [(row, col)], False
            cells = [(row + i, col) for i in range(next_ship.length)]

        valid = all(board[r][c] == 0 for r, c in cells)
        return cells, valid

    def _render_placement_preview(self, player: int, cells, board, active: bool):
        if not active:
            return

        preview_cells, valid = self._preview_cells(player)
        if not preview_cells:
            return

        preview_bg = PREVIEW_VALID_BG if valid else PREVIEW_INVALID_BG
        painted = []
        for row, col in preview_cells:
            if board[row][col] == 0:
                cells[row][col].config(bg=preview_bg)
                painted.append((row, col))
        if painted:
            self._preview_state = (player, painted)

    def _reset_preview_cell(self, player: int, row: int, col: int):
        board = self._board_for_player(player)
        cells = self.p1_buttons if player == 1 else self.p2_buttons
        ship_color = P1_SHIP_BG if player == 1 else P2_SHIP_BG
        cells[row][col].config(bg=ship_color if board[row][col] == 1 else ACTIVE_BG)

    def _clear_preview_overlay(self):
        if self._preview_state is None:
            return

        player, painted = self._preview_state
        for row, col in painted:
            self._reset_preview_cell(player, row, col)
        self._preview_state = None

    def _paint_preview_overlay(self, player: int):
        board = self._board_for_player(player)
        cells = self.p1_buttons if player == 1 else self.p2_buttons
        self._render_placement_preview(player=player, cells=cells, board=board, active=True)


    def _set_active(self, cells, active: bool):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if active:
                    cells[r][c].bind("<Button-1>", cells[r][c]._click_handler)  # Enable clicks
                    cells[r][c].bind("<Enter>", cells[r][c]._hover_handler)
                    cells[r][c].bind("<Motion>", cells[r][c]._hover_handler)
                    cells[r][c].bind("<Leave>", cells[r][c]._leave_handler)
                else:
                    cells[r][c].unbind("<Button-1>")  # Disable clicks
                    cells[r][c].unbind("<Enter>")
                    cells[r][c].unbind("<Motion>")
                    cells[r][c].unbind("<Leave>")

                    
    def _ships_list_for_player(self, player: int):
        s = self.app.state
        return s.p1_ships if player == 1 else s.p2_ships  # Return correct ship list


    def _board_for_player(self, player: int):
        s = self.app.state
        return s.p1_board if player == 1 else s.p2_board  # Return correct board array


    def _next_required_length(self, player: int) -> int:
        next_ship = self._next_required_ship(player)
        if next_ship is None:
            return self._required_ship_count() + 1
        return next_ship.length

    # --- AI helpers (new section) ---
    def _place_ai_ships(self):
        """Randomly place ships for player 2 when an AI mode is active."""
        self._set_random_fleet_for_player(2)

    def _set_random_fleet_for_player(self, player: int):
        s = self.app.state
        if s.num_ships is None:
            return

        board, ships = generate_random_fleet(s.num_ships)

        if player == 1:
            s.p1_board = board
            s.p1_ships = ships
        else:
            s.p2_board = board
            s.p2_ships = ships


class BattleScreen(tk.Frame):
    """
    Battle Phase:
    - Left: current player's own board (ships visible) + incoming marks (what opponent did to you)
    - Right: opponent board hidden except your shots (hit/miss shown)
    - Click selects a target cell (highlight only)
    - FIRE confirms the shot
    - Show big HIT/MISS/SINK, then switch turns after TURN_DELAY_MS
    - Scoreboard shows both players stats and ships remaining
    """

    def __init__(self, parent, app):
        super().__init__(parent, bg=SCREEN_BG)  # Initialize Tkinter Frame base class
        self.app = app  # Store reference to App (for state + screen switching)

        self.selected = None        # Stores selected target cell as (row, col)
        self.input_locked = False   # True while waiting during turn-delay / win-delay
        self._special_armed = False # When True, next FIRE will perform a 3x3 special shot
        self.awaiting_ai_turn = False

        self._ai_targets: list[tuple[int,int]] = []
        self._pending_after = None
        self._board_layout_mode = None
        self._intel_layout_mode = None
        self._battle_cell_size = None
        self._battle_cell_images = {}
        self._battle_compact_mode = None

        root = tk.Frame(self, bg=SCREEN_BG)  # Root container for this screen
        root.pack(fill="both", expand=True, padx=18, pady=12)
        self.root = root

        command_card = tk.Frame(root, bg=CARD_BG, padx=24, pady=18)
        style_panel(command_card, CARD_BG)
        command_card.pack(fill="x", pady=(0, 16))
        self.command_card = command_card

        self.turn_lbl = tk.Label(  # Shows "Player X's turn"
            command_card,
            text="",
            font=self.app.ui_font("section"),
            anchor="center",
            bg=TURN_BADGE_BG,
            fg=BUTTON_FG,
            padx=16,
            pady=8,
        )
        self.turn_lbl.pack(anchor="center", pady=(0, 12))

        self.result_lbl = tk.Label(  # Big feedback text: HIT / MISS / SINK / WINS
            command_card,
            text="",
            font=self.app.ui_font("result"),
            anchor="center",
            bg=CARD_BG,
            fg=TEXT_DARK,
        )
        self.result_lbl.pack(fill="x", pady=(6, 8))

        self.helper_lbl = tk.Label(
            command_card,
            text="Select a target and fire. Random picks an unused cell. Special fires a 3x3 shot.",
            font=self.app.ui_font("body"),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            anchor="center",
        )
        self.helper_lbl.pack(fill="x", pady=(0, 10))

        controls = tk.Frame(command_card, bg=CARD_BG)  # Row with FIRE, RANDOM and SPECIAL buttons
        controls.pack(fill="x", pady=(2, 0))
        self.controls_row = controls

        # Centered inner row so buttons are evenly spaced and centered on screen
        btn_row = tk.Frame(controls, bg=CARD_BG)
        btn_row.pack(anchor="center")
        self.button_row = btn_row

        btn_font = self.app.ui_font("button")
        btn_width = BATTLE_BUTTON_WIDTH

        self.fire_btn = make_action_button(  # Confirm shot button
            btn_row,
            text="FIRE",
            font=btn_font,
            width=btn_width,
            command=self.on_fire_pressed,
            bg=PRIMARY_BTN_BG,
        )
        self.fire_btn.pack(side="left", padx=12)

        # Random shot button: fires at a random unknown cell for current player
        self.random_btn = make_action_button(
            btn_row,
            text="RANDOM",
            font=btn_font,
            width=btn_width,
            command=self.on_random_pressed,
            bg=SECONDARY_BTN_BG,
        )
        self.random_btn.pack(side="left", padx=12)

        # Special area-shot button (3x3) with remaining counter
        self.special_btn = make_action_button(
            btn_row,
            text="SPECIAL",
            font=btn_font,
            width=btn_width,
            command=self.on_special_pressed,
            bg=ACCENT_BTN_BG,
        )
        self.special_btn.pack(side="left", padx=12)

        boards = tk.Frame(root, bg=SCREEN_BG)  # Container holding two boards
        boards.pack(fill="both", expand=True)
        self.boards_container = boards

        # Left panel: Own board
        left = tk.Frame(boards, bg=PANEL_BG, padx=10, pady=8)  # Container for own board
        style_panel(left, PANEL_BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.left_panel = left
        self.left_title = tk.Label(left, text="Your Board", font=self.app.ui_font("board_title"), bg=PANEL_BG, fg=TEXT_DARK)
        self.left_title.pack(pady=(0, 8))
        self.left_subtitle = tk.Label(left, text="Incoming fire and fleet status", font=self.app.ui_font("small"), bg=PANEL_BG, fg=TEXT_MUTED)
        self.left_subtitle.pack(pady=(0, 10))
        self.own_grid = tk.Frame(left, bg=PANEL_BG)  # Frame that holds the own board grid
        self.own_grid.pack()

        # Right panel: Target board
        right = tk.Frame(boards, bg=PANEL_BG, padx=10, pady=8)  # Container for opponent board
        style_panel(right, PANEL_BG)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.right_panel = right
        self.right_title = tk.Label(right, text="Opponent Board", font=self.app.ui_font("board_title"), bg=PANEL_BG, fg=TEXT_DARK)
        self.right_title.pack(pady=(0, 8))
        self.right_subtitle = tk.Label(right, text="Choose a cell to fire on enemy waters", font=self.app.ui_font("small"), bg=PANEL_BG, fg=TEXT_MUTED)
        self.right_subtitle.pack(pady=(0, 10))
        self.target_grid = tk.Frame(right, bg=PANEL_BG)  # Frame holding target board grid
        self.target_grid.pack()

        # 2D matrices holding cell widgets
        self.own_cells = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]  # Own board widgets
        self.target_cells = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]  # Target board widgets

        self._make_grid(self.own_grid, self.own_cells, clickable=False)  # Build own board (no clicks)
        self._make_grid(self.target_grid, self.target_cells, clickable=True)  # Build target board (clickable)

        intel_row = tk.Frame(root, bg=SCREEN_BG)
        intel_row.pack(fill="x", pady=(14, 0))
        self.intel_row = intel_row

        p1_card = tk.Frame(intel_row, bg=CARD_BG, padx=14, pady=12)
        style_panel(p1_card, CARD_BG)
        p1_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.p1_card = p1_card
        tk.Label(p1_card, text="Player 1 Intel", font=self.app.ui_font("small"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.p1_stats_lbl = tk.Label(
            p1_card,
            text="",
            font=self.app.ui_font("body"),
            justify="left",
            anchor="w",
            bg=CARD_BG,
            fg=TEXT_DARK,
        )
        self.p1_stats_lbl.pack(fill="x", pady=(8, 0))

        p2_card = tk.Frame(intel_row, bg=CARD_BG, padx=14, pady=12)
        style_panel(p2_card, CARD_BG)
        p2_card.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.p2_card = p2_card
        tk.Label(p2_card, text="Player 2 Intel", font=self.app.ui_font("small"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.p2_stats_lbl = tk.Label(
            p2_card,
            text="",
            font=self.app.ui_font("body"),
            justify="left",
            anchor="w",
            bg=CARD_BG,
            fg=TEXT_DARK,
        )
        self.p2_stats_lbl.pack(fill="x", pady=(8, 0))

        history_card = tk.Frame(root, bg=CARD_BG, padx=14, pady=12)
        style_panel(history_card, CARD_BG)
        history_card.pack(fill="x", pady=(10, 0))
        self.history_card = history_card
        tk.Label(history_card, text="Recent Moves", font=self.app.ui_font("small"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.history_lbl = tk.Label(
            history_card,
            text="No shots fired yet.",
            font=self.app.ui_font("body"),
            justify="left",
            anchor="w",
            bg=CARD_BG,
            fg=TEXT_DARK,
        )
        self.history_lbl.pack(fill="x", pady=(8, 0))

        # --- Shot blackout (used after a valid shot to briefly cover BOTH boards for hand-off) ---
        # Implemented by temporarily rendering both grids with COVER_BG (same idea as PlacementScreen).
        self._shot_blackout_active = False
        self._shot_blackout_job = None
        self._shot_blackout_hide_job = None
        self.after_idle(self._update_responsive_layout)


    def tkraise(self, aboveThis=None):
        # Reset per-game / per-entry UI state when this screen is shown
        self._cancel_pending_after()
        self._cancel_shot_blackout()
        self._end_shot_blackout()
        self.selected = None  # Clear any previous selection
        self.input_locked = False  # Allow input again
        self.awaiting_ai_turn = False
        self._set_result("")

        # clear the AI hunting queue when a new battle begins
        self._ai_targets.clear()
        self._special_armed = False

        self._update_responsive_layout()
        self.refresh_ui()  # Re-render boards + scoreboard based on current GameState
        super().tkraise(aboveThis)  # Bring this screen to the front

    def on_hide(self):
        self._cancel_pending_after()
        self._cancel_shot_blackout()
        self.awaiting_ai_turn = False

    def on_layout_change(self, _scale=1.0):
        self._update_responsive_layout()

    def _update_responsive_layout(self):
        self._apply_battle_board_layout()
        self._apply_battle_cell_size()
        self._apply_battle_aux_layout()
        self._refresh_wraps()

    def _apply_battle_board_layout(self):
        compact = self._is_compact_battle_mode()
        mode = "compact_side_by_side" if compact else "side_by_side"
        if mode == self._board_layout_mode:
            return

        self._board_layout_mode = mode
        self.left_panel.pack_forget()
        self.right_panel.pack_forget()

        panel_pad = 8 if compact else 12
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, panel_pad))
        self.right_panel.pack(side="left", fill="both", expand=True, padx=(panel_pad, 0))

    def _apply_battle_cell_size(self):
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 920 or height < 700:
            cell_size = 20
        elif width < 1240 or height < 860:
            cell_size = 24
        else:
            cell_size = BATTLE_CELL_SIZE

        if cell_size == self._battle_cell_size:
            return

        self._battle_cell_size = cell_size
        image = self._battle_cell_image(cell_size)

        for cells in (self.own_cells, self.target_cells):
            for row in cells:
                for cell in row:
                    cell.config(image=image)
                    cell.image = image
                    cell.grid_configure(padx=0, pady=0)

    def _is_compact_battle_mode(self) -> bool:
        return self.winfo_width() < 1100 or self.winfo_height() < 760

    def _set_optional_widget(self, widget: tk.Widget, visible: bool, **pack_options):
        is_visible = bool(widget.winfo_manager())
        if visible and not is_visible:
            widget.pack(**pack_options)
        elif not visible and is_visible:
            widget.pack_forget()

    def _apply_battle_aux_layout(self):
        compact = self._is_compact_battle_mode()
        if compact == self._battle_compact_mode:
            return

        self._battle_compact_mode = compact

        self.command_card.config(padx=16 if compact else 24, pady=12 if compact else 18)
        self.turn_lbl.config(padx=12 if compact else 16, pady=6 if compact else 8)
        self.fire_btn.config(width=8 if compact else BATTLE_BUTTON_WIDTH)
        self.random_btn.config(width=8 if compact else BATTLE_BUTTON_WIDTH)
        self.special_btn.config(width=8 if compact else BATTLE_BUTTON_WIDTH)

        self._set_optional_widget(
            self.intel_row,
            not compact,
            fill="x",
            pady=(14, 0),
        )
        self._set_optional_widget(
            self.history_card,
            not compact,
            fill="x",
            pady=(10, 0),
        )


    def _make_grid(self, frame, cells, clickable: bool):
        tk.Label(frame, text="", width=4, bg=PANEL_BG).grid(row=0, column=0)  # Top-left empty corner (aligns headers)

        # Column headers A–J
        for c in range(GRID_SIZE):
            tk.Label(
                frame,
                text=col_to_letter(c),  # Convert column index to A–J
                font=self.app.ui_font("board_label"),
                bg=PANEL_BG,
                fg=TEXT_DARK,
            ).grid(row=0, column=c + 1)  # +1 because col 0 is reserved for row labels

        # Row headers 1–10 + create grid cells
        image = self._battle_cell_image(BATTLE_CELL_SIZE)
        for r in range(GRID_SIZE):
            tk.Label(
                frame,
                text=row_to_number(r),  # Convert row index to 1–10
                font=self.app.ui_font("board_label"),
                bg=PANEL_BG,
                fg=TEXT_DARK,
            ).grid(row=r + 1, column=0)  # +1 because row 0 is reserved for column labels

            for c in range(GRID_SIZE):
                cell = tk.Label(
                    frame,
                    text="",
                    image=image,
                    compound="center",
                    bg=ACTIVE_BG,  # Default background
                    relief="flat",
                    borderwidth=0,
                    highlightthickness=2,
                    highlightbackground=CELL_EDGE,
                    highlightcolor=CELL_EDGE,
                    font=self.app.ui_font("battle_cell"),
                    padx=0,
                    pady=0,
                    fg=TEXT_DARK,
                    cursor="hand2" if clickable else "arrow",
                )
                cell.image = image
                cell.grid(row=r + 1, column=c + 1, padx=0, pady=0)  # Place cell widget

                if clickable:  # Only target grid should be clickable
                    def handler(event, rr=r, cc=c):
                        self.on_select(rr, cc)  # Save selection and refresh UI

                    cell._click_handler = handler  # Store handler so we can rebind later
                    cell.bind("<Button-1>", cell._click_handler)  # Bind click event

                cells[r][c] = cell  # Store the widget in the 2D matrix

    def _controls_locked(self) -> bool:
        return self.input_locked or self.awaiting_ai_turn

    def _battle_cell_image(self, size: int):
        image = self._battle_cell_images.get(size)
        if image is None:
            image = tk.PhotoImage(width=size, height=size)
            self._battle_cell_images[size] = image
        return image

    def _set_result(self, text: str, tone: str = "neutral"):
        color = RESULT_COLORS.get(tone, TEXT_DARK)
        self.result_lbl.config(text=text, fg=color)

    def _coord_label(self, row: int, col: int) -> str:
        return f"{col_to_letter(col)}{row_to_number(row)}"

    def _log_move(self, text: str):
        history = self.app.state.move_history
        history.append(text)
        if len(history) > 8:
            del history[:-8]

    def _refresh_wraps(self):
        width = max(320, self.winfo_width() - 120)
        self.result_lbl.config(wraplength=width)
        self.helper_lbl.config(wraplength=width)
        self.history_lbl.config(wraplength=width)

    def _cancel_pending_after(self):
        if self._pending_after is not None:
            try:
                self.after_cancel(self._pending_after)
            except Exception:
                pass
            self._pending_after = None

    def _schedule_pending(self, delay_ms: int, callback):
        self._cancel_pending_after()
        self._pending_after = self.after(delay_ms, callback)

    def _show_winner(self, winner_text: str):
        win_screen = self.app.screens["WinScreen"]
        win_screen.set_winner(winner_text)
        win_screen.set_stats()
        self.app.show_screen("WinScreen")

    def _schedule_winner(self, winner_num: int):
        winner_text = f"PLAYER {winner_num} WINS!"
        self.input_locked = True
        self.awaiting_ai_turn = False
        self.selected = None
        self._set_result(winner_text, tone="good")
        self.refresh_ui()
        self._schedule_pending(1500, lambda: self._show_winner(winner_text))

    def _update_controls(self):
        locked = self._controls_locked()
        has_selection = self.selected is not None
        specials_left = 0
        if self.app.state.current_turn == 1:
            specials_left = self.app.state.p1_specials
        else:
            specials_left = self.app.state.p2_specials

        set_button_enabled(self.fire_btn, not locked and has_selection)
        set_button_enabled(self.random_btn, not locked and not self._special_armed)
        set_button_enabled(self.special_btn, specials_left > 0 and not locked)

        if self._special_armed:
            self.special_btn.config(text=f"ARMED x{specials_left}")
        else:
            self.special_btn.config(text=f"SPECIAL x{specials_left}")


    def on_select(self, row: int, col: int):
        if self._controls_locked():  # Prevent selecting during turn switch delay / AI turn / win delay
            return

        self.selected = (row, col)  # Store current target selection
        self.refresh_ui()  # Refresh to apply highlight on selected target cell


    def on_random_pressed(self):
        """Select a random UNKNOWN cell for the current player and fire."""
        if self._controls_locked():
            return
        s = self.app.state
        turn = s.current_turn
        shots = s.p1_shots if turn == 1 else s.p2_shots
        unknowns = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if shots[r][c] == UNKNOWN]
        if not unknowns:
            self._set_result("NO TARGETS LEFT", tone="warn")
            return
        import random
        r, c = random.choice(unknowns)
        self.selected = (r, c)
        self.refresh_ui()
        self.on_fire_pressed()


    def on_special_pressed(self):
        """Arm or disarm the 3x3 special shot.

        When armed, the target board will show a 3x3 preview around the
        selected cell. The next `FIRE` press will execute the special shot.
        """
        if self._controls_locked():
            return
        s = self.app.state
        turn = s.current_turn
        remaining = s.p1_specials if turn == 1 else s.p2_specials
        if remaining <= 0:
            self._set_result("NO SPECIALS LEFT", tone="warn")
            return

        # Toggle armed state; do NOT require a prior selection. User can
        # press SPECIAL first, then click a cell to place the 3x3 preview.
        if not self._special_armed:
            self._special_armed = True
            self._set_result("SPECIAL ARMED", tone="neutral")
        else:
            # disarm
            self._special_armed = False
            self._set_result("SPECIAL CANCELED", tone="neutral")

        self.refresh_ui()

    def on_fire_pressed(self):
        if self._controls_locked():  # Block firing while locked (during delay)
            return None

        if self.selected is None:  # Must select a target before firing
            self._set_result("SELECT A TARGET", tone="warn")
            return None

        s = self.app.state  # Shortcut to shared GameState
        row, col = self.selected  # Target cell
        turn = s.current_turn  # Whose turn (1 or 2)

        # If a special shot is armed, perform an area shot instead of single-shot
        if self._special_armed:
            # Ensure player has specials remaining
            remaining = s.p1_specials if turn == 1 else s.p2_specials
            if remaining <= 0:
                self._set_result("NO SPECIALS LEFT", tone="warn")
                self._special_armed = False
                return None

            # Choose attacker/defender structures based on current turn
            if turn == 1:
                attacker_shots = s.p1_shots
                defender_incoming = s.p2_incoming
                defender_ships = s.p2_ships
                defender_hits = s.p2_hits
                winner_num = 1
            else:
                attacker_shots = s.p2_shots
                defender_incoming = s.p1_incoming
                defender_ships = s.p1_ships
                defender_hits = s.p1_hits
                winner_num = 2

            # Execute area shot
            summary = fire_area_shot(attacker_shots, defender_incoming, defender_ships, defender_hits, row, col)

            # consume a special
            if turn == 1:
                s.p1_specials -= 1
            else:
                s.p2_specials -= 1

            hits = summary.get("hits", 0)
            sinks = summary.get("sinks", 0)
            misses = summary.get("misses", 0)
            already = summary.get("already", 0)

            # Show aggregated result
            result_text = f"SPECIAL - Hits: {hits} | Sinks: {sinks} | Misses: {misses}"
            if already:
                result_text += f" | Already: {already}"
            tone = "good" if hits or sinks else "warn"
            self._set_result(result_text, tone=tone)
            self._log_move(
                f"P{turn} SPECIAL {self._coord_label(row, col)}  H:{hits} S:{sinks} M:{misses}"
            )

            # reset special armed state
            self._special_armed = False

            self.selected = None
            self.refresh_ui()

            if s.p2_ai_mode is None:
                self._schedule_shot_blackout(1500, 1500)

            # Check win condition
            if ships_remaining(defender_ships, defender_hits) == 0:
                self._schedule_winner(winner_num)
                return "area"

            # normal turn-switch after area shot
            self.input_locked = True
            if s.p2_ai_mode is None:
                self._schedule_pending(TURN_DELAY_MS, self._switch_turn)
            else:
                self._switch_turn()

            return "area"

        # Choose attacker/defender structures based on current turn
        if turn == 1:
            attacker_shots = s.p1_shots  # What P1 has fired at P2 (public marks)
            defender_incoming = s.p2_incoming  # What P2 has received from P1 (for P2 own-board view)
            defender_ships = s.p2_ships  # P2 ship coordinate lists
            defender_hits = s.p2_hits  # P2 hit set
            winner_num = 1  # If defender loses all ships, attacker is player 1
        else:
            attacker_shots = s.p2_shots  # What P2 has fired at P1
            defender_incoming = s.p1_incoming  # What P1 has received from P2
            defender_ships = s.p1_ships  # P1 ships
            defender_hits = s.p1_hits  # P1 hits
            winner_num = 2  # If defender loses all ships, attacker is player 2

        # Use rules engine to resolve the shot and update boards/sets
        result = fire_shot(
            attacker_shots,      # Attacker's shot-mark board
            defender_incoming,   # Defender's incoming-mark board
            defender_ships,      # Defender ships (list of coord lists)
            defender_hits,       # Defender hit set (tracks all hit coords)
            row,                 # Target row
            col                  # Target col
        )

        # If this cell was already fired on, do not proceed
        if result == "already":
            self._set_result("ALREADY SHOT", tone="warn")
            return result

        # Show HIT/MISS/SINK immediately
        if result == "miss":
            self._set_result("MISS", tone="neutral")
        else:
            self._set_result(result.upper(), tone="good")
        self._log_move(f"P{turn} {self._coord_label(row, col)} {result.upper()}")

        self.selected = None  # Clear current target selection
        self.refresh_ui()  # Repaint boards so shot mark appears immediately
        # 1.5s after a valid shot, briefly black out the screen for hand-off
        # but when playing against any AI we skip the transition entirely
        if s.p2_ai_mode is None:
            self._schedule_shot_blackout(1500, 1500)

        # Check win condition: if defender has 0 ships remaining, attacker wins
        if ships_remaining(defender_ships, defender_hits) == 0:
            self._schedule_winner(winner_num)
            return result

        # If no win, lock input and schedule turn switch
        self.input_locked = True  # Lock input during delay
        if s.p2_ai_mode is None:
            # normal two-player: wait a moment before handing control
            self._schedule_pending(TURN_DELAY_MS, self._switch_turn)
        else:
            # against AI: skip blackout/delay and switch immediately
            self._switch_turn()
        return result

    def _schedule_shot_blackout(self, delay_ms: int = 1500, duration_ms: int = 1500):
        """Wait `delay_ms` after a valid shot, then cover BOTH boards for `duration_ms`."""
        self._cancel_shot_blackout()
        self._shot_blackout_job = self.after(delay_ms, lambda: self._start_shot_blackout(duration_ms))

    def _cancel_shot_blackout(self):
        if self._shot_blackout_job is not None:
            try:
                self.after_cancel(self._shot_blackout_job)
            except Exception:
                pass
            self._shot_blackout_job = None

        if self._shot_blackout_hide_job is not None:
            try:
                self.after_cancel(self._shot_blackout_hide_job)
            except Exception:
                pass
            self._shot_blackout_hide_job = None

    def _start_shot_blackout(self, duration_ms: int = 1500):
        """Cover both boards (own + target) using COVER_BG for local hand-off."""
        if self._shot_blackout_active:
            return

        self._shot_blackout_active = True
        self._render_blackout_boards()

        # End blackout after duration
        self._shot_blackout_hide_job = self.after(duration_ms, self._end_shot_blackout)

    def _end_shot_blackout(self):
        """End board blackout and re-render normal UI."""
        self._shot_blackout_active = False
        self._shot_blackout_hide_job = None
        self.refresh_ui()

    def _render_blackout_boards(self):
        """Render both grids as covered (no marks, no selection, no clicks)."""
        # Cover own grid
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self.own_cells[r][c].config(bg=COVER_BG, fg="black", text="")

        # Cover target grid and disable selection clicks
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self.target_cells[r][c].config(bg=COVER_BG, fg="black", text="")
                self.target_cells[r][c].unbind("<Button-1>")

    def _switch_turn(self):
        s = self.app.state  # Shortcut to shared GameState

        self._cancel_pending_after()
        s.current_turn = 2 if s.current_turn == 1 else 1  # Flip turn: 1 -> 2, 2 -> 1

        self._set_result("")  # Clear result message (HIT/MISS/SINK) for next player
        self.input_locked = False  # Re-enable input now that delay is over
        self.awaiting_ai_turn = s.p2_ai_mode in ("easy", "medium", "hard") and s.current_turn == 2
        self.selected = None

        self.refresh_ui()  # Re-render boards + scoreboard for new player view

        if self.awaiting_ai_turn:
            # small pause so the player can see the turn label update
            self._schedule_pending(500, self._ai_take_turn)


    def refresh_ui(self):
        s = self.app.state  # Shared GameState
        self._refresh_wraps()
        turn = s.current_turn  # Current player turn (1 or 2)
        badge_bg = P1_SHIP_BG if turn == 1 else P2_SHIP_BG
        self.turn_lbl.config(text=f"Player {turn}'s turn", bg=badge_bg, fg="#072033")  # Update top label
        # If we're in the post-shot blackout window, cover both boards and stop.
        if self._shot_blackout_active:
            self._render_blackout_boards()
            self._update_controls()
            return

        # Choose what the current player sees, based on whose turn it is
        # When a human is playing against an AI we never want to expose the
        # AI's ship layout. 
        if s.p2_ai_mode is not None:
            # AI game: left side always P1, right side always P1 shots
            own_ship_board = s.p1_board
            own_incoming = s.p1_incoming
            own_color = P1_SHIP_BG
            own_ships = s.p1_ships
            own_hits = s.p1_hits

            my_shots = s.p1_shots
            target_ships = s.p2_ships
            target_hits = s.p2_hits
            self.left_title.config(text="Your Fleet")
            self.right_title.config(text="Target Grid")
            self.left_subtitle.config(text="Incoming fire and fleet status")
            self.right_subtitle.config(text="Choose a cell to fire on enemy waters")

            p1_stats = self._stats(s.p1_shots, s.p1_ships, s.p1_hits)
            p2_stats = self._stats(s.p2_shots, s.p2_ships, s.p2_hits)
        else:
            # normal two‑player game follows previous logic
            if turn == 1:
                own_ship_board = s.p1_board      # Player 1 ship layout (1s where ships are)
                own_incoming = s.p1_incoming     # What Player 2 has done to Player 1 (hit/miss marks)
                own_color = P1_SHIP_BG           # Color to show P1 ships
                own_ships = s.p1_ships
                own_hits = s.p1_hits

                my_shots = s.p1_shots            # What P1 has fired at P2 (unknown/miss/hit)
                target_ships = s.p2_ships
                target_hits = s.p2_hits
                self.left_title.config(text="Player 1 Fleet")
                self.right_title.config(text="Player 1 Targeting")
                self.left_subtitle.config(text="Incoming fire and fleet status")
                self.right_subtitle.config(text="Select a target on Player 2's ocean")

                p1_stats = self._stats(s.p1_shots, s.p1_ships, s.p1_hits)  # P1 stats
                p2_stats = self._stats(s.p2_shots, s.p2_ships, s.p2_hits)  # P2 stats
            else:
                own_ship_board = s.p2_board      # Player 2 ship layout
                own_incoming = s.p2_incoming     # What Player 1 has done to Player 2
                own_color = P2_SHIP_BG           # Color to show P2 ships
                own_ships = s.p2_ships
                own_hits = s.p2_hits

                my_shots = s.p2_shots            # What P2 has fired at P1
                target_ships = s.p1_ships
                target_hits = s.p1_hits
                self.left_title.config(text="Player 2 Fleet")
                self.right_title.config(text="Player 2 Targeting")
                self.left_subtitle.config(text="Incoming fire and fleet status")
                self.right_subtitle.config(text="Select a target on Player 1's ocean")

                p1_stats = self._stats(s.p1_shots, s.p1_ships, s.p1_hits)  # P1 stats
                p2_stats = self._stats(s.p2_shots, s.p2_ships, s.p2_hits)  # P2 stats

        # Render left board (ships visible + incoming marks)
        own_sunk_cells = sunk_ship_cells(own_ships, own_hits)
        target_sunk_cells = sunk_ship_cells(target_ships, target_hits)
        self._render_own_board(self.own_cells, own_ship_board, own_incoming, own_color, own_sunk_cells)

        # Render right board (opponent ships hidden except your shots)
        self._render_target_board(self.target_cells, my_shots, target_sunk_cells)

        # Build ship-hit counter text for scoreboard
        p1_ship_counters = ship_hit_counters(s.p1_ships, s.p1_hits)  # List like ["1/1", "0/2", ...]
        p2_ship_counters = ship_hit_counters(s.p2_ships, s.p2_hits)

        p1_ship_line = ", ".join(p1_ship_counters) if p1_ship_counters else "-"  # Join or show "-"
        p2_ship_line = ", ".join(p2_ship_counters) if p2_ship_counters else "-"

        self.p1_stats_lbl.config(
            text=(
                f"Shots fired: {p1_stats['shots']}\n"
                f"Hits landed: {p1_stats['hits']}\n"
                f"Misses: {p1_stats['misses']}\n"
                f"Ships afloat: {p1_stats['ships']}\n"
                f"Ship damage: {p1_ship_line}"
            )
        )
        self.p2_stats_lbl.config(
            text=(
                f"Shots fired: {p2_stats['shots']}\n"
                f"Hits landed: {p2_stats['hits']}\n"
                f"Misses: {p2_stats['misses']}\n"
                f"Ships afloat: {p2_stats['ships']}\n"
                f"Ship damage: {p2_ship_line}"
            )
        )
        history_lines = [f"• {entry}" for entry in reversed(s.move_history[-5:])]
        self.history_lbl.config(text="\n".join(history_lines) if history_lines else "Awaiting the opening shot.")
        if self.awaiting_ai_turn:
            self.helper_lbl.config(text="Computer is choosing a target...", fg=TEXT_MUTED)
        elif self._special_armed:
            self.helper_lbl.config(text="Special armed: pick the center of the 3x3 blast zone.", fg=TEXT_DARK)
        else:
            self.helper_lbl.config(
                text="Select a target and fire. Random picks an unused cell. Special fires a 3x3 shot.",
                fg=TEXT_MUTED,
            )

        # Highlight selected target cell (single cell) or 3x3 preview when special armed
        if self.selected is not None and not self._controls_locked():
            r, c = self.selected
            if getattr(self, "_special_armed", False):
                # show 3x3 preview outline (only for UNKNOWN cells)
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < GRID_SIZE and 0 <= cc < GRID_SIZE:
                            if my_shots[rr][cc] == UNKNOWN:
                                self.target_cells[rr][cc].config(bg=HIGHLIGHT_BG)
            else:
                if my_shots[r][c] == UNKNOWN:
                    self.target_cells[r][c].config(bg=HIGHLIGHT_BG)  # Yellow highlight

        # Disable or restore click bindings on target board depending on lock state
        if self._controls_locked():
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    self.target_cells[r][c].unbind("<Button-1>")  # Prevent selecting during delay
        else:
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    self.target_cells[r][c].bind("<Button-1>", self.target_cells[r][c]._click_handler)  # Re-enable selection

        self._update_controls()


    def _render_battle_cell(self, cell, bg: str, fg: str, text: str, edge: str = CELL_EDGE):
        cell.config(
            bg=bg,
            fg=fg,
            text=text,
            highlightbackground=edge,
            highlightcolor=edge,
        )

    def _render_own_board(self, cells, ship_board, incoming_board, ship_color: str, sunk_cells):
        """
        Own view:
        - ships are colored
        - incoming MISS -> gray 'O'
        - incoming HIT  -> red  'X'
        """
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                coord = (r, c)

                # Base layer: show ships (if a ship exists in ship_board)
                if coord in sunk_cells:
                    self._render_battle_cell(cells[r][c], SUNK_BG, "white", "X", edge=SUNK_EDGE)
                elif ship_board[r][c] == 1:
                    self._render_battle_cell(cells[r][c], ship_color, "white", "")  # Ship cell (colored)
                else:
                    self._render_battle_cell(cells[r][c], ACTIVE_BG, "black", "")  # Empty cell (white)

                # Overlay layer: show incoming marks (what opponent did to you)
                v = incoming_board[r][c]  # Cell value: UNKNOWN / MISS / HIT
                if v == MISS:
                    self._render_battle_cell(cells[r][c], MISS_BG, "black", "O")  # Miss mark
                elif v == HIT:
                    if coord in sunk_cells:
                        self._render_battle_cell(cells[r][c], SUNK_BG, "white", "X", edge=SUNK_EDGE)
                    else:
                        self._render_battle_cell(cells[r][c], HIT_BG, "white", "X")  # Hit mark


    def _render_target_board(self, cells, shots_board, sunk_cells):
        """
        Target view:
        - opponent ships hidden (white)
        - your shots show:
          MISS -> gray 'O'
          HIT  -> red  'X'
        """
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                v = shots_board[r][c]  # Cell value: UNKNOWN / MISS / HIT
                coord = (r, c)

                if v == UNKNOWN:
                    self._render_battle_cell(cells[r][c], ACTIVE_BG, "black", "")  # Not shot yet
                elif v == MISS:
                    self._render_battle_cell(cells[r][c], MISS_BG, "black", "O")  # Missed shot
                else:
                    if coord in sunk_cells:
                        self._render_battle_cell(cells[r][c], SUNK_BG, "white", "X", edge=SUNK_EDGE)
                    else:
                        self._render_battle_cell(cells[r][c], HIT_BG, "white", "X")  # Hit shot


    def _ai_take_turn(self):
        """AI chooses and fires a shot according to current difficulty setting."""

        import random
        s = self.app.state
        mode = s.p2_ai_mode
        self._cancel_pending_after()
        self.awaiting_ai_turn = False

        # Hard mode: pre-populate targets with all P1 ship coordinates on first turn
        if mode == "hard" and not self._ai_targets:
            for ship in s.p1_ships:
                for coord in ship:
                    self._ai_targets.append(coord)

        # helper to pop a valid target from queue
        def pop_target():
            while self._ai_targets:
                rr, cc = self._ai_targets.pop(0)
                if 0 <= rr < GRID_SIZE and 0 <= cc < GRID_SIZE and s.p2_shots[rr][cc] == UNKNOWN:
                    return rr, cc
            return None

        rcc = None
        if mode in ("medium", "hard"):
            rcc = pop_target()  # try hunting first (or ship targeting for hard mode)
        if rcc is None:
            # fall back to random unknown cell
            unknowns = [
                (r, c)
                for r in range(GRID_SIZE)
                for c in range(GRID_SIZE)
                if s.p2_shots[r][c] == UNKNOWN
            ]
            if not unknowns:
                return
            rcc = random.choice(unknowns)

        r, c = rcc
        self.selected = (r, c)
        self.refresh_ui()
        result = self.on_fire_pressed()

        # medium mode: if we hit (but not sink) add neighbors for next turns,
        # if we sunk, clear the queue so we start over random again
        if mode == "medium" and result:
            if result == "hit":
                for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                        if s.p2_shots[nr][nc] == UNKNOWN:
                            self._ai_targets.append((nr, nc))
            elif result == "sink":
                self._ai_targets.clear()

    def _stats(self, shots_board, ships_list, hits_set):
        hits = sum(  # Count all HIT values inside the shots_board
            1
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if shots_board[r][c] == HIT
        )

        misses = sum(  # Count all MISS values inside the shots_board
            1
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if shots_board[r][c] == MISS
        )

        shots = hits + misses  # Total shots fired = hits + misses

        ships_left = ships_remaining(ships_list, hits_set)  # Count ships not fully sunk yet

        return {"shots": shots, "hits": hits, "misses": misses, "ships": ships_left}  # Pack into a dict


class WinScreen(tk.Frame):  # Final screen: show winner + stats + play again / exit
    def __init__(self, parent, app):
        super().__init__(parent, bg=SCREEN_BG)  # Initialize Frame base class
        self.app = app  # Reference to App (for new_game + destroy + state)

        card = tk.Frame(self, bg=CARD_BG, padx=30, pady=26)
        style_panel(card, CARD_BG)
        card.place(relx=0.5, rely=0.5, anchor="center")
        self.card = card

        self.title_lbl = tk.Label(card, text="Game Over", font=self.app.ui_font("title"), bg=CARD_BG, fg=TEXT_DARK)
        self.title_lbl.pack(pady=(0, 16))  # Add vertical spacing

        self.winner_lbl = tk.Label(card, text="", font=self.app.ui_font("section"), bg=CARD_BG, fg=TEXT_DARK)
        self.winner_lbl.pack(pady=(0, 10))

        self.summary_lbl = tk.Label(
            card,
            text="Review the final stats below or start a rematch.",
            font=self.app.ui_font("body"),
            bg=CARD_BG,
            fg=TEXT_MUTED,
        )
        self.summary_lbl.pack(pady=(0, 18))

        stats_card = tk.Frame(card, bg=PANEL_BG, padx=24, pady=20)
        style_panel(stats_card, PANEL_BG)
        stats_card.pack(pady=10)

        self.stats_lbl = tk.Label(
            stats_card,
            text="",
            font=self.app.ui_font("body"),
            justify="left",
            bg=PANEL_BG,
            fg=TEXT_DARK,
            anchor="w",
        )
        self.stats_lbl.pack()

        btn_row = tk.Frame(card, bg=CARD_BG)  # Container holding both buttons
        btn_row.pack(pady=25)

        play_btn = make_action_button(  # Restart the game
            btn_row,
            text="Play Again",
            font=self.app.ui_font("button"),
            width=18,
            command=self.play_again,  # Calls play_again()
            bg=PRIMARY_BTN_BG,
        )
        play_btn.grid(row=0, column=0, padx=10)

        exit_btn = make_action_button(  # Close the entire app
            btn_row,
            text="Exit",
            font=self.app.ui_font("button"),
            width=18,
            command=self.exit_game,  # Calls exit_game()
            bg=ACCENT_BTN_BG,
        )
        exit_btn.grid(row=0, column=1, padx=10)

    def on_layout_change(self, _scale=1.0):
        wrap = max(360, min(760, self.winfo_width() - 220))
        self.summary_lbl.config(wraplength=wrap)
        self.stats_lbl.config(wraplength=wrap)

    def set_winner(self, winner_text: str):
        self.winner_lbl.config(text=winner_text)  # Update winner label text

    def play_again(self):
        self.app.new_game()  # Reset state and return to WelcomeScreen

    def exit_game(self):
        self.app.destroy()  # Close the Tk window and exit the program

    def set_stats(self):
        s = self.app.state  # Shortcut to shared GameState

        def counts(shots_board):
            # Count HIT and MISS values in a shots board, then compute accuracy
            hits = sum(
                1 for r in range(GRID_SIZE) for c in range(GRID_SIZE)
                if shots_board[r][c] == HIT
            )
            misses = sum(
                1 for r in range(GRID_SIZE) for c in range(GRID_SIZE)
                if shots_board[r][c] == MISS
            )
            shots = hits + misses  # Total shots taken
            acc = (hits / shots * 100) if shots > 0 else 0.0  # Accuracy percent
            return shots, hits, misses, acc  # Return computed stats

        p1_shots, p1_hits, p1_misses, p1_acc = counts(s.p1_shots)  # Player 1 shot stats
        p2_shots, p2_hits, p2_misses, p2_acc = counts(s.p2_shots)  # Player 2 shot stats

        p1_ships_left = ships_remaining(s.p1_ships, s.p1_hits)  # Ships still alive for Player 1
        p2_ships_left = ships_remaining(s.p2_ships, s.p2_hits)  # Ships still alive for Player 2

        p1_ship_line = ", ".join(ship_hit_counters(s.p1_ships, s.p1_hits)) or "-"  # Per-ship hit counts
        p2_ship_line = ", ".join(ship_hit_counters(s.p2_ships, s.p2_hits)) or "-"

        # Build multi-line stats text block
        text = (
            f"Player 1 Stats\n"
            f"Shots: {p1_shots} | Hits: {p1_hits} | Misses: {p1_misses} | Accuracy: {p1_acc:.1f}% | Ships left: {p1_ships_left}\n"
            f"Ship hits: {p1_ship_line}\n\n"
            f"Player 2 Stats\n"
            f"Shots: {p2_shots} | Hits: {p2_hits} | Misses: {p2_misses} | Accuracy: {p2_acc:.1f}% | Ships left: {p2_ships_left}\n"
            f"Ship hits: {p2_ship_line}"
        )

        self.stats_lbl.config(text=text)  # Display stats text on the screen
