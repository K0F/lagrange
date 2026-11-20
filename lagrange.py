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
from datetime import datetime, timezone, timedelta

PHI = (1.0 + math.sqrt(5.0)) / 2.0

ALPHABET = {
    'A': [[(0, 50), (20, 0), (40, 50)], [(8, 30), (32, 30)]],
    'B': [[(0, 0), (0, 50), (28, 50), (36, 40), (28, 25), (0, 25)], [(28, 25), (36, 12), (28, 0), (0, 0)]],
    'C': [[(40, 10), (30, 0), (10, 0), (0, 12), (0, 38), (10, 50), (30, 50), (40, 40)]],
    'D': [[(0, 0), (0, 50), (25, 50), (40, 35), (40, 15), (25, 0), (0, 0)]],
    'E': [[(40, 0), (0, 0), (0, 50), (40, 50)], [(0, 25), (28, 25)]],
    'F': [[(0, 0), (0, 50), (40, 50)], [(0, 25), (28, 25)]],
    'G': [[(40, 40), (30, 50), (10, 50), (0, 38), (0, 12), (10, 0), (30, 0), (40, 10), (40, 24), (20, 24)]],
    'H': [[(0, 0), (0, 50)], [(40, 0), (40, 50)], [(0, 25), (40, 25)]],
    'I': [[(10, 0), (30, 0)], [(20, 0), (20, 50)], [(10, 50), (30, 50)]],
    'J': [[(5, 12), (15, 0), (30, 0), (40, 10), (40, 50), (20, 50)]],
    'K': [[(0, 0), (0, 50)], [(40, 50), (0, 22), (40, 0)]],
    'L': [[(0, 50), (0, 0), (35, 0)]],
    'M': [[(0, 0), (0, 50), (20, 25), (40, 50), (40, 0)]],
    'N': [[(0, 0), (0, 50), (40, 0), (40, 50)]],
    'O': [[(10, 0), (30, 0), (40, 12), (40, 38), (30, 50), (10, 50), (0, 38), (0, 12), (10, 0)]],
    'P': [[(0, 0), (0, 50), (30, 50), (40, 40), (30, 25), (0, 25)]],
    'Q': [[(10, 0), (30, 0), (40, 12), (40, 38), (30, 50), (10, 50), (0, 38), (0, 12), (10, 0)], [(25, 12), (42, -5)]],
    'R': [[(0, 0), (0, 50), (30, 50), (40, 40), (30, 25), (0, 25)], [(18, 25), (40, 0)]],
    'S': [[(40, 40), (30, 50), (10, 50), (0, 40), (10, 25), (30, 25), (40, 10), (30, 0), (10, 0), (0, 10)]],
    'T': [[(20, 0), (20, 50)], [(0, 50), (40, 50)]],
    'U': [[(0, 50), (0, 15), (12, 0), (28, 0), (40, 15), (40, 50)]],
    'V': [[(0, 50), (20, 0), (40, 50)]],
    'W': [[(0, 50), (10, 0), (20, 28), (30, 0), (40, 50)]],
    'X': [[(0, 0), (40, 50)], [(0, 50), (40, 0)]],
    'Y': [[(20, 0), (20, 25), (0, 50)], [(20, 25), (40, 50)]],
    'Z': [[(0, 50), (40, 50), (0, 0), (40, 0)]],
    '0': [[(10, 0), (30, 0), (40, 15), (40, 35), (30, 50), (10, 50), (0, 35), (0, 15), (10, 0)], [(32, 40), (8, 10)]],
    '1': [[(5, 38), (20, 50), (20, 0)], [(5, 0), (35, 0)]],
    '2': [[(0, 40), (10, 50), (30, 50), (40, 40), (40, 28), (0, 0), (40, 0)]],
    '3': [[(5, 42), (12, 50), (32, 50), (40, 40), (30, 25), (40, 10), (30, 0), (10, 0), (0, 8)], [(18, 25), (30, 25)]],
    '4': [[(30, 0), (30, 50), (0, 15), (42, 15)]],
    '5': [[(40, 50), (0, 50), (0, 26), (28, 26), (40, 18), (40, 8), (28, 0), (8, 0), (0, 6)]],
    '6': [[(35, 45), (20, 50), (10, 45), (0, 30), (0, 15), (10, 0), (30, 0), (40, 12), (40, 22), (30, 30), (0, 30)]],
    '7': [[(0, 50), (40, 50), (18, 0)]],
    '8': [[(12, 25), (0, 35), (10, 50), (30, 50), (40, 35), (28, 25), (40, 12), (30, 0), (10, 0), (0, 12), (12, 25)]],
    '9': [[(40, 20), (10, 20), (0, 28), (0, 38), (10, 50), (30, 50), (40, 35), (40, 20), (30, 5), (15, 0), (5, 5)]],
    ':': [[(18, 14), (22, 14), (22, 18), (18, 18), (18, 14)], [(18, 32), (22, 32), (22, 36), (18, 36), (18, 32)]],
    '.': [[(18, 0), (22, 0), (22, 4), (18, 4), (18, 0)]],
    '-': [[(8, 25), (32, 25)]],
    '+': [[(8, 25), (32, 25)], [(20, 13), (20, 37)]],
    '/': [[(5, 0), (35, 50)]],
    '(': [[(28, 50), (18, 38), (18, 12), (28, 0)]],
    ')': [[(12, 50), (22, 38), (22, 12), (12, 0)]],
    '[': [[(28, 50), (15, 50), (15, 0), (28, 0)]],
    ']': [[(12, 50), (25, 50), (25, 0), (12, 0)]],
    '°': [[(10, 40), (20, 40), (20, 50), (10, 50), (10, 40)]],
    '=': [[(8, 18), (32, 18)], [(8, 32), (32, 32)]],
    '☉': [[(10, 10), (30, 10), (30, 30), (10, 30), (10, 10)], [(20, 17), (20, 23)]],
    '⊕': [[(10, 10), (30, 10), (30, 30), (10, 30), (10, 10)], [(10, 20), (30, 20)], [(20, 10), (20, 30)]],
    '☽': [[(25, 30), (15, 20), (25, 10)]],
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
            pts = [(cursor_x + px * sx, y + (50 - py) * sy) for px, py in stroke]
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
        }
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
    
    # Divider line
    div_x = 59.0
    paths.append(path_line(div_x, 4.5, div_x, h_mm - 4.5))
    paths.append(path_line(div_x + 0.8, 6.0, div_x + 0.8, h_mm - 6.0))
    
    # Right Typography Box
    tx = div_x + 3.2
    y_start = 6.2
    pitch_y = 5.6
    
    lines = [
        ("LAGRANGE // 3-BODY CONSTELLATION", 1.8, 2.5),
        (f"ČAS : {state['cet_str']} CET", 1.5, 2.3),
        (f"DH36: {state['dh36']['str']} (DEKAN {state['dh36']['decan']:02d})", 1.5, 2.3),
        (f"AZIM: {state['dh36']['azimuth_deg']:.1f}° SOLAR VECTOR", 1.5, 2.3),
        (f"LUNA: {state['lunar']['lunation_number']}. LUNACE ({state['lunar']['illumination_pct']}%)", 1.5, 2.3),
        (f"L2  : ANTI-SOLAR SHADOW (JWST/GAIA)", 1.4, 2.1),
        (f"L3  : COUNTER-EARTH (3.0E8 KM)", 1.4, 2.1),
        (f"L4/5: TROJAN TRIAD (+-60° EQUIL)", 1.4, 2.1),
        (f"L2M : LUNAR FAR-SIDE HALO ANCHOR", 1.4, 2.1),
        ("--TÉCHNĒ & KOF // DRKOTA V-PLOTTER", 1.3, 1.9),
    ]
    
    for idx, (txt, cw, ch) in enumerate(lines):
        cur_y = y_start + idx * pitch_y
        paths.extend(render_text_strokes(txt, tx, cur_y, char_w=cw, char_h=ch))
    
    # Title underline
    paths.append(path_line(tx, y_start + 3.8, width_mm - 5.0, y_start + 3.8))
    
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
    elif args.command == "plot":
        svg_data, w, h = generate_lagrange_svg(state, width_mm=args.width)
        out_svg = f"/tmp/lagrange_plot_{int(time.time())}.svg"
        with open(out_svg, "w", encoding="utf-8") as f:
            f.write(svg_data)
        print(f"[+] Připraven tiskový arch pro Drkotu: {out_svg} ({w:.1f}x{h:.1f} mm)")
        if args.dry_run:
            print(f"[DRY-RUN] Simulace plotru Drkota: /home/kof/bin/drkota plot {out_svg}")
        else:
            drkota_cmd = f"/home/kof/bin/drkota plot {out_svg}"
            os.system(drkota_cmd)

if __name__ == "__main__":
    main()
