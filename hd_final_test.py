#!/usr/bin/env python3
"""
Final COMI-HD inventory test.
Loads save game → waits → right-click → X11 screenshot.
"""
import ctypes, ctypes.util, os, sys, time, struct

libX11 = ctypes.CDLL(ctypes.util.find_library("X11"))
libXtst = ctypes.CDLL(ctypes.util.find_library("Xtst"))

Window = ctypes.c_ulong
Bool = ctypes.c_int

# Open display
dpy = libX11.XOpenDisplay(b":99")
if not dpy:
    print("FAIL: can't open :99")
    sys.exit(1)

# Helper: send key
def send_key(ks_hex):
    ks = ctypes.c_ulong(ks_hex)
    kc = ctypes.c_ubyte()
    libX11.XKeysymToKeycode.restype = ctypes.c_ubyte
    libX11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kc = libX11.XKeysymToKeycode(dpy, ks)
    if not kc:
        print(f"  no keycode for 0x{ks_hex:04x}")
        return False
    libXtst.XTestFakeKeyEvent(dpy, ctypes.c_uint(kc), Bool(1), ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    time.sleep(0.02)
    libXtst.XTestFakeKeyEvent(dpy, ctypes.c_uint(kc), Bool(0), ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    return True

# Helper: right-click
def send_rclick(x=364, y=244):
    libXtst.XTestFakeMotionEvent(dpy, -1, x, y, ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    time.sleep(0.05)
    libXtst.XTestFakeButtonEvent(dpy, 3, Bool(1), ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    time.sleep(0.03)
    libXtst.XTestFakeButtonEvent(dpy, 3, Bool(0), ctypes.c_ulong(0))
    libX11.XFlush(dpy)
    print(f"  RCLICK at ({x},{y})")

# Helper: capture game window
def capture_window(path="inventory"):
    libX11.XDefaultRootWindow.restype = Window
    root = libX11.XDefaultRootWindow(dpy)
    
    libX11.XQueryTree.restype = ctypes.c_int
    libX11.XQueryTree.argtypes = [ctypes.c_void_p, Window,
        ctypes.POINTER(Window), ctypes.POINTER(Window),
        ctypes.POINTER(ctypes.POINTER(Window)), ctypes.POINTER(ctypes.c_uint)]
    
    r, p = Window(), Window()
    cp = ctypes.POINTER(Window)()
    nc = ctypes.c_uint()
    if not libX11.XQueryTree(dpy, root, ctypes.byref(r), ctypes.byref(p), ctypes.byref(cp), ctypes.byref(nc)):
        return None
    if nc.value == 0:
        return None
    children = ctypes.cast(cp, ctypes.POINTER(Window * nc.value))[0]
    
    for i in range(nc.value):
        w = children[i]
        libX11.XGetGeometry.restype = ctypes.c_int
        libX11.XGetGeometry.argtypes = [ctypes.c_void_p, Window,
            ctypes.POINTER(Window), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint)]
        x, y = ctypes.c_int(), ctypes.c_int()
        ww, hh = ctypes.c_uint(), ctypes.c_uint()
        bw, depth = ctypes.c_uint(), ctypes.c_uint()
        libX11.XGetGeometry(dpy, w, ctypes.byref(r), ctypes.byref(x), ctypes.byref(y),
                            ctypes.byref(ww), ctypes.byref(hh), ctypes.byref(bw), ctypes.byref(depth))
        if ww.value < 200 or hh.value < 200:
            continue
        # Found a decent window - capture it
        img = libX11.XGetImage(dpy, w, 0, 0, ww.value, hh.value,
                               ctypes.c_ulong(0xffffffff), 2)
        if not img:
            continue
        pp = f"/tmp/comi-hd-ss/hd_{path}.ppm"
        with open(pp, "wb") as f:
            f.write(f"P6\n{ww.value} {hh.value}\n255\n".encode())
            libX11.XGetPixel.restype = ctypes.c_ulong
            libX11.XGetPixel.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
            for yy in range(hh.value):
                for xx in range(ww.value):
                    pxl = libX11.XGetPixel(img, xx, yy)
                    f.write(bytes([(pxl>>16)&0xff, (pxl>>8)&0xff, pxl&0xff]))
        libX11.XDestroyImage(img)
        libX11.XFree(cp)
        return pp
    libX11.XFree(cp)
    return None


# ─── MAIN ─────────────────────────────────────────────────
os.makedirs("/tmp/comi-hd-ss", exist_ok=True)

print("=== COMI-HD: External Key Test ===")
print("1. Waiting for game to load save... (20s)")
time.sleep(20)

print("2. Capturing initial state...")
pre = capture_window("initial")
if pre:
    print(f"   Saved: {pre}")

print("3. Sending ESC to clear any dialog...")
send_key(0xff1b)  # Escape
time.sleep(2)

print("4. Right-click to open inventory...")
send_rclick(364, 244)
time.sleep(3)

print("5. Capturing inventory state...")
inv = capture_window("inventory")
if inv:
    print(f"   Saved: {inv}")

print("6. Sending F12 for built-in screenshot...")
send_key(0xffc9)  # F12
time.sleep(2)

libX11.XCloseDisplay(dpy)
print("\n=== DONE ===")
print(f"Check: {inv}")
