# lagrange — Three-Body Lagrange Libration Points & Constellation Engine

[![Metric Time: 1.0 dh36 = 1/36 Day](https://img.shields.io/badge/chronometry-1.0_dh36_(2400s_%2F_10%C2%B0)-004d40.svg)](https://github.com/K0F/timewarp-alpine)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0_Universal-lightgrey.svg)](https://creativecommons.org/publicdomain/zero/1.0/)
[![Drkota V-Plotter](https://img.shields.io/badge/V--Plotter-Drkota_GoMotor_600DPI-333333.svg)](https://github.com/K0F/drkota)

> *"Gravitační uzly nepatří nikomu. Jsou to tichá sedla v potenciálovém poli, kde se setkává zemská tíže se slunečním větrem a lunárním přílivem."*

Zero-bloat C and Python engine calculating, simulating, and plotting the **circular restricted three-body problem (CRTBP)** for the **Sun ($\odot$), Earth ($\oplus$), and Moon ($\leftmoon$)**, with a dedicated focus on the **outer/distant Lagrange equilibrium points**:
- **Sun–Earth $L_2$**: Outer deep-space night shadow ($\sim 1.5 \times 10^6\text{ km}$ beyond Earth, host of JWST, Gaia, Euclid).
- **Sun–Earth $L_3$**: Distant Anti-Earth point on the far side of the Sun ($\sim 3.0 \times 10^8\text{ km}$).
- **Sun–Earth $L_4$ & $L_5$**: The sacred equilateral Trojan vertices trailing and leading at $\pm 60^\circ$ on Earth's heliocentric orbit.
- **Earth–Moon $L_{2M}$**: Distant lunar far-side halo orbit anchor ($\sim 64\,500\text{ km}$ behind the Moon).
- **Decanic Metric Chronometry (`dh36`)**: Phase-locked to the 36 decans of Earth's diurnal rotation ($1.00.00\text{ dh36} = 2400\text{ s} = 40\text{ min} = 10^\circ$).
- **Vector Pen-Plotter Output**: Clean single-stroke line-art for the **Drkota V-plotter** and laser engravers.
- **Pixel Graphics & Animated GIFs**: Pure C rendering via [`processing.h`](https://github.com/K0F/processing.h) and embedded Terminus bitmap strikes.

---

## 1. Celestial Mechanics & Libration Geometry

In the rotating coordinate frame with the primary mass $M_1$ (Sun) and secondary $M_2$ (Earth), the effective potential $U_{\text{eff}}$ balances gravitational attraction and centrifugal acceleration:

$$U_{\text{eff}}(x, y) = -\frac{G M_1}{r_1} - \frac{G M_2}{r_2} - \frac{1}{2}\omega^2 (x^2 + y^2)$$

The 5 equilibrium Lagrange points satisfy $\nabla U_{\text{eff}} = 0$:

```text
                        [L4: Trojan Equilateral (+60°)]
                                      *
                                    /   \
                                  /       \
  [L3: Anti-Earth]              /           \              [L2: Night Shadow / JWST]
        * ------------------ (SOL) ------- (TERRA) --*-- [L2]
                                \           /    [L1]
                                  \       /
                                    \   /
                                      *
                        [L5: Trojan Equilateral (-60°)]
```

### The Distant Point Constellation Asterism
While $L_1$ resides inward between the bodies, the engine extracts and visualizes the **outer boundary constellation**:
1. **Collinear Spine**: $L_3 \longleftrightarrow \text{Sun} \longleftrightarrow \text{Earth} \longleftrightarrow L_2$
2. **Trojan Sacred Triangle**: $\text{Sun} \longleftrightarrow L_4 \longleftrightarrow \text{Earth} \longleftrightarrow L_5 \longleftrightarrow \text{Sun}$
3. **Lunar Far-Side Antenna**: $\text{Earth} \longleftrightarrow \text{Moon} \longleftrightarrow L_{2M}$

---

## 2. Decanic Harmonization (`dh36`)

The solar and lunar vectors are continuously phased via Prague civil time and the **36 Decans** of the planetary day:
- $1\text{ Day} = 36.00.00\text{ dh36} = 86\,400\text{ s}$
- $1\text{ DH} = 1.00.00\text{ dh36} = 2400\text{ s} = 40\text{ min} = 10^\circ\text{ solar arc}$
- $1\text{ DM} = 0.01.00\text{ dh36} = 24\text{ s}$
- $1\text{ DS} = 0.00.01\text{ dh36} = 240\text{ ms} = 4.166\text{ Hz}$

Each decan transition alters the orientation of the Lagrange asterism, rotating the celestial dial against the fixed stars.

---

## 3. Toolkit Reference

### `lagrange.py` (CLI & Python Generator)
```bash
# Print current celestial constellation coordinates & ASCII map
./lagrange.py status

# Render standalone vector constellation SVG
./lagrange.py svg --out /tmp/lagrange_constellation.svg --width 120

# Export for physical plotting on Drkota
./lagrange.py plot --dry-run
```

### `lagrange_proc.c` (Pixel Graphics & Cyclic GIF via `processing.h`)
```bash
make
./lagrange_proc --gif
```
Generates high-contrast 16-color Bayer dithered cyclic animated GIFs ($320 \times 240$) suitable for brutalist small-web (`k0f.github.io`).

---

## 4. Hardware Deployment: Drkota V-Plotter

Plotted on heavy watercolor/card stock using a Sakura Pigma Micron 0.35 mm fineliner:
- **Kinematic calibration**: $190.47619\text{ steps/mm}$ ($10\,000\text{ steps} = 52.5\text{ mm}$).
- **Gondola width**: $45.0\text{ mm}$.
- **Segment size**: $4.0\text{ mm}$ draw / $8.0\text{ mm}$ travel.
- **Origin**: E-Stop ($Z0$) locks coordinates in place.

---

## 5. License & Lineage

- **License**: **ALL PUBLIC DOMAIN (CC0 1.0 UNIVERSAL) // ANTI-COPYRIGHT**
- **Lineage**:
  - Joseph-Louis Lagrange (*Essai sur le problème des trois corps*, 1772)
  - Stewart Brand (*Whole Earth Catalog*, 1968)
  - Woody & Steina Vašulka (*Video Synthesizer & Scan Processing*, 1970s)
  - Observatoř Cybernetics & The Samizdat Chronicle (2026)

`--τέχνη & kof`
