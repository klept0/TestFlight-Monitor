# TestFlight Monitor

A cross-platform Python GUI app to monitor [Apple TestFlight](https://testflight.apple.com/) invite codes for open slots, with notification support via [Apprise](https://github.com/caronc/apprise).  
The app features a modern, resizable Tkinter interface with dark/light mode, dynamic status display, and heartbeat notifications.

---

## Features

- **Monitor multiple TestFlight codes** for open slots
- **Desktop GUI** with dynamic resizing and dark/light mode
- **Apprise notifications** (push, email, Discord, etc.)
- **Heartbeat notification** every 6 hours to confirm the app is running
- **Manual and automatic status updates**
- **Add/remove codes** via menu
- **Edit Apprise settings** in-app
- **Minimize to taskbar or (optionally) system tray**
- **No credentials hardcoded**—all settings are editable and saved locally

---

## Screenshots

<!--
Add your screenshot here, for example:
![screenshot](screenshot.png)
-->

---

## Requirements

- Python 3.8+
- [Pillow](https://pypi.org/project/Pillow/)
- [requests](https://pypi.org/project/requests/)
- [apprise](https://pypi.org/project/apprise/)

Install dependencies:

```sh
pip install -r requirements.txt
```
