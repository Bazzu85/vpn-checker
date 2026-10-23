import os
import json
import time
import shutil
import subprocess
import threading
import sys
from datetime import datetime
import psutil
import pystray
from PIL import Image, ImageDraw

# Path to the CONFIG folder relative to this script.
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "CONFIG")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LOG_FILE = os.path.join(CONFIG_DIR, "worker.log")
_LOG_STREAM = None
_CONSOLE_STREAM = None
_LOG_LOCK = threading.Lock()

class TimestampedLogWriter:
    def __init__(self, stream):
        self._stream = stream
        self._lock = threading.Lock()
        self._at_line_start = True

    def write(self, text):
        if not text:
            return 0
        with self._lock:
            for line in text.splitlines(keepends=True):
                if self._at_line_start:
                    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
                    self._stream.write(f"[{timestamp}] ")
                self._stream.write(line)
                self._at_line_start = line.endswith(("\n", "\r"))
            self._stream.flush()
        return len(text)

    def flush(self):
        with self._lock:
            self._stream.flush()

def configure_output():
    global _LOG_STREAM, _CONSOLE_STREAM
    os.makedirs(CONFIG_DIR, exist_ok=True)
    _LOG_STREAM = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
    _CONSOLE_STREAM = sys.stdout
    if sys.stdout is None or sys.stderr is None:
        log_writer = TimestampedLogWriter(_LOG_STREAM)
        sys.stdout = log_writer
        sys.stderr = log_writer
        return False
    return True

def log_event(level, message):
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    line = f"[{timestamp}] {level:<5}: {message}\n"
    with _LOG_LOCK:
        if _LOG_STREAM:
            _LOG_STREAM.write(line)
            _LOG_STREAM.flush()
        if _CONSOLE_STREAM:
            _CONSOLE_STREAM.write(line)
            _CONSOLE_STREAM.flush()

def log_debug(debug_enabled, message):
    if debug_enabled:
        log_event("DEBUG", message)

def load_configuration():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as error:
        log_event("ERROR", f"Error reading the configuration file: {error}")
        return None

def resolve_executable_path(process_path):
    expanded_path = os.path.expandvars(os.path.expanduser(process_path.strip().strip('"')))
    if os.path.isfile(expanded_path):
        return os.path.abspath(expanded_path)
    return shutil.which(expanded_path)

def stop_configured_processes(processes, debug_enabled=False):
    process_names = {os.path.basename(process_path).lower() for process_path in processes}
    if not process_names:
        log_debug(debug_enabled, "No configured processes to stop.")
        return

    log_debug(debug_enabled, f"Looking for configured processes to stop: {sorted(process_names)}")
    matching_processes = []
    for process in psutil.process_iter(['name']):
        try:
            process_name = process.info.get('name')
        except psutil.NoSuchProcess:
            continue
        except psutil.Error as error:
            log_event("ERROR", f"Could not inspect a process while stopping configured applications: {error}")
            continue

        if process_name and process_name.lower() in process_names:
            log_debug(debug_enabled, f"Found running process to stop: {process_name} (PID {process.pid}).")
            matching_processes.append(process)

    if not matching_processes:
        log_debug(debug_enabled, "No configured processes are currently running.")
        return

    for process in matching_processes:
        try:
            log_event("INFO", f"Stopping process '{process.info.get('name')}' (PID {process.pid}).")
            process.terminate()
        except psutil.NoSuchProcess:
            continue
        except psutil.Error as error:
            log_event("ERROR", f"Could not stop process with PID {process.pid}: {error}")

    _, still_running = psutil.wait_procs(matching_processes, timeout=3)
    for process in still_running:
        try:
            log_event("WARNING", f"Process PID {process.pid} did not exit; forcing it to stop.")
            process.kill()
        except psutil.NoSuchProcess:
            continue
        except psutil.Error as error:
            log_event("ERROR", f"Could not force-stop process with PID {process.pid}: {error}")

def monitor(stop_event):
    while not stop_event.is_set():
        configuration = load_configuration()
        
        if not configuration:
            log_event("INFO", "Configuration file not found in the CONFIG folder. Waiting 5 seconds.")
            stop_event.wait(5)
            continue
            
        interface_name = configuration.get("interface")
        processes = configuration.get("processes", [])
        auto_start_processes = configuration.get("auto_start_processes") is True
        stop_processes_on_disconnect = configuration.get("stop_processes_on_disconnect") is True
        debug_enabled = configuration.get("debug") is True

        log_debug(debug_enabled, "Starting monitoring cycle.")
        log_debug(
            debug_enabled,
            f"Loaded settings: interface={interface_name!r}, processes={processes!r}, "
            f"auto_start={auto_start_processes}, stop_on_disconnect={stop_processes_on_disconnect}.",
        )
        
        # Check whether the network interface exists and is up.
        network_stats = psutil.net_if_stats()
        log_debug(debug_enabled, f"Available network interfaces: {sorted(network_stats)}")
        if interface_name in network_stats and network_stats[interface_name].isup:
            log_debug(debug_enabled, f"Network interface '{interface_name}' is up.")
            if auto_start_processes:
                log_debug(debug_enabled, "Automatic process start is enabled; scanning active processes.")
                active_processes = {p.info['name'].lower() for p in psutil.process_iter(['name']) if p.info['name']}
                log_debug(debug_enabled, f"Found {len(active_processes)} active process names.")

                for process_path in processes:
                    process_name = os.path.basename(process_path).lower()
                    log_debug(debug_enabled, f"Checking configured process '{process_path}'.")
                    if process_name not in active_processes:
                        log_event("INFO", f"Process '{process_path}' is not running; starting it.")
                        executable_path = resolve_executable_path(process_path)
                        if not executable_path:
                            log_event("ERROR", f"Executable '{process_path}' not found. Enter its full path in the configurator.")
                            continue
                        log_debug(debug_enabled, f"Resolved executable path: '{executable_path}'.")
                        try:
                            subprocess.Popen([executable_path])
                            log_event("INFO", f"Started process '{process_path}'.")
                        except Exception as error:
                            log_event("ERROR", f"Error starting process '{process_path}': {error}")
                    else:
                        log_debug(debug_enabled, f"Process '{process_path}' is already running.")
            else:
                log_debug(debug_enabled, "Automatic process start is disabled.")
        else:
            log_event("INFO", f"Network interface '{interface_name}' is disconnected or not found.")
            if stop_processes_on_disconnect:
                log_debug(debug_enabled, "Process stopping on disconnect is enabled.")
                stop_configured_processes(processes, debug_enabled)
            else:
                log_debug(debug_enabled, "Process stopping on disconnect is disabled.")
            
        log_debug(debug_enabled, "Monitoring cycle complete; waiting 10 seconds.")
        stop_event.wait(10)

class WorkerController:
    def __init__(self):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._start_thread()

    def _start_thread(self):
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=monitor, args=(self._stop_event,), daemon=True)
        self._thread.start()

    def restart(self, icon=None, item=None):
        with self._lock:
            self._stop_event.set()
            if self._thread and self._thread is not threading.current_thread():
                self._thread.join()
            self._start_thread()
        log_event("INFO", "Worker restarted from the tray menu.")

    def stop(self):
        with self._lock:
            self._stop_event.set()
            thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join()

def create_tray_image():
    image = Image.new("RGB", (64, 64), (31, 41, 55))
    draw = ImageDraw.Draw(image)
    draw.polygon([(32, 5), (55, 14), (52, 37), (32, 59), (12, 37), (9, 14)], fill=(38, 145, 125))
    draw.line([(20, 32), (28, 40), (44, 23)], fill=(255, 255, 255), width=5)
    return image

def exit_worker(icon, item, controller):
    log_event("INFO", "Worker stopped from the tray menu.")
    controller.stop()
    icon.stop()

def main():
    configure_output()
    log_event("INFO", "Worker started.")
    log_event("INFO", "Use the tray icon to restart or exit the worker.")

    controller = WorkerController()
    menu = pystray.Menu(
        pystray.MenuItem("Restart worker", controller.restart),
        pystray.MenuItem("Exit", lambda icon, item: exit_worker(icon, item, controller)),
    )
    icon = pystray.Icon("vpn_checker", create_tray_image(), "VPN Checker Worker", menu)
    log_event("INFO", "Tray icon initialized.")
    try:
        icon.run()
    except KeyboardInterrupt:
        log_event("INFO", "Worker stopped by user.")
    finally:
        controller.stop()

if __name__ == "__main__":
    main()