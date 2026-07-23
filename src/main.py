"""
A more "professional" looking Tkinter app:
- Menu bar at the top with dropdown menus (File, Edit, Help)
- A toolbar row of buttons below the menu
- A status bar at the bottom
- Uses ttk widgets for a more modern look
- Swath list on the left, an interactive pannable/zoomable GPS map on the right

Requires: pip install tkintermapview

Run with: python app.py
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from pyproj import Transformer
import os
import numpy as np
from math import atan2, degrees
import tkintermapview

from ml_euroradar.gpr_reader.ids_reader import IDS_Reader

from shapely.geometry import LineString
from shapely.ops import transform
from pyproj import Transformer
# ---- Functions used by both the menu and the toolbar ----

def _gps_line_to_poly(line,work_crs = "EPSG:28992"):
    """
    WGS84 (EPSG:4326)
        ↓
    RD New (EPSG:28992)
            ↓
    Buffer (e.g. 5 m, 20 m, ...)
            ↓
    (Optional) back to WGS84
    """
    transformer_from_gps = Transformer.from_crs("EPSG:4326", work_crs, always_xy=False)
    transformer_to_gps = Transformer.from_crs(work_crs, "EPSG:4326",  always_xy=False)

    line_wgs = LineString(line)
    line_rd = transform(transformer_from_gps.transform, line_wgs)

    # Buffer 25 meters
    buffer_rd = line_rd.buffer(0.3,cap_style="flat")

    buffer_wgs = transform(transformer_to_gps.transform, buffer_rd)

    return buffer_wgs


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



# Keep references to the drawn path objects so we can remove/redraw them
map_paths = []

def update_plot():
    # todo  save path and poly somewere
    """Redraw the GPS routes on the map based on which swaths are checked."""
    for path in map_paths:
        path.delete()
    map_paths.clear()

    for item in tree.get_children():
        values = tree.item(item, "values")
        checked, swath, length, swat_type = values


        ###
        if line_not_poly:
            if checked == "☐":   # ☐ ☑
                path = map_widget.set_path(swath_routes[int(swath)], color="#adb5bd", width=2)
            elif swat_type == "L":
                path = map_widget.set_path(swath_routes[int(swath)], color="#e03131", width=4)
            elif swat_type == "T":
                path = map_widget.set_path(swath_routes[int(swath)], color="#03045e", width=4)
        else:
            if checked == "☐":   # ☐ ☑
                path = map_widget.set_polygon(swath_poly[int(swath)], outline_color="#adb5bd", fill_color="#adb5bd", border_width=2)
            elif swat_type == "L":
                path = map_widget.set_polygon(swath_poly[int(swath)], outline_color="#e03131", fill_color="#e03131", border_width=2)
            elif swat_type == "T":
                path = map_widget.set_polygon(swath_poly[int(swath)], outline_color="#03045e", fill_color="#03045e", border_width=2)


        map_paths.append(path)

def _switch_line_poly():
    global line_not_poly

    if line_not_poly:
        line_button.config(text="line")
        line_not_poly = False
    else:
        line_button.config(text="poly")
        line_not_poly = True
    update_plot()

def _sort_tl():
    # transformer
    work_crs = "EPSG:28992"
    transformer_from_gps = Transformer.from_crs("EPSG:4326", work_crs, always_xy=False)

    # each item. I want to know the angle
    angles_list = []
    for item in tree.get_children():
        values = tree.item(item, "values")
        checked, swath, length, swat_type = values

        p1 = swath_routes[int(swath)][0]
        p2 = swath_routes[int(swath)][-1]

        # Transform to RD coordinates
        x1, y1 = transformer_from_gps.transform(*p1)
        x2, y2 = transformer_from_gps.transform(*p2)



        angle_rad = atan2(y2 - y1, x2 - x1)
        angle_deg = degrees(angle_rad) % 180 # up and down are same direction
        angles_list.append(angle_deg)

    order_list = angles_list.copy()
    order_list.sort()

    end_list = len(order_list)
    nr_close_angles = [0] * end_list
    j = 0
    while j > -end_list and order_list[j] - 180 < order_list[0] - 45:
        j -= 1

    # close_angles[0] += j
    i = 0
    while i < end_list:
        bla = 0
        if j < 0:
            bla = 180

        if order_list[i] > order_list[j] - bla + 45:
            nr_close_angles[j] += i - j - 1
            j += 1
        else:
            nr_close_angles[i] += i - j
            i += 1

    max_val = max(nr_close_angles)
    best_angle = order_list[nr_close_angles.index(max_val)]

    # print(int(swath), angle_deg)

    for item in tree.get_children():
        checked, swath, length, swat_type = tree.item(item, "values")

        p1 = swath_routes[int(swath)][0]
        p2 = swath_routes[int(swath)][-1]

        # Transform to RD coordinates
        x1, y1 = transformer_from_gps.transform(*p1)
        x2, y2 = transformer_from_gps.transform(*p2)

        angle_rad = atan2(y2 - y1, x2 - x1)
        angle_deg = degrees(angle_rad) % 180 # up and down are same direction

        if abs(best_angle - angle_deg) <= 45 or abs(best_angle - angle_deg) >= 135:
            tree.item(item, values=(checked, swath, length, 'L'))
        else:
            tree.item(item, values=(checked, swath, length, 'T'))

    update_plot()

def _save_svy():





def show_swaths():
    clear_content()

    # --- Left/right split: tree on the left, plot on the right ---
    paned = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
    paned.pack(fill=tk.BOTH, expand=True)

    tree_frame = ttk.Frame(paned)
    plot_frame = ttk.Frame(paned)
    paned.add(tree_frame, weight=0)
    paned.add(plot_frame, weight=1)

    # === Toolbar list ===
    toolbar_tree = ttk.Frame(tree_frame, padding=(5, 3))
    toolbar_tree.pack(side="top", fill="x")

    line_button = ttk.Button(toolbar_tree, text="save", command=_save_svy)
    line_button.pack(side="left", padx=2)

    # ttk.Button(toolbar_tree, text="T/L").pack(side="left", padx=2)
    # ttk.Button(toolbar, text="Save").pack(side="left", padx=2)
    # ttk.Button(toolbar, text="KML").pack(side="left", padx=2)

    # === Toolbar map ===
    toolbar_map = ttk.Frame(plot_frame, padding=(5, 3))
    toolbar_map.pack(side="top", fill="x")

    global line_not_poly
    line_not_poly = True
    global line_button

    line_button = ttk.Button(toolbar_map, text="poly", command=_switch_line_poly)
    line_button.pack(side="left", padx=2)

    sort_tl_button = ttk.Button(toolbar_map, text="sort T/L", command=_sort_tl)
    sort_tl_button.pack(side="left", padx=2)



    # ttk.Button(toolbar, text="Save").pack(side="left", padx=2)
    # ttk.Button(toolbar, text="KML").pack(side="left", padx=2)

    # --- Tree (left) ---
    global tree
    tree = ttk.Treeview(
        tree_frame,
        columns=("selected", "swath", "length", "type"),
        show="headings"
    )

    tree.heading("selected", text="")
    tree.heading("swath", text="Swath")
    tree.heading("length", text="Length (m)")
    tree.heading("type", text="Type")

    tree.column("selected", width=35, anchor="center", stretch=False)
    tree.column("swath", width=50, stretch=False)
    tree.column("length", width=100, stretch=False)
    tree.column("type", width=50, anchor="center", stretch=False)

    scrollbar = ttk.Scrollbar(
        tree_frame,
        orient="vertical",
        command=tree.yview
    )
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill=tk.BOTH, expand=True)
    scrollbar.pack(side="right", fill="y")

    length_list = IDS_reader.swat_lengths
    swat_info = IDS_reader.get_swat_info()
    dx = IDS_reader.get_xstep()

    show_list = []
    for key in sorted(swat_info):
        show_list.append((key, sum(length_list[key]), swat_info[key]['Type']))

    # convert to (swath, length_m, "L"/"T") for tree rows + mock GPS generation
    rows = []
    for swath, datapoints, swat_type in show_list:
        length = (datapoints - 1) * dx
        swat_t = "L" if swat_type == "Longitudinal" else "T"
        rows.append((swath, length, swat_t))
        tree.insert("", tk.END, values=("☑", swath, f"{length:.2f}", swat_t))

    # --- Map (right) ---
    global map_widget, swath_routes, swath_poly
    # swath_routes = generate_mock_routes(rows)
    swath_routes = IDS_reader.get_swats_latlong()
    swath_poly = dict()
    for item in swath_routes:
        swath_poly[item] = list(_gps_line_to_poly(swath_routes[item]).exterior.coords)


    map_widget = tkintermapview.TkinterMapView(plot_frame, corner_radius=0, max_zoom=22)
    # map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}", max_zoom=22)
    map_widget.pack(fill=tk.BOTH, expand=True)

    # Center roughly on the mock survey area and zoom in close
    all_points = [pt for pts in swath_routes.values() for pt in pts]
    avg_lat = sum(p[0] for p in all_points) / len(all_points)
    avg_lon = sum(p[1] for p in all_points) / len(all_points)
    map_widget.set_position(avg_lat, avg_lon)
    map_widget.set_zoom(17)

    update_plot()

    # --- Interaction ---
    def toggle_cell(event):
        SHIFT = 0x0001
        CTRL = 0x0004

        if event.state & (SHIFT | CTRL):
            return

        item = tree.identify_row(event.y)
        column = tree.identify_column(event.x)

        if not item:
            return

        values = list(tree.item(item, "values"))

        # Checkbox column
        if column == "#1":
            values[0] = "☑" if values[0] == "☐" else "☐"

        # Type column
        elif column == "#4":
            values[3] = "T" if values[3] == "L" else "L"

        tree.item(item, values=values)
        update_plot()

    tree.bind("<Button-1>", toggle_cell)

# ---
IDS_reader = IDS_Reader()

# ---- Build the window ----
root = tk.Tk()
root.title("IDS data editior")
root.geometry("900x500")

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

# === Main content ===
content_frame = ttk.Frame(root, padding=10)
content_frame.pack(fill="both", expand=True)

# === Status bar at the bottom ===
status_label = ttk.Label(root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
status_label.pack(side=tk.BOTTOM, fill=tk.X)


# Start the app
show_welcome()
root.mainloop()