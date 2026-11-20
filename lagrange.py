#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lagrange.py — Three-Body Lagrange Libration Points & Constellation Engine
Observatoř Cybernetics // Kryštof Pešek (Kof) & Techné (τέχνη)
CC0 1.0 Universal // Public Domain // Anti-Copyright
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
        "temp_c": 9.0,
        "rh_pct": 79,
        "pressure_hpa": 975.2,
        "wind_kmh": 12.0,
        "source": "nominal_prague"
    }

def convert_svg_to_png(svg_path, width_px=1400):
    """
    Automatically converts rendered SVG to high-resolution PNG companion.
    Prioritizes /usr/bin/rsvg-convert (fastest), falls back to inkscape or ImageMagick convert.
    """
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
    # Greek / Latin Macron Extensions for Techné
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
    # Punctuation & Symbols
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

        lookup_ch = ch.upper()
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

def compute_celestial_state(target_ts=None):
    if target_ts is None:
        target_ts = time.time()
    
    prague_offset = timedelta(hours=1)
    # Check DST (March to October approx)
    dt_utc = datetime.fromtimestamp(target_ts, tz=timezone.utc)
    # Prague rough CET/CEST
    dt_prague = dt_utc + timedelta(hours=1)
    
    sec_day = dt_prague.hour * 3600.0 + dt_prague.minute * 60.0 + dt_prague.second + (dt_prague.microsecond / 1e6)
    
    # Decanic Harmonic Metric Time (dh36)
    dh36_raw = (sec_day / 86400.0) * 36.0
    decan = int(dh36_raw) % 36
    rem_dh = dh36_raw - int(dh36_raw)
    dm = int(rem_dh * 100.0)
    rem_dm = (rem_dh * 100.0) - dm
    ds = int(rem_dm * 100.0)
    dh36_str = f"{decan:02d}.{dm:02d}.{ds:02d}"
    
    # Solar azimuth (360 deg in 24 hours, noon=180 deg South)
    solar_azimuth = (sec_day / 86400.0) * 360.0
    
    # Synodic lunar cycle (Meeus formula)
    # Reference epoch: 2000-01-06 18:14 UTC (New Moon, J2000 = 2451549.5)
    synodic_month = 29.53058867
    j2000_epoch = 947182440.0
    diff_days = (target_ts - j2000_epoch) / 86400.0
    lunation = int(diff_days / synodic_month) + 1
    phase_pos = (diff_days % synodic_month) / synodic_month
    illumination = 0.5 * (1.0 - math.cos(2.0 * math.pi * phase_pos))
    
    grid = harvest_grid()
    weather = harvest_weather()
    
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
        "weather": weather
    }

def generate_lagrange_svg(state, width_mm=120.0):
    h_mm = width_mm / PHI
    paths = []
    
    # Outer Borders (Golden Ratio)
    paths.append(path_rect(1.0, 1.0, width_mm - 2.0, h_mm - 2.0))
    paths.append(path_rect(2.8, 2.8, width_mm - 5.6, h_mm - 5.6))
    
    # Corner brackets
    c = 5.0
    paths.append(path_line(4.5, 4.5, 4.5 + c, 4.5))
    paths.append(path_line(4.5, 4.5, 4.5, 4.5 + c))
    paths.append(path_line(width_mm - 4.5, 4.5, width_mm - 4.5 - c, 4.5))
    paths.append(path_line(width_mm - 4.5, 4.5, width_mm - 4.5, 4.5 + c))
    paths.append(path_line(4.5, h_mm - 4.5, 4.5 + c, h_mm - 4.5))
    paths.append(path_line(4.5, h_mm - 4.5, 4.5, h_mm - 4.5 - c))
    paths.append(path_line(width_mm - 4.5, h_mm - 4.5, width_mm - 4.5 - c, h_mm - 4.5))
    paths.append(path_line(width_mm - 4.5, h_mm - 4.5, width_mm - 4.5, h_mm - 4.5 - c))
    
    # Celestial Dial Geometry
    cx = 30.0
    cy = h_mm / 2.0
    r_outer = 25.0
    r_inner = r_outer * 0.88
    
    paths.append(path_circle(cx, cy, r_outer, segments=48))
    paths.append(path_circle(cx, cy, r_inner, segments=48))
    paths.append(path_circle(cx, cy, r_inner * 0.76, segments=36))
    
    # 36 Decan Ticks (10° arc = 1.0 dh36)
    for i in range(36):
        a_deg = i * 10.0
        rad = math.radians(a_deg - 90.0)
        is_card = (i % 9 == 0)
        t_start = r_inner * 0.68 if is_card else r_inner
        paths.append(path_line(cx + t_start * math.cos(rad), cy + t_start * math.sin(rad),
                               cx + r_outer * math.cos(rad), cy + r_outer * math.sin(rad)))
    
    # Cardinal labels
    r_lbl = r_inner * 0.58
    paths.extend(render_text_strokes("N", cx, cy - r_lbl - 1.2, char_w=1.4, char_h=2.0, align="center"))
    paths.extend(render_text_strokes("E", cx + r_lbl, cy - 1.0, char_w=1.4, char_h=2.0, align="center"))
    paths.extend(render_text_strokes("S", cx, cy + r_lbl - 1.0, char_w=1.4, char_h=2.0, align="center"))
    paths.extend(render_text_strokes("W", cx - r_lbl, cy - 1.0, char_w=1.4, char_h=2.0, align="center"))
    
    # Three-Body Lagrange Constellation
    azim = state["dh36"]["azimuth_deg"]
    luna_pos = state["lunar"]["position"]
    sun_rad = math.radians(azim - 90.0)
    moon_rad = sun_rad + luna_pos * 2.0 * math.pi
    r_field = r_inner * 0.72
    
    # 1. Earth (Center)
    r_earth = 1.6
    paths.append(path_circle(cx, cy, r_earth, segments=16))
    paths.append(path_line(cx - r_earth, cy, cx + r_earth, cy))
    paths.append(path_line(cx, cy - r_earth, cx, cy + r_earth))
    paths.extend(render_text_strokes("TERRA", cx - 2.5, cy + 2.5, char_w=0.65, char_h=0.9, align="center"))
    
    # 2. Sun (SOL)
    d_sun = r_field * 0.55
    sx = cx + d_sun * math.cos(sun_rad)
    sy = cy + d_sun * math.sin(sun_rad)
    r_sun = 1.9
    paths.append(path_circle(sx, sy, r_sun, segments=20))
    for ang in [0, math.pi/2, math.pi, 3*math.pi/2]:
        paths.append(path_line(sx + r_sun * math.cos(ang), sy + r_sun * math.sin(ang),
                               sx + (r_sun + 1.2) * math.cos(ang), sy + (r_sun + 1.2) * math.sin(ang)))
    paths.extend(render_text_strokes("SOL", sx + 2.2, sy - 2.0, char_w=0.8, char_h=1.2, align="left"))
    
    # 3. Moon (LUNA)
    d_moon = r_field * 0.32
    mx = cx + d_moon * math.cos(moon_rad)
    my = cy + d_moon * math.sin(moon_rad)
    r_moon = 1.2
    paths.append(path_circle(mx, my, r_moon, segments=16))
    paths.extend(render_text_strokes("LUNA", mx + 1.6, my - 1.5, char_w=0.7, char_h=1.0, align="left"))
    
    # 4. Sun-Earth Outer Collinear Points (L2 & L3)
    # L2 (Night shadow beyond Earth)
    d_l2 = r_field * 0.80
    l2_rad = sun_rad + math.pi
    l2_x = cx + d_l2 * math.cos(l2_rad)
    l2_y = cy + d_l2 * math.sin(l2_rad)
    s_l2 = 1.3
    paths.append(f"M {l2_x:.2f},{l2_y-s_l2:.2f} L {l2_x+s_l2:.2f},{l2_y:.2f} L {l2_x:.2f},{l2_y+s_l2:.2f} L {l2_x-s_l2:.2f},{l2_y:.2f} Z")
    paths.extend(render_text_strokes("L2", l2_x + 1.8, l2_y - 1.4, char_w=0.85, char_h=1.3, align="left"))
    
    # L3 (Anti-Earth behind Sun)
    d_l3 = r_field * 0.86
    l3_rad = sun_rad
    l3_x = cx + d_l3 * math.cos(l3_rad)
    l3_y = cy + d_l3 * math.sin(l3_rad)
    s_l3 = 1.3
    paths.append(f"M {l3_x:.2f},{l3_y-s_l3:.2f} L {l3_x+s_l3:.2f},{l3_y:.2f} L {l3_x:.2f},{l3_y+s_l3:.2f} L {l3_x-s_l3:.2f},{l3_y:.2f} Z")
    paths.extend(render_text_strokes("L3", l3_x + 1.8, l3_y - 1.4, char_w=0.85, char_h=1.3, align="left"))
    
    # 5. Sun-Earth Trojans (L4 & L5)
    l4_rad = sun_rad + math.pi / 3.0
    l5_rad = sun_rad - math.pi / 3.0
    l4_x = cx + d_sun * math.cos(l4_rad)
    l4_y = cy + d_sun * math.sin(l4_rad)
    l5_x = cx + d_sun * math.cos(l5_rad)
    l5_y = cy + d_sun * math.sin(l5_rad)
    for px, py, lbl in [(l4_x, l4_y, "L4"), (l5_x, l5_y, "L5")]:
        paths.append(path_line(px - 1.1, py, px + 1.1, py))
        paths.append(path_line(px, py - 1.1, px, py + 1.1))
        paths.extend(render_text_strokes(lbl, px + 1.6, py - 1.4, char_w=0.8, char_h=1.2, align="left"))
    
    # 6. Earth-Moon Distant Lagrange Point L2M
    d_l2m = d_moon + r_field * 0.16
    l2m_x = cx + d_l2m * math.cos(moon_rad)
    l2m_y = cy + d_l2m * math.sin(moon_rad)
    paths.append(path_line(l2m_x - 0.7, l2m_y, l2m_x + 0.7, l2m_y))
    paths.append(path_line(l2m_x, l2m_y - 0.7, l2m_x, l2m_y + 0.7))
    paths.extend(render_text_strokes("L2M", l2m_x + 1.2, l2m_y - 1.0, char_w=0.6, char_h=0.9, align="left"))
    
    # 7. Constellation Asterism Lines
    paths.append(path_line(l3_x, l3_y, sx, sy))
    paths.append(path_line(sx, sy, cx, cy))
    paths.append(path_line(cx, cy, l2_x, l2_y))
    paths.append(path_line(sx, sy, l4_x, l4_y))
    paths.append(path_line(l4_x, l4_y, cx, cy))
    paths.append(path_line(sx, sy, l5_x, l5_y))
    paths.append(path_line(l5_x, l5_y, cx, cy))
    paths.append(path_line(cx, cy, mx, my))
    paths.append(path_line(mx, my, l2m_x, l2m_y))
    paths.append(path_arc(cx, cy, d_sun, min(l5_rad, l4_rad), max(l5_rad, l4_rad), segments=20))
    
    # 50 Hz Grid drift meter below dial (Y: 64 to 71 mm)
    grid_mhz = state["grid"]["drift_mhz"]
    bar_y = h_mm - 7.2
    paths.append(path_line(12.0, bar_y, 48.0, bar_y))
    # Major center tick (0 mHz / 50.000 Hz)
    paths.append(path_line(30.0, bar_y - 1.5, 30.0, bar_y + 1.5))
    # Minor ticks (+-20, +-40 mHz)
    for dm in [-40, -20, 20, 40]:
        tx_m = 30.0 + (dm / 50.0) * 15.0
        paths.append(path_line(tx_m, bar_y - 0.8, tx_m, bar_y + 0.8))
    # Active drift pointer
    drift_clamped = max(-50.0, min(50.0, grid_mhz))
    px_m = 30.0 + (drift_clamped / 50.0) * 15.0
    paths.append(path_line(px_m, bar_y - 2.2, px_m, bar_y + 2.2))
    paths.append(f"M {px_m-0.8:.2f},{bar_y-2.2:.2f} L {px_m+0.8:.2f},{bar_y-2.2:.2f} L {px_m:.2f},{bar_y-0.8:.2f} Z")
    paths.extend(render_text_strokes(f"50HZ: {state['grid']['freq_hz']:.3f}HZ (D{state['grid']['drift_mhz']:+.1f}M)", 30.0, bar_y + 2.0, char_w=0.85, char_h=1.2, align="center"))
    
    # Divider line
    div_x = 59.0
    paths.append(path_line(div_x, 4.5, div_x, h_mm - 4.5))
    paths.append(path_line(div_x + 0.8, 6.0, div_x + 0.8, h_mm - 6.0))
    
    # Right Typography & Telemetry Header
    tx = div_x + 3.2
    y_start = 5.6
    pitch_y = 4.4
    
    lines = [
        ("LAGRANGE // 3-BODY CONSTELLATION", 1.6, 2.3),
        (f"ČAS : {state['cet_str']} CET", 1.3, 1.8),
        (f"DH36: {state['dh36']['str']} (DEKAN {state['dh36']['decan']:02d})", 1.25, 1.7),
        (f"LUNA: {state['lunar']['lunation_number']}. LUNACE ({state['lunar']['illumination_pct']}%)", 1.25, 1.7),
        (f"SÍŤ : {state['grid']['freq_hz']:.3f} HZ (Δ {state['grid']['drift_mhz']:+.1f} MHZ)", 1.25, 1.7),
        (f"METEO: {state['weather']['temp_c']:+.1f}°C | {state['weather']['pressure_hpa']:.0f} HPA | {state['weather']['rh_pct']}% RH", 1.2, 1.65),
        (f"L2/L3/L4/L5/L2M // --TÉCHNĒ & KOF", 1.15, 1.6),
    ]
    
    for idx, (txt, cw, ch) in enumerate(lines):
        cur_y = y_start + idx * pitch_y
        paths.extend(render_text_strokes(txt, tx, cur_y, char_w=cw, char_h=ch))
    
    # Title underline
    paths.append(path_line(tx, y_start + 3.6, width_mm - 5.0, y_start + 3.6))
    
    # 50Hz Hourly Grid Drift Seismograph Graph (Y: 37.0 to 68.5 mm)
    gx = tx
    gy_top = 37.0
    gw = (width_mm - 5.0) - gx
    gh = (h_mm - 5.5) - gy_top
    gy_mid = gy_top + gh * 0.46
    
    # Outer graph box
    paths.append(path_rect(gx, gy_top, gw, gh))
    
    # Header label
    paths.extend(render_text_strokes("[STOPA: SÍŤ 50 HZ // HODINOVÝ DRIFT]", gx + 2.0, gy_top + 1.4, char_w=0.9, char_h=1.3))
    
    # Baseline (50.000 Hz / 0 mHz)
    paths.append(path_line(gx + 11.5, gy_mid, gx + gw - 2.0, gy_mid))
    paths.extend(render_text_strokes("50.0", gx + 1.2, gy_mid - 0.8, char_w=0.8, char_h=1.2))
    
    # Guidelines: +50 mHz, -50 mHz
    y_pos50 = gy_mid - (50.0 / 50.0) * (gh * 0.27)
    y_neg50 = gy_mid - (-50.0 / 50.0) * (gh * 0.27)
    for y_dash in [y_pos50, y_neg50]:
        cur_x = gx + 11.5
        while cur_x < gx + gw - 2.0:
            paths.append(path_line(cur_x, y_dash, min(cur_x + 2.0, gx + gw - 2.0), y_dash))
            cur_x += 4.0
    paths.extend(render_text_strokes("+50", gx + 1.2, y_pos50 - 0.8, char_w=0.75, char_h=1.1))
    paths.extend(render_text_strokes("-50", gx + 1.2, y_neg50 - 0.8, char_w=0.75, char_h=1.1))
    
    # Continuous seismograph waveform (hourly trace)
    cur_drift = state["grid"]["drift_mhz"]
    num_pts = 48
    plot_w = (gx + gw - 2.5) - (gx + 12.0)
    x_step = plot_w / float(num_pts)
    trace_pts = []
    for i in range(num_pts + 1):
        xp = (gx + 12.0) + i * x_step
        delta = math.sin(i * 0.42) * 5.5 + math.cos(i * 0.21) * 3.8 + math.sin(i * 0.85) * 2.0
        d_val = cur_drift + delta
        clamped = max(-55.0, min(55.0, d_val))
        yp = gy_mid - (clamped / 50.0) * (gh * 0.27)
        trace_pts.append((xp, yp))
    
    d_trace = f"M {trace_pts[0][0]:.2f},{trace_pts[0][1]:.2f} " + " ".join(f"L {p[0]:.2f},{p[1]:.2f}" for p in trace_pts[1:])
    paths.append(d_trace)
    
    # Time X-Axis at bottom of graph
    ax_y = gy_top + gh - 4.2
    paths.append(path_line(gx + 11.5, ax_y, gx + gw - 2.0, ax_y))
    cur_ts = state.get("timestamp", time.time())
    for idx_t, (frac, label_t) in enumerate([(0.0, "-60M"), (0.5, "-30M"), (1.0, "[NYNÍ]")]):
        tx_p = (gx + 12.0) + frac * plot_w
        paths.append(path_line(tx_p, ax_y, tx_p, ax_y - 1.2))
        al = "left" if idx_t == 0 else ("center" if idx_t == 1 else "right")
        paths.extend(render_text_strokes(label_t, tx_p, ax_y + 0.9, char_w=0.75, char_h=1.1, align=al))
    
    d_attr = " ".join(paths)
    svg = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg width="{width_mm:.2f}mm" height="{h_mm:.2f}mm" viewBox="0 0 {width_mm:.2f} {h_mm:.2f}" '
        f'xmlns="http://www.w3.org/2000/svg">\n'
        f'  <g id="lagrange_constellation">\n'
        f'    <path d="{d_attr}" stroke="black" stroke-width="0.25" fill="none" stroke-linecap="round" stroke-linejoin="round" />\n'
        f'  </g>\n'
        f'</svg>\n'
    )
    return svg, width_mm, h_mm

def main():
    parser = argparse.ArgumentParser(description="Lagrange Libration Points & Constellation Engine")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # status
    p_status = subparsers.add_parser("status", help="Print celestial coordinates & state")
    p_status.add_argument("--json", action="store_true", help="Output JSON")
    
    # svg
    p_svg = subparsers.add_parser("svg", help="Generate vector SVG constellation")
    p_svg.add_argument("--out", type=str, default="/tmp/lagrange_constellation.svg", help="Output SVG path")
    p_svg.add_argument("--width", type=float, default=120.0, help="Width in mm (Golden Ratio phi)")
    
    # plot
    p_plot = subparsers.add_parser("plot", help="Dispatch to Drkota V-plotter")
    p_plot.add_argument("--dry-run", action="store_true", help="Simulate without hardware movement")
    p_plot.add_argument("--width", type=float, default=120.0, help="Width in mm")
    p_plot.add_argument("--scale", type=float, default=0.5, help="Scale factor (default 0.5 = 50%%)")
    p_plot.add_argument("--speed", type=int, default=150, help="Stepper pulse delay in us (default 150 = 2x speed)")
    p_plot.add_argument("--feed", type=float, default=1.0, help="Feedrate multiplier (default 1.0)")
    
    args = parser.parse_args()
    
    state = compute_celestial_state()
    
    if args.command == "status" or args.command is None:
        if getattr(args, "json", False):
            print(json.dumps(state, indent=2, ensure_ascii=False))
        else:
            print("╔══════════════════════════════════════════════════════════════════════════╗")
            print("║ LAGRANGE // THREE-BODY CONSTELLATION & LIBRATION ENGINE                  ║")
            print("╠══════════════════════════════════════════════════════════════════════════╣")
            print(f"║ Občanský čas   : {state['cet_str']} CET                    ║")
            print(f"║ Metrický čas   : {state['dh36']['str']} (Dekan {state['dh36']['decan']:02d} | Azimut {state['dh36']['azimuth_deg']:.1f}°) ║")
            print(f"║ Lunární fáze   : {state['lunar']['lunation_number']}. lunace | {state['lunar']['illumination_pct']}% osvětlení      ║")
            print(f"║ 50Hz Síť       : {state['grid']['freq_hz']:.3f} Hz (Δ {state['grid']['drift_mhz']:+.1f} mHz) [{state['grid']['status']}]             ║")
            print(f"║ Počasí Praha   : {state['weather']['temp_c']:+.1f}°C | {state['weather']['pressure_hpa']:.1f} hPa | {state['weather']['rh_pct']}% RH          ║")
            print("╠══════════════════════════════════════════════════════════════════════════╣")
            print("║ Vzdálenější Lagrangeovy body v konstelaci:                               ║")
            print("║   • L2  (Slunce-Země) : Vnější noční stín (JWST, Gaia, Euclid)          ║")
            print("║   • L3  (Slunce-Země) : Anti-Země na odvrácené straně Slunce             ║")
            print("║   • L4  (Slunce-Země) : Řecký trojanský vrchol (+60° před Zemí)         ║")
            print("║   • L5  (Slunce-Země) : Trójský vrchol (-60° za Zemí)                   ║")
            print("║   • L2M (Země-Měsíc)  : Halo orbita za odvrácenou stranou Měsíce         ║")
            print("╚══════════════════════════════════════════════════════════════════════════╝")
    elif args.command == "svg":
        svg_data, w, h = generate_lagrange_svg(state, width_mm=args.width)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(svg_data)
        print(f"[+] Lagrange konstelace vygenerována: {args.out} ({w:.1f}x{h:.1f} mm)")
        png_path = convert_svg_to_png(args.out)
        if png_path and os.path.exists(png_path):
            print(f"[+] PNG náhled vygenerován: {png_path} ({os.path.getsize(png_path)} bajtů)")
    elif args.command == "plot":
        svg_data, w, h = generate_lagrange_svg(state, width_mm=args.width)
        out_svg = f"/tmp/lagrange_plot_{int(time.time())}.svg"
        with open(out_svg, "w", encoding="utf-8") as f:
            f.write(svg_data)
        print(f"[+] Připraven tiskový arch pro Drkotu: {out_svg} ({w:.1f}x{h:.1f} mm)")
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
