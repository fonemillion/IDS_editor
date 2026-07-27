"""
A more "professional" looking Tkinter app:
- Menu bar at the top with dropdown menus (File, Edit, Help)
- A toolbar row of buttons below the menu
- A status bar at the bottom
- Uses ttk widgets for a more modern look
- Swath list on the left, an interactive pannable/zoomable GPS map on the right

Requires: pip install tkintermapview

Run with: python main.py

pyinstaller --onefile --windowed src/main.py
pyinstaller --onefile --windowed --paths "..\ML_euroradar\src" src\main.py
"""
import requests
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog, simpledialog
from pyproj import Transformer
import os
import numpy as np
from math import atan2, degrees
import tkintermapview
from tkintermapview import TkinterMapView

from ml_euroradar.gpr_creator.ids_creator import GSSI_to_IDS
from ml_euroradar.gpr_reader.gssi_reader import GSSI_Reader
from ml_euroradar.gpr_reader.ids_reader import IDS_Reader

from shapely.geometry import LineString
from shapely.ops import transform
from pyproj import Transformer
# ---- Functions used by both the menu and the toolbar ----

class OverzoomMapView(TkinterMapView):
    """Allows zooming past the tile server's native max zoom by
    cropping and upscaling the deepest available real tile."""

    native_max_zoom = 19  # highest zoom level the tile server actually has

    def request_image(self, zoom, x, y, db_cursor=None):
        if zoom <= self.native_max_zoom:
            # normal behavior, tile really exists at this zoom
            return super().request_image(zoom, x, y, db_cursor=db_cursor)

        # how many zoom levels past the native max are we?
        diff = zoom - self.native_max_zoom
        factor = 2 ** diff

        # the "parent" tile at native zoom that covers this deep tile
        native_x = x // factor
        native_y = y // factor

        # fetch (or reuse from cache) the real tile at native zoom
        cache_key = f"{self.native_max_zoom}{native_x}{native_y}"
        if cache_key in self.tile_image_cache:
            native_image_tk = self.tile_image_cache[cache_key]
            native_image = ImageTk.getimage(native_image_tk).convert("RGB")
        else:
            url = self.tile_server.replace("{x}", str(native_x)) \
                                   .replace("{y}", str(native_y)) \
                                   .replace("{z}", str(self.native_max_zoom))
            response = requests.get(url, stream=True, headers={"User-Agent": "TkinterMapView"})
            native_image = Image.open(response.raw).convert("RGB")

        # figure out which sub-square of the native tile this deep tile is
        crop_size = self.tile_size / factor
        left = (x % factor) * crop_size
        top = (y % factor) * crop_size
        cropped = native_image.crop((left, top, left + crop_size, top + crop_size))

        # scale that crop back up to full tile size (this is the "distortion")
        upscaled = cropped.resize((self.tile_size, self.tile_size), Image.LANCZOS)

        image_tk = ImageTk.PhotoImage(upscaled)
        self.tile_image_cache[f"{zoom}{x}{y}"] = image_tk
        return image_tk


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
    messagebox.showinfo("About", "Quick GPR data checker \nVersion 1.0")

def _exit_app():
    root.destroy()

def clear_content():
    for widget in content_frame.winfo_children():
        widget.destroy()

def show_welcome():
    clear_content()

    label = ttk.Label(
        content_frame,
        text="Open an IDS or GSSI project to begin",
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

        show_swaths_ids()

def _open_gssi():
    folder = filedialog.askdirectory(
        title="Select IDS Data Folder"
    )

    if folder:  # User didn't cancel
        GSSI_reader.load_project(folder)
        status_label.config(text=f"Loaded folder: {folder}")

        show_swaths_gssi()

# Keep references to the drawn path objects so we can remove/redraw them
map_paths = []

def update_plot():
    # todo cleanup
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
                if item in tree.selection():
                    path = map_widget.set_path(swath_routes[int(swath)], color="#b1b5ba", width=3)
                else:
                    path = map_widget.set_path(swath_routes[int(swath)], color="#adb5bd", width=1)
            elif swat_type == "L":
                if item in tree.selection():
                    path = map_widget.set_path(swath_routes[int(swath)], color="#f5e022", width=4)
                else:
                    path = map_widget.set_path(swath_routes[int(swath)], color="#e03131", width=2)
            elif swat_type == "T":
                if item in tree.selection():
                    path = map_widget.set_path(swath_routes[int(swath)], color="#22b2f5", width=4)
                else:
                    path = map_widget.set_path(swath_routes[int(swath)], color="#03045e", width=2)
        else:
            if checked == "☐":   # ☐ ☑
                if item in tree.selection():
                    path = map_widget.set_polygon(swath_poly[int(swath)], outline_color="#b1b5ba", fill_color="#b1b5ba", border_width=3)
                else:
                    path = map_widget.set_polygon(swath_poly[int(swath)], outline_color="#adb5bd", fill_color="#adb5bd", border_width=1)
            elif swat_type == "L":
                if item in tree.selection():
                    path = map_widget.set_polygon(swath_poly[int(swath)], outline_color="#f5e022", fill_color="#f5e022", border_width=4)
                else:
                    path = map_widget.set_polygon(swath_poly[int(swath)], outline_color="#e03131", fill_color="#e03131", border_width=2)
            elif swat_type == "T":
                if item in tree.selection():
                    path = map_widget.set_polygon(swath_poly[int(swath)], outline_color="#22b2f5", fill_color="#22b2f5", border_width=4)
                else:
                    path = map_widget.set_polygon(swath_poly[int(swath)], outline_color="#03045e", fill_color="#03045e", border_width=2)


        map_paths.append(path)

def update_plot_gssi():
    # todo cleanup
    """Redraw the GPS routes on the map based on which swaths are checked."""
    for path in map_paths:
        path.delete()
    map_paths.clear()

    for item in tree.get_children():
        values = tree.item(item, "values")
        checked, swath, gnns_string, swat_type, swat_depth = values

        swath = swath + '.DZT'
        if gnns_string == "☐":
            continue
        ###
        if line_not_poly:
            if checked == "☐":   # ☐ ☑
                if item in tree.selection():
                    path = map_widget.set_path(swath_routes[swath], color="#b1b5ba", width=3)
                else:
                    path = map_widget.set_path(swath_routes[swath], color="#adb5bd", width=1)
            else:
                if item in tree.selection():
                    path = map_widget.set_path(swath_routes[swath], color="#f5e022", width=4)
                else:
                    path = map_widget.set_path(swath_routes[swath], color="#e03131", width=2)

        else:
            if checked == "☐":   # ☐ ☑
                if item in tree.selection():
                    path = map_widget.set_polygon(swath_poly[swath], outline_color="#b1b5ba", fill_color="#b1b5ba", border_width=3)
                else:
                    path = map_widget.set_polygon(swath_poly[swath], outline_color="#adb5bd", fill_color="#adb5bd", border_width=1)
            else:
                if item in tree.selection():
                    path = map_widget.set_polygon(swath_poly[swath], outline_color="#f5e022", fill_color="#f5e022", border_width=4)
                else:
                    path = map_widget.set_polygon(swath_poly[swath], outline_color="#e03131", fill_color="#e03131", border_width=2)


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

def _switch_line_poly_gssi():
    global line_not_poly

    if line_not_poly:
        line_button.config(text="line")
        line_not_poly = False
    else:
        line_button.config(text="poly")
        line_not_poly = True
    update_plot_gssi()

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

    tr = {"T": "Transversal",
          "L": "Longitudinal",}

    edits_checked = dict()
    edits_type = dict()
    for item in tree.get_children():
        values = tree.item(item, "values")
        checked, swath, length, swat_type = values

        edits_checked[str(swath)] = (checked == "☑")
        edits_type[str(swath)] = tr[swat_type]

    IDS_reader.edit_svy_type(edits_type)
    IDS_reader.save_svy()

def _switch_tl():
    selected_items = tree.selection()

    for item in selected_items:
        values = list(tree.item(item, "values"))
        values[3] = "T" if values[3] == "L" else "L"
        tree.item(item, values=values)
    update_plot()

def _switch_map():
    global map_toggle
    if map_toggle:
        map_widget.set_tile_server("https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/2026_orthoHR/EPSG:3857/{z}/{x}/{y}.jpeg",
                                   max_zoom=22)
        map_widget.native_max_zoom = 21
    else:
        map_widget.set_tile_server("https://tile.openstreetmap.org/{z}/{x}/{y}.png", max_zoom=22)
        map_widget.native_max_zoom = 19

    map_toggle = (not map_toggle)

def _to_ids():

    path = filedialog.asksaveasfilename(
        title="Choose location and name for new project folder",
        initialdir=GSSI_reader.folder_name,
    )
    if os.path.exists(path):
        messagebox.showerror(title="Error",message="Folder already exists.")


    output_dir, project_name = os.path.split(path)
    GSSI_to_IDS(project_name, output_dir, GSSI_reader.get_proj_folder())


def _selected_to_ids():

    selected_items = tree.selection()

    selected_swats = []
    for item in selected_items:
        values = list(tree.item(item, "values"))
        selected_swats.append(values[1])

    path = filedialog.asksaveasfilename(
        title="Choose location and name for new project folder",
        initialdir=GSSI_reader.folder_name,
    )
    if os.path.exists(path):
        messagebox.showerror(title="Error", message="Folder already exists.")

    output_dir, project_name = os.path.split(path)
    GSSI_to_IDS(project_name, output_dir, GSSI_reader.get_proj_folder(),subswat=selected_swats)

def show_swaths_ids():
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

    save_button = ttk.Button(toolbar_tree, text="save", command=_save_svy)
    save_button.pack(side="left", padx=2)

    switch_tl_button = ttk.Button(toolbar_tree, text="switch T/L", command=_switch_tl)
    switch_tl_button.pack(side="left", padx=2)

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

    switch_map_button = ttk.Button(toolbar_map, text="switch map", command=_switch_map)
    switch_map_button.pack(side="left", padx=2)

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

    global map_toggle
    map_toggle = True
    map_widget = OverzoomMapView(plot_frame, corner_radius=0, max_zoom=22)
    map_widget.native_max_zoom = 19
    # map_widget = tkintermapview.TkinterMapView(plot_frame, corner_radius=0, max_zoom=22)
    # map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}", max_zoom=22)
    # map_widget.set_tile_server(
    #     "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/2026_orthoHR/EPSG:3857/{z}/{x}/{y}.jpeg",
    #     max_zoom=22  # try 20, 21, 22 - see note below
    # )
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

    def on_tree_select(event):
        update_plot()

    tree.bind("<<TreeviewSelect>>", on_tree_select)

def show_swaths_gssi():
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

    convert_button = ttk.Button(toolbar_tree, text="to ids", command=_to_ids)
    convert_button.pack(side="left", padx=2)

    convert_selected_button = ttk.Button(toolbar_tree, text="selected to ids", command=_selected_to_ids)
    convert_selected_button.pack(side="left", padx=2)
    #
    # switch_tl_button = ttk.Button(toolbar_tree, text="switch T/L", command=_switch_tl)
    # switch_tl_button.pack(side="left", padx=2)


    # === Toolbar map ===
    toolbar_map = ttk.Frame(plot_frame, padding=(5, 3))
    toolbar_map.pack(side="top", fill="x")
    #
    global line_not_poly
    line_not_poly = True
    global line_button
    #
    line_button = ttk.Button(toolbar_map, text="poly", command=_switch_line_poly_gssi)
    line_button.pack(side="left", padx=2)
    #
    # sort_tl_button = ttk.Button(toolbar_map, text="sort T/L", command=_sort_tl)
    # sort_tl_button.pack(side="left", padx=2)
    #
    # switch_map_button = ttk.Button(toolbar_map, text="switch map", command=_switch_map)
    # switch_map_button.pack(side="left", padx=2)

    # ttk.Button(toolbar, text="Save").pack(side="left", padx=2)
    # ttk.Button(toolbar, text="KML").pack(side="left", padx=2)

    # --- Tree (left) ---
    global tree
    tree = ttk.Treeview(
        tree_frame,
        columns=("selected", "swath", "gnns", "type", "depth"),
        show="headings"
    )



    tree.heading("selected", text="")
    tree.heading("swath", text="Swath")
    tree.heading("gnns", text="GNNS")
    tree.heading("type", text="Type")
    tree.heading("depth", text="Depth")

    tree.column("selected", width=35, anchor="center", stretch=False)
    tree.column("swath", width=50, stretch=False)
    tree.column("gnns", width=35, anchor="center", stretch=False)
    tree.column("type", width=50, anchor="center", stretch=False)
    tree.column("depth", width=50, stretch=False)

    scrollbar = ttk.Scrollbar(
        tree_frame,
        orient="vertical",
        command=tree.yview
    )
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill=tk.BOTH, expand=True)
    scrollbar.pack(side="right", fill="y")

    # length_list = IDS_reader.swat_lengths
    swat_list = []
    for swat in GSSI_reader.DZT_files:
        swat_list.append(swat)



    show_list = []
    for swat in swat_list:
        swat_type, data_points =  GSSI_reader.read_header(swat)
        show_list.append((swat,  (swat[:-4]+".DZG") in GSSI_reader.DZG_files, swat_type, GSSI_reader.get_time_window(swat)))

    # convert to (swath, length_m, "L"/"T") for tree rows
    for swath, gnns, swat_type, swat_depth in show_list:
        gnns_string = "☑" if gnns else "☐"
        tree.insert("", tk.END, values=("☑", swath[:-4], gnns_string, swat_type, str(swat_depth)))

    # --- Map (right) ---
    global map_widget, swath_routes, swath_poly
    # swath_routes = generate_mock_routes(rows)
    swath_routes = dict()
    for swat in swat_list:
        if (swat[:-4]+".DZG") in GSSI_reader.DZG_files:
            swath_routes[swat] = GSSI_reader.get_swat_latlong(swat)


    swath_poly = dict()
    for item in swath_routes:
        swath_poly[item] = list(_gps_line_to_poly(swath_routes[item]).exterior.coords)

    global map_toggle
    map_toggle = True
    map_widget = OverzoomMapView(plot_frame, corner_radius=0, max_zoom=22)
    map_widget.native_max_zoom = 19
    # map_widget = tkintermapview.TkinterMapView(plot_frame, corner_radius=0, max_zoom=22)
    # map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}", max_zoom=22)
    # map_widget.set_tile_server(
    #     "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/2026_orthoHR/EPSG:3857/{z}/{x}/{y}.jpeg",
    #     max_zoom=22  # try 20, 21, 22 - see note below
    # )
    map_widget.pack(fill=tk.BOTH, expand=True)

    # Center roughly on the mock survey area and zoom in close
    all_points = [pt for pts in swath_routes.values() for pt in pts]
    avg_lat = sum(p[0] for p in all_points) / len(all_points)
    avg_lon = sum(p[1] for p in all_points) / len(all_points)
    map_widget.set_position(avg_lat, avg_lon)
    map_widget.set_zoom(17)

    update_plot_gssi()

    # --- Interaction ---
    # def toggle_cell(event):
    #     SHIFT = 0x0001
    #     CTRL = 0x0004
    #
    #     if event.state & (SHIFT | CTRL):
    #         return
    #
    #     item = tree.identify_row(event.y)
    #     column = tree.identify_column(event.x)
    #
    #     if not item:
    #         return
    #
    #     values = list(tree.item(item, "values"))
    #
    #     # Checkbox column
    #     if column == "#1":
    #         values[0] = "☑" if values[0] == "☐" else "☐"
    #
    #     # Type column
    #     elif column == "#4":
    #         values[3] = "T" if values[3] == "L" else "L"
    #
    #     tree.item(item, values=values)
    #     update_plot()
    #
    # tree.bind("<Button-1>", toggle_cell)

    def on_tree_select(event):
        update_plot_gssi()

    tree.bind("<<TreeviewSelect>>", on_tree_select)

# ---
IDS_reader = IDS_Reader()
GSSI_reader = GSSI_Reader()

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
file_menu.add_command(label="Open GSSI", command=_open_gssi)
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