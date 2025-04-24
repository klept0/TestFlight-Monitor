import time
import threading
import requests
import json
from io import BytesIO
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, messagebox
from apprise import Apprise
from urllib.parse import urlparse

# --- Color constants for light/dark mode ---
LIGHT_BG = "#f5f5f5"
LIGHT_FG = "#222"
LIGHT_ENTRY = "#fafafa"
LIGHT_BTN = "#2196F3"
LIGHT_BTN_ACTIVE = "#1976D2"
LIGHT_STATUS = "#eeeeee"

DARK_BG = "#23272e"
DARK_FG = "#e0e0e0"
DARK_ENTRY = "#2c313c"
DARK_BTN = "#2196F3"
DARK_BTN_ACTIVE = "#1565C0"
DARK_STATUS = "#1a1d23"

# Constants
TESTFLIGHT_PREFIX = "https://testflight.apple.com/join/"
SAVE_FILE = "testflight_monitor.json"

testflight_links = []
apprise_url = ""
app_icons = {}  # Maps link code to PhotoImage
app_names = {}  # Maps code to app name

monitor_thread = None
monitoring = threading.Event()

# Default intervals (in seconds)
search_interval = 60
status_interval = 300
dark_mode = False

def load_data():
    global testflight_links, apprise_url, search_interval, status_interval
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            testflight_links[:] = data.get("links", [])
            apprise_url = data.get("apprise_url", "")
            search_interval = data.get("search_interval", 60)
            status_interval = data.get("status_interval", 300)
    except Exception:
        pass

def save_data():
    with open(SAVE_FILE, "w") as f:
        json.dump({
            "links": testflight_links,
            "apprise_url": apprise_url,
            "search_interval": search_interval,
            "status_interval": status_interval
        }, f)

def is_open(link):
    try:
        resp = requests.get(link, allow_redirects=True, timeout=10)
        return "This beta is full" not in resp.text
    except Exception:
        return False

def get_app_icon(link):
    try:
        resp = requests.get(link, allow_redirects=True, timeout=10)
        start = resp.text.find('meta property="og:image" content="')
        if start != -1:
            start += len('meta property="og:image" content="')
            end = resp.text.find('"', start)
            icon_url = resp.text[start:end]
            icon_resp = requests.get(icon_url, timeout=10)
            img = Image.open(BytesIO(icon_resp.content)).resize((32, 32))
            return ImageTk.PhotoImage(img)
    except Exception:
        pass
    return None

def get_app_name(link):
    try:
        resp = requests.get(link, allow_redirects=True, timeout=10)
        start = resp.text.find('<meta property="og:title" content="')
        if start != -1:
            start += len('<meta property="og:title" content="')
            end = resp.text.find('"', start)
            return resp.text[start:end]
    except Exception:
        pass
    return "Unknown"

def notify(link, manual=False):
    if not apprise_url:
        return
    code = link.replace(TESTFLIGHT_PREFIX, "")
    app_name = app_names.get(code, "Unknown")
    apobj = Apprise()
    apobj.add(apprise_url)
    prefix = "Manual Check - " if manual else ""
    apobj.notify(
        title=f"{prefix}TestFlight Slot Available!",
        body=f"A slot is open for: {app_name}\n{link}"
    )

def send_final_status():
    if not apprise_url:
        return
    apobj = Apprise()
    apobj.add(apprise_url)
    open_apps = []
    for code in testflight_links:
        link = TESTFLIGHT_PREFIX + code
        name = app_names.get(code, "Unknown")
        if is_open(link):
            open_apps.append((name, link))
    for name, link in open_apps:
        apobj.notify(
            title="TestFlight Still Open",
            body=f"Slot still open for: {name}\n{link}"
        )

def send_heartbeat():
    if not apprise_url:
        return
    apobj = Apprise()
    apobj.add(apprise_url)
    apobj.notify(
        title="TestFlight Monitor Heartbeat",
        body="The TestFlight Monitor app is still running."
    )
    # Schedule next heartbeat in 6 hours (21600 seconds)
    root.after(21600000, send_heartbeat)

def manual_status_update():
    status_text.config(state=tk.NORMAL)
    status_text.delete(1.0, tk.END)
    max_code_len = max((len(code) for code in testflight_links), default=8)
    max_name_len = max((len(app_names.get(code, "")) for code in testflight_links), default=8)
    for code in testflight_links:
        link = TESTFLIGHT_PREFIX + code
        open_status = is_open(link)
        if code not in app_icons:
            icon = get_app_icon(link)
            if icon:
                app_icons[code] = icon
        if code not in app_names:
            app_names[code] = get_app_name(link)
        if code in app_icons:
            status_text.image_create(tk.END, image=app_icons[code])
            status_text.insert(tk.END, " ")
        name = app_names.get(code, "Unknown")
        if open_status:
            status_line = f"{'OPEN':<6} {code:<{max_code_len}}  {name:<{max_name_len}}\n"
            status_text.insert(tk.END, status_line, "green")
            notify(link, manual=True)
        else:
            status_line = f"{'FULL':<6} {code:<{max_code_len}}  {name:<{max_name_len}}\n"
            status_text.insert(tk.END, status_line, "red")
    status_text.config(state=tk.DISABLED)

def monitor():
    checked = set()
    while monitoring.is_set():
        for code in testflight_links:
            link = TESTFLIGHT_PREFIX + code
            if code not in checked and is_open(link):
                notify(link)
                checked.add(code)
        # Show countdown in the status bar
        for remaining in range(int(search_interval), 0, -1):
            if not monitoring.is_set():
                return
            statusbar.set(f"Monitoring... Next check in {remaining}s")
            time.sleep(1)
    statusbar.set("Monitoring stopped.")

def status_update():
    status_text.config(state=tk.NORMAL)
    status_text.delete(1.0, tk.END)
    max_code_len = max((len(code) for code in testflight_links), default=8)
    max_name_len = max((len(app_names.get(code, "")) for code in testflight_links), default=8)
    for code in testflight_links:
        link = TESTFLIGHT_PREFIX + code
        open_status = is_open(link)
        if code not in app_icons:
            icon = get_app_icon(link)
            if icon:
                app_icons[code] = icon
        if code not in app_names:
            app_names[code] = get_app_name(link)
        if code in app_icons:
            status_text.image_create(tk.END, image=app_icons[code])
            status_text.insert(tk.END, " ")
        name = app_names.get(code, "Unknown")
        if open_status:
            status_line = f"{'OPEN':<6} {code:<{max_code_len}}  {name:<{max_name_len}}\n"
            status_text.insert(tk.END, status_line, "green")
        else:
            status_line = f"{'FULL':<6} {code:<{max_code_len}}  {name:<{max_name_len}}\n"
            status_text.insert(tk.END, status_line, "red")
    status_text.config(state=tk.DISABLED)
    root.after(status_interval * 1000, status_update)

def refresh_display():
    status_update()
    root.update_idletasks()

def edit_intervals():
    global search_interval, status_interval
    try:
        new_search = simpledialog.askinteger(
            "Set Search Interval",
            "Enter search interval in seconds (default 60):",
            initialvalue=search_interval,
            minvalue=10, maxvalue=3600
        )
        if new_search:
            search_interval = new_search
        new_status = simpledialog.askinteger(
            "Set Status Interval",
            "Enter status update interval in seconds (default 300):",
            initialvalue=status_interval,
            minvalue=30, maxvalue=7200
        )
        if new_status:
            status_interval = new_status
        save_data()
        messagebox.showinfo("Intervals Updated", f"Search: {search_interval}s\nStatus: {status_interval}s")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to update intervals: {e}")

def start_monitoring():
    global monitor_thread
    if not monitoring.is_set():
        monitoring.set()
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        statusbar.set(f"Monitoring started. Next check in {search_interval}s")

def stop_monitoring():
    monitoring.clear()
    if monitor_thread and monitor_thread.is_alive():
        monitor_thread.join(timeout=2)
    send_final_status()
    statusbar.set("Monitoring stopped. Final status sent.")
    root.quit()

def add_link():
    code = simpledialog.askstring("Add TestFlight Link", "Enter code after the last / in the invite URL:")
    if code and code not in testflight_links:
        testflight_links.append(code)
        link = TESTFLIGHT_PREFIX + code
        app_names[code] = get_app_name(link)
        save_data()
        statusbar.set(f"Added code: {code}")
        refresh_display()

def remove_link():
    code = simpledialog.askstring("Remove TestFlight Link", "Enter code to remove:")
    if code and code in testflight_links:
        testflight_links.remove(code)
        if code in app_icons:
            del app_icons[code]
        if code in app_names:
            del app_names[code]
        save_data()
        statusbar.set(f"Removed code: {code}")
        refresh_display()

def update_apprise_icons():
    # Placeholder for Apprise icon logic
    pass

def update_statusbar_icon():
    statusbar.set("Ready")

def open_apprise_settings():
    def save_apprise():
        global apprise_url
        apprise_url = entry.get().strip()
        save_data()
        apprise_win.destroy()
        statusbar.set("Apprise URL updated.")

    apprise_win = tk.Toplevel(root)
    apprise_win.title("Apprise Settings")
    apprise_win.grab_set()
    apprise_win.resizable(False, False)
    tk.Label(apprise_win, text="Apprise URL:", font=("Courier New", 10)).grid(row=0, column=0, padx=8, pady=8, sticky="w")
    entry = tk.Entry(apprise_win, width=60, font=("Courier New", 10))
    entry.grid(row=1, column=0, padx=8, pady=4)
    entry.insert(0, apprise_url)
    save_btn = ttk.Button(apprise_win, text="Save", command=save_apprise)
    save_btn.grid(row=2, column=0, padx=8, pady=8, sticky="e")

class StatusBar(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.label = ttk.Label(self, anchor="w", background=LIGHT_STATUS, font=("Courier New", 10), relief="groove", borderwidth=1)
        self.label.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        self.icon_label = tk.Label(self, bg=LIGHT_STATUS)
        self.icon_label.grid(row=0, column=0, sticky="w", padx=(4, 2))
        self.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        self.grid_columnconfigure(1, weight=1)
        self._icon = None
    def set(self, text):
        self.label.config(text=text)
    def set_icon(self, icon):
        self._icon = icon
        if icon:
            self.icon_label.config(image=icon)
            self.icon_label.image = icon
        else:
            self.icon_label.config(image="", text="")

def set_theme(dark):
    global dark_mode
    dark_mode = dark
    font_family = "Courier New"
    if dark:
        root.configure(bg=DARK_BG)
        main_frame.configure(style="Dark.TFrame")
        style.configure("TFrame", background=DARK_BG)
        style.configure("TLabel", background=DARK_BG, foreground=DARK_FG, font=(font_family, 10))
        style.configure("TButton", background=DARK_BTN, foreground="#fff", font=(font_family, 10))
        style.map("TButton",
            background=[("active", DARK_BTN_ACTIVE), ("disabled", "#444")],
            foreground=[("disabled", "#888")]
        )
        status_text.config(bg=DARK_ENTRY, fg=DARK_FG, insertbackground=DARK_FG, font=(font_family, 11))
        statusbar.label.config(background=DARK_STATUS, foreground=DARK_FG, font=(font_family, 10))
    else:
        root.configure(bg=LIGHT_BG)
        main_frame.configure(style="TFrame")
        style.configure("TFrame", background=LIGHT_BG)
        style.configure("TLabel", background=LIGHT_BG, foreground=LIGHT_FG, font=(font_family, 10))
        style.configure("TButton", background=LIGHT_BTN, foreground="#fff", font=(font_family, 10))
        style.map("TButton",
            background=[("active", LIGHT_BTN_ACTIVE), ("disabled", "#B0BEC5")],
            foreground=[("disabled", "#ECECEC")]
        )
        status_text.config(bg=LIGHT_ENTRY, fg=LIGHT_FG, insertbackground=LIGHT_FG, font=(font_family, 11))
        statusbar.label.config(background=LIGHT_STATUS, foreground=LIGHT_FG, font=(font_family, 10))

# --- GUI Setup ---
root = tk.Tk()
root.title("TestFlight Monitor")
root.configure(bg=LIGHT_BG)
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
root.minsize(500, 300)

style = ttk.Style()
style.theme_use('clam')
style.configure("TButton", font=("Courier New", 10), padding=8, background=LIGHT_BTN, foreground="#fff")
style.map("TButton",
    background=[("active", LIGHT_BTN_ACTIVE), ("disabled", "#B0BEC5")],
    foreground=[("disabled", "#ECECEC")]
)
style.configure("TLabel", background=LIGHT_BG, font=("Courier New", 10))
style.configure("TFrame", background=LIGHT_BG)

main_frame = ttk.Frame(root)
main_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
main_frame.grid_columnconfigure(0, weight=1)
main_frame.grid_rowconfigure(1, weight=1)

# --- Menu Bar ---
menubar = tk.Menu(root)

# File menu
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Add Link", command=add_link)
file_menu.add_command(label="Remove Link", command=remove_link)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=file_menu)

# Actions menu
actions_menu = tk.Menu(menubar, tearoff=0)
actions_menu.add_command(label="Refresh Display", command=refresh_display)
actions_menu.add_command(label="Manual Status Update", command=manual_status_update)
actions_menu.add_separator()
actions_menu.add_command(label="Start Monitoring", command=start_monitoring)
actions_menu.add_command(label="Stop Monitoring", command=stop_monitoring)
actions_menu.add_separator()
actions_menu.add_command(label="Set Intervals", command=edit_intervals)
menubar.add_cascade(label="Actions", menu=actions_menu)

# View menu
view_menu = tk.Menu(menubar, tearoff=0)
view_menu.add_command(label="Toggle Dark Mode", command=lambda: set_theme(not dark_mode))
view_menu.add_command(label="Apprise Settings...", command=open_apprise_settings)
menubar.add_cascade(label="View", menu=view_menu)

root.config(menu=menubar)

# --- Only Status Window ---
status_text = scrolledtext.ScrolledText(
    main_frame,
    width=60,
    height=12,
    font=("Courier New", 11),
    bg=LIGHT_ENTRY,
    relief="flat",
    borderwidth=1,
    wrap="none"  # Disable word wrap
)
status_text.grid(row=1, column=0, pady=10, padx=10, sticky="nsew")
status_text.config(state=tk.DISABLED)
status_text.tag_configure("green", foreground="#388E3C", font=("Courier New", 11, "bold"))
status_text.tag_configure("red", foreground="#D32F2F", font=("Courier New", 11, "bold"))

statusbar = StatusBar(root)

def resize_to_fit_text():
    status_text.update_idletasks()
    # Get number of lines and max line length
    content = status_text.get("1.0", "end-1c")
    lines = content.splitlines() or [""]
    num_lines = len(lines)
    max_line_len = max((len(line) for line in lines), default=1)
    # Set min/max for usability
    min_lines, max_lines = 4, 30
    min_cols, max_cols = 30, 120
    height = min(max(num_lines + 2, min_lines), max_lines)
    width = min(max(max_line_len + 2, min_cols), max_cols)
    status_text.config(height=height, width=width)
    # Resize window to fit
    main_frame.update_idletasks()
    root.geometry("")
    root.minsize(main_frame.winfo_width() + 20, main_frame.winfo_height() + statusbar.winfo_height() + 20)

# Patch status_update and manual_status_update to call resize_to_fit_text
_original_status_update = status_update
def status_update_patched():
    _original_status_update()
    resize_to_fit_text()
status_update = status_update_patched

_original_manual_status_update = manual_status_update
def manual_status_update_patched():
    _original_manual_status_update()
    resize_to_fit_text()
manual_status_update = manual_status_update_patched

# --- Minimize to Taskbar or System Tray on Minimize ---
def on_minimize(event):
    # Ask user if they want to minimize to taskbar or system tray
    # For system tray support, you would need pystray or similar (not included here)
    # This dialog only appears the first time
    if not hasattr(root, "_minimize_choice"):
        choice = messagebox.askquestion(
            "Minimize",
            "Minimize to taskbar or system tray?\n\n"
            "Yes = Taskbar\nNo = System Tray (requires restart, not implemented)",
            icon="question"
        )
        root._minimize_choice = choice
    else:
        choice = root._minimize_choice

    if choice == "yes":
        root.iconify()
    else:
        # Placeholder for system tray support
        root.iconify()
        # You could integrate pystray here for real tray support

root.bind("<Unmap>", on_minimize)

# Load saved data
load_data()
update_statusbar_icon()
update_apprise_icons()

# Start periodic status update
root.after(1000, status_update)
# Start heartbeat
root.after(21600000, send_heartbeat)  # 6 hours in ms

def on_closing():
    if monitoring.is_set():
        # Ask for confirmation before sending final message
        result = messagebox.askyesno("Confirm", "Send final status message before exit?")
        if result:
            send_final_status()
        stop_monitoring()
    else:
        result = messagebox.askyesno("Confirm", "Send final status message before exit?")
        if result:
            send_final_status()
        root.quit()

root.protocol("WM_DELETE_WINDOW", on_closing)

set_theme(False)

root.mainloop()