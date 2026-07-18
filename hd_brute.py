#!/usr/bin/env python3
"""Brute force: skip intro with many ESCs, then right-click inventory."""
import ctypes, ctypes.util, os, sys, time

libX11 = ctypes.CDLL(ctypes.util.find_library("X11"))
libXtst = ctypes.CDLL(ctypes.util.find_library("Xtst"))
Window = ctypes.c_ulong; Bool = ctypes.c_int

dpy = libX11.XOpenDisplay(b":99")
if not dpy: print("FAIL"); sys.exit(1)

def key(ks_hex):
    libX11.XKeysymToKeycode.restype = ctypes.c_ubyte
    kc = libX11.XKeysymToKeycode(dpy, ctypes.c_ulong(ks_hex))
    if not kc: return
    libXtst.XTestFakeKeyEvent(dpy, ctypes.c_uint(kc), Bool(1), ctypes.c_ulong(0))
    libX11.XFlush(dpy); time.sleep(0.02)
    libXtst.XTestFakeKeyEvent(dpy, ctypes.c_uint(kc), Bool(0), ctypes.c_ulong(0))
    libX11.XFlush(dpy)

def click(x=364, y=244, btn=3):
    libXtst.XTestFakeMotionEvent(dpy, -1, x, y, ctypes.c_ulong(0))
    libX11.XFlush(dpy); time.sleep(0.05)
    libXtst.XTestFakeButtonEvent(dpy, btn, Bool(1), ctypes.c_ulong(0))
    libX11.XFlush(dpy); time.sleep(0.03)
    libXtst.XTestFakeButtonEvent(dpy, btn, Bool(0), ctypes.c_ulong(0))
    libX11.XFlush(dpy)

def capture(path="ss"):
    root = libX11.XDefaultRootWindow(dpy)
    libX11.XQueryTree.restype = ctypes.c_int
    libX11.XQueryTree.argtypes = [ctypes.c_void_p, Window, ctypes.POINTER(Window),
        ctypes.POINTER(Window), ctypes.POINTER(ctypes.POINTER(Window)), ctypes.POINTER(ctypes.c_uint)]
    r, p = Window(), Window()
    cp = ctypes.POINTER(Window)(); nc = ctypes.c_uint()
    if not libX11.XQueryTree(dpy, root, ctypes.byref(r), ctypes.byref(p), ctypes.byref(cp), ctypes.byref(nc)) or nc.value == 0:
        return None
    wins = ctypes.cast(cp, ctypes.POINTER(Window * nc.value))[0]
    for i in range(nc.value):
        w = wins[i]
        x, y = ctypes.c_int(), ctypes.c_int()
        ww, hh = ctypes.c_uint(), ctypes.c_uint()
        bw, dep = ctypes.c_uint(), ctypes.c_uint()
        libX11.XGetGeometry(dpy, w, ctypes.byref(r), ctypes.byref(x), ctypes.byref(y), ctypes.byref(ww), ctypes.byref(hh), ctypes.byref(bw), ctypes.byref(dep))
        if ww.value < 200 or hh.value < 200: continue
        img = libX11.XGetImage(dpy, w, 0, 0, ww.value, hh.value, ctypes.c_ulong(0xffffffff), 2)
        if not img: continue
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

os.makedirs("/tmp/comi-hd-ss", exist_ok=True)

print("=== COMI-HD Brute Force Test ===")

# Step 1: Wait for boot
print("1. Wait for boot (10s)")
time.sleep(10)

# Step 2: Send 30 ESCs rapidly to skip everything
print("2. Sending 30× ESC to skip intro/menus...")
for i in range(30):
    key(0xff1b)
    time.sleep(0.3)  # ~3fps spacing
    if i % 5 == 4:
        print(f"   {i+1}/30 ESCs sent")

# Step 3: Wait for any menu to settle
print("3. Wait 3s...")
time.sleep(3)

# Step 4: Take a screenshot to see where we are
print("4. Screenshot mid-state")
capture("mid")

# Step 5: Try Enter (might select New Game or OK)
print("5. Press Enter")
key(0xff0d)  # Return
time.sleep(2)

# Step 6: If there's a load game dialog, send ESCs to cancel back to game
print("6. More ESCs")
for i in range(10):
    key(0xff1b)
    time.sleep(0.3)

# Step 7: Wait for game to reach gameplay
print("7. Wait 5s for game to settle...")
time.sleep(5)

# Step 8: Right-click to open inventory  
print("8. Right-click!")
click(364, 244)
time.sleep(3)

# Step 9: Capture
print("9. Capture inventory")
inv = capture("inventory_brute")
print(f"   Saved: {inv}")

# Step 10: F12 for built-in screenshot
print("10. F12")
key(0xffc9)  # F12
time.sleep(2)

libX11.XCloseDisplay(dpy)
print("\n=== DONE ===")
