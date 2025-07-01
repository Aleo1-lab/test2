import tkinter as tk
from tkinter import ttk, messagebox
import sys

# --- SABİTLER ---
COLOR_GREEN = "#009933"
COLOR_RED = "#CC0000"
COLOR_BLUE = "#0066CC"
COLOR_BLACK = "black"
STATUS_RUNNING = "Durum: ÇALIŞIYOR"
STATUS_IDLE = "Durum: Beklemede"
STATUS_STOPPED = "Durum: Durduruldu"
STATUS_ERROR = "Durum: Hatalı Ayar"
ASSIGN_KEY_PROMPT = "TUŞA BASIN VEYA FARE TUŞUNA TIKLAYIN... (İptal: ESC)"
KEY_NOT_ASSIGNED = "ATANMADI"

class Tooltip:
    """Widget'lar için fare üzerine gelince ipucu gösteren basit bir sınıf."""
    def __init__(self, widget, text):
        self.widget, self.text, self.tooltip_window = widget, text, None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tooltip_window, text=self.text, justify='left', background="#ffffe0", relief='solid', borderwidth=1, font=("tahoma", "8", "normal")).pack(ipadx=1)

    def hide_tooltip(self, event):
        if self.tooltip_window: self.tooltip_window.destroy()
        self.tooltip_window = None

class AutoClickerUI(tk.Tk):
    def __init__(self, app_core):
        super().__init__()
        self.app_core = app_core
        self.title("Gelişmiş Otomatik Tıklayıcı v6.0")
        self.geometry("550x750") # Increased width and height for tabs and more controls
        self.resizable(False, False)
        style = ttk.Style(self)
        style.theme_use('vista' if 'win' in sys.platform else 'clam')

        # Store all widgets that need to be enabled/disabled
        self.settings_widgets = []
        # Store widgets per tab to manage them easily
        self.left_click_widgets = {}
        self.right_click_widgets = {}

        self._create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.app_core.emergency_shutdown)
        # Initialize mode-specific UI for both tabs
        self._on_mode_change(event=None, click_type='left')
        self._on_mode_change(event=None, click_type='right')


    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)

        # --- Status and Real-time Info ---
        status_info_frame = ttk.Frame(main_frame)
        status_info_frame.pack(pady=(0,10), fill="x")
        self.status_label = ttk.Label(status_info_frame, text=STATUS_IDLE, font=("Segoe UI", 16, "bold"), anchor="center")
        self.status_label.pack(fill="x")
        self.real_time_cps_label = ttk.Label(status_info_frame, text="Anlık CPS: 0.0", font=("Segoe UI", 12, "italic"), anchor="center", foreground=COLOR_BLUE)
        self.real_time_cps_label.pack(fill="x")


        # --- Notebook for Left and Right Click Settings ---
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=(5,10))

        left_tab_frame = ttk.Frame(notebook, padding="10")
        right_tab_frame = ttk.Frame(notebook, padding="10")
        notebook.add(left_tab_frame, text='Sol Tık Ayarları')
        notebook.add(right_tab_frame, text='Sağ Tık Ayarları')

        self._create_click_settings_tab(left_tab_frame, 'left')
        self._create_click_settings_tab(right_tab_frame, 'right')

        # --- Global Controls and Keybindings ---
        global_controls_frame = ttk.LabelFrame(main_frame, text="Genel Kontroller ve Tuş Atama", padding="15")
        global_controls_frame.pack(fill="x", pady=(10,5))
        global_controls_frame.columnconfigure((0,1), weight=1) # Make buttons expand

        # Active Click Configuration
        self.active_click_config_var = tk.StringVar(value="Use Left Click Settings")
        active_click_lbl = ttk.Label(global_controls_frame, text="Aktif Tıklama Yapılandırması:")
        active_click_lbl.grid(row=0, column=0, sticky="w", pady=(0,5), padx=(0,5))
        active_click_combo = ttk.Combobox(global_controls_frame, textvariable=self.active_click_config_var,
                                          values=["Use Left Click Settings", "Use Right Click Settings", "Use Both Settings"],
                                          state="readonly", width=25)
        active_click_combo.grid(row=0, column=1, sticky="ew", pady=(0,5))
        self.settings_widgets.append(active_click_combo) # Add to global list for enable/disable

        self.toggle_button = ttk.Button(global_controls_frame, text="Başlat", command=self.app_core.toggle_clicking, style="Accent.TButton") # Example of using a style
        self.toggle_button.grid(row=1, column=0, sticky="ew", pady=5, padx=(0,5))

        assign_button = ttk.Button(global_controls_frame, text="Tetikleyici Ata", command=self.app_core.set_assign_mode)
        assign_button.grid(row=1, column=1, sticky="ew", pady=5, padx=(5,0))
        self.settings_widgets.append(assign_button)

        self.trigger_key_label = ttk.Label(global_controls_frame, text=KEY_NOT_ASSIGNED, foreground=COLOR_RED,
                                           font=("Segoe UI", 10, "bold"), anchor="center",
                                           relief="sunken", padding=5)
        self.trigger_key_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5,0))


        # --- Stats and Info ---
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill="x", pady=(5,0))
        self.click_count_label = ttk.Label(stats_frame, text="Toplam Tıklama: 0", font=("Segoe UI", 10), anchor="center")
        self.click_count_label.pack(fill="x")
        ttk.Label(stats_frame, text="Acil Kapatma: F12 TUŞU", foreground=COLOR_RED,
                  font=("Segoe UI", 10, "italic"), anchor="center").pack(fill='x', pady=(5,0))

    def _create_click_settings_tab(self, parent_frame, click_type_prefix: str):
        """Helper to create the settings UI for a single tab (left or right)."""
        parent_frame.columnconfigure(1, weight=1)
        widgets_dict = self.left_click_widgets if click_type_prefix == 'left' else self.right_click_widgets

        # Variables
        widgets_dict['cps_mode_var'] = tk.StringVar(value="Sabit")
        widgets_dict['cps_var'] = tk.DoubleVar(value=15.0)
        widgets_dict['timing_rand_var'] = tk.StringVar(value="15")
        widgets_dict['jitter_intensity_var'] = tk.StringVar(value="3")
        # Mode specific vars
        widgets_dict['burst_duration_var'] = tk.StringVar(value="5")
        widgets_dict['min_cps_random_var'] = tk.StringVar(value="5.0")
        widgets_dict['max_cps_random_var'] = tk.StringVar(value="15.0")
        widgets_dict['click_pattern_var'] = tk.StringVar(value="100-80-120")


        # Click Mode
        mode_lbl = ttk.Label(parent_frame, text="Tıklama Modu:")
        mode_lbl.grid(row=0, column=0, sticky="w", pady=5, padx=(0,5))
        mode_combo = ttk.Combobox(parent_frame, textvariable=widgets_dict['cps_mode_var'],
                                  values=["Sabit", "Dalgalı (Sinüs)", "Patlama", "Gerçekçi (Perlin)", "Rastgele Aralık", "Pattern (Desen)"],
                                  state="readonly")
        mode_combo.grid(row=0, column=1, sticky="ew", pady=5)
        mode_combo.bind("<<ComboboxSelected>>", lambda e, ct=click_type_prefix: self._on_mode_change(e, ct))
        Tooltip(mode_lbl, "Tıklama davranışını belirler (Sabit hız, dalgalı, patlama vb.).")
        self.settings_widgets.extend([mode_lbl, mode_combo])
        widgets_dict['mode_combo'] = mode_combo # Store for later

        # CPS Scale
        widgets_dict['cps_title_label'] = ttk.Label(parent_frame, text="Hedef Hız (CPS):")
        widgets_dict['cps_title_label'].grid(row=1, column=0, sticky="w", pady=5, padx=(0,5))
        widgets_dict['cps_label_display'] = ttk.Label(parent_frame, text=f"{widgets_dict['cps_var'].get():.1f} CPS")
        widgets_dict['cps_label_display'].grid(row=1, column=1, sticky="e", pady=5)
        widgets_dict['cps_scale'] = ttk.Scale(parent_frame, from_=1, to=40, orient="horizontal", variable=widgets_dict['cps_var'],
                                            command=lambda val, ct=click_type_prefix: self._update_cps_label_display(val, ct))
        widgets_dict['cps_scale'].grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0,10))
        self.settings_widgets.extend([widgets_dict['cps_title_label'], widgets_dict['cps_scale'], widgets_dict['cps_label_display']])


        # --- Mode Specific Settings Frames (created once, shown/hidden in _on_mode_change) ---
        # These frames are parented to the tab frame (parent_frame)
        # Burst Mode
        widgets_dict['burst_frame'] = ttk.Frame(parent_frame)
        burst_lbl = ttk.Label(widgets_dict['burst_frame'], text="Patlama Süresi (sn):")
        burst_lbl.grid(row=0, column=0, sticky="w")
        burst_entry = ttk.Entry(widgets_dict['burst_frame'], textvariable=widgets_dict['burst_duration_var'], width=12)
        burst_entry.grid(row=0, column=1, sticky="e")
        self.settings_widgets.extend([widgets_dict['burst_frame'], burst_lbl, burst_entry]) # Add controlling frame and its children

        # Random Interval Mode
        widgets_dict['random_interval_frame'] = ttk.Frame(parent_frame)
        min_cps_lbl = ttk.Label(widgets_dict['random_interval_frame'], text="Min CPS (Rastgele):")
        min_cps_lbl.grid(row=0, column=0, sticky="w", pady=(5,0))
        min_cps_entry = ttk.Entry(widgets_dict['random_interval_frame'], textvariable=widgets_dict['min_cps_random_var'], width=12)
        min_cps_entry.grid(row=0, column=1, sticky="e", pady=(5,0))
        max_cps_lbl = ttk.Label(widgets_dict['random_interval_frame'], text="Max CPS (Rastgele):")
        max_cps_lbl.grid(row=1, column=0, sticky="w", pady=(0,5))
        max_cps_entry = ttk.Entry(widgets_dict['random_interval_frame'], textvariable=widgets_dict['max_cps_random_var'], width=12)
        max_cps_entry.grid(row=1, column=1, sticky="e", pady=(0,5))
        self.settings_widgets.extend([widgets_dict['random_interval_frame'], min_cps_lbl, min_cps_entry, max_cps_lbl, max_cps_entry])

        # Pattern Mode
        widgets_dict['pattern_mode_frame'] = ttk.Frame(parent_frame)
        pattern_lbl = ttk.Label(widgets_dict['pattern_mode_frame'], text="Pattern (gecikmeler ms, '-' ile ayrılmış):")
        pattern_lbl.grid(row=0, column=0, sticky="w", columnspan=2)
        pattern_entry = ttk.Entry(widgets_dict['pattern_mode_frame'], textvariable=widgets_dict['click_pattern_var'], width=30)
        pattern_entry.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.settings_widgets.extend([widgets_dict['pattern_mode_frame'], pattern_lbl, pattern_entry])

        # --- Common Settings (Timing, Jitter) ---
        # These are placed starting from row 3, after mode-specific settings might be inserted.
        # The mode-specific frames will be grid() or grid_remove() into row=3.
        current_row = 4 # Start common settings after the space for mode-specific ones

        timing_lbl = ttk.Label(parent_frame, text="Zamanlama Rastgeleliği (± ms):")
        timing_lbl.grid(row=current_row, column=0, sticky="w", pady=5, padx=(0,5))
        timing_entry = ttk.Entry(parent_frame, textvariable=widgets_dict['timing_rand_var'], width=12)
        timing_entry.grid(row=current_row, column=1, sticky="e", pady=5)
        self.settings_widgets.extend([timing_lbl, timing_entry])
        current_row += 1

        jitter_lbl = ttk.Label(parent_frame, text="Jitter Yoğunluğu (Piksel):")
        jitter_lbl.grid(row=current_row, column=0, sticky="w", pady=5, padx=(0,5))
        jitter_entry = ttk.Entry(parent_frame, textvariable=widgets_dict['jitter_intensity_var'], width=12)
        jitter_entry.grid(row=current_row, column=1, sticky="e", pady=5)
        self.settings_widgets.extend([jitter_lbl, jitter_entry])
        current_row += 1
        # Note: The old "Mouse Button" selection is now replaced by the "Active Click Configuration" global setting.

    def _on_mode_change(self, event, click_type: str):
        """Handles UI changes when the click mode is changed for a specific tab."""
        widgets_dict = self.left_click_widgets if click_type == 'left' else self.right_click_widgets
        mode = widgets_dict['cps_mode_var'].get()

        # Hide all mode-specific frames for this tab first
        widgets_dict['burst_frame'].grid_forget()
        widgets_dict['random_interval_frame'].grid_forget()
        widgets_dict['pattern_mode_frame'].grid_forget()

        cps_title = "Hedef Hız (CPS):"
        show_main_cps_scale = True
        mode_specific_frame_row = 3 # Grid row for mode specific settings

        if mode == "Sabit":
            cps_title = "Hedef Hız (CPS):"
        elif mode == "Dalgalı (Sinüs)":
            cps_title = "Ortalama Hız (CPS):"
        elif mode == "Patlama":
            cps_title = "Zirve Hız (CPS):"
            widgets_dict['burst_frame'].grid(row=mode_specific_frame_row, column=0, columnspan=2, sticky='ew', pady=5)
        elif mode == "Gerçekçi (Perlin)":
            cps_title = "Ortalama Hız (CPS):"
        elif mode == "Rastgele Aralık":
            cps_title = "Referans Max CPS:"
            widgets_dict['random_interval_frame'].grid(row=mode_specific_frame_row, column=0, columnspan=2, sticky='ew', pady=5)
        elif mode == "Pattern (Desen)":
            cps_title = "Ref. Jitter CPS:"
            show_main_cps_scale = False # CPS scale not directly used for pattern delays
            widgets_dict['pattern_mode_frame'].grid(row=mode_specific_frame_row, column=0, columnspan=2, sticky='ew', pady=5)

        widgets_dict['cps_title_label'].config(text=cps_title)

        if show_main_cps_scale:
            widgets_dict['cps_title_label'].grid()
            widgets_dict['cps_scale'].grid()
            widgets_dict['cps_label_display'].grid()
        else:
            widgets_dict['cps_title_label'].grid_remove()
            widgets_dict['cps_scale'].grid_remove()
            widgets_dict['cps_label_display'].grid_remove()

        self.app_core.on_mode_changed(mode, click_type) # Notify core, passing click_type

    def _update_cps_label_display(self, value, click_type: str):
        widgets_dict = self.left_click_widgets if click_type == 'left' else self.right_click_widgets
        widgets_dict['cps_label_display'].config(text=f"{float(value):.1f} CPS")

    def update_status_display(self, status_text, color, is_running):
        font_weight = "bold" if "ÇALIŞIYOR" in status_text else "normal"
        self.status_label.config(text=status_text, foreground=color, font=("Segoe UI", 16, font_weight))
        self.toggle_button.config(text="Durdur" if is_running else "Başlat")

        widget_state = "disabled" if is_running else "normal"
        for widget in self.settings_widgets: # This list now contains all configurable widgets
            try:
                if isinstance(widget, ttk.Combobox) and widget.cget('state') == 'readonly':
                    widget.config(state="disabled" if is_running else "readonly")
                elif isinstance(widget, ttk.Scale): # Scales also need state handling
                     widget.config(state=widget_state)
                elif isinstance(widget, ttk.Entry): # Entries
                     widget.config(state=widget_state)
                elif isinstance(widget, ttk.Button): # Buttons like Assign Key
                     widget.config(state=widget_state)
                # Add other widget types if necessary (e.g. Checkbuttons, Radiobuttons)
                # Frames themselves don't have a 'state' but their children are in settings_widgets
            except (tk.TclError, AttributeError):
                 # This can happen for frames or labels that are in settings_widgets but don't have a state
                pass

    def update_realtime_cps(self, cps, click_type_str: str = ""):
        """Updates the real-time CPS display, optionally indicating click type."""
        if click_type_str:
            self.real_time_cps_label.config(text=f"Anlık {click_type_str} CPS: {cps:.1f}")
        else:
            self.real_time_cps_label.config(text=f"Anlık CPS: {cps:.1f}")


    def update_click_count(self, count):
        self.click_count_label.config(text=f"Toplam Tıklama: {count}")

    def update_trigger_key_display(self, key_name, is_assigned):
        self.trigger_key_label.config(text=key_name, foreground=COLOR_GREEN if is_assigned else COLOR_RED)
        if key_name == ASSIGN_KEY_PROMPT:
            self.trigger_key_label.config(foreground=COLOR_BLUE)

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def show_warning(self, title, message):
        messagebox.showwarning(title, message)

    def _get_settings_for_tab(self, click_type: str) -> dict:
        """Helper to get settings from a specific tab's widgets."""
        widgets_dict = self.left_click_widgets if click_type == 'left' else self.right_click_widgets
        settings = {
            'mode': widgets_dict['cps_mode_var'].get(),
            'peak_cps': widgets_dict['cps_var'].get(),
            'timing_rand_ms': widgets_dict['timing_rand_var'].get(),
            'jitter_px': widgets_dict['jitter_intensity_var'].get(),
        }
        # Mode-specific settings
        if settings['mode'] == 'Patlama':
            settings['burst_duration'] = widgets_dict['burst_duration_var'].get()
        elif settings['mode'] == 'Rastgele Aralık':
            settings['min_cps_random'] = widgets_dict['min_cps_random_var'].get()
            settings['max_cps_random'] = widgets_dict['max_cps_random_var'].get()
        elif settings['mode'] == 'Pattern (Desen)':
            settings['click_pattern'] = widgets_dict['click_pattern_var'].get()
        return settings

    def get_current_settings(self) -> dict:
        """Returns a dictionary of all UI settings, including both tabs and global settings."""
        return {
            'left': self._get_settings_for_tab('left'),
            'right': self._get_settings_for_tab('right'),
            'active_config': self.active_click_config_var.get() # "Use Left Click Settings", etc.
        }

if __name__ == '__main__':
    class MockAppCore:
        def toggle_clicking(self): print("Toggle Clicking")
        def set_assign_mode(self): print("Set Assign Mode")
        def emergency_shutdown(self): print("Emergency Shutdown"); app.destroy(); sys.exit()
        def on_mode_changed(self, mode_name, click_type): print(f"Mode for {click_type} changed to: {mode_name}")

    core = MockAppCore()
    app = AutoClickerUI(core)
    app.mainloop()
