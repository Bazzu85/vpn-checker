import os
import json
import psutil

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "CONFIG")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def ask_yes_no(message):
    """Prompt for a yes/no answer, repeating the question if the input is invalid."""
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        print("Invalid input. Enter 'y' for yes or 'n' for no.")

def list_and_select_interface():
    interfaces = list(psutil.net_if_stats().keys())
    print("\nAvailable network interfaces:")
    for idx, iface in enumerate(interfaces, 1):
        print(f"  {idx}. {iface}")
    
    while True:
        try:
            choice = int(input("Enter the number of the interface to configure: "))
            if 1 <= choice <= len(interfaces):
                return interfaces[choice - 1]
        except ValueError:
            pass
        print("Invalid choice. Try again.")

def get_sorted_active_processes():
    processes_by_path = {}
    for p in psutil.process_iter(['name', 'exe']):
        try:
            name = p.info.get('name')
            path = p.info.get('exe')
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        if name:
            key = path.casefold() if path else name.casefold()
            processes_by_path.setdefault(key, (name, path))
    return sorted(processes_by_path.values(), key=lambda process: (process[0].lower(), (process[1] or '').lower()))

def process_key(process_path):
    expanded_path = os.path.expandvars(os.path.expanduser(process_path.strip().strip('"')))
    return os.path.basename(expanded_path).casefold()

def configure_automation_options(configuration):
    auto_start = configuration.get("auto_start_processes") is True
    stop_on_disconnect = configuration.get("stop_processes_on_disconnect") is True

    configuration["auto_start_processes"] = ask_yes_no(
        f"Enable automatic process start when the interface is connected? (currently {'enabled' if auto_start else 'disabled'})"
    )
    configuration["stop_processes_on_disconnect"] = ask_yes_no(
        f"Stop configured processes when the interface disconnects? (currently {'enabled' if stop_on_disconnect else 'disabled'})"
    )

def manage_process_additions(process_list):
    manual_entry = ask_yes_no("Do you want to enter Windows processes manually?")
    if manual_entry:
        while True:
            while True:
                process_path = input("Enter the full path to the .exe file (e.g. C:\\Program Files\\app\\app.exe): ").strip().strip('"')
                expanded_path = os.path.expandvars(os.path.expanduser(process_path))
                if not os.path.isabs(expanded_path):
                    print("Incomplete path: enter an absolute path, for example C:\\Program Files\\app\\app.exe.")
                    continue
                if not expanded_path.lower().endswith('.exe') or not os.path.isfile(expanded_path):
                    print(".exe file not found. Check the path in File Explorer and enter it again.")
                    continue
                process_path = os.path.abspath(expanded_path)
                break

            if not any(process_key(existing) == process_key(process_path) for existing in process_list):
                process_list.append(process_path)
                print(f"Process '{process_path}' added.")
            else:
                print("This process is already in the configuration.")
            
            if not ask_yes_no("Do you want to add another process?"):
                break
    else:
        active_processes = get_sorted_active_processes()
        print("\nProcesses currently running:")
        for idx, (name, path) in enumerate(active_processes, 1):
            details = path or "path unavailable"
            print(f"  {idx}. {name} - {details}")
            
        selections = input("Enter the numbers of the processes to add, separated by spaces (e.g. 1 3 5): ").strip()
        try:
            indices = [int(value) for value in selections.split()]
            for idx in indices:
                if 1 <= idx <= len(active_processes):
                    process_name, process_path = active_processes[idx - 1]
                    config_value = process_path or process_name
                    if not any(process_key(existing) == process_key(config_value) for existing in process_list):
                        process_list.append(config_value)
                        print(f"Process '{config_value}' added.")
                    else:
                        print(f"Process '{process_name}' is already in the configuration.")
                else:
                    print(f"Index {idx} is invalid and was skipped.")
        except ValueError:
            print("Invalid format. No processes were added.")

def main():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Check whether the configuration file exists.
    if not os.path.exists(CONFIG_FILE):
        print("=== CONFIGURATOR: New Configuration ===")
        interface_name = list_and_select_interface()
        processes = []
        
        manage_process_additions(processes)
        
        configuration = {
            "interface": interface_name,
            "processes": processes,
            "auto_start_processes": False,
            "stop_processes_on_disconnect": False
        }

        configure_automation_options(configuration)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(configuration, f, indent=4)
        print(f"\nConfiguration created and saved successfully to: {CONFIG_FILE}")
        
    else:
        print("=== CONFIGURATOR: Edit Existing Configuration ===")
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                configuration = json.load(f)
        except Exception:
            configuration = {"interface": "", "processes": []}
            
        print(f"Current network interface: {configuration.get('interface', 'None')}")
        
        if ask_yes_no("Do you want to change the network interface?"):
            configuration['interface'] = list_and_select_interface()
            
        processes = configuration.get('processes', [])
        
        # Process management loop (add and remove).
        while True:
            print("\n--- Currently configured processes ---")
            if not processes:
                print("  (No processes configured)")
            else:
                for idx, process in enumerate(processes, 1):
                    print(f"  ID {idx}: {process}")
                    
            if ask_yes_no("Do you want to add a process?"):
                manage_process_additions(processes)
                continue
                
            if processes and ask_yes_no("Do you want to remove a process?"):
                while processes:
                    try:
                        remove_id = int(input("Enter the ID of the process to remove: "))
                        if 1 <= remove_id <= len(processes):
                            removed_process = processes.pop(remove_id - 1)
                            print(f"Process '{removed_process}' removed successfully.")
                        else:
                            print("Invalid ID.")
                            break
                    except ValueError:
                        print("Enter a valid integer.")
                        break

                    if not processes or not ask_yes_no("Do you want to remove another process?"):
                        break

                    print("\n--- Updated list of configured processes ---")
                    for idx, process in enumerate(processes, 1):
                        print(f"  ID {idx}: {process}")
                    
            if not ask_yes_no("Do you want to make other process changes?"):
                break
                
        configuration['processes'] = processes
        configure_automation_options(configuration)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(configuration, f, indent=4)
        print(f"\nConfiguration updated and saved to: {CONFIG_FILE}")

if __name__ == "__main__":
    main()
    input("Press ENTER to close...")