# VPN Checker

VPN Checker is a Windows utility that monitors a selected network interface and optionally starts or stops configured applications according to that interface's state. It includes both console and graphical configuration modes, plus a background worker managed from the system tray.

## Features

- Configure a network interface and a list of Windows executable paths.
- Add applications by browsing to an `.exe` file or selecting currently running processes.
- Choose whether the worker starts configured applications while the selected interface is up.
- Choose whether the worker stops configured applications when the interface is down or missing.
- Enable detailed, timestamped debug logging.
- Manage the worker from the system tray: restart it, open its log, or exit.

## Requirements

- Windows
- Python 3
- Tkinter, included with most standard Windows Python installations
- Packages listed in `requirements.txt`: `psutil`, `pystray`, and `Pillow`

Install the packages from PowerShell in the project directory:

```powershell
python -m pip install -r requirements.txt
```

## Configure

Choose one configuration interface:

```powershell
python configurator.py
```

This starts the interactive console configurator. It can select the network interface, add or remove processes, toggle the automation and debug settings, save, or exit without saving.

To open the graphical configurator without a console, double-click `configurator.pyw` in File Explorer, or run:

```powershell
pythonw configurator.py
```

The GUI can browse for executable files or select one or more running processes. If Windows does not expose a selected process's executable path, its process name is saved instead. The **Save** button saves the configuration and leaves the GUI open; **Close without saving** exits without saving unsaved changes.

Both modes save to `CONFIG/config.json`.

## Run the Worker

To start the worker in the system tray without a console, double-click `worker.pyw`, or run:

```powershell
pythonw worker.py
```

The tray menu provides:

- **Restart worker**: restart the monitoring loop.
- **Open log file**: open `CONFIG/worker.log` with the default Windows application.
- **Exit**: stop the worker and remove its tray icon.

For console output while debugging, run:

```powershell
python worker.py
```

The worker reloads `CONFIG/config.json` every 10 seconds. If the configuration file is missing, it checks again after 5 seconds.

## Configuration

The configuration is a JSON object with the selected interface, configured process paths or names, and three boolean settings:

```json
{
  "interface": "Your VPN interface name",
  "processes": [
    "C:\\Program Files\\Example App\\example.exe"
  ],
  "auto_start_processes": false,
  "stop_processes_on_disconnect": false,
  "debug": false
}
```

Use escaped backslashes in Windows paths. All three settings default to `false`, including when they are absent from an older configuration.

## Worker Behavior

When **automatic process start** is enabled and the selected interface is up, the worker checks whether each configured process is already running. If not, it resolves and starts the executable. When the interface is down or missing, it logs the condition; if **stop processes on disconnect** is enabled, it attempts to terminate every running process whose executable name matches a configured process. Processes that do not exit within three seconds are force-stopped.

With **debug logging** enabled, the worker records details of each monitoring cycle. Routine events use the `INFO` level; warnings and errors use `WARNING` and `ERROR`. Every log line includes a local timestamp. Messages go to `CONFIG/worker.log` and also to standard output when a console is available. With the no-console `worker.pyw` launcher, messages are written to the log file.

This utility only checks whether the selected network interface is up. It does not verify VPN connectivity, route application traffic through the VPN, or provide a network kill switch. Configure VPN routing and any required traffic protections separately.
