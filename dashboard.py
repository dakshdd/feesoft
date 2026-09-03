import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import webbrowser


def run_script(script_name):
    try:
        subprocess.Popen([sys.executable, script_name])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to run {script_name}\n{e}")

# Master Entry action


def master_entry():
    # Run app.py
    run_script("app.py")
    # Open in Google Chrome (localhost:5000)
    try:
        webbrowser.get("chrome").open("http://localhost:5000")
    except:
        # fallback: open in default browser if chrome not registered
        webbrowser.open("http://localhost:5000")


def fee_entry():
    run_script("fee_entry.py")
    try:
        webbrowser.get("chrome").open("http://localhost:5000/fee")
    except:
        webbrowser.open("http://localhost:5000/fee")


def fee_structure():
    run_script("feestru.py")
    try:
        webbrowser.get("chrome").open("http://localhost:5000/structure")
    except:
        webbrowser.open("http://localhost:5000/structure")


def reprint_receipts():
    messagebox.showinfo("Re-Print Receipts",
                        "Re-print receipts module will be added here.")


def printing_report():
    messagebox.showinfo("Printing Report",
                        "Printing report module will be added here.")


def utils():
    messagebox.showinfo("Utils", "Utility functions will be added here.")


def exit_app():
    root.destroy()


# Main window
root = tk.Tk()
root.title("School Management Dashboard")
root.state('zoomed')

root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

menu_frame = tk.Frame(root, bg="#2c3e50", width=220)
menu_frame.grid(row=0, column=0, sticky="ns")
menu_frame.grid_propagate(False)

content_frame = tk.Frame(root, bg="#ecf0f1")
content_frame.grid(row=0, column=1, sticky="nsew")

title_label = tk.Label(content_frame, text="📊 Dashboard", font=(
    "Segoe UI", 28, "bold"), bg="#ecf0f1", fg="#333")
title_label.pack(pady=40)

style = ttk.Style()
style.theme_use("clam")
style.configure("Menu.TButton",
                font=("Segoe UI", 14),
                padding=10,
                relief="flat",
                background="#34495e",
                foreground="white")
style.map("Menu.TButton",
          background=[("active", "#1abc9c")])

buttons = [
    ("Master Entry", master_entry),
    ("Fee Entry", fee_entry),
    ("Fee Structure", fee_structure),
    ("Re-Print Receipts", reprint_receipts),
    ("Printing Report", printing_report),
    ("Utils", utils),
    ("Exit", exit_app)
]

for i, (text, cmd) in enumerate(buttons):
    menu_frame.grid_rowconfigure(i, weight=1)
    btn = ttk.Button(menu_frame, text=text, style="Menu.TButton", command=cmd)
    btn.grid(row=i, column=0, sticky="ew", padx=20, pady=10)

root.mainloop()
