#!/usr/bin/env python3
"""List X11 windows on :99 using ctypes."""
import ctypes
import ctypes.util
import sys

libX11_path = ctypes.util.find_library("X11")
libX11 = ctypes.CDLL(libX11_path)

Window = ctypes.c_ulong
Atom = ctypes.c_ulong
Status = ctypes.c_int
Bool = ctypes.c_int

dpy = libX11.XOpenDisplay(b":99")
if not dpy:
    print("FAIL: can't open :99")
    sys.exit(1)

root = libX11.XDefaultRootWindow(dpy)
print(f"Root: {root}")

# ── XQueryTree ──────────────────────────────────────────────────
libX11.XQueryTree.restype = Status
libX11.XQueryTree.argtypes = [
    ctypes.c_void_p, Window,
    ctypes.POINTER(Window), ctypes.POINTER(Window),
    ctypes.POINTER(ctypes.POINTER(Window)), ctypes.POINTER(ctypes.c_uint)
]

def list_windows(win, indent=0):
    r, p = Window(), Window()
    cp = ctypes.POINTER(Window)()
    nc = ctypes.c_uint()
    ret = libX11.XQueryTree(dpy, win, ctypes.byref(r), ctypes.byref(p),
                            ctypes.byref(cp), ctypes.byref(nc))
    if not ret:
        return
    if nc.value > 0:
        children = ctypes.cast(cp, ctypes.POINTER(Window * nc.value))[0]
        for i in range(nc.value):
            w = children[i]
            # Get name via XFetchName
            libX11.XFetchName.restype = Status
            libX11.XFetchName.argtypes = [ctypes.c_void_p, Window, ctypes.POINTER(ctypes.c_char_p)]
            name_p = ctypes.c_char_p()
            has_name = libX11.XFetchName(dpy, w, ctypes.byref(name_p))
            
            # Get geometry
            x, y = ctypes.c_int(), ctypes.c_int()
            ww, hh = ctypes.c_uint(), ctypes.c_uint()
            bw, depth = ctypes.c_uint(), ctypes.c_uint()
            libX11.XGetGeometry.restype = Status
            libX11.XGetGeometry.argtypes = [ctypes.c_void_p, Window,
                ctypes.POINTER(Window), ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_uint),
                ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
                ctypes.POINTER(ctypes.c_uint)]
            libX11.XGetGeometry(dpy, w, ctypes.byref(r), ctypes.byref(x),
                                ctypes.byref(y), ctypes.byref(ww), ctypes.byref(hh),
                                ctypes.byref(bw), ctypes.byref(depth))
            
            pad = "  " * indent
            if has_name and name_p.value:
                print(f"{pad}Window {w}: \"{name_p.value.decode()}\" ({ww.value}x{hh.value} @{x.value},{y.value})")
                libX11.XFree(name_p)
            else:
                print(f"{pad}Window {w}: ({ww.value}x{hh.value} @{x.value},{y.value})")
            
            list_windows(w, indent + 1)
        
        libX11.XFree(cp)

list_windows(root)
libX11.XCloseDisplay(dpy)
