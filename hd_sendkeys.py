#!/usr/bin/env python3
"""
hd_sendkeys.py — Send exact key sequence from hd_state.log to COMI-HD
via X11/XTest (ctypes), running inside Xvfb :99.

Timing (frames at ~6fps = 167ms/frame):
  @27 KEY ESC   → room 2
  @41 KEY ESC   → room 1 → room 4
  @50 KEY ESC   → room 9
  @62 KEY ESC   → dialog skip
  @71 RCLICK    → INVENTORY
"""

import ctypes
import ctypes.util
import os
import sys
import time
import struct

# ── Load X11 libraries ───────────────────────────────────────────
libX11_path = ctypes.util.find_library("X11")
libXtst_path = ctypes.util.find_library("Xtst")
if not libX11_path or not libXtst_path:
    print("ERROR: can't find libX11 or libXtst", file=sys.stderr)
    sys.exit(1)

libX11 = ctypes.CDLL(libX11_path, use_errno=True)
libXtst = ctypes.CDLL(libXtst_path, use_errno=True)

# ── X11 types ────────────────────────────────────────────────────
Display = ctypes.c_void_p
Window = ctypes.c_ulong
Colormap = ctypes.c_ulong
XID = ctypes.c_ulong
Atom = ctypes.c_ulong
Bool = ctypes.c_int
Status = ctypes.c_int

# ── XOpenDisplay / XCloseDisplay / XFlush / XDefaultRootWindow ───
libX11.XOpenDisplay.restype = Display
libX11.XOpenDisplay.argtypes = [ctypes.c_char_p]

libX11.XCloseDisplay.restype = ctypes.c_int
libX11.XCloseDisplay.argtypes = [Display]

libX11.XFlush.restype = ctypes.c_int
libX11.XFlush.argtypes = [Display]

libX11.XDefaultRootWindow.restype = Window
libX11.XDefaultRootWindow.argtypes = [Display]

libX11.XDefaultScreen.restype = ctypes.c_int
libX11.XDefaultScreen.argtypes = [Display]

libX11.XRootWindow.restype = Window
libX11.XRootWindow.argtypes = [Display, ctypes.c_int]

# ── Keysym → Keycode ─────────────────────────────────────────────
libX11.XKeysymToKeycode.restype = ctypes.c_ubyte
libX11.XKeysymToKeycode.argtypes = [Display, ctypes.c_ulong]

# ── XTest functions ──────────────────────────────────────────────
libXtst.XTestFakeKeyEvent.restype = Status
libXtst.XTestFakeKeyEvent.argtypes = [Display, ctypes.c_uint, Bool, ctypes.c_ulong]

libXtst.XTestFakeMotionEvent.restype = Status
libXtst.XTestFakeMotionEvent.argtypes = [Display, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]

libXtst.XTestFakeButtonEvent.restype = Status
libXtst.XTestFakeButtonEvent.argtypes = [Display, ctypes.c_uint, Bool, ctypes.c_ulong]

# ── XGetImage / XDestroyImage for screenshot ─────────────────────
class XImage(ctypes.Structure):
    pass

libX11.XGetImage.restype = ctypes.POINTER(XImage)
libX11.XGetImage.argtypes = [
    Display, Window, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
    ctypes.c_ulong, ctypes.c_int
]

libX11.XDestroyImage.restype = ctypes.c_int
libX11.XDestroyImage.argtypes = [ctypes.POINTER(XImage)]

# XImage struct fields we need (offset-based, simplified)
# We'll access via offsets for portability

# ── XWindowAttributes ────────────────────────────────────────────
class XWindowAttributes(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int), ("y", ctypes.c_int),
        ("width", ctypes.c_int), ("height", ctypes.c_int),
        ("border_width", ctypes.c_int), ("depth", ctypes.c_int),
        ("visual", ctypes.c_void_p),
        ("root", Window),
        ("class", ctypes.c_int), ("bit_gravity", ctypes.c_int),
        ("win_gravity", ctypes.c_int), ("backing_store", ctypes.c_int),
        ("backing_planes", ctypes.c_ulong), ("backing_pixel", ctypes.c_ulong),
        ("save_under", Bool), ("map_installed", Bool),
        ("map_state", ctypes.c_int), ("all_event_masks", ctypes.c_long),
        ("your_event_mask", ctypes.c_long),
        ("do_not_propagate_mask", ctypes.c_long),
        ("override_redirect", Bool), ("colormap", Colormap),
    ]

libX11.XGetWindowAttributes.restype = Status
libX11.XGetWindowAttributes.argtypes = [Display, Window, ctypes.POINTER(XWindowAttributes)]

# ZPixmap format constant
ZPixmap = 2
AllPlanes = ctypes.c_ulong(0xffffffff)


def open_display(name=":99"):
    dpy = libX11.XOpenDisplay(name.encode())
    if not dpy:
        print(f"ERROR: Can't open display {name}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] Opened display {name}")
    return dpy


def send_key(dpy, keysym_name="Escape"):
    """Send a key press+release via XTest."""
    keysym_map = {
        "Escape": 0xff1b,
        "F12": 0xffc9,
    }
    ks = keysym_map.get(keysym_name)
    if ks is None:
        print(f"ERROR: unknown keysym {keysym_name}")
        return
    kc = libX11.XKeysymToKeycode(dpy, ctypes.c_ulong(ks))
    if not kc:
        print(f"ERROR: no keycode for {keysym_name}")
        return
    libXtst.XTestFakeKeyEvent(dpy, ctypes.c_uint(kc), Bool(True), ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    time.sleep(0.02)
    libXtst.XTestFakeKeyEvent(dpy, ctypes.c_uint(kc), Bool(False), ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    print(f"[KEY] {keysym_name} (keycode {kc})")


def send_right_click(dpy, x=364, y=244):
    """Move pointer and right-click."""
    libXtst.XTestFakeMotionEvent(dpy, ctypes.c_int(-1),
                                  ctypes.c_int(x), ctypes.c_int(y),
                                  ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    time.sleep(0.05)
    # Button 3 = right
    libXtst.XTestFakeButtonEvent(dpy, ctypes.c_uint(3), Bool(True), ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    time.sleep(0.05)
    libXtst.XTestFakeButtonEvent(dpy, ctypes.c_uint(3), Bool(False), ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    print(f"[RCLICK] at ({x},{y})")


def capture_screen(dpy, path):
    """Capture root window as PPM via XGetImage."""
    screen = libX11.XDefaultScreen(dpy)
    root = libX11.XRootWindow(dpy, screen)
    
    wa = XWindowAttributes()
    ret = libX11.XGetWindowAttributes(dpy, root, ctypes.byref(wa))
    if not ret:
        print("ERROR: XGetWindowAttributes failed")
        return
    
    w, h = wa.width, wa.height
    print(f"[CAPTURE] grabbing {w}x{h} ...")
    
    img_ptr = libX11.XGetImage(dpy, root, 0, 0, w, h, AllPlanes, ZPixmap)
    if not img_ptr:
        print("ERROR: XGetImage failed")
        return
    
    # Read XImage fields using offsets (portable across ABI)
    # offsetof(XImage, bytes_per_line) ≈ depends on platform
    # Simpler: just dump directly via the XImage structure layout
    # Actually let's access via known struct layout
    
    try:
        with open(path, "wb") as f:
            f.write(f"P6\n{w} {h}\n255\n".encode())
            
            # XGetPixel — slow but correct, avoids struct layout issues
            libX11.XGetPixel.restype = ctypes.c_ulong
            libX11.XGetPixel.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
            
            for y in range(h):
                for x in range(w):
                    pixel = libX11.XGetPixel(img_ptr, ctypes.c_int(x), ctypes.c_int(y))
                    r = (pixel >> 16) & 0xff
                    g = (pixel >> 8) & 0xff
                    b = pixel & 0xff
                    f.write(bytes([r, g, b]))
        
        print(f"[SCREENSHOT] saved {path} ({w}x{h})")
        
    finally:
        libX11.XDestroyImage(img_ptr)


def main():
    os.makedirs("/tmp/comi-hd-ss", exist_ok=True)
    
    dpy = open_display(":99")
    
    print("\n=== HD SendKeys ===")
    print("Target: COMI-HD via Xvfb :99")
    print("Sequence: ESC×4 → RCLICK → F12 (screenshot)\n")
    
    FPS = 6.0  # Xvfb is slow, ~6 fps
    
    # Phase 1: Let game boot and reach the starting state
    print("[BOOT] Waiting 8s for game startup...")
    time.sleep(8)
    
    # Take a screenshot of the initial game state
    print("[PREVIEW] Capturing initial game state...")
    try:
        # Check what room we might be in using the HD background 
        print("[ESC#1] Sending first ESC to see game reaction...")
        send_key(dpy, "Escape")
        time.sleep(1)
    except:
        pass
    
    # Phase 2: Four ESC keys at exact intervals from hd_state.log
    # @27→@41: 14 frames, @41→@50: 9 frames, @50→@62: 12 frames, @62→@71: 9 frames
    esc_gaps = [14, 9, 12, 9]
    for i, gap in enumerate(esc_gaps):
        wait = gap / FPS
        print(f"\n[WAIT] {wait:.2f}s ({gap} frames)...")
        time.sleep(wait)
        send_key(dpy, "Escape")
        print(f"  → ESC #{i+1} sent")
    
    # Phase 3: Right-click at (364, 244) — opens inventory
    # Last ESC to RCLICK: 18 frames
    wait = 18 / FPS
    print(f"\n[WAIT] {wait:.2f}s (18 frames to RCLICK)...")
    time.sleep(wait)
    send_right_click(dpy, 364, 244)
    
    # Phase 4: Let inventory render
    print("\n[WAIT] 3s for inventory to render...")
    time.sleep(3)
    
    # Phase 5: Capture from the game window directly
    print("\n[F12] Sending F12 for built-in screenshot...")
    send_key(dpy, "F12")
    time.sleep(1)
    
    # Also capture via X11 from the game window
    print("[CAPTURE] Grabbing game window...")
    try:
        # Find the game window
        root = libX11.XDefaultRootWindow(dpy)
        libX11.XQueryTree.restype = ctypes.c_int
        libX11.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)), ctypes.POINTER(ctypes.c_uint)]
        
        r = ctypes.c_ulong(); p = ctypes.c_ulong()
        cp = ctypes.POINTER(ctypes.c_ulong)()
        nc = ctypes.c_uint()
        if libX11.XQueryTree(dpy, root, ctypes.byref(r), ctypes.byref(p), ctypes.byref(cp), ctypes.byref(nc)):
            children = ctypes.cast(cp, ctypes.POINTER(ctypes.c_ulong * nc.value))[0]
            for i in range(nc.value):
                # Get geometry to find the game window
                x, y = ctypes.c_int(), ctypes.c_int()
                w, h = ctypes.c_uint(), ctypes.c_uint()
                bw, depth = ctypes.c_uint(), ctypes.c_uint()
                libX11.XGetGeometry.restype = ctypes.c_int
                libX11.XGetGeometry.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                    ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
                    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_uint),
                    ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
                    ctypes.POINTER(ctypes.c_uint)]
                libX11.XGetGeometry(dpy, children[i], ctypes.byref(r), ctypes.byref(x),
                                    ctypes.byref(y), ctypes.byref(w), ctypes.byref(h),
                                    ctypes.byref(bw), ctypes.byref(depth))
                
                if w.value > 100 and h.value > 100:
                    print(f"  Window {children[i]}: {w.value}x{h.value}+{x.value}+{y.value}")
                    
                    # Capture this window
                    img_ptr = libX11.XGetImage(dpy, children[i], 0, 0, w.value, h.value,
                                               ctypes.c_ulong(0xffffffff), 2)
                    if img_ptr:
                        # Write PPM
                        with open("/tmp/comi-hd-ss/hd_inventory.ppm", "wb") as f:
                            f.write(f"P6\n{w.value} {h.value}\n255\n".encode())
                            libX11.XGetPixel.restype = ctypes.c_ulong
                            libX11.XGetPixel.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
                            for yy in range(h.value):
                                for xx in range(w.value):
                                    pixel = libX11.XGetPixel(img_ptr, ctypes.c_int(xx), ctypes.c_int(yy))
                                    f.write(bytes([(pixel >> 16) & 0xff, (pixel >> 8) & 0xff, pixel & 0xff]))
                        print(f"  ✓ Saved /tmp/comi-hd-ss/hd_inventory.ppm ({w.value}x{h.value})")
                        libX11.XDestroyImage(img_ptr)
                    break  # first large window found
    except Exception as e:
        print(f"  ✗ Capture failed: {e}")
    
    time.sleep(1)
    
    libX11.XCloseDisplay(dpy)
    print("\n=== DONE ===")
    print("Check /tmp/comi-hd-ss/hd_inventory.ppm and ~/.local/share/scummvm/screenshots/")


if __name__ == "__main__":
    main()
