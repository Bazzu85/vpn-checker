# VPN Checker

A small Windows utility that monitors a selected network interface and starts configured applications when they are not running while that interface is up.

## Features

- Select a network interface from those available on the system.
- Add applications by entering an executable path or selecting from currently running processes.
- Remove configured applications and update the configuration interactively.
- Check the selected interface every 10 seconds and start missing applications.

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

2. Select a network interface and add the applications to monitor. For manual entry, provide the full path to an existing `.exe` file, for example:

   ```text
   C:\Program Files\Example App\example.exe
   ```

   The active-process list displays executable paths when Windows makes them available. If a process path is unavailable, the configurator stores its process name instead.

3. Start the worker without a console window by double-clicking `worker.pyw` in File Explorer. You can also run it from PowerShell with `pythonw worker.py`:

   ```powershell
   pythonw worker.py
   ```

   The worker runs in the system tray only, with **Restart worker** and **Exit** options. Its output is written to `CONFIG/worker.log`. For console output while debugging, run `python worker.py` instead.

The configurator saves settings to `CONFIG/config.json`. When this file already exists, running the configurator lets you edit the selected interface and process list.

## Configuration Format

The configuration file contains the selected interface name and a list of executable paths or process names:

```json
{
  "interface": "Your VPN interface name",
  "processes": [
    "C:\\Program Files\\Example App\\example.exe"
  ]
}
```

Use JSON-escaped backslashes in Windows paths, as shown above.

## Important Behavior

The worker starts a configured application only when the selected interface is reported as up and the application is not already running. It retries the check every 10 seconds. If the interface is down or missing, it does not start the applications during that check.

This tool does not route application traffic through a VPN, verify that the VPN can reach the internet, or stop applications when the interface disconnects. Configure VPN routing and any required network protections separately.
