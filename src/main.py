"""
Load all .nmea files in a folder (containing $GNGGA / $GPGGA sentences),
extract lat/lon positions, and plot each file's path.

Usage:
    python plot_nmea_paths.py /path/to/folder
    python plot_nmea_paths.py /path/to/folder --separate   # one subplot per file
"""

import os
import struct
import sys
import xml.etree.ElementTree as ET
from typing import Optional

import numpy as np
from PyQt5.QtWidgets import QApplication, QFileDialog
from matplotlib import pyplot as plt

import argparse
import glob
import os

import matplotlib.pyplot as plt
import pynmea2
import sys

sys.path.append(r"C:\Users\TheoB\PycharmProjects\ML_euroradar")
from src.ml_euroradar.gpr_reader.ids_reader import IDS_Reader
# from model import MyModel

def load_track(filepath):
    """Parse a single .nmea file and return lists of (lat, lon) for GGA sentences."""
    lats, lons = [], []

    with open(filepath, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line.startswith(("$GNGGA", "$GPGGA")):
                continue
            try:
                msg = pynmea2.parse(line)
            except pynmea2.ParseError:
                continue

            # Skip fixes with no valid position (lat/lon empty, or fix quality 0)
            if msg.latitude == 0 and msg.longitude == 0:
                continue
            if getattr(msg, "gps_qual", None) == 0:
                continue

            lats.append(msg.latitude)
            lons.append(msg.longitude)

    return lats, lons


def load_all_tracks(folder):
    """Find all .nmea files in folder and parse each into a track."""
    pattern = os.path.join(folder, "*.nmea")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"No .nmea files found in: {folder}")
        return {}

    tracks = {}
    for filepath in files:
        lats, lons = load_track(filepath)
        name = os.path.basename(filepath)
        if not lats:
            print(f"  [skip] {name}: no valid GGA fixes found")
            continue
        tracks[name] = (lats, lons)
        print(f"  [ok]   {name}: {len(lats)} points")

    return tracks


def plot_combined(tracks):
    """Plot all tracks as separate colored lines on one set of axes."""
    fig, ax = plt.subplots(figsize=(10, 8))

    for name, (lats, lons) in tracks.items():
        ax.plot(lons, lats, marker="o", markersize=2, linewidth=1, label=name)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("GPS Paths from NMEA Files")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    return fig


def plot_separate(tracks):
    """Plot each track on its own subplot."""
    n = len(tracks)
    cols = min(3, n)
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 5 * rows), squeeze=False)
    axes_flat = axes.flatten()

    for ax, (name, (lats, lons)) in zip(axes_flat, tracks.items()):
        ax.plot(lons, lats, marker="o", markersize=2, linewidth=1, color="tab:blue")
        ax.set_title(name, fontsize=9)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(True, alpha=0.3)

    # Hide any unused subplot axes
    for ax in axes_flat[n:]:
        ax.axis("off")

    fig.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(description="Plot GPS paths from .nmea files.")
    parser.add_argument("folder", help="Folder containing .nmea files")
    parser.add_argument(
        "--separate",
        action="store_true",
        help="Plot each file in its own subplot instead of combining them",
    )
    parser.add_argument(
        "--output",
        default="nmea_paths.png",
        help="Output image filename (default: nmea_paths.png)",
    )
    args = parser.parse_args()

    print(f"Scanning folder: {args.folder}")
    tracks = load_all_tracks(args.folder)

    if not tracks:
        print("No valid tracks to plot.")
        return

    if args.separate:
        fig = plot_separate(tracks)
    else:
        fig = plot_combined(tracks)

    fig.savefig(args.output, dpi=150)
    print(f"\nSaved plot to: {args.output}")
    plt.show()


if __name__ == "__main__":
    main()