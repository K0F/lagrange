#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#include "processing.h"
#include <math.h>

static int total_frames = 36;

void setup(void) {
    size(320, 240);
    frameRate(18);
}

void draw(void) {
    background(10);

    int f = frameCount;
    float t = (float)f / (float)total_frames;
    float solar_rad = t * 2.0f * (float)M_PI - (float)M_PI / 2.0f;
    float lunar_rad = solar_rad + 0.81f * 2.0f * (float)M_PI; // ~81% illumination

    // Outer grid (16px)
    stroke(25);
    for (int x = 0; x < width; x += 16) line(x, 0, x, height);
    for (int y = 0; y < height; y += 16) line(0, y, width, y);

    float cx = width / 2.0f;
    float cy = height / 2.0f - 10.0f;
    float r_field = 75.0f;

    // Outer decanic ring
    stroke(50);
    noFill();
    ellipse(cx, cy, r_field * 2.0f, r_field * 2.0f);

    // 1. Earth at center (circle with cross)
    stroke(0, 255, 180);
    ellipse(cx, cy, 6, 6);
    line(cx - 5, cy, cx + 5, cy);
    line(cx, cy - 5, cx, cy + 5);

    // 2. Sun (SOL)
    float d_sun = r_field * 0.58f;
    float sx = cx + d_sun * cosf(solar_rad);
    float sy = cy + d_sun * sinf(solar_rad);
    stroke(255, 220, 60);
    ellipse(sx, sy, 8, 8);
    line(sx - 7, sy, sx + 7, sy);
    line(sx, sy - 7, sx, sy + 7);

    // 3. Moon (LUNA)
    float d_moon = r_field * 0.32f;
    float mx = cx + d_moon * cosf(lunar_rad);
    float my = cy + d_moon * sinf(lunar_rad);
    stroke(200, 200, 255);
    ellipse(mx, my, 4, 4);

    // 4. Distant Lagrange Points: L2 and L3
    // L2: Beyond Earth in the anti-solar night shadow
    float d_l2 = r_field * 0.82f;
    float l2_x = cx + d_l2 * cosf(solar_rad + (float)M_PI);
    float l2_y = cy + d_l2 * sinf(solar_rad + (float)M_PI);
    stroke(255, 60, 100);
    line(l2_x - 3, l2_y, l2_x + 3, l2_y);
    line(l2_x, l2_y - 3, l2_x, l2_y + 3);

    // L3: Behind Sun (Anti-Earth)
    float d_l3 = r_field * 0.90f;
    float l3_x = cx + d_l3 * cosf(solar_rad);
    float l3_y = cy + d_l3 * sinf(solar_rad);
    stroke(255, 60, 100);
    line(l3_x - 3, l3_y, l3_x + 3, l3_y);
    line(l3_x, l3_y - 3, l3_x, l3_y + 3);

    // 5. Trojans L4 and L5 (+-60 deg)
    float l4_x = cx + d_sun * cosf(solar_rad + (float)M_PI / 3.0f);
    float l4_y = cy + d_sun * sinf(solar_rad + (float)M_PI / 3.0f);
    float l5_x = cx + d_sun * cosf(solar_rad - (float)M_PI / 3.0f);
    float l5_y = cy + d_sun * sinf(solar_rad - (float)M_PI / 3.0f);
    stroke(0, 200, 255);
    line(l4_x - 2, l4_y - 2, l4_x + 2, l4_y + 2);
    line(l4_x - 2, l4_y + 2, l4_x + 2, l4_y - 2);
    line(l5_x - 2, l5_y - 2, l5_x + 2, l5_y + 2);
    line(l5_x - 2, l5_y + 2, l5_x + 2, l5_y - 2);

    // 6. Constellation lines
    stroke(80);
    line(l3_x, l3_y, sx, sy);
    line(sx, sy, cx, cy);
    line(cx, cy, l2_x, l2_y);
    line(sx, sy, l4_x, l4_y);
    line(l4_x, l4_y, cx, cy);
    line(sx, sy, l5_x, l5_y);
    line(l5_x, l5_y, cx, cy);
    line(cx, cy, mx, my);

    // Header & Telemetry
    fill(220);
    text("LAGRANGE 3-BODY CONSTELLATION", 10, 18);
    text("DH36: 10.93.92 | DEKAN 10", 10, 32);

    fill(140);
    text("L2: JWST / NIGHT SHADOW", 10, height - 12);
    text("L3: ANTI-EARTH", width - 110, height - 12);

    saveFrame("/tmp/lagrange_frames/frame-####.png");

    if (f >= total_frames) {
        exit_sketch();
    }
}

int main(void) {
    setup();
    if (_windowInit == 0) size3(320, 240, "Lagrange Constellation");
    while (!WindowShouldClose() && !_exitRequested) {
        beginDraw();
        if (_loopRunning || _redrawPending) {
            _redrawPending = false;
            draw();
        }
        endDraw();
    }
    return 0;
}
