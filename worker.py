import os
import json
import time
import shutil
import subprocess
import psutil

# Path to the CONFIG folder relative to this script.
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "CONFIG")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

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

def main():
    print("=== WORKER STARTED ===")
    print("Press CTRL+C to stop the script.\n")
    
    while True:
        configuration = load_configuration()
        
        if not configuration:
            print("Configuration file not found in the CONFIG folder. Waiting...")
            time.sleep(5)
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
            
        # Check every 10 seconds.
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nWorker stopped by user.")
    
    input("Press ENTER to close...")