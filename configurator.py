import json
import os

import psutil

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "CONFIG")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def list_and_select_interface():
    interfaces = list(psutil.net_if_stats())
    if not interfaces:
        print("No network interfaces are available.")
        return None

    print("\nAvailable network interfaces:")
    for idx, interface in enumerate(interfaces, 1):
        print(f"  {idx}. {interface}")

    while True:
        try:
            choice = int(input("Select an interface number (0 to cancel): "))
            if choice == 0:
                return None
            if 1 <= choice <= len(interfaces):
                return interfaces[choice - 1]
        except ValueError:
            pass
        print("Invalid choice. Try again.")


def get_sorted_active_processes():
    processes_by_path = {}
    for process in psutil.process_iter(["name", "exe"]):
        try:
            name = process.info.get("name")
            path = process.info.get("exe")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        if name:
            key = path.casefold() if path else name.casefold()
            processes_by_path.setdefault(key, (name, path))
    return sorted(
        processes_by_path.values(),
        key=lambda process: (process[0].casefold(), (process[1] or "").casefold()),
    )


def process_key(process_path):
    expanded_path = os.path.expandvars(os.path.expanduser(process_path.strip().strip('"')))
    return os.path.basename(expanded_path).casefold()


def add_processes(process_list):
    source = input(
        "\nAdd process: [1] enter executable path, [2] choose a running process, [0] cancel: "
    ).strip()

    if source == "1":
        while True:
            process_path = input("Enter the full path to an .exe (blank to cancel): ").strip().strip('"')
            if not process_path:
                return
            expanded_path = os.path.expandvars(os.path.expanduser(process_path))
            if not os.path.isabs(expanded_path):
                print("Enter an absolute path.")
                continue
            if not expanded_path.lower().endswith(".exe") or not os.path.isfile(expanded_path):
                print("Executable not found. Check the path and try again.")
                continue
            candidates = [os.path.abspath(expanded_path)]
            break
    elif source == "2":
        active_processes = get_sorted_active_processes()
        if not active_processes:
            print("No running processes are available.")
            return
        print("\nProcesses currently running:")
        for idx, (name, path) in enumerate(active_processes, 1):
            print(f"  {idx}. {name} - {path or 'path unavailable'}")
        selections = input("Enter process numbers separated by spaces (blank to cancel): ").split()
        try:
            indices = [int(selection) for selection in selections]
        except ValueError:
            print("Invalid selection. No processes were added.")
            return
        candidates = []
        for index in indices:
            if 1 <= index <= len(active_processes):
                name, path = active_processes[index - 1]
                candidates.append(path or name)
            else:
                print(f"Process number {index} is invalid and was skipped.")
    elif source == "0":
        return
    else:
        print("Invalid choice.")
        return

    existing = {process_key(process) for process in process_list}
    for candidate in candidates:
        key = process_key(candidate)
        if key in existing:
            print(f"'{candidate}' is already configured.")
            continue
        process_list.append(candidate)
        existing.add(key)
        print(f"Added '{candidate}'.")


def remove_process(process_list):
    if not process_list:
        print("No configured processes to remove.")
        return

    print("\nConfigured processes:")
    for idx, process in enumerate(process_list, 1):
        print(f"  {idx}. {process}")

    try:
        choice = int(input("Select a process number to remove (0 to cancel): "))
    except ValueError:
        print("Invalid choice.")
        return
    if choice == 0:
        return
    if 1 <= choice <= len(process_list):
        removed = process_list.pop(choice - 1)
        print(f"Removed '{removed}'.")
    else:
        print("Invalid process number.")


def load_configuration():
    if not os.path.exists(CONFIG_FILE):
        return {
            "interface": "",
            "processes": [],
            "auto_start_processes": False,
            "stop_processes_on_disconnect": False,
        }

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            configuration = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read configuration: {error}")
        return None

    if not isinstance(configuration, dict):
        print("Invalid configuration: expected a JSON object.")
        return None
    if not isinstance(configuration.get("processes", []), list):
        print("Invalid configuration: 'processes' must be a list.")
        return None

    configuration.setdefault("interface", "")
    configuration.setdefault("processes", [])
    configuration.setdefault("auto_start_processes", False)
    configuration.setdefault("stop_processes_on_disconnect", False)
    configuration["auto_start_processes"] = configuration["auto_start_processes"] is True
    configuration["stop_processes_on_disconnect"] = configuration["stop_processes_on_disconnect"] is True
    return configuration


def save_configuration(configuration):
    with open(CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump(configuration, config_file, indent=4)
    print(f"Configuration saved to: {CONFIG_FILE}")


def main():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    configuration = load_configuration()
    if configuration is None:
        return

    while True:
        clear_console()
        print("\n=== VPN Checker Configuration ===")
        print(f"Interface: {configuration['interface'] or '(not selected)'}")
        if configuration["processes"]:
            for idx, process in enumerate(configuration["processes"], 1):
                print(f"  {idx}. {process}")
        else:
            print("Processes: (none)")
        print(f"Automatic start: {'on' if configuration['auto_start_processes'] else 'off'}")
        print(f"Stop on disconnect: {'on' if configuration['stop_processes_on_disconnect'] else 'off'}")
        print(
            "\n[1] Select interface  [2] Add process  [3] Remove process\n"
            "[4] Toggle automatic start  [5] Toggle stop on disconnect\n"
            "[6] Save and exit  [0] Exit without saving"
        )

        choice = input("Choose an action: ").strip()
        if choice == "1":
            interface = list_and_select_interface()
            if interface is not None:
                configuration["interface"] = interface
        elif choice == "2":
            add_processes(configuration["processes"])
        elif choice == "3":
            remove_process(configuration["processes"])
        elif choice == "4":
            configuration["auto_start_processes"] = not configuration["auto_start_processes"]
        elif choice == "5":
            configuration["stop_processes_on_disconnect"] = not configuration["stop_processes_on_disconnect"]
        elif choice == "6":
            if not configuration["interface"]:
                print("Select a network interface before saving.")
                continue
            save_configuration(configuration)
            return
        elif choice == "0":
            print("No changes saved.")
            return
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
    input("Press ENTER to close...")
