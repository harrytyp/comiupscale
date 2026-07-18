/*
 * hd_sendkeys — Send exact key sequence (ESC ×4 → RCLICK) to COMI-HD
 * running inside Xvfb :99, then capture screenshot.
 * Timing matches hd_state.log: 27→41→50→62→71 frames
 * (14, 9, 12, 9, 18 frame gaps) at ~6 fps in Xvfb.
 *
 * Compile: gcc -o hd_sendkeys hd_sendkeys.c -lX11 -lXtst
 * Usage:   DISPLAY=:99 ./hd_sendkeys
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>

/* Timing from hd_state.log (frame numbers) */
/* At ~6 fps, 1 frame ≈ 167ms */
#define FRAME_MS      167     /* ~6 fps in Xvfb */
/* Absolute frame numbers from log */
#define TARGET_FRAMES  5
static const int esc_frames[] = {27, 41, 50, 62};
static const int click_frame   = 71;

/* Helper: wait for target frame number */
static void wait_for_frame(int target_frame) {
    static int current = 0;
    while (current < target_frame) {
        usleep(FRAME_MS * 1000);
        current++;
    }
    printf("[frame %d] reached\n", current);
}

/* Send a single key press+release */
static void send_key(Display *dpy, KeySym ks) {
    KeyCode kc = XKeysymToKeycode(dpy, ks);
    if (!kc) {
        fprintf(stderr, "ERROR: no keycode for 0x%lx\n", ks);
        return;
    }
    XTestFakeKeyEvent(dpy, kc, True, 0);   /* press */
    XFlush(dpy);
    usleep(20000); /* 20ms between press and release */
    XTestFakeKeyEvent(dpy, kc, False, 0);  /* release */
    XFlush(dpy);
    printf("[KEY] sent keysym 0x%lx (keycode %d)\n", ks, kc);
}

/* Send a right mouse click at (x, y) */
static void send_right_click(Display *dpy, int x, int y) {
    /* Move pointer */
    XTestFakeMotionEvent(dpy, -1, x, y, 0);
    XFlush(dpy);
    usleep(50000);

    /* Button press (button 3 = right) */
    XTestFakeButtonEvent(dpy, 3, True, 0);
    XFlush(dpy);
    usleep(50000);
    /* Button release */
    XTestFakeButtonEvent(dpy, 3, False, 0);
    XFlush(dpy);
    printf("[RCLICK] at (%d,%d)\n", x, y);
}

/* Capture the root window as PPM via XImage */
static void capture_screen(Display *dpy, const char *path) {
    Window root = RootWindow(dpy, DefaultScreen(dpy));
    XWindowAttributes wa;
    XGetWindowAttributes(dpy, root, &wa);

    XImage *img = XGetImage(dpy, root, 0, 0, wa.width, wa.height,
                            AllPlanes, ZPixmap);
    if (!img) {
        fprintf(stderr, "ERROR: XGetImage failed\n");
        return;
    }

    FILE *f = fopen(path, "wb");
    if (!f) {
        fprintf(stderr, "ERROR: can't open %s\n", path);
        XDestroyImage(img);
        return;
    }

    fprintf(f, "P6\n%d %d\n255\n", wa.width, wa.height);
    for (int y = 0; y < wa.height; y++) {
        for (int x = 0; x < wa.width; x++) {
            unsigned long pixel = XGetPixel(img, x, y);
            unsigned char r = (pixel >> img->red_shift)   & ((1 << img->red_mask) - 1);
            unsigned char g = (pixel >> img->green_shift) & ((1 << img->green_mask) - 1);
            unsigned char b = (pixel >> img->blue_shift)  & ((1 << img->blue_mask) - 1);
            /* Scale if needed */
            if (img->red_mask   != 0xff) r = (r * 255) / ((1 << img->red_mask) - 1);
            if (img->green_mask != 0xff) g = (g * 255) / ((1 << img->green_mask) - 1);
            if (img->blue_mask  != 0xff) b = (b * 255) / ((1 << img->blue_mask) - 1);
            fputc(r, f);
            fputc(g, f);
            fputc(b, f);
        }
    }
    fclose(f);
    XDestroyImage(img);
    printf("[SCREENSHOT] saved %s (%dx%d)\n", path, wa.width, wa.height);
}

int main(int argc, char **argv) {
    const char *display_name = ":99";
    Display *dpy = XOpenDisplay(display_name);
    if (!dpy) {
        fprintf(stderr, "ERROR: can't open display %s\n", display_name);
        return 1;
    }

    printf("=== HD SendKeys started on %s ===\n", display_name);
    printf("Timing: %dms per frame\n", FRAME_MS);
    printf("Sequence: ESC@27 → ESC@41 → ESC@50 → ESC@62 → RCLICK@71\n\n");

    /* Give the game a moment to actually reach the starting room/scene */
    sleep(2);

    /* === Phase 1: Four ESC keys at exact frame timings === */
    for (int i = 0; i < 4; i++) {
        int target = esc_frames[i];
        wait_for_frame(target);
        send_key(dpy, XK_Escape);
    }

    /* === Phase 2: Right-click at frame 71 === */
    wait_for_frame(click_frame);
    send_right_click(dpy, 364, 244);

    /* === Phase 3: Wait for inventory to render, then capture === */
    printf("\nWaiting 3s for inventory to render...\n");
    sleep(3);

    capture_screen(dpy, "/tmp/comi-hd-ss/hd_inventory.ppm");

    XCloseDisplay(dpy);
    printf("\n=== HD SendKeys complete ===\n");
    return 0;
}
