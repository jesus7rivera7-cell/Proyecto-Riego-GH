#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Simulación de Riego Inteligente - BioFlow Python Edition
Simulación dinámica y variable en tiempo real del clima y la humedad del suelo.
"""

import os
import sys
import time
import math
import random
from datetime import datetime, timedelta
import json
import threading
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configuración del terminal de Windows para interpretar secuencias ANSI de color
if sys.platform == "win32":
    import ctypes
    import msvcrt
    kernel32 = ctypes.windll.kernel32
    # Habilitar ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x0004) y ENABLE_PROCESSED_OUTPUT (0x0001)
    # GetStdHandle(-11) obtiene la salida estándar
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
else:
    # Soporte para Unix si se ejecuta en otra plataforma
    import select
    import tty
    import termios

# Colores y Formato ANSI
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN = "\033[96m"
C_WHITE = "\033[97m"
C_GRAY = "\033[90m"

# Fondos ANSI
BG_DARK = "\033[48;5;234m"

# Configuración de Climas / Eventos Climáticos
WEATHER_EVENTS = {
    "DESPEJADO": {
        "name": "Soleado / Despejado",
        "icon": "☀️ ",
        "color": C_YELLOW,
        "temp_offset": 0.0,       # Sin offset sobre la curva normal
        "light_scale": 1.0,       # Luz solar completa
        "rain_rate": 0.0,         # Sin lluvia
        "description": "Cielo completamente despejado, sol directo."
    },
    "NUBLADO": {
        "name": "Nublado",
        "icon": "☁️ ",
        "color": C_GRAY,
        "temp_offset": -3.5,      # Nublado refresca el ambiente
        "light_scale": 0.25,      # La luz solar se reduce a la cuarta parte
        "rain_rate": 0.0,         # Sin lluvia
        "description": "Nubes densas cubren el cielo."
    },
    "LLOVIZNA": {
        "name": "Llovizna Constante",
        "icon": "🌧️ ",
        "color": C_BLUE,
        "temp_offset": -5.0,      # La lluvia enfría el ambiente
        "light_scale": 0.1,       # Muy poca luz solar
        "rain_rate": 0.15,        # Humedad sube +0.15% por minuto simulado
        "description": "Lluvia fina y constante humedece el suelo."
    },
    "TORMENTA": {
        "name": "Tormenta Eléctrica",
        "icon": "⛈️ ",
        "color": C_RED,
        "temp_offset": -8.0,      # Descenso térmico severo
        "light_scale": 0.05,      # Prácticamente a oscuras
        "rain_rate": 0.45,        # Rápida inundación del suelo (+0.45% por min)
        "description": "Lluvia torrencial y tormenta eléctrica activa."
    },
    "OLA_DE_CALOR": {
        "name": "Ola de Calor Extrema",
        "icon": "🔥",
        "color": C_MAGENTA,
        "temp_offset": 8.5,       # Incremento térmico drástico
        "light_scale": 1.15,      # Radiación solar máxima (ligeramente aumentada)
        "rain_rate": 0.0,         # Sequedad absoluta
        "description": "Temperaturas sofocantes e insolación extrema."
    }
}

class SimulatorHTTPRequestHandler(BaseHTTPRequestHandler):
    simulator = None

    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            # Clean terminal ANSI codes from logs
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_logs = [ansi_escape.sub('', log) for log in self.simulator.logs]
            
            status = {
                "moisture": round(self.simulator.moisture, 2),
                "temperature": round(self.simulator.temperature, 2),
                "light": round(self.simulator.light, 2),
                "sim_time": self.simulator.sim_time.strftime("%Y-%m-%d %H:%M:%S"),
                "speed_multiplier": self.simulator.speed_multiplier,
                "current_weather_key": self.simulator.current_weather_key,
                "weather_name": WEATHER_EVENTS[self.simulator.current_weather_key]["name"],
                "weather_description": WEATHER_EVENTS[self.simulator.current_weather_key]["description"],
                "weather_icon": WEATHER_EVENTS[self.simulator.current_weather_key]["icon"].strip(),
                "climate_override": self.simulator.climate_override,
                "auto_mode": self.simulator.auto_mode,
                "pump_active": self.simulator.pump_active,
                "led_green": self.simulator.led_green,
                "led_red": self.simulator.led_red,
                "logs": clean_logs
            }
            self.wfile.write(json.dumps(status).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/control':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                if "auto_mode" in data:
                    self.simulator.auto_mode = bool(data["auto_mode"])
                    mode_name = "Automático (Firmware)" if self.simulator.auto_mode else "Manual (Override)"
                    self.simulator.add_log(f"Modo cambiado a: {mode_name} (API)")
                    if not self.simulator.auto_mode:
                        self.simulator.pump_active = False
                
                if "pump_active" in data and not self.simulator.auto_mode:
                    self.simulator.pump_active = bool(data["pump_active"])
                    state_str = "ENCENDIDA" if self.simulator.pump_active else "APAGADA"
                    self.simulator.add_log(f"Bomba conmutada: {state_str} (API)")
                
                if "force_weather" in data:
                    weather_key = data["force_weather"]
                    if weather_key in WEATHER_EVENTS:
                        self.simulator.force_weather_event(weather_key)
                
                if "climate_override" in data and not data["climate_override"]:
                    self.simulator.climate_override = False
                    self.simulator.add_log("Clima dinámico natural activado (API)")
                
                if "speed_multiplier" in data:
                    val = int(data["speed_multiplier"])
                    if 0 <= val <= 86400:
                        self.simulator.speed_multiplier = val
                        self.simulator.add_log(f"Velocidad: {val}x (API)")
                        
                if "moisture" in data and not self.simulator.auto_mode:
                    self.simulator.moisture = max(0.0, min(100.0, float(data["moisture"])))
                    
                if "temperature" in data and self.simulator.climate_override:
                    self.simulator.temperature = max(-15.0, min(50.0, float(data["temperature"])))
                    
                if "light" in data and self.simulator.climate_override:
                    self.simulator.light = max(0.0, min(100.0, float(data["light"])))

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


def start_api_server(simulator, port=5000):
    SimulatorHTTPRequestHandler.simulator = simulator
    server_address = ('', port)
    try:
        httpd = HTTPServer(server_address, SimulatorHTTPRequestHandler)
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        simulator.add_log(f"Servidor API en puerto {port}")
    except Exception as e:
        simulator.add_log(f"Err API: {str(e)}")


class SmartIrrigationSimulator:
    def __init__(self):
        # Estado del entorno
        self.moisture = 45.0          # Porcentaje inicial (0-100)
        self.temperature = 22.0       # Temperatura inicial en °C
        self.light = 60.0             # Porcentaje inicial de luz (0-100)
        
        # Ruido climático acumulado (Random Walk)
        self.noise_temp = 0.0
        self.noise_light = 0.0
        
        # Parámetros del Reloj Simulador
        self.sim_time = datetime(2026, 8, 1, 12, 0, 0)
        self.speed_multiplier = 600   # 1 seg real = 10 minutos simulados (0.1 seg = 1 minuto simulado)
        self.running = True
        
        # Clima inicial
        self.current_weather_key = "DESPEJADO"
        self.weather_duration = 360   # Duración restante del evento en minutos simulados
        self.climate_override = False # True si el usuario forzó el clima
        
        # Controlador y actuadores
        self.auto_mode = True
        self.pump_active = False
        self.led_green = False
        self.led_red = False
        
        # Historial y animaciones
        self.logs = []
        self.spinner_frames = ["/", "-", "\\", "|"]
        self.spinner_idx = 0
        
        self.add_log("Sistema inicializado. Autómata en marcha.")
        self.add_log("Modo automático activo: Riego si humedad < 40%, apagar a >= 55%.")
        start_api_server(self)

    def add_log(self, message):
        timestamp = self.sim_time.strftime("%H:%M")
        self.logs.append(f"[{C_CYAN}{timestamp}{C_RESET}] {message}")
        if len(self.logs) > 6:
            self.logs.pop(0)

    def get_keypress(self):
        """Lectura no bloqueante del teclado (específica de Windows/Unix)"""
        if sys.platform == "win32":
            if msvcrt.kbhit():
                try:
                    return msvcrt.getch().decode("utf-8").lower()
                except UnicodeDecodeError:
                    return None
        else:
            # Implementación no bloqueante básica para Linux/Mac
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            if dr:
                return sys.stdin.read(1).lower()
        return None

    def update_weather_event(self, elapsed_minutes):
        """Controla el paso de eventos climáticos naturales"""
        if self.climate_override:
            return  # Si está anulado por el usuario, no cambiar automáticamente

        self.weather_duration -= elapsed_minutes
        if self.weather_duration <= 0:
            # Seleccionar un nuevo evento climático al azar
            keys = list(WEATHER_EVENTS.keys())
            # Mayor probabilidad de Despejado/Nublado que Tormenta u Ola de Calor
            weights = [0.4, 0.3, 0.15, 0.08, 0.07]
            new_key = random.choices(keys, weights=weights)[0]
            
            if new_key != self.current_weather_key:
                old_name = WEATHER_EVENTS[self.current_weather_key]["name"]
                new_name = WEATHER_EVENTS[new_key]["name"]
                self.current_weather_key = new_key
                self.add_log(f"El clima cambió de {old_name} a {C_YELLOW}{new_name}{C_RESET}.")
            
            # Duración aleatoria del evento (de 4 a 12 horas simuladas)
            self.weather_duration = random.randint(240, 720)

    def force_weather_event(self, key):
        if key in WEATHER_EVENTS:
            self.current_weather_key = key
            self.climate_override = True
            self.add_log(f"Clima FORZADO por usuario: {C_BOLD}{WEATHER_EVENTS[key]['name']}{C_RESET}.")

    def simulate_physics(self, elapsed_minutes):
        """Aplica las ecuaciones físicas del clima y el suelo usando delta time"""
        # 1. Obtener la hora del día como decimal
        hour = self.sim_time.hour + self.sim_time.minute / 60.0 + self.sim_time.second / 3600.0
        
        # 2. Curva base de temperatura diurna (sinusoide con máximo a las 15:00 y mínimo a las 03:00)
        temp_base = 22.0 + 8.0 * math.cos(2.0 * math.pi * (hour - 15.0) / 24.0)
        
        # 3. Curva base de radiación solar / luz (máximo al mediodía, cero en la noche)
        sunrise, sunset = 6.0, 19.0
        if sunrise <= hour <= sunset:
            day_length = sunset - sunrise
            relative_time = hour - sunrise
            light_base = 100.0 * math.sin(math.pi * relative_time / day_length)
        else:
            light_base = 0.0

        # 4. Modificar según el evento climático actual
        weather = WEATHER_EVENTS[self.current_weather_key]
        temp_target = temp_base + weather["temp_offset"]
        light_target = light_base * weather["light_scale"]

        # 5. Ruido Natural (Random Walk filtrado para evitar derivas infinitas)
        # El ruido se actualiza en cada paso y se suaviza hacia cero para mantener la estabilidad
        self.noise_temp = (self.noise_temp * 0.95) + random.uniform(-0.4, 0.4)
        self.noise_light = (self.noise_light * 0.95) + random.uniform(-3.0, 3.0)
        
        # Acotar los rangos de ruido
        self.noise_temp = max(-3.0, min(3.0, self.noise_temp))
        self.noise_light = max(-15.0, min(15.0, self.noise_light))

        # Clima final
        self.temperature = max(-15.0, min(50.0, temp_target + self.noise_temp))
        self.light = max(0.0, min(100.0, light_target + self.noise_light))

        # 6. Física de la humedad del suelo (Higrómetro)
        if self.pump_active:
            # Bomba encendida: El suelo absorbe agua de forma constante (+1.8% por minuto simulado)
            watering_rate = 1.8
            self.moisture += watering_rate * elapsed_minutes
        
        if weather["rain_rate"] > 0:
            # Llueve: Aporte de humedad natural de la precipitación
            self.moisture += weather["rain_rate"] * elapsed_minutes

        if not self.pump_active and weather["rain_rate"] == 0:
            # Secado por Evaporación (Depende fuertemente de la temperatura y la radiación solar)
            base_evap = 0.015
            temp_factor = 0.003 * max(0.0, self.temperature)
            light_factor = 0.001 * self.light
            evap_rate = base_evap + temp_factor + light_factor
            
            # En ola de calor extremo la evaporación se acelera un 50%
            if self.current_weather_key == "OLA_DE_CALOR":
                evap_rate *= 1.5
                
            self.moisture -= evap_rate * elapsed_minutes

        # Restringir la humedad entre 0 y 100%
        self.moisture = max(0.0, min(100.0, self.moisture))

    def run_controller(self):
        """Emula el bucle del firmware del microcontrolador"""
        if self.auto_mode:
            # Histéresis: Activar a menos del 40%, apagar al superar o igualar el 55%
            if self.moisture < 40.0:
                if not self.pump_active:
                    self.pump_active = True
                    self.add_log("Microcontrolador: Humedad baja detectada. RIEGO ACTIVADO.")
            elif self.moisture >= 55.0:
                if self.pump_active:
                    self.pump_active = False
                    self.add_log("Microcontrolador: Humedad óptima alcanzada. RIEGO DETENIDO.")
        
        # LEDs de estado
        if self.pump_active:
            self.led_red = True
            self.led_green = False
        else:
            self.led_red = False
            self.led_green = True

    def process_keyboard(self):
        key = self.get_keypress()
        if not key:
            return

        if key == "q":
            self.running = False
            self.add_log("Deteniendo simulador...")
        elif key == "m":
            self.auto_mode = not self.auto_mode
            mode_name = "Automático (Firmware)" if self.auto_mode else "Manual (Override)"
            self.add_log(f"Modo de riego cambiado a: {C_BOLD}{mode_name}{C_RESET}.")
            if not self.auto_mode:
                self.pump_active = False  # Apagar preventivo al cambiar a manual
        elif key == "p":
            if not self.auto_mode:
                self.pump_active = not self.pump_active
                state_str = "ENCENDIDA" if self.pump_active else "APAGADA"
                self.add_log(f"Bomba conmutada manualmente: {C_BOLD}{state_str}{C_RESET}.")
            else:
                self.add_log(f"{C_RED}Advertencia:{C_RESET} Desactiva el modo Auto (presiona 'm') para conmutar la bomba.")
        elif key == "c":
            self.climate_override = False
            self.add_log("Restablecido control climático dinámico natural.")
        elif key == "+":
            # Aumentar velocidad
            if self.speed_multiplier < 3600:
                self.speed_multiplier += 150
                self.add_log(f"Velocidad acelerada a: {self.speed_multiplier}x.")
        elif key == "-":
            # Disminuir velocidad
            if self.speed_multiplier > 60:
                self.speed_multiplier -= 150
                self.add_log(f"Velocidad reducida a: {self.speed_multiplier}x.")
        elif key == "1":
            self.force_weather_event("DESPEJADO")
        elif key == "2":
            self.force_weather_event("NUBLADO")
        elif key == "3":
            self.force_weather_event("LLOVIZNA")
        elif key == "4":
            self.force_weather_event("TORMENTA")
        elif key == "5":
            self.force_weather_event("OLA_DE_CALOR")

    def make_progress_bar(self, value, min_val, max_val, length=22, color=C_RESET):
        """Dibuja una barra de progreso limpia con colores de la terminal"""
        span = max_val - min_val
        val_clamped = max(min_val, min(max_val, value))
        percentage = (val_clamped - min_val) / span
        filled_len = int(round(length * percentage))
        
        bar = "█" * filled_len + "░" * (length - filled_len)
        return f"{color}[{bar}]{C_RESET}"

    def render_ui(self):
        """Dibuja la interfaz visual de consola estilo dashboard"""
        # Limpiar consola (ANSI home position)
        sys.stdout.write("\033[H")
        
        # Animación del motor
        if self.pump_active:
            self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
            spinner_char = self.spinner_frames[self.spinner_idx]
        else:
            spinner_char = "●"

        # Tasa de evaporación actual estimada para mostrar en pantalla
        base_evap = 0.015
        temp_factor = 0.003 * max(0.0, self.temperature)
        light_factor = 0.001 * self.light
        current_evap_rate = (base_evap + temp_factor + light_factor) * 60.0  # tasa por hora
        if WEATHER_EVENTS[self.current_weather_key]["rain_rate"] > 0:
            current_evap_rate = 0.0
        elif self.current_weather_key == "OLA_DE_CALOR":
            current_evap_rate *= 1.5

        # Colores e íconos dinámicos del clima
        weather = WEATHER_EVENTS[self.current_weather_key]
        weather_icon = weather["icon"]
        weather_color = weather["color"]
        weather_name = weather["name"]
        
        # Formatear fecha y hora
        time_str = self.sim_time.strftime("%d/%m/%Y %H:%M:%S")

        # Dibujo del Dashboard en la Terminal
        print(f"{C_BOLD}{C_GREEN}┌──────────────────────────────────────────────────────────────────────────┐{C_RESET}")
        print(f"{C_BOLD}{C_GREEN}│          BioFlow v2.0 - Dashboard de Simulación de Riego Python          │{C_RESET}")
        print(f"{C_BOLD}{C_GREEN}└──────────────────────────────────────────────────────────────────────────┘{C_RESET}")
        
        print(f" {C_BOLD}Fecha y Hora Simulada:{C_RESET} {C_WHITE}{time_str}{C_RESET}   |   {C_BOLD}Velocidad:{C_RESET} {C_CYAN}{self.speed_multiplier}x{C_RESET}")
        print(f" {C_BOLD}Estado Climático:     {C_RESET} {weather_color}{weather_icon} {weather_name}{C_RESET}")
        print(f" {C_BOLD}Comportamiento:       {C_RESET} {C_GRAY}{weather['description']}{C_RESET}")
        print(f" {C_BOLD}Control Clima:        {C_RESET} {'[Manual Override]' if self.climate_override else '[Natural/Dinámico]'}")
        print(f"{C_GRAY}────────────────────────────────────────────────────────────────────────────{C_RESET}")
        
        # Fila de Sensores y Gráficos
        print(f" {C_BOLD}SENSORES VIRTUALES:{C_RESET}")
        
        # Humedad
        hum_bar = self.make_progress_bar(self.moisture, 0, 100, color=C_BLUE)
        hum_lbl = f"{self.moisture:5.1f}%"
        if self.moisture < 40.0:
            hum_status = f"{C_RED}Seco (Crítico){C_RESET}"
        elif 40.0 <= self.moisture <= 60.0:
            hum_status = f"{C_GREEN}Adecuada{C_RESET}"
        else:
            hum_status = f"{C_CYAN}Muy Húmedo{C_RESET}"
        print(f"  ● Humedad del Suelo (A0): {hum_bar} {C_BOLD}{hum_lbl}{C_RESET} ({hum_status})")
        
        # Temperatura
        temp_bar = self.make_progress_bar(self.temperature, -10, 45, color=C_RED)
        temp_lbl = f"{self.temperature:5.1f} °C"
        if self.temperature < 15.0:
            temp_status = f"{C_BLUE}Frío{C_RESET}"
        elif 15.0 <= self.temperature <= 32.0:
            temp_status = f"{C_YELLOW}Templado{C_RESET}"
        else:
            temp_status = f"{C_RED}Caliente (Estrés){C_RESET}"
        print(f"  ● Temperatura (A1):       {temp_bar} {C_BOLD}{temp_lbl}{C_RESET} ({temp_status})")
        
        # Luz
        light_bar = self.make_progress_bar(self.light, 0, 100, color=C_YELLOW)
        light_lbl = f"{self.light:5.1f}%"
        if self.light < 30.0:
            light_status = f"{C_GRAY}Sombra{C_RESET}"
        elif 30.0 <= self.light <= 75.0:
            light_status = f"{C_YELLOW}Semisombra{C_RESET}"
        else:
            light_status = f"{C_WHITE}{C_BOLD}Sol Directo{C_RESET}"
        print(f"  ● Luz Solar / LDR (A2):   {light_bar} {C_BOLD}{light_lbl}{C_RESET} ({light_status})")
        
        # Fila de Evaporación
        evap_desc = f"{C_YELLOW}-{current_evap_rate:.2f}% / hora sim.{C_RESET}" if current_evap_rate > 0 else f"{C_GREEN}+{weather['rain_rate']*60.0:.2f}% / hora (lluvia){C_RESET}"
        print(f"  ● Dinámica del Suelo:     Tasa neta = {evap_desc}")
        
        print(f"{C_GRAY}────────────────────────────────────────────────────────────────────────────{C_RESET}")
        
        # Actuadores
        print(f" {C_BOLD}ACTUADORES Y HARDWARE SIMULADO:{C_RESET}")
        
        # Modo
        mode_badge = f"{C_GREEN}AUTOMÁTICO{C_RESET}" if self.auto_mode else f"{C_YELLOW}MANUAL{C_RESET}"
        print(f"  ● Modo de Riego:   {C_BOLD}{mode_badge}{C_RESET}")
        
        # Bomba
        bomba_badge = f"{C_RED}ENCENDIDA {C_RESET}" if self.pump_active else f"{C_GRAY}APAGADA   {C_RESET}"
        spinner_color = C_RED if self.pump_active else C_GRAY
        print(f"  ● Bomba de Agua:   {C_BOLD}{bomba_badge}{C_RESET} {spinner_color}[ {spinner_char} ] (~3200 RPM){C_RESET}")
        
        # LEDs
        led_g_status = f"{C_GREEN}● ON{C_RESET}" if self.led_green else f"{C_GRAY}○ OFF{C_RESET}"
        led_r_status = f"{C_RED}● ON{C_RESET}" if self.led_red else f"{C_GRAY}○ OFF{C_RESET}"
        print(f"  ● LEDs en Placa:   [Verde OK: {led_g_status}]  [Rojo Riego: {led_r_status}]")
        
        print(f"{C_GRAY}────────────────────────────────────────────────────────────────────────────{C_RESET}")
        
        # Registro de Logs en Vivo
        print(f" {C_BOLD}LOGS EN VIVO COM1:{C_RESET}")
        print(f" ┌────────────────────────────────────────────────────────────────────────┐")
        for log in self.logs:
            print(f" │ {log:<84} │")
        # Rellenar logs vacíos si hay menos de 6
        for _ in range(6 - len(self.logs)):
            print(f" │ {'':<72} │")
        print(f" └────────────────────────────────────────────────────────────────────────┘")
        
        # Guía de Teclas
        print(f" {C_BOLD}CONTROLES DEL TECLADO:{C_RESET}")
        print(f"  [{C_CYAN}m{C_RESET}] Alternar Automático/Manual | [{C_CYAN}p{C_RESET}] Conmutar Bomba | [{C_CYAN}c{C_RESET}] Volver a Clima Dinámico")
        print(f"  [{C_CYAN}1{C_RESET}] Despejado | [{C_CYAN}2{C_RESET}] Nublado | [{C_CYAN}3{C_RESET}] Llovizna | [{C_CYAN}4{C_RESET}] Tormenta | [{C_CYAN}5{C_RESET}] Ola de Calor")
        print(f"  [{C_CYAN}+{C_RESET}/{C_CYAN}-{C_RESET}] Aumentar/Disminuir velocidad del tiempo | [{C_CYAN}q{C_RESET}] Salir del Simulador")

    def run(self):
        """Bucle principal de la simulación"""
        # Limpiar pantalla al inicio
        os.system("cls" if os.name == "nt" else "clear")
        
        last_tick_time = time.time()
        
        while self.running:
            current_real_time = time.time()
            elapsed_real_seconds = current_real_time - last_tick_time
            last_tick_time = current_real_time
            
            # 1. Avanzar el reloj de la simulación
            simulated_seconds_step = elapsed_real_seconds * self.speed_multiplier
            self.sim_time += timedelta(seconds=simulated_seconds_step)
            
            elapsed_sim_minutes = simulated_seconds_step / 60.0
            
            # 2. Actualizar el clima y su autómata de eventos
            self.update_weather_event(elapsed_sim_minutes)
            self.simulate_physics(elapsed_sim_minutes)
            
            # 3. Lógica del microcontrolador y actuadores
            self.run_controller()
            
            # 4. Leer teclado no bloqueante
            self.process_keyboard()
            
            # 5. Dibujar UI
            self.render_ui()
            
            # Retardo para mantener el bucle a ~10 Hz (cada 100ms)
            time.sleep(0.1)

if __name__ == "__main__":
    if sys.platform != "win32":
        # Habilitar modo raw en la terminal Unix para que funcione lectura de teclado
        # de un solo carácter sin presionar Enter.
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(sys.stdin.fileno())
            simulator = SmartIrrigationSimulator()
            simulator.run()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    else:
        # En Windows funciona directo con msvcrt
        simulator = SmartIrrigationSimulator()
        simulator.run()
