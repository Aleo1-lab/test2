"""
Handles the graphical user interface (GUI) for the Gelişmiş Otomatik Tıklayıcı.

Uses tkinter and ttk for creating widgets and laying out the application window.
Manages UI elements for configuring click modes, triggers, and displaying status.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys

# --- CONSTANTS ---
COLOR_GREEN = "#009933"
COLOR_RED = "#CC0000"
COLOR_BLUE = "#0066CC"
COLOR_BLACK = "black" # Default text color
STATUS_IDLE = "Durum: Beklemede"
STATUS_STOPPED = "Durum: Durduruldu"
STATUS_ERROR = "Durum: Hatalı Ayar"
ASSIGN_KEY_PROMPT = "TUŞA BASIN VEYA FARE TUŞUNA TIKLAYIN... (İptal: ESC)"
KEY_NOT_ASSIGNED = "ATANMADI"
# Note: STATUS_RUNNING is now dynamic, e.g., "Durum: SOL TIK AKTİF"

class Tooltip:
    """
    Creates a tooltip for a given widget.
    The tooltip appears when the mouse hovers over the widget and disappears when it leaves.
    """
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tooltip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self._show_tooltip_event)
        self.widget.bind("<Leave>", self._hide_tooltip_event)

    def _show_tooltip_event(self, event: tk.Event) -> None:
        """Event handler to show the tooltip."""
        if self.tooltip_window or not self.text:
            return

        # Calculate position for the tooltip window
        x, y, _, _ = self.widget.bbox("insert") # Get widget bounding box
        x += self.widget.winfo_rootx() + 25     # Offset from widget
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True) # Remove window decorations
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def _hide_tooltip_event(self, event: tk.Event) -> None:
        """Event handler to hide the tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

class AutoClickerUI(tk.Tk):
    """
    Main class for the AutoClicker's Tkinter-based user interface.
    """
    def __init__(self, app_core): # app_core is an instance of AppCore
        super().__init__()
        self.app_core = app_core
        self.title("Gelişmiş Otomatik Tıklayıcı v6.0")
        self.geometry("550x750")
        self.resizable(False, False)

        style = ttk.Style(self)
        # Use 'clam' on non-Windows, 'vista' on Windows if available, else default.
        current_theme = style.theme_use()
        if 'win' in sys.platform and 'vista' in style.theme_names():
            style.theme_use('vista')
        elif 'clam' in style.theme_names(): # 'clam' is a good cross-platform default
            style.theme_use('clam')
        # else: use system default theme (already active)

        # Stores all widgets that need their state (disabled/normal) managed globally
        self.settings_widgets: list[tk.Widget] = []
        # Stores widgets specific to each click type tab for easier management
        self.left_click_widgets: dict[str, tk.Widget | tk.StringVar | tk.DoubleVar] = {}
        self.right_click_widgets: dict[str, tk.Widget | tk.StringVar | tk.DoubleVar] = {}

        self._create_widgets()
        # Use lambda for the protocol to ensure the method is resolved correctly at call time,
        # which can sometimes be an issue with direct method references in Tkinter.
        self.protocol("WM_DELETE_WINDOW", lambda: self.app_core.emergency_shutdown())

        # Initial UI setup for modes is called after all widgets are created
        # to ensure dependent widgets exist.
        self._on_mode_change(event=None, click_type='left')
        self._on_mode_change(event=None, click_type='right')

    def _create_widgets(self) -> None:
        """Creates and lays out all widgets in the main window."""
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)

        # --- Status and Real-time Info ---
        status_info_frame = ttk.Frame(main_frame)
        status_info_frame.pack(pady=(0, 10), fill="x")
        self.status_label = ttk.Label(status_info_frame, text=STATUS_IDLE,
                                      font=("Segoe UI", 16, "bold"), anchor="center")
        self.status_label.pack(fill="x")
        self.real_time_cps_label = ttk.Label(status_info_frame, text="Anlık CPS: 0.0",
                                           font=("Segoe UI", 12, "italic"), anchor="center",
                                           foreground=COLOR_BLUE)
        self.real_time_cps_label.pack(fill="x")

        # --- Notebook for Left and Right Click Settings ---
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=(5, 10))

        left_tab_frame = ttk.Frame(notebook, padding="10")
        right_tab_frame = ttk.Frame(notebook, padding="10")
        notebook.add(left_tab_frame, text='Sol Tık Ayarları')
        notebook.add(right_tab_frame, text='Sağ Tık Ayarları')

        self._create_click_settings_tab(left_tab_frame, 'left')
        self._create_click_settings_tab(right_tab_frame, 'right')

        # --- Global Controls and Keybindings ---
        global_controls_frame = ttk.LabelFrame(main_frame, text="Genel Kontroller ve Tuş Atama",
                                               padding="15")
        global_controls_frame.pack(fill="x", pady=(10, 5))
        global_controls_frame.columnconfigure((0, 1, 2, 3), weight=1)

        assign_left_button = ttk.Button(global_controls_frame,
                                        text="Sol Tık Tetikleyici Ata",
                                        command=lambda: self.app_core.set_assign_mode('left'))
        assign_left_button.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5, padx=(0,5))
        self.settings_widgets.append(assign_left_button)

        self.left_trigger_key_label = ttk.Label(global_controls_frame, text=KEY_NOT_ASSIGNED,
                                                foreground=COLOR_RED,
                                                font=("Segoe UI", 10, "bold"), anchor="center",
                                                relief="sunken", padding=5)
        self.left_trigger_key_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,10), padx=(0,5))

        assign_right_button = ttk.Button(global_controls_frame,
                                         text="Sağ Tık Tetikleyici Ata",
                                         command=lambda: self.app_core.set_assign_mode('right'))
        assign_right_button.grid(row=0, column=2, columnspan=2, sticky="ew", pady=5, padx=(5,0))
        self.settings_widgets.append(assign_right_button)

        self.right_trigger_key_label = ttk.Label(global_controls_frame, text=KEY_NOT_ASSIGNED,
                                                 foreground=COLOR_RED,
                                                 font=("Segoe UI", 10, "bold"), anchor="center",
                                                 relief="sunken", padding=5)
        self.right_trigger_key_label.grid(row=1, column=2, columnspan=2, sticky="ew", pady=(0,10), padx=(5,0))

        # --- Stats and Info ---
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill="x", pady=(5,0))
        self.click_count_label = ttk.Label(stats_frame, text="Toplam Tıklama: 0",
                                           font=("Segoe UI", 10), anchor="center")
        self.click_count_label.pack(fill="x")
        ttk.Label(stats_frame, text="Acil Kapatma: F12 TUŞU", foreground=COLOR_RED,
                  font=("Segoe UI", 10, "italic"), anchor="center").pack(fill='x', pady=(5,0))

    def _create_click_settings_tab(self, parent_frame: ttk.Frame, click_type_prefix: str) -> None:
        """Helper to create the settings UI for a single tab (left or right)."""
        parent_frame.columnconfigure(1, weight=1) # Make the widget column expandable
        widgets_dict = self.left_click_widgets if click_type_prefix == 'left' else self.right_click_widgets

        # --- Tkinter Variables ---
        widgets_dict['cps_mode_var'] = tk.StringVar(value="Sabit")
        widgets_dict['cps_var'] = tk.DoubleVar(value=15.0)
        widgets_dict['timing_rand_var'] = tk.StringVar(value="15")
        widgets_dict['jitter_intensity_var'] = tk.StringVar(value="3")
        widgets_dict['burst_duration_var'] = tk.StringVar(value="5")
        widgets_dict['min_cps_random_var'] = tk.StringVar(value="5.0")
        widgets_dict['max_cps_random_var'] = tk.StringVar(value="15.0")
        widgets_dict['click_pattern_var'] = tk.StringVar(value="100-80-120")

        # --- Click Mode Selection ---
        ttk.Label(parent_frame, text="Tıklama Modu:").grid(row=0, column=0, sticky="w", pady=5, padx=(0,5))
        mode_combo = ttk.Combobox(parent_frame, textvariable=widgets_dict['cps_mode_var'],
                                  values=["Sabit", "Dalgalı (Sinüs)", "Patlama", "Gerçekçi (Perlin)",
                                          "Rastgele Aralık", "Pattern (Desen)"],
                                  state="readonly")
        mode_combo.grid(row=0, column=1, sticky="ew", pady=5)
        mode_combo.bind("<<ComboboxSelected>>",
                        lambda event, ct=click_type_prefix: self._on_mode_change(event, ct))
        Tooltip(mode_combo, "Tıklama davranışını belirler.")
        self.settings_widgets.append(mode_combo)
        widgets_dict['mode_combo'] = mode_combo

        # --- CPS Scale ---
        widgets_dict['cps_title_label'] = ttk.Label(parent_frame, text="Hedef Hız (CPS):")
        widgets_dict['cps_title_label'].grid(row=1, column=0, sticky="w", pady=5, padx=(0,5))
        widgets_dict['cps_label_display'] = ttk.Label(parent_frame,
                                                     text=f"{widgets_dict['cps_var'].get():.1f} CPS")
        widgets_dict['cps_label_display'].grid(row=1, column=1, sticky="e", pady=5)
        widgets_dict['cps_scale'] = ttk.Scale(parent_frame, from_=1, to=40, orient="horizontal",
                                            variable=widgets_dict['cps_var'],
                                            command=lambda val, ct=click_type_prefix:
                                                self._update_cps_label_display(val, ct))
        widgets_dict['cps_scale'].grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0,10))
        self.settings_widgets.append(widgets_dict['cps_scale'])

        # --- Mode Specific Settings Frames (dynamically shown/hidden) ---
        # Burst Mode Frame
        widgets_dict['burst_frame'] = ttk.Frame(parent_frame) # Parent is the tab frame
        ttk.Label(widgets_dict['burst_frame'], text="Patlama Süresi (sn):").grid(row=0, column=0, sticky="w")
        burst_entry = ttk.Entry(widgets_dict['burst_frame'],
                                textvariable=widgets_dict['burst_duration_var'], width=12)
        burst_entry.grid(row=0, column=1, sticky="e")
        self.settings_widgets.append(burst_entry) # Only the entry needs state management

        # Random Interval Mode Frame
        widgets_dict['random_interval_frame'] = ttk.Frame(parent_frame)
        ttk.Label(widgets_dict['random_interval_frame'], text="Min CPS (Rastgele):").grid(row=0, column=0, sticky="w", pady=(5,0))
        min_cps_entry = ttk.Entry(widgets_dict['random_interval_frame'],
                                  textvariable=widgets_dict['min_cps_random_var'], width=12)
        min_cps_entry.grid(row=0, column=1, sticky="e", pady=(5,0))
        ttk.Label(widgets_dict['random_interval_frame'], text="Max CPS (Rastgele):").grid(row=1, column=0, sticky="w", pady=(0,5))
        max_cps_entry = ttk.Entry(widgets_dict['random_interval_frame'],
                                  textvariable=widgets_dict['max_cps_random_var'], width=12)
        max_cps_entry.grid(row=1, column=1, sticky="e", pady=(0,5))
        self.settings_widgets.extend([min_cps_entry, max_cps_entry])

        # Pattern Mode Frame
        widgets_dict['pattern_mode_frame'] = ttk.Frame(parent_frame)
        ttk.Label(widgets_dict['pattern_mode_frame'],
                  text="Pattern (gecikmeler ms, '-' ile ayrılmış):").grid(row=0, column=0, sticky="w", columnspan=2)
        pattern_entry = ttk.Entry(widgets_dict['pattern_mode_frame'],
                                 textvariable=widgets_dict['click_pattern_var'], width=30)
        pattern_entry.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.settings_widgets.append(pattern_entry)

        # --- Common Settings (Timing, Jitter) ---
        current_row = 4 # Row index for common settings, after mode-specific frames area

        ttk.Label(parent_frame, text="Zamanlama Rastgeleliği (± ms):").grid(row=current_row, column=0, sticky="w", pady=5, padx=(0,5))
        timing_entry = ttk.Entry(parent_frame, textvariable=widgets_dict['timing_rand_var'], width=12)
        timing_entry.grid(row=current_row, column=1, sticky="e", pady=5)
        self.settings_widgets.append(timing_entry)
        current_row += 1

        ttk.Label(parent_frame, text="Jitter Yoğunluğu (Piksel):").grid(row=current_row, column=0, sticky="w", pady=5, padx=(0,5))
        jitter_entry = ttk.Entry(parent_frame, textvariable=widgets_dict['jitter_intensity_var'], width=12)
        jitter_entry.grid(row=current_row, column=1, sticky="e", pady=5)
        self.settings_widgets.append(jitter_entry)

    def _on_mode_change(self, event: tk.Event | None, click_type: str) -> None:
        """Handles UI changes when the click mode is selected for a specific tab."""
        widgets_dict = self.left_click_widgets if click_type == 'left' else self.right_click_widgets
        selected_mode = widgets_dict['cps_mode_var'].get()

        # Hide all mode-specific frames first
        widgets_dict['burst_frame'].grid_forget()
        widgets_dict['random_interval_frame'].grid_forget()
        widgets_dict['pattern_mode_frame'].grid_forget()

        cps_title_text = "Hedef Hız (CPS):" # Default title
        show_main_cps_controls = True
        mode_specific_frame_grid_row = 3 # Row where mode-specific frames are placed

        if selected_mode == "Sabit":
            cps_title_text = "Hedef Hız (CPS):"
        elif selected_mode == "Dalgalı (Sinüs)":
            cps_title_text = "Ortalama Hız (CPS):"
        elif selected_mode == "Patlama":
            cps_title_text = "Zirve Hız (CPS):"
            widgets_dict['burst_frame'].grid(row=mode_specific_frame_grid_row, column=0,
                                           columnspan=2, sticky='ew', pady=5)
        elif selected_mode == "Gerçekçi (Perlin)":
            cps_title_text = "Ortalama Hız (CPS):"
        elif selected_mode == "Rastgele Aralık":
            cps_title_text = "Referans Max CPS:"
            widgets_dict['random_interval_frame'].grid(row=mode_specific_frame_grid_row, column=0,
                                                     columnspan=2, sticky='ew', pady=5)
        elif selected_mode == "Pattern (Desen)":
            show_main_cps_controls = False # CPS scale not directly used for pattern delays
            widgets_dict['pattern_mode_frame'].grid(row=mode_specific_frame_grid_row, column=0,
                                                  columnspan=2, sticky='ew', pady=5)
            # cps_title_text for Pattern mode is not strictly needed if scale is hidden.

        widgets_dict['cps_title_label'].config(text=cps_title_text)

        # Show or hide main CPS controls (scale and its labels)
        for widget_key in ['cps_title_label', 'cps_scale', 'cps_label_display']:
            if widget_key in widgets_dict: # Ensure widget exists
                if show_main_cps_controls:
                    widgets_dict[widget_key].grid()
                else:
                    widgets_dict[widget_key].grid_remove()

        self.app_core.on_mode_changed(selected_mode, click_type)

        # If core failed to load the mode (e.g., even fallback failed),
        # reset UI combobox to "Sabit" to reflect a default state.
        core_mode_instance = getattr(self.app_core, f"{click_type}_click_mode", None)
        if core_mode_instance is None:
            widgets_dict['mode_combo'].set("Sabit")
            print(f"UI Warning: Core failed to load mode '{selected_mode}' for {click_type}. UI reflects 'Sabit'.")
            # Avoid recursive call if "Sabit" was already the mode that failed.
            if selected_mode != "Sabit":
                 # This re-triggers _on_mode_change to ensure UI is consistent with "Sabit" attempt.
                 self._on_mode_change(None, click_type)

    def _update_cps_label_display(self, value_str: str, click_type: str) -> None:
        """Updates the CPS display label next to the scale."""
        widgets_dict = self.left_click_widgets if click_type == 'left' else self.right_click_widgets
        try:
            value = float(value_str)
            widgets_dict['cps_label_display'].config(text=f"{value:.1f} CPS")
        except ValueError: # Should not happen with a Scale widget
            widgets_dict['cps_label_display'].config(text="Hatalı CPS")


    def update_status_display(self, status_text: str, color: str, is_running: bool) -> None:
        """Updates the main status label and enables/disables settings widgets."""
        font_weight = "bold" if "AKTİF" in status_text.upper() else "normal"
        self.status_label.config(text=status_text, foreground=color,
                                 font=("Segoe UI", 16, font_weight))

        widget_state = "disabled" if is_running else "normal"
        for widget in self.settings_widgets:
            try:
                if isinstance(widget, ttk.Combobox):
                    # Comboboxes are 'readonly', so they become 'disabled' or 'readonly'
                    widget.config(state="disabled" if is_running else "readonly")
                elif isinstance(widget, (ttk.Scale, ttk.Entry, ttk.Button)):
                     widget.config(state=widget_state)
                # Other widget types (Labels, Frames) in settings_widgets don't have a 'state'
            except tk.TclError:
                pass # Widget might not support 'state' or already destroyed
            except AttributeError:
                # This should ideally not happen if settings_widgets is populated correctly.
                print(f"Warning: Widget {widget} in settings_widgets lacks state config methods or does not exist.")