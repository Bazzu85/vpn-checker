import os
import json
import time
import shutil
import subprocess
import threading
import sys
import psutil
import pystray
from PIL import Image, ImageDraw

# Path to the CONFIG folder relative to this script.
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "CONFIG")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LOG_FILE = os.path.join(CONFIG_DIR, "worker.log")

def configure_output():
    if sys.stdout is None or sys.stderr is None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        log_file = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
        return False
    return True

def load_configuration():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as error:
        print(f"Error reading the configuration file: {error}")
        return None

def resolve_executable_path(process_path):
    expanded_path = os.path.expandvars(os.path.expanduser(process_path.strip().strip('"')))
    if os.path.isfile(expanded_path):
        return os.path.abspath(expanded_path)
    return shutil.which(expanded_path)

def stop_configured_processes(processes):
    process_names = {os.path.basename(process_path).lower() for process_path in processes}
    if not process_names:
        return

    matching_processes = []
    for process in psutil.process_iter(['name']):
        try:
            process_name = process.info.get('name')
        except psutil.NoSuchProcess:
            continue
        except psutil.Error as error:
            print(f"[ERROR] Could not inspect a process while stopping configured applications: {error}")
            continue

        if process_name and process_name.lower() in process_names:
            matching_processes.append(process)

    for process in matching_processes:
        try:
            print(f"[INFO] Stopping process '{process.info.get('name')}'.")
            process.terminate()
        except psutil.NoSuchProcess:
            continue
        except psutil.Error as error:
            print(f"[ERROR] Could not stop process with PID {process.pid}: {error}")

    _, still_running = psutil.wait_procs(matching_processes, timeout=3)
    for process in still_running:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            continue
        except psutil.Error as error:
            print(f"[ERROR] Could not force-stop process with PID {process.pid}: {error}")

def monitor(stop_event):
    while not stop_event.is_set():
        configuration = load_configuration()
        
        if not configuration:
            print("Configuration file not found in the CONFIG folder. Waiting...")
            stop_event.wait(5)
            continue
            
        interface_name = configuration.get("interface")
        processes = configuration.get("processes", [])
        
        # Check whether the network interface exists and is up.
        network_stats = psutil.net_if_stats()
        if interface_name in network_stats and network_stats[interface_name].isup:
            # Compare active process names case-insensitively.
            active_processes = {p.info['name'].lower() for p in psutil.process_iter(['name']) if p.info['name']}
            
            for process_path in processes:
                process_name = os.path.basename(process_path).lower()
                if process_name not in active_processes:
                    print(f"[WARNING] Process '{process_path}' is not running. Starting it...")
                    executable_path = resolve_executable_path(process_path)
                    if not executable_path:
                        print(f"[ERROR] Executable '{process_path}' not found. Enter the full path to the .exe file in the configurator.")
                        continue
                    try:
                        subprocess.Popen([executable_path])
                    except Exception as error:
                        print(f"Error starting process '{process_path}': {error}")
        else:
            print(f"Network interface '{interface_name}' is disconnected or not found.")
            stop_configured_processes(processes)
            
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
        print("[INFO] Worker restarted from the tray menu.")

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

def hide_startup_console():
    if os.name != "nt":
        return
    terminal_processes = {
        "cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe",
        "code.exe", "openconsole.exe", "conhost.exe"
    }
    try:
        for ancestor in psutil.Process().parents():
            ancestor_name = ancestor.name().lower()
            if ancestor_name == "explorer.exe":
                break
            if ancestor_name in terminal_processes:
                return
        else:
            return
    except psutil.Error:
        return

    import ctypes
    console_window = ctypes.windll.kernel32.GetConsoleWindow()
    if console_window:
        ctypes.windll.user32.ShowWindow(console_window, 0)

def exit_worker(icon, item, controller):
    controller.stop()
    icon.stop()

def main():
    has_console = configure_output()
    print("=== WORKER STARTED ===")
    print("Use the tray icon to restart or exit the worker. Press CTRL+C to stop.\n")
    if has_console:
        sys.stdout.flush()
        time.sleep(2)
        hide_startup_console()

    controller = WorkerController()
    menu = pystray.Menu(
        pystray.MenuItem("Restart worker", controller.restart),
        pystray.MenuItem("Exit", lambda icon, item: exit_worker(icon, item, controller)),
    )
    icon = pystray.Icon("vpn_checker", create_tray_image(), "VPN Checker Worker", menu)
    try:
        icon.run()
    except KeyboardInterrupt:
        print("\nWorker stopped by user.")
    finally:
        controller.stop()

if __name__ == "__main__":
    main()