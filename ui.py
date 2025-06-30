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
ASSIGN_KEY_PROMPT = "TUŞA BASIN... (İptal: ESC)"
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
        self.title("Gerçekçi Jitter Simülatörü v5.0"); self.geometry("450x700"); self.resizable(False, False) # Increased height for new options
        style = ttk.Style(self); style.theme_use('vista' if 'win' in sys.platform else 'clam')

        self.settings_widgets = [] # To enable/disable all settings easily
        self._create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.app_core.emergency_shutdown)
        self._on_mode_change() # Initialize mode-specific UI

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20"); main_frame.pack(fill="both", expand=True)

        self.status_label = ttk.Label(main_frame, text=STATUS_IDLE, font=("Segoe UI", 16, "bold"), anchor="center")
        self.status_label.pack(pady=(0, 10), fill="x")

        self.real_time_cps_label = ttk.Label(main_frame, text="Anlık CPS: 0.0", font=("Segoe UI", 12, "italic"), anchor="center", foreground=COLOR_BLUE)
        self.real_time_cps_label.pack(pady=(0, 10), fill="x")

        settings_frame = ttk.LabelFrame(main_frame, text="Ayarlar", padding="15"); settings_frame.pack(fill="x", expand=True)
        settings_frame.columnconfigure(1, weight=1)

        # Click Mode
        self.cps_mode_var = tk.StringVar(value="Sabit")
        mode_lbl = ttk.Label(settings_frame, text="Tıklama Modu:")
        mode_lbl.grid(row=0, column=0, sticky="w", pady=5)
        self.mode_combo = ttk.Combobox(settings_frame, textvariable=self.cps_mode_var,
                                       values=["Sabit", "Dalgalı (Sinüs)", "Patlama", "Gerçekçi (Perlin)", "Rastgele Aralık", "Pattern (Desen)"],
                                       state="readonly")
        self.mode_combo.grid(row=0, column=1, sticky="ew", pady=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)
        Tooltip(mode_lbl, "Sabit: Belirlenen hızda sürekli tıklar.\nDalgalı: Sinüs dalgasıyla hızı değiştirir.\nPatlama: Kısa süreliğine maksimum hıza çıkar.\nGerçekçi (Perlin): Organik hız ve jitter.\nRastgele Aralık: Min/Max CPS arasında rastgele hız.\nPattern (Desen): Belirli bir gecikme dizisini tekrarlar.")
        self.settings_widgets.extend([mode_lbl, self.mode_combo])

        # CPS Scale (Common for most modes)
        self.cps_var = tk.DoubleVar(value=15.0)
        self.cps_title_label = ttk.Label(settings_frame, text="Hedef Hız (CPS):")
        self.cps_title_label.grid(row=1, column=0, sticky="w", pady=5)
        self.cps_scale = ttk.Scale(settings_frame, from_=1, to=40, orient="horizontal", variable=self.cps_var, command=self._update_cps_label_display)
        self.cps_scale.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0,5))
        self.cps_label_display = ttk.Label(settings_frame, text=f"{self.cps_var.get():.1f} CPS") # Renamed from cps_label to avoid conflict
        self.cps_label_display.grid(row=1, column=1, sticky="e")
        self.settings_widgets.extend([self.cps_title_label, self.cps_scale, self.cps_label_display])

        self._create_mode_specific_settings(settings_frame) # Placeholder for mode-specific UI elements

        current_row = 4 # Starting row for common settings, adjust as mode settings are added

        # Timing Randomness
        self.timing_rand_var = tk.StringVar(value="15")
        timing_lbl = ttk.Label(settings_frame, text="Zamanlama Rastgeleliği (± ms):")
        timing_lbl.grid(row=current_row, column=0, sticky="w", pady=5)
        timing_entry = ttk.Entry(settings_frame, textvariable=self.timing_rand_var, width=12)
        timing_entry.grid(row=current_row, column=1, sticky="e")
        self.settings_widgets.extend([timing_lbl, timing_entry])
        current_row += 1

        # Jitter Intensity
        self.jitter_intensity_var = tk.StringVar(value="3")
        jitter_lbl = ttk.Label(settings_frame, text="Jitter Yoğunluğu (Piksel):")
        jitter_lbl.grid(row=current_row, column=0, sticky="w", pady=5)
        jitter_entry = ttk.Entry(settings_frame, textvariable=self.jitter_intensity_var, width=12)
        jitter_entry.grid(row=current_row, column=1, sticky="e")
        self.settings_widgets.extend([jitter_lbl, jitter_entry])
        current_row += 1

        # Mouse Button Selection (Updated for Left/Right/Both)
        self.mouse_button_var = tk.StringVar(value="Sol Tık")
        mouse_lbl = ttk.Label(settings_frame, text="Fare Tuşu:")
        mouse_lbl.grid(row=current_row, column=0, sticky="w", pady=5)
        # Values will be: "Sol Tık", "Sağ Tık", "Sol ve Sağ Tık"
        button_combo = ttk.Combobox(settings_frame, textvariable=self.mouse_button_var,
                                    values=["Sol Tık", "Sağ Tık", "Sol ve Sağ Tık"],
                                    state="readonly", width=15) # Adjusted width
        button_combo.grid(row=current_row, column=1, sticky="e")
        button_combo.set("Sol Tık")
        self.settings_widgets.extend([mouse_lbl, button_combo])
        current_row +=1

        # Control Frame
        control_frame = ttk.LabelFrame(main_frame, text="Kontrol", padding="15")
        control_frame.pack(fill="x", pady=(20, 10))
        control_frame.columnconfigure((0, 1), weight=1)

        self.toggle_button = ttk.Button(control_frame, text="Başlat", command=self.app_core.toggle_clicking)
        self.toggle_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        assign_button = ttk.Button(control_frame, text="Tetikleyici Tuş Ata", command=self.app_core.set_assign_mode)
        assign_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.trigger_key_label = ttk.Label(control_frame, text=KEY_NOT_ASSIGNED, foreground=COLOR_RED,
                                           font=("Segoe UI", 10, "bold"), width=20, anchor="center",
                                           relief="sunken", padding=5)
        self.trigger_key_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.settings_widgets.append(assign_button) # assign_button can be disabled while running

        # Stats and Info
        self.click_count_label = ttk.Label(main_frame, text="Toplam Tıklama: 0", font=("Segoe UI", 10), anchor="center")
        self.click_count_label.pack(pady=(10, 0), fill="x")

        ttk.Label(main_frame, text="\nAcil Kapatma:  F12 TUŞU", foreground=COLOR_RED,
                  font=("Segoe UI", 10, "italic"), anchor="center").pack(pady=(10,0), fill='x')

    def _create_mode_specific_settings(self, parent_frame):
        """Creates UI elements specific to click modes."""
        self.burst_frame = ttk.Frame(parent_frame)
        # Burst Mode settings
        self.burst_duration_var = tk.StringVar(value="5")
        burst_lbl = ttk.Label(self.burst_frame, text="Patlama Süresi (sn):")
        burst_lbl.grid(row=0, column=0, sticky="w")
        burst_entry = ttk.Entry(self.burst_frame, textvariable=self.burst_duration_var, width=12)
        burst_entry.grid(row=0, column=1, sticky="e")
        # Add burst_frame and its children to settings_widgets if they should be disabled when running
        self.settings_widgets.extend([self.burst_frame, burst_lbl, burst_entry])

        # Random Interval Mode settings
        self.random_interval_frame = ttk.Frame(parent_frame)
        self.min_cps_random_var = tk.StringVar(value="5.0")
        min_cps_lbl = ttk.Label(self.random_interval_frame, text="Min CPS (Rastgele):")
        min_cps_lbl.grid(row=0, column=0, sticky="w", pady=(5,0))
        min_cps_entry = ttk.Entry(self.random_interval_frame, textvariable=self.min_cps_random_var, width=12)
        min_cps_entry.grid(row=0, column=1, sticky="e", pady=(5,0))

        self.max_cps_random_var = tk.StringVar(value="15.0") # Default max, can be tied to main CPS
        max_cps_lbl = ttk.Label(self.random_interval_frame, text="Max CPS (Rastgele):")
        max_cps_lbl.grid(row=1, column=0, sticky="w", pady=(0,5))
        max_cps_entry = ttk.Entry(self.random_interval_frame, textvariable=self.max_cps_random_var, width=12)
        max_cps_entry.grid(row=1, column=1, sticky="e", pady=(0,5))
        self.settings_widgets.extend([self.random_interval_frame, min_cps_lbl, min_cps_entry, max_cps_lbl, max_cps_entry])

        # Pattern Mode settings
        self.pattern_mode_frame = ttk.Frame(parent_frame)
        self.click_pattern_var = tk.StringVar(value="100-80-120") # Default pattern: e.g. 100ms-80ms-120ms delays
        pattern_lbl = ttk.Label(self.pattern_mode_frame, text="Pattern (gecikmeler ms, '-' ile ayrılmış):")
        pattern_lbl.grid(row=0, column=0, sticky="w", columnspan=2)
        pattern_entry = ttk.Entry(self.pattern_mode_frame, textvariable=self.click_pattern_var, width=30) # Wider entry
        pattern_entry.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.settings_widgets.extend([self.pattern_mode_frame, pattern_lbl, pattern_entry])


    def _on_mode_change(self, event=None):
        """Handles UI changes when the click mode is changed."""
        mode = self.cps_mode_var.get()

        # Hide all mode-specific frames first
        self.burst_frame.grid_forget()
        self.random_interval_frame.grid_forget()
        self.pattern_mode_frame.grid_forget()
        # Add other mode-specific frames here to hide them

        # Default CPS title
        cps_title = "Hedef Hız (CPS):" # Default for Sabit
        show_main_cps_scale = True

        if mode == "Sabit":
            cps_title = "Hedef Hız (CPS):"
        elif mode == "Dalgalı (Sinüs)":
            cps_title = "Ortalama Hız (CPS):"
        elif mode == "Patlama":
            cps_title = "Zirve Hız (CPS):"
            self.burst_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=5)
        elif mode == "Gerçekçi (Perlin)":
            cps_title = "Ortalama Hız (CPS):"
        elif mode == "Rastgele Aralık":
            cps_title = "Referans Max CPS:" # Main CPS scale can act as a reference or default max
            self.random_interval_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=5)
            # Optionally, you could link self.max_cps_random_var to self.cps_var here or in get_current_settings
        elif mode == "Pattern (Desen)":
            cps_title = "Referans Jitter/Diğer Ayarlar İçin CPS:" # Main CPS scale less relevant for Pattern delays
            show_main_cps_scale = False # Hide main CPS scale as it's not directly used for delays
            self.pattern_mode_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=5)

        self.cps_title_label.config(text=cps_title)

        # Show/hide the main CPS scale and its label based on mode
        if show_main_cps_scale:
            self.cps_title_label.grid()
            self.cps_scale.grid()
            self.cps_label_display.grid()
        else:
            self.cps_title_label.grid_remove()
            self.cps_scale.grid_remove()
            self.cps_label_display.grid_remove()

        self.app_core.on_mode_changed(mode)


    def _update_cps_label_display(self, value):
        self.cps_label_display.config(text=f"{float(value):.1f} CPS")

    def update_status_display(self, status_text, color, is_running):
        """Updates the status label, button text, and enables/disables settings."""
        font_weight = "bold" if "ÇALIŞIYOR" in status_text else "normal"
        self.status_label.config(text=status_text, foreground=color, font=("Segoe UI", 16, font_weight))

        self.toggle_button.config(text="Durdur" if is_running else "Başlat")

        widget_state = "disabled" if is_running else "normal"
        for widget in self.settings_widgets:
            try:
                # Comboboxes need 'state' handled carefully if they are 'readonly'
                if isinstance(widget, ttk.Combobox) and widget.cget('state') == 'readonly':
                    if is_running:
                        widget.config(state="disabled") # Temporarily disable
                    else:
                        widget.config(state="readonly") # Restore to readonly
                else:
                    widget.config(state=widget_state)
            except (tk.TclError, AttributeError):
                pass # Some widgets (like Frames) might not have a 'state'

    def update_realtime_cps(self, cps):
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

    def get_current_settings(self) -> dict:
        """Returns a dictionary of the current UI settings."""
        settings = {
            'peak_cps': self.cps_var.get(),
            'timing_rand_ms': self.timing_rand_var.get(), # Will be converted to int in core
            'jitter_px': self.jitter_intensity_var.get(),    # Will be converted to int in core
            'mouse_button_pref': self.mouse_button_var.get(), # e.g., "Sol Tık", "Sağ Tık", "Sol ve Sağ Tık"
            'mode': self.cps_mode_var.get()
        }
        if settings['mode'] == 'Patlama':
            settings['burst_duration'] = self.burst_duration_var.get() # Will be converted to float
        elif settings['mode'] == 'Rastgele Aralık':
            settings['min_cps_random'] = self.min_cps_random_var.get() # Converted to float in core
            settings['max_cps_random'] = self.max_cps_random_var.get() # Converted to float in core
        elif settings['mode'] == 'Pattern (Desen)':
            settings['click_pattern'] = self.click_pattern_var.get() # Parsed in click_mode

        # Add other mode-specific settings here
        return settings

if __name__ == '__main__':
    # This part is for testing the UI independently.
    # It won't run when ui.py is imported.
    class MockAppCore:
        def toggle_clicking(self): print("Toggle Clicking")
        def set_assign_mode(self): print("Set Assign Mode")
        def emergency_shutdown(self): print("Emergency Shutdown"); app.destroy(); sys.exit()
        def on_mode_changed(self, mode_name): print(f"Mode changed to: {mode_name}")

    core = MockAppCore()
    app = AutoClickerUI(core)
    app.mainloop()
