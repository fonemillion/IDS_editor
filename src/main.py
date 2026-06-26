"""
A more "professional" looking Tkinter app:
- Menu bar at the top with dropdown menus (File, Edit, Help)
- A toolbar row of buttons below the menu
- A status bar at the bottom
- Uses ttk widgets for a more modern look

Run with: python app.py
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
import os
from ml_euroradar.gpr_reader.ids_reader import IDS_Reader
# ---- Functions used by both the menu and the toolbar ----

def _show_about():
    messagebox.showinfo("About", "My Professional App\nVersion 1.0")

def _exit_app():
    root.destroy()

def clear_content():
    for widget in content_frame.winfo_children():
        widget.destroy()

def show_welcome():
    clear_content()

    label = ttk.Label(
        content_frame,
        text="Open an IDS project to begin",
        font=("Segoe UI", 14)
    )
    label.place(relx=0.5, rely=0.5, anchor="center")

def _open_ids():
    folder = filedialog.askdirectory(
        title="Select IDS Data Folder"
    )

    if folder:  # User didn't cancel
        IDS_reader.load_project(folder)
        status_label.config(text=f"Loaded folder: {folder}")
        show_swaths()

def show_swaths():
    clear_content()

    tree = ttk.Treeview(
        content_frame,
        columns=("swath", "length"),
        show="headings"
    )

    tree.heading("swath", text="Swath")
    tree.heading("length", text="Length (m)")

    tree.pack(fill=tk.BOTH, expand=True)

    dummy_data = [
        ("Swath_001", 125.4),
        ("Swath_002", 87.2),
        ("Swath_003", 312.7),
    ]

    for swath, length in dummy_data:
        tree.insert("", tk.END, values=(swath, length))

# ---
IDS_reader = IDS_Reader()

# ---- Build the window ----
root = tk.Tk()
root.title("IDS data editior")
root.geometry("600x400")

# === Menu bar ===
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

# File menu
file_menu = tk.Menu(menu_bar, tearoff=0)
# file_menu.add_command(label="New ", command=new_file)
file_menu.add_command(label="Open IDS", command=_open_ids)
# file_menu.add_command(label="Save As...", command=save_file)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=_exit_app)
menu_bar.add_cascade(label="File", menu=file_menu)

# Edit menu
edit_menu = tk.Menu(menu_bar, tearoff=0)
# edit_menu.add_command(label="Cut", command=cut_text)
# edit_menu.add_command(label="Copy", command=copy_text)
# edit_menu.add_command(label="Paste", command=paste_text)
menu_bar.add_cascade(label="Edit", menu=edit_menu)

# Help menu
help_menu = tk.Menu(menu_bar, tearoff=0)
help_menu.add_command(label="About", command=_show_about)
menu_bar.add_cascade(label="Help", menu=help_menu)

# Main content area
content_frame = ttk.Frame(root, padding=10)
content_frame.pack(fill=tk.BOTH, expand=True)



# === Status bar at the bottom ===
status_label = ttk.Label(root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
status_label.pack(side=tk.BOTTOM, fill=tk.X)


# Start the app
show_welcome()
root.mainloop()