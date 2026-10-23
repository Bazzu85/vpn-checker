import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import psutil

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "CONFIG")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


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


def add_processes(process_list, candidates):
    existing = {process_key(process) for process in process_list}
    for candidate in candidates:
        key = process_key(candidate)
        if key in existing:
            continue
        process_list.append(candidate)
        existing.add(key)


def load_configuration():
    if not os.path.exists(CONFIG_FILE):
        return {
            "interface": "",
            "processes": [],
            "auto_start_processes": False,
            "stop_processes_on_disconnect": False,
            "debug": False,
        }

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            configuration = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read configuration: {error}") from error

    if not isinstance(configuration, dict):
        raise ValueError("Invalid configuration: expected a JSON object.")
    if not isinstance(configuration.get("processes", []), list):
        raise ValueError("Invalid configuration: 'processes' must be a list.")

    configuration.setdefault("interface", "")
    configuration.setdefault("processes", [])
    configuration.setdefault("auto_start_processes", False)
    configuration.setdefault("stop_processes_on_disconnect", False)
    configuration.setdefault("debug", False)
    configuration["auto_start_processes"] = configuration["auto_start_processes"] is True
    configuration["stop_processes_on_disconnect"] = configuration["stop_processes_on_disconnect"] is True
    configuration["debug"] = configuration["debug"] is True
    return configuration


def save_configuration(configuration):
    with open(CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump(configuration, config_file, indent=4)


def ask_yes_no(prompt, default):
    default_text = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} ({default_text}): ").strip().lower()
        if not response:
            return default
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Invalid input. Enter 'y' or 'n'.")


def select_console_interface(current_interface):
    interfaces = list(psutil.net_if_stats())
    if current_interface and current_interface not in interfaces:
        interfaces.insert(0, current_interface)
    if not interfaces:
        print("No network interfaces are available.")
        return ""

    print("\nAvailable network interfaces:")
    for index, interface in enumerate(interfaces, 1):
        current_marker = " (current)" if interface == current_interface else ""
        print(f"  {index}. {interface}{current_marker}")

    while True:
        default_hint = f" [Enter to keep {current_interface}]" if current_interface in interfaces else ""
        selection = input(f"Select an interface number{default_hint}: ").strip()
        if not selection and current_interface in interfaces:
            return current_interface
        try:
            selected_index = int(selection)
            if 1 <= selected_index <= len(interfaces):
                return interfaces[selected_index - 1]
        except ValueError:
            pass
        print("Invalid selection. Try again.")


def add_process_from_console(process_list):
    while True:
        process_path = input("Enter the full path to an existing .exe file: ").strip().strip('"')
        expanded_path = os.path.expandvars(os.path.expanduser(process_path))
        if not os.path.isabs(expanded_path):
            print("Enter an absolute path to the executable.")
            continue
        if not expanded_path.lower().endswith(".exe") or not os.path.isfile(expanded_path):
            print("The .exe file was not found. Check the path and try again.")
            continue

        previous_count = len(process_list)
        add_processes(process_list, [os.path.abspath(expanded_path)])
        if len(process_list) > previous_count:
            print(f"Added '{process_list[-1]}'.")
        else:
            print("This process is already configured.")
        return


def add_running_processes_from_console(process_list):
    running_processes = get_sorted_active_processes()
    if not running_processes:
        print("No running processes are available.")
        return

    print("\nRunning processes:")
    for index, (name, path) in enumerate(running_processes, 1):
        print(f"  {index}. {name} - {path or 'path unavailable'}")

    selection = input("Enter process numbers separated by spaces: ").strip()
    try:
        indices = [int(value) for value in selection.split()]
    except ValueError:
        print("Invalid format. No processes were added.")
        return

    candidates = [
        running_processes[index - 1][1] or running_processes[index - 1][0]
        for index in indices
        if 1 <= index <= len(running_processes)
    ]
    previous_count = len(process_list)
    add_processes(process_list, candidates)
    print(f"Added {len(process_list) - previous_count} process(es).")


def remove_processes_from_console(process_list):
    while process_list:
        print("\nConfigured processes:")
        for index, process_path in enumerate(process_list, 1):
            print(f"  {index}. {process_path}")

        selection = input("Enter process numbers to remove, separated by spaces: ").strip()
        try:
            indices = sorted({int(value) for value in selection.split()}, reverse=True)
        except ValueError:
            print("Invalid format. Enter numeric process IDs.")
            continue

        valid_indices = [index for index in indices if 1 <= index <= len(process_list)]
        if not valid_indices:
            print("No valid process IDs were selected.")
            continue

        for index in valid_indices:
            removed_process = process_list.pop(index - 1)
            print(f"Removed '{removed_process}'.")
        if not process_list or not ask_yes_no("Remove more processes?", False):
            return


def main_console():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        configuration = load_configuration()
    except ValueError as error:
        print(f"Configuration error: {error}")
        return

    print("=== VPN CHECKER CONFIGURATOR ===")
    configuration["interface"] = select_console_interface(configuration["interface"])
    if not configuration["interface"]:
        return

    while True:
        print("\n--- Configuration ---")
        print(f"Interface: {configuration['interface']}")
        print(f"Processes: {len(configuration['processes'])}")
        print(f"Automatic start: {'on' if configuration['auto_start_processes'] else 'off'}")
        print(f"Stop on disconnect: {'on' if configuration['stop_processes_on_disconnect'] else 'off'}")
        print(f"Debug logging: {'on' if configuration['debug'] else 'off'}")
        print("1. Change network interface")
        print("2. Add executable by path")
        print("3. Add from running processes")
        print("4. Remove configured processes")
        print("5. Toggle automatic process start")
        print("6. Toggle stop on disconnect")
        print("7. Toggle debug logging")
        print("8. Save configuration")
        print("9. Save and exit")
        print("0. Exit without saving")

        choice = input("Select an action: ").strip()
        if choice == "1":
            configuration["interface"] = select_console_interface(configuration["interface"])
        elif choice == "2":
            add_process_from_console(configuration["processes"])
        elif choice == "3":
            add_running_processes_from_console(configuration["processes"])
        elif choice == "4":
            remove_processes_from_console(configuration["processes"])
        elif choice == "5":
            configuration["auto_start_processes"] = not configuration["auto_start_processes"]
        elif choice == "6":
            configuration["stop_processes_on_disconnect"] = not configuration["stop_processes_on_disconnect"]
        elif choice == "7":
            configuration["debug"] = not configuration["debug"]
        elif choice in ("8", "9"):
            try:
                save_configuration(configuration)
            except OSError as error:
                print(f"Could not save configuration: {error}")
                continue
            print(f"Configuration saved to: {CONFIG_FILE}")
            if choice == "9":
                return
        elif choice == "0":
            return
        else:
            print("Invalid selection. Try again.")


def main():
    os.makedirs(CONFIG_DIR, exist_ok=True)

    root = tk.Tk()
    root.title("VPN Checker - Configuration")
    root.minsize(620, 460)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)

    try:
        configuration = load_configuration()
    except ValueError as error:
        messagebox.showerror("Configuration error", str(error), parent=root)
        root.destroy()
        return

    interfaces = list(psutil.net_if_stats())
    current_interface = configuration["interface"]
    if current_interface and current_interface not in interfaces:
        interfaces.insert(0, current_interface)

    interface_var = tk.StringVar(value=current_interface)
    auto_start_var = tk.BooleanVar(value=configuration["auto_start_processes"])
    stop_disconnect_var = tk.BooleanVar(value=configuration["stop_processes_on_disconnect"])
    debug_var = tk.BooleanVar(value=configuration["debug"])

    interface_frame = ttk.LabelFrame(root, text="Network interface", padding=10)
    interface_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
    interface_frame.columnconfigure(0, weight=1)
    interface_combo = ttk.Combobox(
        interface_frame,
        textvariable=interface_var,
        values=interfaces,
        state="readonly",
    )
    interface_combo.grid(row=0, column=0, sticky="ew")

    process_frame = ttk.LabelFrame(root, text="Configured processes", padding=10)
    process_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
    process_frame.columnconfigure(0, weight=1)
    process_frame.rowconfigure(0, weight=1)
    process_listbox = tk.Listbox(process_frame, selectmode=tk.EXTENDED, height=10)
    process_listbox.grid(row=0, column=0, sticky="nsew")
    process_scrollbar = ttk.Scrollbar(process_frame, orient="vertical", command=process_listbox.yview)
    process_scrollbar.grid(row=0, column=1, sticky="ns")
    process_listbox.configure(yscrollcommand=process_scrollbar.set)

    def refresh_process_list():
        process_listbox.delete(0, tk.END)
        for process in configuration["processes"]:
            process_listbox.insert(tk.END, process)

    def add_selected_processes(candidates):
        add_processes(configuration["processes"], candidates)
        refresh_process_list()

    def add_from_file():
        path = filedialog.askopenfilename(
            title="Select an application",
            filetypes=[("Executable files", "*.exe")],
        )
        if path:
            if not path.lower().endswith(".exe"):
                messagebox.showerror("Invalid file", "Select a Windows .exe file.", parent=root)
                return
            add_selected_processes([os.path.abspath(path)])

    def add_running_process():
        running_processes = get_sorted_active_processes()
        if not running_processes:
            messagebox.showinfo("Running processes", "No running processes are available.", parent=root)
            return

        dialog = tk.Toplevel(root)
        dialog.title("Select running processes")
        dialog.minsize(550, 350)
        dialog.transient(root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)

        running_list = tk.Listbox(dialog, selectmode=tk.EXTENDED)
        running_list.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        running_scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=running_list.yview)
        running_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        running_list.configure(yscrollcommand=running_scrollbar.set)

        for name, path in running_processes:
            running_list.insert(tk.END, f"{name} - {path or 'path unavailable'}")

        def confirm_running_selection():
            selected = [running_processes[index][1] or running_processes[index][0]
                        for index in running_list.curselection()]
            add_selected_processes(selected)
            dialog.destroy()

        dialog_buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
        dialog_buttons.grid(row=1, column=0, columnspan=2, sticky="e")
        ttk.Button(dialog_buttons, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(dialog_buttons, text="Add selected", command=confirm_running_selection).pack(
            side="right", padx=(0, 8)
        )

    def remove_selected_processes():
        selected = process_listbox.curselection()
        if not selected:
            messagebox.showinfo("Remove process", "Select one or more processes first.", parent=root)
            return
        for index in reversed(selected):
            del configuration["processes"][index]
        refresh_process_list()

    options_frame = ttk.LabelFrame(root, text="Automation and logging", padding=10)
    options_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
    ttk.Checkbutton(
        options_frame,
        text="Start configured processes automatically when the interface is connected",
        variable=auto_start_var,
    ).pack(anchor="w")
    ttk.Checkbutton(
        options_frame,
        text="Stop configured processes when the interface disconnects",
        variable=stop_disconnect_var,
    ).pack(anchor="w", pady=(6, 0))
    ttk.Checkbutton(
        options_frame,
        text="Enable detailed worker debug logging",
        variable=debug_var,
    ).pack(anchor="w", pady=(6, 0))

    process_buttons = ttk.Frame(process_frame)
    process_buttons.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
    ttk.Button(process_buttons, text="Add executable...", command=add_from_file).pack(side="left")
    ttk.Button(process_buttons, text="Choose running process...", command=add_running_process).pack(
        side="left", padx=6
    )
    ttk.Button(process_buttons, text="Remove selected", command=remove_selected_processes).pack(side="left")

    def save_settings():
        selected_interface = interface_var.get()
        if not selected_interface:
            messagebox.showerror("Missing interface", "Select a network interface before saving.", parent=root)
            return
        configuration["interface"] = selected_interface
        configuration["auto_start_processes"] = auto_start_var.get()
        configuration["stop_processes_on_disconnect"] = stop_disconnect_var.get()
        configuration["debug"] = debug_var.get()
        try:
            save_configuration(configuration)
        except OSError as error:
            messagebox.showerror("Save error", f"Could not save configuration: {error}", parent=root)
            return
        messagebox.showinfo("Settings saved", "Configuration saved successfully.", parent=root)

    footer = ttk.Frame(root, padding=12)
    footer.grid(row=3, column=0, sticky="ew")
    ttk.Button(footer, text="Close without saving", command=root.destroy).pack(side="right")
    ttk.Button(footer, text="Save", command=save_settings).pack(side="right", padx=(0, 8))

    refresh_process_list()
    root.mainloop()


if __name__ == "__main__":
    main_console()
