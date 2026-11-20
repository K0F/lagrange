#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lagrange.py — Multi-Planetary Three-Body Lagrange Libration & Spirograph Engine
Observatoř Cybernetics // Kryštof Pešek (Kof) & Techné (τέχνη)
CC0 1.0 Universal // Public Domain // Anti-Copyright

Calculates and renders multi-planetary Restricted Three-Body Problem (RTBP)
libration points (L1..L5) for Mercury ☿, Venus ♀, Earth ♁, Mars ♂, Jupiter ♃, and Saturn ♄,
combined with 50Hz continental European grid frequency deviations and Prague atmospheric telemetry
into a continuous, non-repeating Guilloché / Spirograph mandala plate for Drkota (V-plotter).
"""

import os
import sys
import time
import math
import json
import argparse
import shutil
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

PHI = (1.0 + math.sqrt(5.0)) / 2.0

GRID_SHM_STATUS = "/dev/shm/observator_status.json"
GRID_SHM_LOCAL = "/dev/shm/grid50.json"
GRID_NETZFREQUENZ_URL = "https://netzfrequenz.info/json/act.json"

WEATHER_CACHE_PATH = "/dev/shm/drkota_weather.json"
WEATHER_CACHE_BACKUP = "/tmp/drkota_weather.json"
OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast?"
    "latitude=50.0875&longitude=14.4214&current="
    "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m"
    "&timezone=Europe%2FPrague"
)

# Multi-Planetary Keplerian & Restricted Three-Body System
# L0: Mean longitude at J2000.0 (deg), n: mean motion (deg/day), mu: mass ratio M_planet / M_sun
PLANETS = {
    "Mercury": {"L0": 252.25, "n": 4.0923344, "mu": 1.66e-7, "color": "#9ca3af", "symbol": "☿", "name_la": "MERCURIUS", "short": "MER"},
    "Venus":   {"L0": 181.98, "n": 1.6021305, "mu": 2.45e-6, "color": "#fbbf24", "symbol": "♀", "name_la": "VENUS",     "short": "VEN"},
    "Earth":   {"L0": 100.46, "n": 0.9856474, "mu": 3.00e-6, "color": "#60a5fa", "symbol": "♁", "name_la": "TERRA",     "short": "TER"},
    "Mars":    {"L0": 355.45, "n": 0.5240330, "mu": 3.23e-7, "color": "#f87171", "symbol": "♂", "name_la": "MARS",      "short": "MAR"},
    "Jupiter": {"L0": 34.40,  "n": 0.0830853, "mu": 9.54e-4, "color": "#fb923c", "symbol": "♃", "name_la": "IUPPITER",  "short": "JUP"},
    "Saturn":  {"L0": 49.94,  "n": 0.0334442, "mu": 2.86e-4, "color": "#facc15", "symbol": "♄", "name_la": "SATURNUS",  "short": "SAT"}
}

def compute_planetary_lagrange(target_ts=None):
    """
    Computes Keplerian ecliptic longitudes and Restricted Three-Body Problem (RTBP)
    libration points (L1, L2, L3, L4, L5) for the 6 primary planets.
    Reference epoch: J2000.0 = 2000-01-01 12:00 UTC (946728000.0s).
    """
    if target_ts is None:
        target_ts = time.time()
    d = (target_ts - 946728000.0) / 86400.0
    bodies = {}
    for name, p in PLANETS.items():
        L = (p["L0"] + p["n"] * d) % 360.0
        rad = math.radians(L)
        l4_deg = (L + 60.0) % 360.0
        l5_deg = (L - 60.0) % 360.0
        l2_deg = (L + 180.0) % 360.0
        l1_deg = L
        l3_deg = (L + 180.0) % 360.0
        ampl = 3.2 * (math.log(1.0 + p["mu"] / 1e-7) / math.log(1.0 + 9.54e-4 / 1e-7))
        bodies[name] = {
            "name": name,
            "name_la": p["name_la"],
            "short": p["short"],
            "symbol": p["symbol"],
            "longitude_deg": round(L, 1),
            "rad": rad,
            "l4_deg": round(l4_deg, 1),
            "l5_deg": round(l5_deg, 1),
            "l2_deg": round(l2_deg, 1),
            "ampl_mm": round(ampl, 2),
            "mu": p["mu"],
            "color": p["color"]
        }
    return bodies

def harvest_grid():
    """Harvests 50Hz continental European grid telemetry."""
    if os.path.exists(GRID_SHM_STATUS):
        try:
            with open(GRID_SHM_STATUS, "r") as f:
                d = json.load(f)
                hz = float(d.get("grid_freq", 50.0))
                drift = float(d.get("grid_drift_mhz", (hz - 50.0) * 1000.0))
                return {
                    "freq_hz": round(hz, 3),
                    "drift_mhz": round(drift, 1),
                    "status": "LOCKED" if abs(drift) < 50.0 else "UNSTABLE",
                    "source": d.get("grid_source", "observator_shm")
                }
        except Exception:
            pass

    if os.path.exists(GRID_SHM_LOCAL):
        try:
            with open(GRID_SHM_LOCAL, "r") as f:
                d = json.load(f)
                hz = float(d.get("frequency_hz", 50.0))
                drift = float(d.get("drift_mhz", (hz - 50.0) * 1000.0))
                return {
                    "freq_hz": round(hz, 3),
                    "drift_mhz": round(drift, 1),
                    "status": d.get("status", "LOCKED"),
                    "source": "grid50_local"
                }
        except Exception:
            pass

    try:
        req = urllib.request.Request(GRID_NETZFREQUENZ_URL, headers={"User-Agent": "DrkotaLagrange/1.0"})
        with urllib.request.urlopen(req, timeout=1.8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            hz = float(data.get("frequency", 50.0))
            drift = (hz - 50.0) * 1000.0
            return {
                "freq_hz": round(hz, 3),
                "drift_mhz": round(drift, 1),
                "status": "LOCKED" if abs(drift) < 50.0 else "UNSTABLE",
                "source": "netzfrequenz.info (live)"
            }
    except Exception:
        pass

    return {
        "freq_hz": 50.000,
        "drift_mhz": 0.0,
        "status": "NOMINAL",
        "source": "nominal_fallback"
    }

def harvest_weather():
    """Harvests Prague weather telemetry from Open-Meteo with local shm cache fallback."""
    cached = None
    cache_file = WEATHER_CACHE_PATH if os.path.exists(os.path.dirname(WEATHER_CACHE_PATH)) else WEATHER_CACHE_BACKUP
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
        except Exception:
            cached = None

    try:
        req = urllib.request.Request(OPEN_METEO_URL, headers={"User-Agent": "DrkotaLagrange/1.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            cur = data.get("current", {})
            temp = float(cur.get("temperature_2m", 9.5))
            rh = float(cur.get("relative_humidity_2m", 75))
            press = float(cur.get("surface_pressure", 975.0))
            wind = float(cur.get("wind_speed_10m", 15.0))
            res = {
                "temp_c": round(temp, 1),
                "rh_pct": int(rh),
                "pressure_hpa": round(press, 1),
                "wind_kmh": round(wind, 1),
                "source": "Open-Meteo Prague (live)"
            }
            try:
                with open(cache_file, "w") as f:
                    json.dump(res, f, indent=2)
            except Exception:
                pass
            return res
    except Exception:
        pass

    if cached and "temp_c" in cached:
        cached["source"] = "Open-Meteo (cached fallback)"
        return cached

    return {
        "temp_c": 9.5,
        "rh_pct": 75,
        "pressure_hpa": 975.2,
        "wind_kmh": 14.8,
        "source": "nominal_prague"
    }

def convert_svg_to_png(svg_path, width_px=1400):
    """Automatically converts rendered SVG to high-resolution PNG companion."""
    if not os.path.exists(svg_path):
        return None
    base, _ = os.path.splitext(svg_path)
    png_path = f"{base}.png"
    try:
        if shutil.which("rsvg-convert"):
            subprocess.run(["rsvg-convert", "-w", str(width_px), svg_path, "-o", png_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return png_path
        elif shutil.which("inkscape"):
            subprocess.run(["inkscape", svg_path, f"--export-filename={png_path}", f"--export-width={width_px}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return png_path
        elif shutil.which("convert"):
            subprocess.run(["convert", "-density", "300", svg_path, png_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return png_path
    except Exception as e:
        sys.stderr.write(f"[-] SVG->PNG konverze selhala: {e}\n")
        return None
    return None

ALPHABET = {
    'A': [[(0, 50), (20, 0), (40, 50)], [(10, 25), (30, 25)]],
    'B': [[(0, 50), (0, 0), (30, 0), (40, 12), (30, 25), (0, 25)], [(30, 25), (40, 37), (30, 50), (0, 50)]],
    'C': [[(40, 0), (0, 0), (0, 50), (40, 50)]],
    'D': [[(0, 50), (0, 0), (30, 0), (40, 25), (30, 50), (0, 50)]],
    'E': [[(40, 0), (0, 0), (0, 50), (40, 50)], [(0, 25), (30, 25)]],
    'F': [[(0, 50), (0, 0), (40, 0)], [(0, 25), (30, 25)]],
    'G': [[(40, 0), (0, 0), (0, 50), (40, 50), (40, 25), (20, 25)]],
    'H': [[(0, 0), (0, 50)], [(40, 0), (40, 50)], [(0, 25), (40, 25)]],
    'I': [[(20, 0), (20, 50)], [(8, 0), (32, 0)], [(8, 50), (32, 50)]],
    'J': [[(40, 0), (40, 50), (0, 50), (0, 25)]],
    'K': [[(0, 0), (0, 50)], [(40, 0), (0, 25), (40, 50)]],
    'L': [[(0, 0), (0, 50), (40, 50)]],
    'M': [[(0, 50), (0, 0), (20, 25), (40, 0), (40, 50)]],
    'N': [[(0, 50), (0, 0), (40, 50), (40, 0)]],
    'O': [[(0, 0), (40, 0), (40, 50), (0, 50), (0, 0)]],
    'P': [[(0, 50), (0, 0), (40, 0), (40, 25), (0, 25)]],
    'Q': [[(0, 0), (40, 0), (40, 50), (0, 50), (0, 0)], [(20, 30), (40, 50)]],
    'R': [[(0, 50), (0, 0), (40, 0), (40, 25), (0, 25)], [(20, 25), (40, 50)]],
    'S': [[(40, 0), (0, 0), (0, 25), (40, 25), (40, 50), (0, 50)]],
    'T': [[(0, 0), (40, 0)], [(20, 0), (20, 50)]],
    'U': [[(0, 0), (0, 50), (40, 50), (40, 0)]],
    'V': [[(0, 0), (20, 50), (40, 0)]],
    'W': [[(0, 0), (10, 50), (20, 25), (30, 50), (40, 0)]],
    'X': [[(0, 0), (40, 50)], [(40, 0), (0, 50)]],
    'Y': [[(0, 0), (20, 25), (40, 0)], [(20, 25), (20, 50)]],
    'Z': [[(0, 0), (40, 0), (0, 50), (40, 50)]],
    # Czech Accents
    'Á': [[(0, 50), (20, 0), (40, 50)], [(10, 25), (30, 25)], [(15, -14), (28, -4)]],
    'Č': [[(40, 0), (0, 0), (0, 50), (40, 50)], [(10, -14), (20, -4), (30, -14)]],
    'Ď': [[(0, 50), (0, 0), (30, 0), (40, 25), (30, 50), (0, 50)], [(10, -14), (20, -4), (30, -14)]],
    'É': [[(40, 0), (0, 0), (0, 50), (40, 50)], [(0, 25), (30, 25)], [(15, -14), (28, -4)]],
    'Ě': [[(40, 0), (0, 0), (0, 50), (40, 50)], [(0, 25), (30, 25)], [(10, -14), (20, -4), (30, -14)]],
    'Í': [[(20, 0), (20, 50)], [(15, -14), (28, -4)]],
    'Ň': [[(0, 50), (0, 0), (40, 50), (40, 0)], [(10, -14), (20, -4), (30, -14)]],
    'Ó': [[(0, 0), (40, 0), (40, 50), (0, 50), (0, 0)], [(15, -14), (28, -4)]],
    'Ř': [[(0, 50), (0, 0), (40, 0), (40, 25), (0, 25)], [(20, 25), (40, 50)], [(10, -14), (20, -4), (30, -14)]],
    'Š': [[(40, 0), (0, 0), (0, 25), (40, 25), (40, 50), (0, 50)], [(10, -14), (20, -4), (30, -14)]],
    'Ť': [[(0, 0), (40, 0)], [(20, 0), (20, 50)], [(10, -14), (20, -4), (30, -14)]],
    'Ú': [[(0, 0), (0, 50), (40, 50), (40, 0)], [(15, -14), (28, -4)]],
    'Ů': [[(0, 0), (0, 50), (40, 50), (40, 0)], [(14, -8), (26, -8), (26, -18), (14, -18), (14, -8)]],
    'Ý': [[(0, 0), (20, 25), (40, 0)], [(20, 25), (20, 50)], [(15, -14), (28, -4)]],
    'Ž': [[(0, 0), (40, 0), (0, 50), (40, 50)], [(10, -14), (20, -4), (30, -14)]],
    'Ē': [[(40, 0), (0, 0), (0, 50), (40, 50)], [(0, 25), (30, 25)], [(10, -10), (30, -10)]],
    # Numbers
    '0': [[(0, 0), (40, 0), (40, 50), (0, 50), (0, 0)]],
    '1': [[(10, 15), (20, 0), (20, 50)], [(5, 50), (35, 50)]],
    '2': [[(0, 0), (40, 0), (40, 25), (0, 25), (0, 50), (40, 50)]],
    '3': [[(0, 0), (40, 0), (40, 25), (0, 25)], [(40, 25), (40, 50), (0, 50)]],
    '4': [[(0, 0), (0, 25), (40, 25)], [(30, 0), (30, 50)]],
    '5': [[(40, 0), (0, 0), (0, 25), (40, 25), (40, 50), (0, 50)]],
    '6': [[(40, 0), (0, 0), (0, 50), (40, 50), (40, 25), (0, 25)]],
    '7': [[(0, 0), (40, 0), (20, 50)]],
    '8': [[(0, 0), (40, 0), (40, 50), (0, 50), (0, 0)], [(0, 25), (40, 25)]],
    '9': [[(40, 25), (0, 25), (0, 0), (40, 0), (40, 50), (0, 50)]],
    # Symbols
    '-': [[(5, 25), (35, 25)]],
    '+': [[(20, 10), (20, 40)], [(5, 25), (35, 25)]],
    '=': [[(5, 18), (35, 18)], [(5, 32), (35, 32)]],
    '.': [[(18, 45), (22, 45), (22, 50), (18, 50), (18, 45)]],
    ',': [[(22, 44), (16, 56)]],
    ':': [[(18, 15), (22, 15)], [(18, 45), (22, 45)]],
    ';': [[(18, 15), (22, 15)], [(22, 44), (16, 56)]],
    '/': [[(35, 0), (5, 50)]],
    '\\': [[(5, 0), (35, 50)]],
    '(': [[(28, 0), (12, 25), (28, 50)]],
    ')': [[(12, 0), (28, 25), (12, 50)]],
    '[': [[(28, 0), (12, 0), (12, 50), (28, 50)]],
    ']': [[(12, 0), (28, 0), (28, 50), (12, 50)]],
    '?': [[(0, 12), (0, 0), (40, 0), (40, 22), (20, 32), (20, 38)], [(18, 46), (22, 46)]],
    '!': [[(20, 0), (20, 35)], [(18, 46), (22, 46)]],
    '|': [[(20, 0), (20, 50)]],
    '_': [[(0, 50), (40, 50)]],
    '~': [[(5, 25), (15, 18), (25, 32), (35, 25)]],
    '*': [[(10, 15), (30, 35)], [(30, 15), (10, 35)], [(20, 10), (20, 40)]],
    '#': [[(14, 5), (14, 45)], [(26, 5), (26, 45)], [(5, 18), (35, 18)], [(5, 32), (32, 32)]],
    '&': [[(35, 50), (10, 25), (25, 0), (10, 0), (0, 25), (25, 50), (35, 35)]],
    '\'': [[(20, 0), (20, 15)]],
    '"': [[(15, 0), (15, 15)], [(25, 0), (25, 15)]],
    '°': [[(26, 2), (36, 2), (36, 14), (26, 14), (26, 2)]],
    '%': [[(35, 5), (5, 45)], [(10, 8), (18, 8), (18, 16), (10, 16), (10, 8)], [(22, 34), (30, 34), (30, 42), (22, 42), (22, 34)]],
    'Δ': [[(20, 0), (40, 50), (0, 50), (20, 0)]],
    '>': [[(10, 10), (30, 25), (10, 40)]],
    '<': [[(30, 10), (10, 25), (30, 40)]],
    # Planetary Vector Stroke Glyphs
    '☿': [[(20, 10), (14, 2), (26, 2), (20, 10)], [(20, 10), (20, 35)], [(20, 10), (30, 20), (20, 30), (10, 20), (20, 10)], [(10, 42), (30, 42)], [(20, 35), (20, 48)]],
    '♀': [[(20, 5), (32, 17), (20, 29), (8, 17), (20, 5)], [(20, 29), (20, 48)], [(10, 38), (30, 38)]],
    '♁': [[(20, 5), (35, 20), (20, 35), (5, 20), (20, 5)], [(20, 5), (20, 35)], [(5, 20), (35, 20)], [(20, 5), (20, 0)], [(14, 0), (26, 0)]],
    '♂': [[(15, 20), (27, 32), (15, 44), (3, 32), (15, 20)], [(27, 20), (38, 9)], [(26, 9), (38, 9), (38, 21)]],
    '♃': [[(10, 15), (20, 5), (26, 15), (26, 35), (5, 35)], [(26, 10), (26, 48)], [(18, 25), (34, 25)]],
    '♄': [[(12, 5), (12, 35)], [(4, 15), (20, 15)], [(12, 22), (22, 22), (28, 30), (22, 45), (14, 45)]]
}

def render_text_strokes(text, x, y, char_w=1.6, char_h=2.5, char_gap=0.45, align='left'):
    sx = char_w / 40.0
    sy = char_h / 50.0
    step_x = char_w + char_gap
    total_w = len(text) * step_x

    start_x = x
    if align == 'center':
        start_x = x - total_w / 2.0
    elif align == 'right':
        start_x = x - total_w

    paths = []
    cursor_x = start_x

    for ch in text:
        if ch == ' ':
            cursor_x += step_x * 0.85
            continue

        lookup_ch = ch.upper() if ch not in ALPHABET else ch
        if lookup_ch not in ALPHABET:
            mapping = {'é': 'E', 'ě': 'E', 'í': 'I', 'á': 'A', 'ý': 'Y', 'č': 'C', 'š': 'S', 'ž': 'Z', 'ř': 'R', 'ů': 'U', 'ú': 'U'}
            lookup_ch = mapping.get(ch, lookup_ch)
            if lookup_ch not in ALPHABET:
                lookup_ch = '?'

        strokes = ALPHABET.get(lookup_ch, [[(0, 0), (40, 50)], [(0, 50), (40, 0)]])
        for stroke in strokes:
            pts = [(cursor_x + px * sx, y + py * sy) for px, py in stroke]
            d = f"M {pts[0][0]:.2f},{pts[0][1]:.2f} " + " ".join(f"L {p[0]:.2f},{p[1]:.2f}" for p in pts[1:])
            paths.append(d)

        cursor_x += step_x

    return paths

def path_circle(cx, cy, r, segments=36):
    pts = []
    for i in range(segments + 1):
        a = 2.0 * math.pi * i / segments
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return f"M {pts[0][0]:.2f},{pts[0][1]:.2f} " + " ".join(f"L {p[0]:.2f},{p[1]:.2f}" for p in pts[1:])

def path_line(x1, y1, x2, y2):
    return f"M {x1:.2f},{y1:.2f} L {x2:.2f},{y2:.2f}"

def path_arc(cx, cy, r, start_rad, end_rad, segments=24):
    pts = []
    span = end_rad - start_rad
    for i in range(segments + 1):
        a = start_rad + span * (i / float(segments))
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return f"M {pts[0][0]:.2f},{pts[0][1]:.2f} " + " ".join(f"L {p[0]:.2f},{p[1]:.2f}" for p in pts[1:])

def path_rect(x, y, w, h):
    return f"M {x:.2f},{y:.2f} L {x+w:.2f},{y:.2f} L {x+w:.2f},{y+h:.2f} L {x:.2f},{y+h:.2f} Z"

def evaluate_nurbs_segment(p0, p1, p2, p3, w0=1.0, w1=1.0, w2=1.0, w3=1.0, steps=6):
    """Uniform cubic rational B-spline (NURBS) segment evaluation."""
    pts = []
    h = [
        (p0[0] * w0, p0[1] * w0, w0),
        (p1[0] * w1, p1[1] * w1, w1),
        (p2[0] * w2, p2[1] * w2, w2),
        (p3[0] * w3, p3[1] * w3, w3)
    ]
    for s in range(1, steps + 1):
        u = s / float(steps)
        u2 = u * u
        u3 = u2 * u
        b0 = (-u3 + 3.0 * u2 - 3.0 * u + 1.0) / 6.0
        b1 = (3.0 * u3 - 6.0 * u2 + 4.0) / 6.0
        b2 = (-3.0 * u3 + 3.0 * u2 + 3.0 * u + 1.0) / 6.0
        b3 = u3 / 6.0

        hx = b0 * h[0][0] + b1 * h[1][0] + b2 * h[2][0] + b3 * h[3][0]
        hy = b0 * h[0][1] + b1 * h[1][1] + b2 * h[2][1] + b3 * h[3][1]
        hw = b0 * h[0][2] + b1 * h[1][2] + b2 * h[2][2] + b3 * h[3][2]
        if hw != 0.0:
            pts.append((hx / hw, hy / hw))
        else:
            pts.append((hx, hy))
    return pts

def compute_spiro_point(t, cfg, grid, weather, planets):
    """
    Computes polar spirograph coordinate modulated by:
    1. Base thermal dilatancy (temperature)
    2. 50Hz continental European grid frequency deviation (symlog)
    3. Multi-planetary RTBP Lagrange harmonics (Mercury, Venus, Earth, Mars, Jupiter, Saturn)
    4. Prague wind speed 36-decan ripple petals
    5. Relative humidity Guilloché precession
    """
    T0 = float(cfg.get("period_sec", 24.0))
    R0 = float(cfg.get("r0_mm", 50.0))
    c = float(cfg.get("log_c", 5.0))
    ampl_grid_max = float(cfg.get("ampl_grid_max", 6.0))
    temp_factor = float(cfg.get("temp_factor", 0.15))
    lagrange_ampl = float(cfg.get("lagrange_ampl", 5.0))
    wind_ampl = float(cfg.get("wind_ampl", 3.0))

    omega0 = (2.0 * math.pi) / T0
    theta = omega0 * t

    # Thermal base
    R = R0 + temp_factor * (weather["temp_c"] - 10.0)

    # 50Hz Grid Symlog
    df = grid["drift_mhz"]
    sgn = 1.0 if df >= 0 else -1.0
    delta_grid = sgn * (math.log(1.0 + abs(df) / c) / math.log(1.0 + 50.0 / c)) * ampl_grid_max

    # Primary 6-fold Earth-Sun-Moon envelope
    r_lagrange = lagrange_ampl + (delta_grid * 0.3)

    # Multi-Planetary Libration potential
    delta_planets = 0.0
    grid_coupling = 1.0 + (df / 100.0)
    for name, p in planets.items():
        diff = theta - p["rad"]
        trojan = math.cos(3.0 * diff) * 0.55
        collinear = math.cos(2.0 * diff) * 0.35
        body = math.cos(diff) * 0.30
        delta_planets += p["ampl_mm"] * (body + collinear + trojan) * 0.22 * grid_coupling

    # 36 Decan wind ripples
    r_wind = 0.8 + (weather["wind_kmh"] / 40.0) * wind_ampl

    # Combined radius
    r_total = R + delta_grid + (r_lagrange * math.cos(6.0 * theta)) + delta_planets + (r_wind * math.cos(36.0 * theta))

    # Archimedean spiral pitch
    orbit_num = t / T0
    spiral_dr = cfg.get("spiral_dr_per_orbit", -0.4) * (orbit_num % 12.0)
    r_total += spiral_dr

    # Precession from humidity
    precess = orbit_num * (2.0 * math.pi / 36.0) * (0.8 + (weather["rh_pct"] / 100.0) * 0.4)
    ang = theta + precess

    x = r_total * math.sin(ang)
    y = -r_total * math.cos(ang)
    return x, y, r_total

def generate_spirograph_curve(cx, cy, scale=1.0, orbits=6, cfg=None, grid=None, weather=None, planets=None):
    """
    Generates a continuous, smooth multi-turn NURBS Spirograph mandala curve
    centered at (cx, cy) and scaled by scale factor.
    """
    if cfg is None:
        cfg = {
            "period_sec": 24.0,
            "r0_mm": 50.0,
            "step_interval_sec": 0.4,
            "nurbs_substeps": 5,
            "spiral_dr_per_orbit": -0.35,
            "log_c": 5.0,
            "ampl_grid_max": 5.5,
            "lagrange_ampl": 4.5,
            "wind_ampl": 2.5,
            "temp_factor": 0.12
        }
    if grid is None:
        grid = harvest_grid()
    if weather is None:
        weather = harvest_weather()
    if planets is None:
        planets = compute_planetary_lagrange()

    T0 = cfg["period_sec"]
    total_time = orbits * T0
    ctrl_dt = cfg["step_interval_sec"]
    num_ctrl = int(total_time / ctrl_dt)

    ctrl_pts = []
    ctrl_w = []
    for i in range(num_ctrl + 4):
        t_sim = i * ctrl_dt
        px, py, pr = compute_spiro_point(t_sim, cfg, grid, weather, planets)
        pw = 1.0 + abs(grid["drift_mhz"]) / 50.0 + (weather["wind_kmh"] / 80.0)
        ctrl_pts.append((cx + px * scale, cy + py * scale))
        ctrl_w.append(pw)

    all_pts = []
    substeps = cfg.get("nurbs_substeps", 5)
    for i in range(len(ctrl_pts) - 3):
        seg = evaluate_nurbs_segment(
            ctrl_pts[i], ctrl_pts[i+1], ctrl_pts[i+2], ctrl_pts[i+3],
            ctrl_w[i], ctrl_w[i+1], ctrl_w[i+2], ctrl_w[i+3],
            steps=substeps
        )
        all_pts.extend(seg)

    if not all_pts:
        return ""
    d_str = f"M {all_pts[0][0]:.2f},{all_pts[0][1]:.2f} " + " ".join(f"L {p[0]:.2f},{p[1]:.2f}" for p in all_pts[1:])
    return d_str

def compute_celestial_state(target_ts=None):
    if target_ts is None:
        target_ts = time.time()

    dt_utc = datetime.fromtimestamp(target_ts, tz=timezone.utc)
    dt_prague = dt_utc + timedelta(hours=1)

    sec_day = dt_prague.hour * 3600.0 + dt_prague.minute * 60.0 + dt_prague.second + (dt_prague.microsecond / 1e6)

    # Decanic Metric Time (dh36)
    dh36_raw = (sec_day / 86400.0) * 36.0
    decan = int(dh36_raw) % 36
    rem_dh = dh36_raw - int(dh36_raw)
    dm = int(rem_dh * 100.0)
    rem_dm = (rem_dh * 100.0) - dm
    ds = int(rem_dm * 100.0)
    dh36_str = f"{decan:02d}.{dm:02d}.{ds:02d}"

    solar_azimuth = (sec_day / 86400.0) * 360.0

    synodic_month = 29.53058867
    j2000_epoch = 947182440.0
    diff_days = (target_ts - j2000_epoch) / 86400.0
    lunation = int(diff_days / synodic_month) + 1
    phase_pos = (diff_days % synodic_month) / synodic_month
    illumination = 0.5 * (1.0 - math.cos(2.0 * math.pi * phase_pos))

    grid = harvest_grid()
    weather = harvest_weather()
    planets = compute_planetary_lagrange(target_ts)

    return {
        "timestamp": target_ts,
        "cet_str": dt_prague.strftime("%Y-%m-%d %H:%M:%S"),
        "dh36": {
            "str": dh36_str,
            "decan": decan,
            "azimuth_deg": round(solar_azimuth, 2),
            "val": dh36_raw
        },
        "lunar": {
            "position": round(phase_pos, 4),
            "illumination_pct": round(illumination * 100.0, 1),
            "lunation_number": lunation
        },
        "grid": grid,
        "weather": weather,
        "planets": planets
    }

def generate_lagrange_svg(state, width_mm=120.0, mode="plate"):
    """
    Renders SVG vector drawing:
    - mode="plate": Golden ratio broadsheet with multi-planetary constellation dial,
                    overlaid continuous spirograph curve, telemetry table, and 50Hz drift seismograph.
    - mode="spirograph": Full circular 10cm Spirograph mandala with planetary libration lobes,
                         outer decanic dial, and technical title block.
    """
    paths = []
    planets = state.get("planets", compute_planetary_lagrange(state.get("timestamp")))
    grid = state.get("grid", harvest_grid())
    weather = state.get("weather", harvest_weather())

    if mode == "spirograph":
        # Pure Circular Spirograph Mandala (Square layout, e.g. 140x140 mm)
        w_mm = width_mm
        h_mm = width_mm
        cx = w_mm / 2.0
        cy = h_mm / 2.0 - 4.0
        r_outer = 56.0
        r_inner = 50.0

        # Outer border
        paths.append(path_rect(1.5, 1.5, w_mm - 3.0, h_mm - 3.0))
        paths.append(path_rect(3.5, 3.5, w_mm - 7.0, h_mm - 7.0))

        # 36 Decan dial rim
        paths.append(path_circle(cx, cy, r_outer, segments=72))
        paths.append(path_circle(cx, cy, r_inner, segments=72))
        for i in range(36):
            a_deg = i * 10.0
            rad = math.radians(a_deg - 90.0)
            is_card = (i % 9 == 0)
            r_t = r_inner - (3.5 if is_card else 1.8)
            paths.append(path_line(cx + r_t * math.cos(rad), cy + r_t * math.sin(rad),
                                   cx + r_outer * math.cos(rad), cy + r_outer * math.sin(rad)))

        # Multi-Planetary orbital guide rings
        orbit_radii = {
            "Mercury": 10.0,
            "Venus":   17.0,
            "Earth":   24.0,
            "Mars":    31.0,
            "Jupiter": 39.0,
            "Saturn":  47.0
        }
        for p_name, r_orb in orbit_radii.items():
            paths.append(path_circle(cx, cy, r_orb, segments=48))
            p_dat = planets.get(p_name, {})
            l_deg = p_dat.get("longitude_deg", 0.0)
            p_rad = math.radians(l_deg - 90.0)
            px = cx + r_orb * math.cos(p_rad)
            py = cy + r_orb * math.sin(p_rad)

            # Planet marker & label
            paths.append(path_circle(px, py, 1.4, segments=16))
            paths.extend(render_text_strokes(p_dat.get("symbol", p_name[0]), px + 1.8, py - 1.5, char_w=1.2, char_h=1.6))

            # Trojan libration markers L4 (+60) & L5 (-60)
            l4_rad = p_rad + math.pi / 3.0
            l5_rad = p_rad - math.pi / 3.0
            for l_rad, l_lbl in [(l4_rad, "L4"), (l5_rad, "L5")]:
                lx = cx + r_orb * math.cos(l_rad)
                ly = cy + r_orb * math.sin(l_rad)
                paths.append(path_line(lx - 0.8, ly, lx + 0.8, ly))
                paths.append(path_line(lx, ly - 0.8, lx, ly + 0.8))
                paths.append(path_line(cx, cy, lx, ly)) # Light ray from Sun

        # Center Sun (SOL)
        paths.append(path_circle(cx, cy, 2.5, segments=24))
        for sang in [0, math.pi/4, math.pi/2, 3*math.pi/4, math.pi, 5*math.pi/4, 3*math.pi/2, 7*math.pi/4]:
            paths.append(path_line(cx + 2.5 * math.cos(sang), cy + 2.5 * math.sin(sang),
                                   cx + 4.0 * math.cos(sang), cy + 4.0 * math.sin(sang)))
        paths.extend(render_text_strokes("SOL", cx - 2.0, cy - 3.8, char_w=1.0, char_h=1.4, align="center"))

        # The Spirograph mandala curve (full size 10 cm, 8 orbits)
        cfg_spiro = {
            "period_sec": 24.0,
            "r0_mm": 50.0,
            "step_interval_sec": 0.35,
            "nurbs_substeps": 6,
            "spiral_dr_per_orbit": -0.4,
            "log_c": 5.0,
            "ampl_grid_max": 6.0,
            "lagrange_ampl": 5.0,
            "wind_ampl": 3.0,
            "temp_factor": 0.15
        }
        spiro_d = generate_spirograph_curve(cx, cy, scale=1.0, orbits=8, cfg=cfg_spiro, grid=grid, weather=weather, planets=planets)
        if spiro_d:
            paths.append(spiro_d)

        # Bottom Title Block
        tb_y = h_mm - 12.0
        paths.append(path_line(6.0, tb_y, w_mm - 6.0, tb_y))
        paths.extend(render_text_strokes("LAGRANGE // MULTI-PLANETARY CELESTIAL SPIROGRAPH", cx, tb_y + 1.2, char_w=1.4, char_h=2.0, align="center"))
        t_info = f"50HZ: {grid['freq_hz']:.3f} HZ (D{grid['drift_mhz']:+.1f}M) | {state['cet_str']} CET | DEKAN {state['dh36']['decan']:02d} | --TÉCHNĒ & KOF"
        paths.extend(render_text_strokes(t_info, cx, tb_y + 4.4, char_w=1.0, char_h=1.4, align="center"))

    else:
        # Standard Golden Ratio Plate (120 x 74.2 mm)
        h_mm = width_mm / PHI
        w_mm = width_mm

        # Outer Borders
        paths.append(path_rect(1.0, 1.0, w_mm - 2.0, h_mm - 2.0))
        paths.append(path_rect(2.8, 2.8, w_mm - 5.6, h_mm - 5.6))

        # Corner brackets
        c = 5.0
        paths.append(path_line(4.5, 4.5, 4.5 + c, 4.5))
        paths.append(path_line(4.5, 4.5, 4.5, 4.5 + c))
        paths.append(path_line(w_mm - 4.5, 4.5, w_mm - 4.5 - c, 4.5))
        paths.append(path_line(w_mm - 4.5, 4.5, w_mm - 4.5, 4.5 + c))
        paths.append(path_line(4.5, h_mm - 4.5, 4.5 + c, h_mm - 4.5))
        paths.append(path_line(4.5, h_mm - 4.5, 4.5, h_mm - 4.5 - c))
        paths.append(path_line(w_mm - 4.5, h_mm - 4.5, w_mm - 4.5 - c, h_mm - 4.5))
        paths.append(path_line(w_mm - 4.5, h_mm - 4.5, w_mm - 4.5, h_mm - 4.5 - c))

        # Left Celestial Dial Geometry
        cx = 30.0
        cy = h_mm / 2.0
        r_outer = 25.0
        r_inner = r_outer * 0.88
        r_field = r_inner * 0.78

        paths.append(path_circle(cx, cy, r_outer, segments=48))
        paths.append(path_circle(cx, cy, r_inner, segments=48))
        paths.append(path_circle(cx, cy, r_field, segments=36))

        # 36 Decan Ticks (10° arc = 1.0 dh36)
        for i in range(36):
            a_deg = i * 10.0
            rad = math.radians(a_deg - 90.0)
            is_card = (i % 9 == 0)
            t_start = r_inner * 0.70 if is_card else r_inner
            paths.append(path_line(cx + t_start * math.cos(rad), cy + t_start * math.sin(rad),
                                   cx + r_outer * math.cos(rad), cy + r_outer * math.sin(rad)))

        # Cardinal labels
        r_lbl = r_inner * 0.60
        paths.extend(render_text_strokes("N", cx, cy - r_lbl - 1.2, char_w=1.3, char_h=1.8, align="center"))
        paths.extend(render_text_strokes("E", cx + r_lbl, cy - 0.9, char_w=1.3, char_h=1.8, align="center"))
        paths.extend(render_text_strokes("S", cx, cy + r_lbl - 0.9, char_w=1.3, char_h=1.8, align="center"))
        paths.extend(render_text_strokes("W", cx - r_lbl, cy - 0.9, char_w=1.3, char_h=1.8, align="center"))

        # Center: Sun (SOL)
        paths.append(path_circle(cx, cy, 1.4, segments=16))
        for sang in [0, math.pi/2, math.pi, 3*math.pi/2]:
            paths.append(path_line(cx + 1.4 * math.cos(sang), cy + 1.4 * math.sin(sang),
                                   cx + 2.2 * math.cos(sang), cy + 2.2 * math.sin(sang)))
        paths.extend(render_text_strokes("SOL", cx, cy - 2.8, char_w=0.65, char_h=0.9, align="center"))

        # Multi-Planetary orbital guide radii scaled for the 20mm dial field
        dial_orbit_r = {
            "Mercury": 3.8,
            "Venus":   6.4,
            "Earth":   9.2,
            "Mars":    12.0,
            "Jupiter": 15.2,
            "Saturn":  18.5
        }

        for p_name, r_orb in dial_orbit_r.items():
            paths.append(path_circle(cx, cy, r_orb, segments=36))
            p_dat = planets.get(p_name, {})
            l_deg = p_dat.get("longitude_deg", 0.0)
            p_rad = math.radians(l_deg - 90.0)
            px = cx + r_orb * math.cos(p_rad)
            py = cy + r_orb * math.sin(p_rad)

            # Planet marker & Symbol
            p_sz = 0.9 if p_name != "Jupiter" else 1.2
            paths.append(path_circle(px, py, p_sz, segments=12))
            paths.extend(render_text_strokes(p_dat.get("symbol", p_name[0]), px + 1.2, py - 1.0, char_w=0.8, char_h=1.1))

            # Trojan Libration Points L4 & L5
            l4_rad = p_rad + math.pi / 3.0
            l5_rad = p_rad - math.pi / 3.0
            for l_rad, l_lbl in [(l4_rad, "4"), (l5_rad, "5")]:
                lx = cx + r_orb * math.cos(l_rad)
                ly = cy + r_orb * math.sin(l_rad)
                paths.append(path_line(lx - 0.5, ly, lx + 0.5, ly))
                paths.append(path_line(lx, ly - 0.5, lx, ly + 0.5))
                # Light dashed vector from planet to Trojan
                paths.append(path_line(px, py, lx, ly))

            # Collinear L2 point (night-side shadow)
            l2_rad = p_rad + math.pi
            l2_x = cx + r_orb * math.cos(l2_rad)
            l2_y = cy + r_orb * math.sin(l2_rad)
            paths.append(path_circle(l2_x, l2_y, 0.4, segments=8))

        # Earth-Moon Subsystem
        p_ear = planets.get("Earth", {})
        ear_rad = math.radians(p_ear.get("longitude_deg", 59.4) - 90.0)
        ex = cx + dial_orbit_r["Earth"] * math.cos(ear_rad)
        ey = cy + dial_orbit_r["Earth"] * math.sin(ear_rad)
        luna_pos = state["lunar"]["position"]
        moon_rad = ear_rad + luna_pos * 2.0 * math.pi
        mx = ex + 1.8 * math.cos(moon_rad)
        my = ey + 1.8 * math.sin(moon_rad)
        paths.append(path_circle(mx, my, 0.45, segments=8))
        paths.append(path_line(ex, ey, mx, my))

        # Overlaid Spirograph Mandala curve inside dial (scale = 0.38)
        spiro_plate = generate_spirograph_curve(cx, cy, scale=0.38, orbits=5, grid=grid, weather=weather, planets=planets)
        if spiro_plate:
            paths.append(spiro_plate)

        # 50 Hz Grid drift meter below dial (Y: 64 to 71 mm)
        grid_mhz = grid["drift_mhz"]
        bar_y = h_mm - 7.2
        paths.append(path_line(12.0, bar_y, 48.0, bar_y))
        paths.append(path_line(30.0, bar_y - 1.5, 30.0, bar_y + 1.5))
        for dm in [-40, -20, 20, 40]:
            tx_m = 30.0 + (dm / 50.0) * 15.0
            paths.append(path_line(tx_m, bar_y - 0.8, tx_m, bar_y + 0.8))
        drift_clamped = max(-50.0, min(50.0, grid_mhz))
        px_m = 30.0 + (drift_clamped / 50.0) * 15.0
        paths.append(path_line(px_m, bar_y - 2.2, px_m, bar_y + 2.2))
        paths.append(f"M {px_m-0.8:.2f},{bar_y-2.2:.2f} L {px_m+0.8:.2f},{bar_y-2.2:.2f} L {px_m:.2f},{bar_y-0.8:.2f} Z")
        paths.extend(render_text_strokes(f"50HZ: {grid['freq_hz']:.3f}HZ (D{grid['drift_mhz']:+.1f}M)", 30.0, bar_y + 2.0, char_w=0.85, char_h=1.2, align="center"))

        # Divider line
        div_x = 59.0
        paths.append(path_line(div_x, 4.5, div_x, h_mm - 4.5))
        paths.append(path_line(div_x + 0.8, 6.0, div_x + 0.8, h_mm - 6.0))

        # Right Typography & Telemetry Header
        tx = div_x + 3.2
        y_start = 5.2
        pitch_y = 3.8

        p_mer = planets.get("Mercury", {})
        p_ven = planets.get("Venus", {})
        p_ear = planets.get("Earth", {})
        p_mar = planets.get("Mars", {})
        p_jup = planets.get("Jupiter", {})
        p_sat = planets.get("Saturn", {})

        lines = [
            ("LAGRANGE // MULTI-PLANETARY SPIROGRAPH", 1.5, 2.2),
            (f"ČAS : {state['cet_str']} CET", 1.25, 1.7),
            (f"DH36: {state['dh36']['str']} (DEKAN {state['dh36']['decan']:02d})", 1.2, 1.6),
            (f"LUNA: {state['lunar']['lunation_number']}. LUNACE ({state['lunar']['illumination_pct']}%)", 1.2, 1.6),
            (f"SÍŤ : {grid['freq_hz']:.3f} HZ (Δ {grid['drift_mhz']:+.1f} MHZ)", 1.2, 1.6),
            (f"METEO: {weather['temp_c']:+.1f}°C | {weather['pressure_hpa']:.0f} HPA | {weather['wind_kmh']:.0f} KM/H", 1.15, 1.55),
            (f"☿:{p_mer.get('longitude_deg',0):.0f}° ♀:{p_ven.get('longitude_deg',0):.0f}° ♁:{p_ear.get('longitude_deg',0):.0f}° ♂:{p_mar.get('longitude_deg',0):.0f}° ♃:{p_jup.get('longitude_deg',0):.0f}° ♄:{p_sat.get('longitude_deg',0):.0f}°", 1.05, 1.45),
            ("RTBP L1-L5 LIBRAČNÍ HARMONIKY // --TÉCHNĒ & KOF", 1.05, 1.45),
        ]

        for idx, (txt, cw, ch) in enumerate(lines):
            cur_y = y_start + idx * pitch_y
            paths.extend(render_text_strokes(txt, tx, cur_y, char_w=cw, char_h=ch))

        # Title underline
        paths.append(path_line(tx, y_start + 3.4, w_mm - 5.0, y_start + 3.4))

        # 50Hz Hourly Grid Drift Seismograph Graph (Y: 37.0 to 68.5 mm)
        gx = tx
        gy_top = 37.0
        gw = (w_mm - 5.0) - gx
        gh = (h_mm - 5.5) - gy_top
        gy_mid = gy_top + gh * 0.46

        paths.append(path_rect(gx, gy_top, gw, gh))
        paths.extend(render_text_strokes("[STOPA: SÍŤ 50 HZ // HODINOVÝ DRIFT]", gx + 2.0, gy_top + 1.4, char_w=0.85, char_h=1.2))

        paths.append(path_line(gx + 11.5, gy_mid, gx + gw - 2.0, gy_mid))
        paths.extend(render_text_strokes("50.0", gx + 1.2, gy_mid - 0.8, char_w=0.8, char_h=1.2))

        y_pos50 = gy_mid - (50.0 / 50.0) * (gh * 0.27)
        y_neg50 = gy_mid - (-50.0 / 50.0) * (gh * 0.27)
        for y_dash in [y_pos50, y_neg50]:
            cur_x = gx + 11.5
            while cur_x < gx + gw - 2.0:
                paths.append(path_line(cur_x, y_dash, min(cur_x + 2.0, gx + gw - 2.0), y_dash))
                cur_x += 4.0
        paths.extend(render_text_strokes("+50", gx + 1.2, y_pos50 - 0.8, char_w=0.75, char_h=1.1))
        paths.extend(render_text_strokes("-50", gx + 1.2, y_neg50 - 0.8, char_w=0.75, char_h=1.1))

        # Seismograph trace with planetary libration modulation
        cur_drift = grid["drift_mhz"]
        num_pts = 48
        plot_w = (gx + gw - 2.5) - (gx + 12.0)
        x_step = plot_w / float(num_pts)
        trace_pts = []
        for i in range(num_pts + 1):
            xp = (gx + 12.0) + i * x_step
            delta = math.sin(i * 0.42) * 5.5 + math.cos(i * 0.21) * 3.8 + math.sin(i * 0.85) * 2.0
            # Jupiter & Saturn libration undertone
            jup_wave = math.sin(i * 0.15 + p_jup.get("rad", 0.0)) * 2.5
            d_val = cur_drift + delta + jup_wave
            clamped = max(-55.0, min(55.0, d_val))
            yp = gy_mid - (clamped / 50.0) * (gh * 0.27)
            trace_pts.append((xp, yp))

        d_trace = f"M {trace_pts[0][0]:.2f},{trace_pts[0][1]:.2f} " + " ".join(f"L {p[0]:.2f},{p[1]:.2f}" for p in trace_pts[1:])
        paths.append(d_trace)

        ax_y = gy_top + gh - 4.2
        paths.append(path_line(gx + 11.5, ax_y, gx + gw - 2.0, ax_y))
        for idx_t, (frac, label_t) in enumerate([(0.0, "-60M"), (0.5, "-30M"), (1.0, "[NYNÍ]")]):
            tx_p = (gx + 12.0) + frac * plot_w
            paths.append(path_line(tx_p, ax_y, tx_p, ax_y - 1.2))
            al = "left" if idx_t == 0 else ("center" if idx_t == 1 else "right")
            paths.extend(render_text_strokes(label_t, tx_p, ax_y + 0.9, char_w=0.75, char_h=1.1, align=al))

    d_attr = " ".join(paths)
    svg = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg width="{w_mm:.2f}mm" height="{h_mm:.2f}mm" viewBox="0 0 {w_mm:.2f} {h_mm:.2f}" '
        f'xmlns="http://www.w3.org/2000/svg">\n'
        f'  <g id="lagrange_constellation">\n'
        f'    <path d="{d_attr}" stroke="black" stroke-width="0.25" fill="none" stroke-linecap="round" stroke-linejoin="round" />\n'
        f'  </g>\n'
        f'</svg>\n'
    )
    return svg, w_mm, h_mm

def main():
    parser = argparse.ArgumentParser(description="Multi-Planetary Three-Body Lagrange Libration & Spirograph Engine")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # status
    p_status = subparsers.add_parser("status", help="Print celestial coordinates, planetary positions & telemetry")
    p_status.add_argument("--json", action="store_true", help="Output JSON")

    # svg
    p_svg = subparsers.add_parser("svg", help="Generate vector SVG constellation / spirograph")
    p_svg.add_argument("--out", type=str, default="/tmp/lagrange_constellation.svg", help="Output SVG path")
    p_svg.add_argument("--width", type=float, default=120.0, help="Width in mm (Golden Ratio phi)")
    p_svg.add_argument("--spiro", action="store_true", help="Generate standalone circular Spirograph mandala")

    # plot
    p_plot = subparsers.add_parser("plot", help="Dispatch to Drkota V-plotter")
    p_plot.add_argument("--dry-run", action="store_true", help="Simulate without hardware movement")
    p_plot.add_argument("--width", type=float, default=120.0, help="Width in mm")
    p_plot.add_argument("--spiro", action="store_true", help="Plot standalone circular Spirograph mandala")
    p_plot.add_argument("--scale", type=float, default=0.5, help="Scale factor (default 0.5 = 50%%)")
    p_plot.add_argument("--speed", type=int, default=150, help="Stepper pulse delay in us (default 150 = 2x speed)")
    p_plot.add_argument("--feed", type=float, default=1.0, help="Feedrate multiplier (default 1.0)")

    args = parser.parse_args()
    state = compute_celestial_state()

    if args.command == "status" or args.command is None:
        if getattr(args, "json", False):
            print(json.dumps(state, indent=2, ensure_ascii=False))
        else:
            planets = state["planets"]
            print("╔══════════════════════════════════════════════════════════════════════════╗")
            print("║ LAGRANGE // MULTI-PLANETARY THREE-BODY LIBRATION & SPIROGRAPH ENGINE     ║")
            print("╠══════════════════════════════════════════════════════════════════════════╣")
            print(f"║ Občanský čas   : {state['cet_str']} CET                    ║")
            print(f"║ Metrický čas   : {state['dh36']['str']} (Dekan {state['dh36']['decan']:02d} | Azimut {state['dh36']['azimuth_deg']:.1f}°) ║")
            print(f"║ Lunární fáze   : {state['lunar']['lunation_number']}. lunace | {state['lunar']['illumination_pct']}% osvětlení      ║")
            print(f"║ 50Hz Síť       : {state['grid']['freq_hz']:.3f} Hz (Δ {state['grid']['drift_mhz']:+.1f} mHz) [{state['grid']['status']}]             ║")
            print(f"║ Počasí Praha   : {state['weather']['temp_c']:+.1f}°C | {state['weather']['pressure_hpa']:.1f} hPa | {state['weather']['rh_pct']}% RH          ║")
            print("╠══════════════════════════════════════════════════════════════════════════╣")
            print("║ Planety & Librační body L4 (+60°) / L5 (-60°) / L2 (stín):               ║")
            for p_name, p in planets.items():
                print(f"║   • {p['symbol']} {p['name_la']:<9} (λ={p['longitude_deg']:>5.1f}°) : L4={p['l4_deg']:>5.1f}°, L5={p['l5_deg']:>5.1f}°, L2={p['l2_deg']:>5.1f}° (μ={p['mu']:.2e}) ║")
            print("╚══════════════════════════════════════════════════════════════════════════╝")

    elif args.command == "svg":
        mode = "spirograph" if args.spiro else "plate"
        svg_data, w, h = generate_lagrange_svg(state, width_mm=args.width, mode=mode)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(svg_data)
        print(f"[+] Multi-planetární Lagrange SVG vygenerováno ({mode}): {args.out} ({w:.1f}x{h:.1f} mm)")
        png_path = convert_svg_to_png(args.out)
        if png_path and os.path.exists(png_path):
            print(f"[+] PNG náhled vygenerován: {png_path} ({os.path.getsize(png_path)} bajtů)")

    elif args.command == "plot":
        mode = "spirograph" if args.spiro else "plate"
        svg_data, w, h = generate_lagrange_svg(state, width_mm=args.width, mode=mode)
        out_svg = f"/tmp/lagrange_plot_{int(time.time())}.svg"
        with open(out_svg, "w", encoding="utf-8") as f:
            f.write(svg_data)
        print(f"[+] Připraven tiskový arch pro Drkotu ({mode}): {out_svg} ({w:.1f}x{h:.1f} mm)")
        png_path = convert_svg_to_png(out_svg)
        if png_path and os.path.exists(png_path):
            print(f"[+] PNG náhled vygenerován: {png_path} ({os.path.getsize(png_path)} bajtů)")
        plot_args = f"--scale {args.scale} --speed {args.speed} --feed {args.feed}"
        if args.dry_run:
            print(f"[DRY-RUN] Simulace plotru Drkota: /home/kof/bin/drkota plot {out_svg} {plot_args}")
        else:
            drkota_cmd = f"/home/kof/bin/drkota plot {out_svg} {plot_args}"
            os.system(drkota_cmd)

if __name__ == "__main__":
    main()
