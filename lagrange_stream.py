#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lagrange_stream.py — Real-Time Continuous Three-Body Lagrange & 50Hz Grid Spirograph Plotter
Observatoř Cybernetics // Kryštof Pešek (Kof) & Techné (τέχνη)
CC0 1.0 Universal // Public Domain // Anti-Copyright

Drives Drkota (polargraph) continuously in real time:
- 1 full orbit = 1 DH = 40 minutes (2400 seconds, configurable on the fly)
- Base circle: diameter 10 cm (R0 = 50.0 mm)
- 6 Lagrange libration lobes (L1, L2, L3, L4, L5, L2M)
- 50Hz continental European grid frequency: symlog radial breathing
- Prague wind speed: 36 decanic ripple petals
- Temperature: thermal radial dilatancy
- Relative humidity: Guilloché precession density
- Continuous non-repeating Spirograph mandala
"""

import os
import sys
import time
import math
import json
import signal
import argparse
import threading
import subprocess
import urllib.request

# Kinematics constants from gomotor (bazina CNC Shield V3)
STEPS_PER_MM_LEFT = 190.476190476
STEPS_PER_MM_RIGHT = 190.476190476
MOTOR_A_X = -370.0
MOTOR_B_X = 370.0
MOTOR_A_Y = 500.0
MOTOR_B_Y = 500.0
GONDOLA_WIDTH = 45.0
HALF_GONDOLA = GONDOLA_WIDTH / 2.0

def find_drkota_port():
    env_port = os.environ.get("DRKOTA_PORT")
    if env_port and os.path.exists(env_port):
        return env_port
    candidates = [
        "/dev/drkota",
        "/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0",
        "/dev/ttyUSB0",
        "/dev/ttyUSB1",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return env_port or "/dev/ttyUSB0"

SERIAL_PORT = find_drkota_port()
BAUD_RATE = int(os.environ.get("DRKOTA_BAUD", 115200))

GRID_SHM_STATUS = "/dev/shm/observator_status.json"
GRID_SHM_LOCAL = "/dev/shm/grid50.json"
WEATHER_CACHE = "/dev/shm/drkota_weather.json"

CONFIG_FILE = "/dev/shm/drkota_clock_config.json"
STATUS_FILE = "/dev/shm/drkota_clock_status.json"
TRAIL_FILE = "/dev/shm/drkota_live_trail.json"

PLANETS = {
    "Mercury": {"L0": 252.25, "n": 4.0923344, "mu": 1.66e-7, "color": "#9ca3af", "symbol": "☿"},
    "Venus":   {"L0": 181.98, "n": 1.6021305, "mu": 2.45e-6, "color": "#fbbf24", "symbol": "♀"},
    "Earth":   {"L0": 100.46, "n": 0.9856474, "mu": 3.00e-6, "color": "#60a5fa", "symbol": "♁"},
    "Mars":    {"L0": 355.45, "n": 0.5240330, "mu": 3.23e-7, "color": "#f87171", "symbol": "♂"},
    "Jupiter": {"L0": 34.40,  "n": 0.0830853, "mu": 9.54e-4, "color": "#fb923c", "symbol": "♃"},
    "Saturn":  {"L0": 49.94,  "n": 0.0334442, "mu": 2.86e-4, "color": "#facc15", "symbol": "♄"}
}

def compute_planetary_lagrange(target_ts=None):
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
        ampl = 3.2 * (math.log(1.0 + p["mu"] / 1e-7) / math.log(1.0 + 9.54e-4 / 1e-7))
        bodies[name] = {
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

running = True
serial_conn = None
current_x = 0.0
current_y = 0.0

def calc_dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

CENTER_LEN_A = calc_dist(-HALF_GONDOLA, 0.0, MOTOR_A_X, MOTOR_A_Y)
CENTER_LEN_B = calc_dist(HALF_GONDOLA, 0.0, MOTOR_B_X, MOTOR_B_Y)

def mm_to_steps(x_mm, y_mm):
    len_a = calc_dist(x_mm - HALF_GONDOLA, y_mm, MOTOR_A_X, MOTOR_A_Y)
    len_b = calc_dist(x_mm + HALF_GONDOLA, y_mm, MOTOR_B_X, MOTOR_B_Y)
    steps_a = int(round((len_a - CENTER_LEN_A) * STEPS_PER_MM_LEFT))
    steps_b = int(round((len_b - CENTER_LEN_B) * STEPS_PER_MM_RIGHT))
    return steps_a, steps_b

def harvest_grid():
    if os.path.exists(GRID_SHM_STATUS):
        try:
            with open(GRID_SHM_STATUS, "r") as f:
                d = json.load(f)
                hz = float(d.get("grid_freq", 50.0))
                drift = float(d.get("grid_drift_mhz", (hz - 50.0) * 1000.0))
                return {"freq_hz": hz, "drift_mhz": drift}
        except Exception:
            pass
    if os.path.exists(GRID_SHM_LOCAL):
        try:
            with open(GRID_SHM_LOCAL, "r") as f:
                d = json.load(f)
                hz = float(d.get("frequency_hz", 50.0))
                drift = float(d.get("drift_mhz", (hz - 50.0) * 1000.0))
                return {"freq_hz": hz, "drift_mhz": drift}
        except Exception:
            pass
    return {"freq_hz": 50.0, "drift_mhz": 0.0}

def harvest_weather():
    if os.path.exists(WEATHER_CACHE):
        try:
            with open(WEATHER_CACHE, "r") as f:
                d = json.load(f)
                return {
                    "temp_c": float(d.get("temp_c", 9.5)),
                    "rh_pct": float(d.get("rh_pct", 75.0)),
                    "wind_kmh": float(d.get("wind_kmh", 14.8))
                }
        except Exception:
            pass
    return {"temp_c": 9.5, "rh_pct": 75.0, "wind_kmh": 14.8}

def load_config():
    default_cfg = {
        "period_sec": 40.0,    # 2000 cycles of 50Hz (60x Dekan harmonic, 1 orbit = 40.0s)
        "r0_mm": 50.0,         # 10 cm diameter
        "step_interval_sec": 0.4, # NURBS control point interval
        "nurbs_substeps": 4,   # micro-steps along each NURBS segment
        "spiral_dr_per_orbit": -0.2,
        "direction": "ccw",    # Counter-Clockwise (CCW)
        "log_c": 5.0,
        "ampl_grid_max": 5.0,
        "lagrange_ampl": 4.5,
        "wind_ampl": 0.35,     # Subdued wind ripple (less significant)
        "temp_factor": 0.03,   # Subdued thermal drift (less significant)
        "stepper_delay": 550,  # Continuous laminar stepping delay (~9 mm/s glide)
        "enabled": True,
        "dry_run": False
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                user_cfg = json.load(f)
                default_cfg.update(user_cfg)
        except Exception:
            pass
    else:
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(default_cfg, f, indent=2)
        except Exception:
            pass
    return default_cfg

serial_err_count = 0

def connect_serial():
    global serial_conn
    port = find_drkota_port()
    if not port or not os.path.exists(port):
        return False
    try:
        import serial
        if serial_conn:
            try:
                serial_conn.close()
            except Exception:
                pass
        serial_conn = serial.Serial(port, BAUD_RATE, timeout=2.0)
        time.sleep(1.8)
        cfg = load_config()
        payload = f"S{cfg.get('stepper_delay', 200)}\nE1\n".encode("ascii")
        serial_conn.write(payload)
        serial_conn.flush()
        return True
    except Exception as e:
        sys.stderr.write(f"[-] Serial connection failed on {port}: {e}\n")
        serial_conn = None
        return False

def send_serial(cmd):
    global serial_conn, serial_err_count
    if serial_conn is None:
        if not connect_serial():
            return ""
    try:
        payload = (cmd.strip() + "\n").encode("ascii")
        serial_conn.write(payload)
        serial_conn.flush()
        resp = serial_conn.readline().decode("ascii", errors="replace").strip()
        serial_err_count = 0
        return resp
    except Exception as e:
        serial_err_count += 1
        sys.stderr.write(f"[-] Serial error ({serial_err_count}): {e}\n")
        try:
            if serial_conn:
                serial_conn.close()
        except Exception:
            pass
        serial_conn = None
        # Attempt immediate reconnect
        if connect_serial():
            try:
                payload = (cmd.strip() + "\n").encode("ascii")
                serial_conn.write(payload)
                serial_conn.flush()
                resp = serial_conn.readline().decode("ascii", errors="replace").strip()
                serial_err_count = 0
                return resp
            except Exception:
                pass
        if serial_err_count >= 5:
            sys.stderr.write("[-] Příliš mnoho sériových chyb za sebou. Ukončuji pro čistý restart systemd...\n")
            sys.exit(1)
        return ""

def move_to(target_x, target_y):
    global current_x, current_y
    steps_a, steps_b = mm_to_steps(target_x, target_y)
    cmd = f"X{steps_a}Y{steps_b}"
    send_serial(cmd)
    current_x = target_x
    current_y = target_y

def evaluate_nurbs_segment(p0, p1, p2, p3, w0=1.0, w1=1.0, w2=1.0, w3=1.0, steps=8):
    """
    Evaluates a uniform cubic Rational B-Spline (NURBS) segment between control points
    p1 and p2 using homogeneous coordinates with weights w0..w3.
    Returns a list of (x, y) coordinates.
    """
    pts = []
    # Homogeneous control points (wx, wy, w)
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

def sig_handler(signum, frame):
    global running
    sys.stderr.write("\n[drkota-clock] Obdržen signál k ukončení. Zvedám pero (P1) a vracím se do počátku (0, 0)...\n")
    running = False
    try:
        send_serial("P1")
        time.sleep(0.3)
        move_to(0.0, 0.0)
        time.sleep(0.5)
        send_serial("E0")  # disable steppers
    except Exception:
        pass
    try:
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)
    except Exception:
        pass
    sys.exit(0)

def sync_to_boxc_worker():
    while running:
        time.sleep(1.2)
        if os.path.exists(TRAIL_FILE):
            try:
                subprocess.run(
                    ["scp", "-q", "-o", "ConnectTimeout=2", TRAIL_FILE, "boxC:/var/www/html/lagrange/live_trail.json"],
                    timeout=2.5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

def main():
    global running, serial_conn, current_x, current_y
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    parser = argparse.ArgumentParser(description="Lagrange Libration Spirograph Real-Time Plotter Clock")
    parser.add_argument("--dry-run", action="store_true", help="Run simulation without moving hardware")
    parser.add_argument("--period", type=float, default=None, help="Orbit duration in seconds (default: 2400.0 = 40 min / 1 DH)")
    parser.add_argument("--fraction", type=str, default=None, help="Fraction of 1 DH (e.g. 1/8 for 5 min, 1/10 for 4 min, 1/1 for 40 min)")
    parser.add_argument("--step", type=float, default=1.0, help="Step interval in seconds (default: 1.0 s)")
    parser.add_argument("--spiral-dr", type=float, default=-0.8, help="Radial shift in mm per orbit (default: -0.8 mm)")
    parser.add_argument("--speed", type=int, default=120, help="Stepper pulse delay in us (default: 120)")
    parser.add_argument("--direction", choices=["cw", "ccw"], default=None, help="Rotation direction (cw or ccw)")
    parser.add_argument("--ccw", action="store_true", help="Rotate Counter-Clockwise (default)")
    parser.add_argument("--cw", action="store_true", help="Rotate Clockwise")
    parser.add_argument("--status", action="store_true", help="Print live clock status and exit")
    parser.add_argument("--zero", action="store_true", help="Lift pen and zero plotter to (0, 0)")
    args = parser.parse_args()

    if args.status:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                print(f.read())
        else:
            print("Status: Plotter clock is not currently active.")
        return

    if args.zero:
        if os.path.exists(SERIAL_PORT):
            import serial
            s = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2.0)
            time.sleep(1.0)
            s.write(b"P1\nZ0\n")
            s.flush()
            time.sleep(0.5)
            s.close()
            print("[✓] Plotter lifted (P1) and zeroed (Z0).")
        return

    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║ LAGRANGE // REAL-TIME 50HZ & CELESTIAL SPIROGRAPH PLOTTER CLOCK        ║")
    print("║ Observatoř Cybernetics // Techné & Kof                                ║")
    print("╚════════════════════════════════════════════════════════════════════════╝")

    cfg = load_config()
    if args.dry_run:
        cfg["dry_run"] = True
    if args.period is not None:
        cfg["period_sec"] = args.period
    elif args.fraction:
        fractions = {
            "1/1": 2400.0,
            "1/2": 1200.0,
            "1/4": 600.0,
            "1/8": 300.0,
            "1/10": 240.0,
            "1/12": 200.0,
            "1/36": 66.666
        }
        cfg["period_sec"] = fractions.get(args.fraction, 2400.0)
    if args.step:
        cfg["step_interval_sec"] = args.step
    if args.spiral_dr is not None:
        cfg["spiral_dr_per_orbit"] = args.spiral_dr
    if args.speed:
        cfg["stepper_delay"] = args.speed
    if args.cw:
        cfg["direction"] = "cw"
    elif args.ccw or args.direction:
        cfg["direction"] = args.direction or "ccw"
    active_port = find_drkota_port()
    is_dry = cfg.get("dry_run", False) or not (active_port and os.path.exists(active_port))

    if not is_dry:
        print(f"[*] Otevírám {active_port} při {BAUD_RATE} baud...")
        if not connect_serial():
            is_dry = True
            print(f"[-] Nepodařilo se připojit k {active_port}, přepínám do režimu DRY-RUN.")
        else:
            send_serial("P1") # Lift pen initially
            time.sleep(0.5)
    else:
        print(f"[*] Režim simulace / DRY-RUN (Port {active_port} není fyzicky připojen).")

    start_time = time.time()
    last_time = time.time()
    accum_theta = 0.0
    direction = -1.0 if str(cfg.get("direction", "ccw")).lower() == "ccw" else 1.0
    ctrl_dt = max(0.15, cfg.get("step_interval_sec", 0.5))
    history_pts = []
    history_w = []
    last_feed_mult = 1.0
    planets = compute_planetary_lagrange()

    # Pre-populate 4 initial NURBS control points
    omega0 = (2.0 * math.pi) / cfg.get("period_sec", 20.0)
    for step_i in range(-3, 1):
        th_init = step_i * ctrl_dt * omega0 * direction
        g = harvest_grid()
        w_env = harvest_weather()
        px, py, pr, _ = compute_spiro_point(th_init, 0.0, cfg, g, w_env, planets)
        pw = 1.0 + abs(g["drift_mhz"]) / 50.0 + (w_env["wind_kmh"] / 80.0)
        history_pts.append((px, py))
        history_w.append(pw)

    # Initial start position from NURBS evaluation
    init_pts = evaluate_nurbs_segment(
        history_pts[0], history_pts[1], history_pts[2], history_pts[3],
        history_w[0], history_w[1], history_w[2], history_w[3],
        steps=2
    )
    init_x, init_y = init_pts[0]
    print(f"[*] Pomalý nájezd na startovní pozici ciferníku: ({init_x:.2f}, {init_y:.2f}) mm...")
    move_to(init_x, init_y)
    time.sleep(0.5)
    if not is_dry:
        send_serial("P0") # Lower pen to paper
        time.sleep(0.3)

    print(f"[✓] Tisk v reálném čase zahájen (NURBS interpolace). 1 oběh = {cfg['period_sec']:.1f} s ({cfg['period_sec']/60.0:.2f} min).")

    # Start background synchronization to boxC
    sync_thread = threading.Thread(target=sync_to_boxc_worker, daemon=True)
    sync_thread.start()

    trail_points = []
    last_trail_save = time.time()

    while running:
        cfg = load_config()
        if not cfg.get("enabled", True):
            time.sleep(1.0)
            continue

        ctrl_dt = max(0.15, cfg.get("step_interval_sec", 0.5))
        now = time.time()
        dt = now - last_time
        last_time = now
        if dt <= 0.0:
            dt = 0.05
        elif dt > 1.0:
            dt = 0.2

        elapsed = now - start_time
        grid = harvest_grid()
        weather = harvest_weather()
        planets = compute_planetary_lagrange()

        # 50Hz Continental European Grid speed modulation:
        # Under-frequency (<50.000 Hz) slows down rotation; over-frequency (>50.000 Hz) accelerates it.
        df = grid["drift_mhz"]
        speed_mod = max(0.40, min(1.85, 1.0 + (df / 65.0)))

        # Dynamically update hardware stepper feed rate multiplier if shifted by > 0.03
        if not is_dry and abs(speed_mod - last_feed_mult) > 0.03:
            send_serial(f"F{speed_mod:.2f}")
            last_feed_mult = speed_mod

        # Advance continuous phase angle by instantaneous 50Hz-modulated angular velocity
        omega0 = (2.0 * math.pi) / cfg.get("period_sec", 20.0)
        d_theta = direction * omega0 * speed_mod * dt
        accum_theta += d_theta
        orbit_idx = abs(accum_theta) / (2.0 * math.pi)

        # Generate next control point with Inverse Discrete Fourier Planetary Synthesis
        px, py, pr, fourier_meta = compute_spiro_point(accum_theta, orbit_idx, cfg, grid, weather, planets)
        pw = 1.0 + abs(grid["drift_mhz"]) / 100.0 + (weather["wind_kmh"] / 200.0)
        history_pts.append((px, py))
        history_w.append(pw)
        if len(history_pts) > 4:
            history_pts.pop(0)
            history_w.pop(0)

        # Interpolate smooth NURBS curve between history_pts[1] and history_pts[2]
        nurbs_substeps = max(2, cfg.get("nurbs_substeps", 4))
        interpolated = evaluate_nurbs_segment(
            history_pts[0], history_pts[1], history_pts[2], history_pts[3],
            history_w[0], history_w[1], history_w[2], history_w[3],
            steps=nurbs_substeps
        )

        substep_delay = ctrl_dt / float(len(interpolated))
        last_mx, last_my = current_x, current_y
        for mx, my in interpolated:
            if not running:
                break
            if not is_dry:
                move_to(mx, my)
            else:
                time.sleep(substep_delay)
            last_mx, last_my = mx, my
            trail_points.append([round(mx, 2), round(my, 2)])
            if len(trail_points) > 1500:
                trail_points.pop(0)

        # Update live status in SHM
        status = {
            "timestamp": time.time(),
            "elapsed_sec": round(elapsed, 1),
            "orbit_number": int(orbit_idx),
            "orbit_progress_pct": round((orbit_idx - int(orbit_idx)) * 100.0, 1),
            "period_sec": cfg["period_sec"],
            "period_desc": f"{cfg['period_sec']:.1f} s ({int(cfg['period_sec']*50)} grid cycles, {int(2400/cfg['period_sec'])}x Dekan)",
            "direction": str(cfg.get("direction", "ccw")).upper(),
            "speed_multiplier": round(speed_mod, 3),
            "speed_desc": f"{speed_mod:.2f}x ({'+' if df >= 0 else ''}{df:.1f} mHz)",
            "pos_mm": {"x": round(last_mx, 2), "y": round(last_my, 2), "r": round(math.hypot(last_mx, last_my), 2)},
            "grid": grid,
            "weather": weather,
            "planets": planets,
            "fourier_synthesis": fourier_meta,
            "nurbs_interpolation": True,
            "pen_down": True
        }
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f, indent=2)
        except Exception:
            pass

        if time.time() - last_trail_save > 1.2:
            trail_payload = {
                "timestamp": time.time(),
                "orbit_number": int(orbit_idx),
                "orbit_progress_pct": round((orbit_idx - int(orbit_idx)) * 100.0, 1),
                "pos_mm": [round(last_mx, 2), round(last_my, 2)],
                "direction": str(cfg.get("direction", "ccw")).upper(),
                "period_sec": cfg["period_sec"],
                "speed_multiplier": round(speed_mod, 3),
                "speed_desc": f"{speed_mod:.2f}x ({'+' if df >= 0 else ''}{df:.1f} mHz)",
                "grid": grid,
                "weather": weather,
                "planets": planets,
                "fourier_synthesis": fourier_meta,
                "trail": trail_points
            }
            try:
                with open(TRAIL_FILE, "w") as f:
                    json.dump(trail_payload, f)
                last_trail_save = time.time()
            except Exception:
                pass

def compute_inverse_fourier_planetary(theta, planets):
    """
    Inverse Discrete Fourier Planetary Synthesis:
    Superimposes harmonic sinusoids with orbital resonance integer modes n in {1, 2, 3, 5, 6, 8},
    where phase angles are phase-locked to real-time planetary ecliptic longitudes phi_k.
    Continuous constructive and destructive interference creates an organic, breathing geometric wave.
    """
    components = {}
    r_sum = 0.0

    # 1. Jupiter (♃): Tidal Quadrupole (n=2) + Great Inequality (n=5) resonance with Saturn
    phi_jup = planets["Jupiter"]["rad"]
    v_jup2 = 6.2 * math.cos(2.0 * theta - phi_jup)
    v_jup5 = 2.6 * math.cos(5.0 * theta - phi_jup)
    v_jup = v_jup2 + v_jup5
    components["Jupiter"] = {"symbol": "♃", "n": [2, 5], "val_mm": round(v_jup, 2), "phase_deg": round(math.degrees(phi_jup), 1)}
    r_sum += v_jup

    # 2. Venus (♀): Sacred Pentagram resonance (n=5, 8:13 Earth resonance)
    phi_ven = planets["Venus"]["rad"]
    v_ven = 5.4 * math.cos(5.0 * theta - phi_ven)
    components["Venus"] = {"symbol": "♀", "n": [5], "val_mm": round(v_ven, 2), "phase_deg": round(math.degrees(phi_ven), 1)}
    r_sum += v_ven

    # 3. Saturn (♄): Dipole eccentricity offset (n=1) + Triangular resonance (n=3)
    phi_sat = planets["Saturn"]["rad"]
    v_sat1 = 4.2 * math.cos(theta - phi_sat)
    v_sat3 = 2.2 * math.cos(3.0 * theta - 2.0 * phi_sat)
    v_sat = v_sat1 + v_sat3
    components["Saturn"] = {"symbol": "♄", "n": [1, 3], "val_mm": round(v_sat, 2), "phase_deg": round(math.degrees(phi_sat), 1)}
    r_sum += v_sat

    # 4. Mars (♂): Triangular harmonic (n=3)
    phi_mar = planets["Mars"]["rad"]
    v_mar = 3.4 * math.cos(3.0 * theta - phi_mar)
    components["Mars"] = {"symbol": "♂", "n": [3], "val_mm": round(v_mar, 2), "phase_deg": round(math.degrees(phi_mar), 1)}
    r_sum += v_mar

    # 5. Earth-Moon (♁): Hexagonal Lagrange Libration (n=6, L4/L5 Trojan symmetry)
    phi_ear = planets["Earth"]["rad"]
    v_ear = 4.2 * math.cos(6.0 * theta - phi_ear)
    components["Earth"] = {"symbol": "♁", "n": [6], "val_mm": round(v_ear, 2), "phase_deg": round(math.degrees(phi_ear), 1)}
    r_sum += v_ear

    # 6. Mercury (☿): Octave ripple (n=8, relativistic fast precession)
    phi_mer = planets["Mercury"]["rad"]
    v_mer = 2.0 * math.cos(8.0 * theta - phi_mer)
    components["Mercury"] = {"symbol": "☿", "n": [8], "val_mm": round(v_mer, 2), "phase_deg": round(math.degrees(phi_mer), 1)}
    r_sum += v_mer

    return r_sum, components

def compute_spiro_point(theta, orbit_num, cfg, grid, weather, planets=None):
    if planets is None:
        planets = compute_planetary_lagrange()

    T0 = float(cfg.get("period_sec", 20.0))
    R0 = float(cfg.get("r0_mm", 50.0))
    c = float(cfg.get("log_c", 5.0))
    ampl_grid_max = float(cfg.get("ampl_grid_max", 3.5))
    temp_factor = float(cfg.get("temp_factor", 0.03))
    wind_ampl = float(cfg.get("wind_ampl", 0.35))
    direction = -1.0 if str(cfg.get("direction", "ccw")).lower() == "ccw" else 1.0

    # 1. Base thermal dilatancy (subdued influence)
    R = R0 + temp_factor * (weather["temp_c"] - 10.0)

    # 2. 50Hz Continental Grid Symlog modulation
    df = grid["drift_mhz"]
    sgn = 1.0 if df >= 0 else -1.0
    delta_grid = sgn * (math.log(1.0 + abs(df) / c) / math.log(1.0 + 50.0 / c)) * ampl_grid_max

    # 3. Inverse Discrete Fourier Planetary Synthesis (Interfering harmonic rosettes)
    delta_fourier, fourier_meta = compute_inverse_fourier_planetary(theta, planets)

    # 4. 36 Decan wind ripple petals (subdued influence)
    r_wind = 0.10 + (weather["wind_kmh"] / 100.0) * wind_ampl
    delta_wind = r_wind * math.cos(36.0 * theta)

    # 5. Continuous slow Archimedean spiral pitch
    spiral_dr = cfg.get("spiral_dr_per_orbit", -0.2) * (orbit_num % 12.0)

    # Combined polar radius
    r_total = R + delta_grid + delta_fourier + delta_wind + spiral_dr

    # 6. Precession angle controlled smoothly by lunar phase & subtle humidity
    precess = direction * orbit_num * (2.0 * math.pi / 36.0) * (0.95 + (weather["rh_pct"] / 100.0) * 0.05)
    ang = theta + precess

    # Cartesian coordinates centered at (0, 0)
    # Under CCW, ang < 0: sin(ang) < 0 -> x < 0 (left/West), -cos(ang) < 0 (top/North -> bottom/South).
    x = r_total * math.sin(ang)
    y = -r_total * math.cos(ang)

    return x, y, r_total, fourier_meta

if __name__ == "__main__":
    main()
