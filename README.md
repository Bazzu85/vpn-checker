# VPN Checker

A small Windows utility that monitors a selected network interface and starts configured applications when they are not running while that interface is up.

## Features

- Select a network interface from those available on the system.
- Add applications by entering an executable path or selecting from currently running processes.
- Remove configured applications and update the configuration interactively.
- Check the selected interface every 10 seconds, with optional automatic process start and stop.

## Requirements

- Windows
- Python 3
- `psutil`
- `pystray`
- `Pillow`

Install the dependencies from PowerShell in the project folder:

```powershell
python -m pip install -r requirements.txt
```

## Usage

1. Run the configurator:

   ```powershell
   python configurator.py
   ```

2. Use the configurator window to select a network interface, add or remove applications, and enable either automation option. Add applications by browsing to an `.exe` file or selecting one or more currently running processes.

   For running processes whose executable path Windows does not expose, the configurator stores their process name instead.

3. Start the worker without a console window by double-clicking `worker.pyw` in File Explorer. You can also run it from PowerShell with `pythonw worker.py`:

   ```powershell
   pythonw worker.py
   ```

   The worker runs in the system tray only, with **Restart worker** and **Exit** options. Its output is written to `CONFIG/worker.log`. For console output while debugging, run `python worker.py` instead.

The configurator saves settings to `CONFIG/config.json` when you click **Save**. Click **Close without saving** to discard changes. It uses Python's built-in Tkinter GUI toolkit and does not require additional dependencies.

## Configuration Format

The configuration file contains the selected interface name, a list of executable paths or process names, and two optional automation settings:

```json
{
  "interface": "Your VPN interface name",
  "processes": [
    "C:\\Program Files\\Example App\\example.exe"
  ],
  "auto_start_processes": false,
  "stop_processes_on_disconnect": false
}
```

Use JSON-escaped backslashes in Windows paths, as shown above.

## Important Behavior

Both automation options are disabled by default, including for existing configuration files that do not yet contain these settings. When **automatic process start** is enabled, the worker starts configured applications that are not already running while the selected interface is up. When **stop processes on disconnect** is enabled, it stops all running instances of configured applications if the selected interface is down or missing. The worker checks the interface every 10 seconds.

This tool does not route application traffic through a VPN or verify that the VPN can reach the internet. Configure VPN routing and any required network protections separately.
