import pyautogui
pyautogui.PAUSE = 0  # Otomatik beklemeyi kaldır
pyautogui.FAILSAFE = False  # Failsafe özelliğini kapat

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
import sys
import math
from pynput import keyboard
from perlin_noise import PerlinNoise # YENİ: Perlin gürültüsü için import

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

class JitterClickerApp(tk.Tk):
    """Gelişmiş tıklama profillerine sahip ana uygulama sınıfı."""
    def __init__(self):
        super().__init__()
        self.title("Gerçekçi Jitter Simülatörü v4.0"); self.geometry("450x680"); self.resizable(False, False)
        style = ttk.Style(self); style.theme_use('vista' if 'win' in sys.platform else 'clam')

        self.is_running = False; self.click_thread = None; self.trigger_key = None
        self.is_assigning_key = False; self.click_count = 0
        
        # YENİ: Perlin Gürültüsü motorları (farklı seed'lerle daha zengin desenler)
        self.noise_x = PerlinNoise(octaves=4, seed=random.randint(1, 1000))
        self.noise_y = PerlinNoise(octaves=4, seed=random.randint(1, 1000))
        self.noise_cps = PerlinNoise(octaves=2, seed=random.randint(1, 1000))

        self._create_widgets()
        self._start_keyboard_listener()
        self.protocol("WM_DELETE_WINDOW", self.emergency_shutdown)
        self._on_mode_change()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20"); main_frame.pack(fill="both", expand=True)

        self.status_label = ttk.Label(main_frame, text=STATUS_IDLE, font=("Segoe UI", 16, "bold"), anchor="center")
        self.status_label.pack(pady=(0, 10), fill="x")
        
        self.real_time_cps_label = ttk.Label(main_frame, text="Anlık CPS: 0.0", font=("Segoe UI", 12, "italic"), anchor="center", foreground=COLOR_BLUE)
        self.real_time_cps_label.pack(pady=(0, 10), fill="x")

        settings_frame = ttk.LabelFrame(main_frame, text="Ayarlar", padding="15"); settings_frame.pack(fill="x", expand=True)
        settings_frame.columnconfigure(1, weight=1)
        self.settings_widgets = []

        # YENİ: Gerçekçi mod eklendi
        self.cps_mode_var = tk.StringVar(value="Sabit")
        mode_lbl = ttk.Label(settings_frame, text="Tıklama Modu:")
        mode_lbl.grid(row=0, column=0, sticky="w", pady=5)
        self.mode_combo = ttk.Combobox(settings_frame, textvariable=self.cps_mode_var, values=["Sabit", "Dalgalı (Sinüs)", "Patlama", "Gerçekçi (Perlin)"], state="readonly")
        self.mode_combo.grid(row=0, column=1, sticky="ew", pady=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)
        Tooltip(mode_lbl, "Sabit: Belirlenen hızda sürekli tıklar.\nDalgalı: Sinüs dalgasıyla hızı değiştirir.\nPatlama: Kısa süreliğine maksimum hıza çıkar.\nGerçekçi: Perlin gürültüsü ile organik hız ve jitter simülasyonu yapar.")
        self.settings_widgets.extend([mode_lbl, self.mode_combo])

        self.cps_var = tk.DoubleVar(value=15.0)
        self.cps_title_label = ttk.Label(settings_frame, text="Hedef Hız (CPS):")
        self.cps_title_label.grid(row=1, column=0, sticky="w", pady=5)
        self.cps_scale = ttk.Scale(settings_frame, from_=1, to=40, orient="horizontal", variable=self.cps_var, command=self._update_cps_label)
        self.cps_scale.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0,5))
        self.cps_label = ttk.Label(settings_frame, text=f"{self.cps_var.get():.1f} CPS")
        self.cps_label.grid(row=1, column=1, sticky="e")
        self.settings_widgets.extend([self.cps_title_label, self.cps_scale, self.cps_label])
        
        self._create_mode_settings(settings_frame)
        
        # YENİ: Ayarların başlayacağı satır indeksi daha dinamik hale getirildi.
        common_settings_row = 4
        
        self.timing_rand_var = tk.StringVar(value="15"); timing_lbl = ttk.Label(settings_frame, text="Zamanlama Rastgeleliği (± ms):")
        timing_lbl.grid(row=common_settings_row, column=0, sticky="w", pady=5)
        timing_entry = ttk.Entry(settings_frame, textvariable=self.timing_rand_var, width=12); timing_entry.grid(row=common_settings_row, column=1, sticky="e")
        self.settings_widgets.extend([timing_lbl, timing_entry])

        self.jitter_intensity_var = tk.StringVar(value="3"); jitter_lbl = ttk.Label(settings_frame, text="Jitter Yoğunluğu (Piksel):")
        jitter_lbl.grid(row=common_settings_row+1, column=0, sticky="w", pady=5)
        jitter_entry = ttk.Entry(settings_frame, textvariable=self.jitter_intensity_var, width=12); jitter_entry.grid(row=common_settings_row+1, column=1, sticky="e")
        self.settings_widgets.extend([jitter_lbl, jitter_entry])

        self.mouse_button_var = tk.StringVar(value="Sol Tık"); mouse_lbl = ttk.Label(settings_frame, text="Fare Tuşu:");
        mouse_lbl.grid(row=common_settings_row+2, column=0, sticky="w", pady=5)
        button_combo = ttk.Combobox(settings_frame, textvariable=self.mouse_button_var, values=["Sol Tık", "Sağ Tık"], state="readonly", width=10); button_combo.grid(row=common_settings_row+2, column=1, sticky="e"); button_combo.set("Sol Tık")
        self.settings_widgets.extend([mouse_lbl, button_combo])

        control_frame = ttk.LabelFrame(main_frame, text="Kontrol", padding="15"); control_frame.pack(fill="x", pady=(20, 10))
        control_frame.columnconfigure((0, 1), weight=1)
        self.toggle_button = ttk.Button(control_frame, text="Başlat", command=self.toggle_clicking); self.toggle_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        assign_button = ttk.Button(control_frame, text="Tetikleyici Tuş Ata", command=self._set_assign_mode); assign_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.trigger_key_label = ttk.Label(control_frame, text=KEY_NOT_ASSIGNED, foreground=COLOR_RED, font=("Segoe UI", 10, "bold"), width=20, anchor="center", relief="sunken", padding=5); self.trigger_key_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.settings_widgets.append(assign_button)
        
        self.click_count_label = ttk.Label(main_frame, text="Toplam Tıklama: 0", font=("Segoe UI", 10), anchor="center"); self.click_count_label.pack(pady=(10, 0), fill="x")
        ttk.Label(main_frame, text="\nAcil Kapatma:  F12 TUŞU", foreground=COLOR_RED, font=("Segoe UI", 10, "italic"), anchor="center").pack(pady=(10,0), fill='x')

    def _create_mode_settings(self, parent):
        self.burst_frame = ttk.Frame(parent)
        self.burst_duration_var = tk.StringVar(value="5")
        burst_lbl = ttk.Label(self.burst_frame, text="Patlama Süresi (sn):")
        burst_lbl.grid(row=0, column=0, sticky="w")
        burst_entry = ttk.Entry(self.burst_frame, textvariable=self.burst_duration_var, width=12)
        burst_entry.grid(row=0, column=1, sticky="e")
        self.settings_widgets.extend([self.burst_frame, burst_lbl, burst_entry])

    def _on_mode_change(self, event=None):
        mode = self.cps_mode_var.get()
        self.burst_frame.grid_forget()

        title_map = {
            "Sabit": "Hedef Hız (CPS):", "Dalgalı (Sinüs)": "Ortalama Hız (CPS):",
            "Patlama": "Zirve Hız (CPS):", "Gerçekçi (Perlin)": "Ortalama Hız (CPS):"
        }
        self.cps_title_label.config(text=title_map.get(mode, "Hız (CPS):"))
        
        if mode == "Patlama":
            self.burst_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=5)

    def _update_cps_label(self, value):
        self.cps_label.config(text=f"{float(value):.1f} CPS")

    def _set_program_state(self, running: bool):
        self.is_running = running
        state_map = {True: ("Durdur", STATUS_RUNNING, COLOR_GREEN, "disabled"), False: ("Başlat", STATUS_STOPPED if self.click_thread else STATUS_IDLE, COLOR_BLACK, "normal")}
        self.toggle_button.config(text=state_map[running][0])
        self._update_status(state_map[running][1], state_map[running][2])
        for widget in self.settings_widgets:
            try: widget.config(state=state_map[running][3])
            except (tk.TclError, AttributeError): pass
        
    def _update_status(self, text, color):
        font_weight = "bold" if "ÇALIŞIYOR" in text else "normal"
        self.status_label.config(text=text, foreground=color, font=("Segoe UI", 16, font_weight))
    
    def start_clicking(self):
        if self.is_running: return
        if not self.trigger_key: return messagebox.showwarning("Hata", "Lütfen önce bir tetikleyici tuş atayın!")
            
        try:
            params = {
                'peak_cps': self.cps_var.get(), 'timing_rand_ms': int(self.timing_rand_var.get()),
                'jitter_px': int(self.jitter_intensity_var.get()),
                'mouse_button': 'left' if self.mouse_button_var.get() == "Sol Tık" else 'right',
                'mode': self.cps_mode_var.get()
            }
            if params['mode'] == 'Patlama':
                params['burst_duration'] = float(self.burst_duration_var.get())
                if params['burst_duration'] <= 0: raise ValueError("Patlama süresi pozitif olmalı.")
        except (ValueError, TypeError) as e:
            self._update_status(STATUS_ERROR, COLOR_RED); messagebox.showerror("Geçersiz Girdi", f"Lütfen ayarları kontrol edin.\nHata: {e}"); return

        self.click_count = 0; self._update_click_count_label()
        self._set_program_state(True)
        self.click_thread = threading.Thread(target=self._click_loop, args=(params,), daemon=True)
        self.click_thread.start()

    def _click_loop(self, params: dict):
        start_time = time.time()
        time_counter = 0.0 # YENİ: Perlin gürültüsü için zaman sayacı
        
        while self.is_running:
            try:
                current_cps, jitter_x, jitter_y = 0, 0, 0
                elapsed_time = time.time() - start_time
                mode = params['mode']
                peak_cps = params['peak_cps']
                jitter_intensity = params['jitter_px']

                if mode == 'Sabit':
                    current_cps = peak_cps
                    jitter_x = random.randint(-jitter_intensity, jitter_intensity)
                    jitter_y = random.randint(-jitter_intensity, jitter_intensity)
                
                elif mode == 'Dalgalı (Sinüs)':
                    fluctuation = math.sin(elapsed_time * 1.5) * (peak_cps * 0.25)
                    current_cps = peak_cps + fluctuation
                    jitter_x = random.randint(-jitter_intensity, jitter_intensity)
                    jitter_y = random.randint(-jitter_intensity, jitter_intensity)
                
                elif mode == 'Patlama':
                    duration, ramp_time, peak_time = params['burst_duration'], duration * 0.3, duration - (2 * (duration * 0.3))
                    if elapsed_time < ramp_time: current_cps = (elapsed_time / ramp_time) * peak_cps
                    elif elapsed_time < ramp_time + peak_time: current_cps = peak_cps
                    elif elapsed_time < duration: current_cps = (1 - (elapsed_time - ramp_time - peak_time) / ramp_time) * peak_cps
                    else: self.after(0, self.stop_clicking); break
                    jitter_x = random.randint(-jitter_intensity, jitter_intensity)
                    jitter_y = random.randint(-jitter_intensity, jitter_intensity)

                # --- YENİ: Gerçekçi Perlin Gürültüsü Modu ---
                elif mode == 'Gerçekçi (Perlin)':
                    # CPS'i Perlin gürültüsü ile dalgalandır
                    # Gürültü fonksiyonu -0.5 ile 0.5 arası değer verir. Bunu CPS'e uygun aralığa çekiyoruz.
                    cps_noise = self.noise_cps(time_counter) # time_counter yavaşça artarak gürültüde gezinmemizi sağlar
                    cps_fluctuation = cps_noise * (peak_cps * 0.4) # Ortalama CPS'in %40'ı kadar dalgalansın
                    current_cps = peak_cps + cps_fluctuation

                    # Jitter'ı 2D Perlin gürültüsü ile oluştur
                    # Bu, imlecin rastgele zıplaması yerine küçük, dairesel/akışkan yollar çizmesini sağlar
                    jitter_x = self.noise_x(time_counter) * jitter_intensity
                    jitter_y = self.noise_y(time_counter) * jitter_intensity
                
                current_cps = max(0.1, current_cps)
                self.after(0, self._update_realtime_cps, current_cps)

                pos = pyautogui.position()
                pyautogui.click(x=pos.x + int(jitter_x), y=pos.y + int(jitter_y), button=params['mouse_button'])
                
                self.click_count += 1
                self.after(0, self._update_click_count_label)
                
                base_delay = 1.0 / current_cps
                rand_delay = random.uniform(-params['timing_rand_ms']/1000.0, params['timing_rand_ms']/1000.0)
                actual_delay = max(0.001, base_delay + rand_delay)
                
                # Hassas bekleme: time.sleep yerine busy-wait
                target_time = time.perf_counter() + actual_delay
                while time.perf_counter() < target_time:
                    pass
                time_counter += actual_delay * 0.5 # Gürültüdeki ilerleme hızını ayarlar

            except Exception as e:
                print(f"Click Loop Hatası: {e}")
                self.after(0, self.stop_clicking); break
    
    # Kalan fonksiyonlar aynı kaldığı için kısaltıldı
    def stop_clicking(self):
        if not self.is_running: return
        self._set_program_state(False)

    def toggle_clicking(self):
        if self.is_running: self.stop_clicking()
        else: self.start_clicking()

    def _update_realtime_cps(self, cps):
        self.real_time_cps_label.config(text=f"Anlık CPS: {cps:.1f}")

    def _update_click_count_label(self):
        self.click_count_label.config(text=f"Toplam Tıklama: {self.click_count}")

    def _set_assign_mode(self):
        self.is_assigning_key = True; self.trigger_key_label.config(text=ASSIGN_KEY_PROMPT, foreground=COLOR_BLUE)

    def _assign_key(self, key):
        def format_key_name(k):
            if hasattr(k, 'char') and k.char: return k.char.upper()
            if hasattr(k, 'name'): return k.name.upper()
            return str(k).split('.')[-1].upper()

        if not self.is_assigning_key: return
        self.is_assigning_key = False
        if key == keyboard.Key.esc:
            if self.trigger_key: self.trigger_key_label.config(text=format_key_name(self.trigger_key), foreground=COLOR_GREEN)
            else: self.trigger_key_label.config(text=KEY_NOT_ASSIGNED, foreground=COLOR_RED)
            return
        self.trigger_key = key; self.trigger_key_label.config(text=format_key_name(key), foreground=COLOR_GREEN)

    def _start_keyboard_listener(self):
        listener = keyboard.Listener(on_press=self._on_press); listener.daemon = True; listener.start()

    def _on_press(self, key):
        if key == keyboard.Key.f12: self.emergency_shutdown(); return
        def process():
            if self.is_assigning_key: self._assign_key(key)
            elif self.trigger_key and key == self.trigger_key: self.toggle_clicking()
        self.after(0, process)

    def emergency_shutdown(self):
        print("Acil Durum Kapatma... Program sonlandırılıyor..."); self.is_running = False
        self.destroy(); sys.exit()

if __name__ == "__main__":
    app_instance = JitterClickerApp()
    app_instance.mainloop()
