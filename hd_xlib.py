#!/usr/bin/env python3
"""COMI-HD: Python-Xlib based key sender for Xvfb."""
import os, sys, time
os.environ['DISPLAY'] = ':99'

from Xlib import X, display, Xatom, Xutil
from Xlib.ext import xtest
from Xlib.protocol import event as xevent

d = display.Display()
root = d.screen().root

# Find game window
def find_game_window():
    """Find the game window by enumerating children."""
    windows = root.query_tree().children
    for w in windows:
        try:
            name = w.get_wm_name()
            if name and 'Monkey Island' in name:
                return w
        except:
            pass
        # Check children recursively
        try:
            for child in w.query_tree().children:
                try:
                    name = child.get_wm_name()
                    if name and 'Monkey Island' in name:
                        return child
                except:
                    pass
        except:
            pass
    # Return first sizable window
    for w in windows:
        try:
            geom = w.get_geometry()
            if geom.width > 200 and geom.height > 200:
                return w
        except:
            pass
    return None

def send_key(keycode, press=True):
    """Send a key event using XTest."""
    xtest.fake_input(d, X.KeyPress if press else X.KeyRelease, keycode)
    d.sync()

def send_key_xtest(keysym_str):
    """Send a key press+release using XTest."""
    keysym_map = {
        'Escape': 0xff1b, 'Return': 0xff0d, 'F12': 0xffc9,
        'space': 0x0020,
    }
    ks = keysym_map.get(keysym_str)
    if not ks:
        print(f'  Unknown keysym: {keysym_str}')
        return
    keycode = d.keysym_to_keycode(ks)
    if not keycode:
        print(f'  No keycode for {keysym_str}')
        return
    send_key(keycode, True)
    d.sync()
    time.sleep(0.02)
    send_key(keycode, False)
    d.sync()

def send_event_key(win, keysym, press=True):
    """Send a key event directly to a window."""
    keycode = d.keysym_to_keycode(keysym)
    if not keycode:
        return
    
    ev_type = X.KeyPress if press else X.KeyRelease
    ev = xevent.KeyPress(
        time=X.CurrentTime,
        root=root,
        window=win,
        same_screen=0,
        child=X.NONE,
        root_x=0, root_y=0,
        event_x=0, event_y=0,
        state=0,
        detail=keycode,
    )
    ev.type = ev_type
    win.send_event(ev, propagate=True)
    d.sync()

def capture_window(win, path):
    """Capture a window's content as PPM."""
    geom = win.get_geometry()
    raw = win.get_image(0, 0, geom.width, geom.height, X.ZPixmap, 0xffffffff)
    data = raw.data
    
    with open(path, 'wb') as f:
        f.write(f'P6\n{geom.width} {geom.height}\n255\n'.encode())
        # data is bytes object with BGRX format (32bpp)
        for y in range(geom.height):
            offset = y * geom.width * 4  # 4 bytes per pixel (32bpp)
            for x in range(geom.width):
                px = offset + x * 4
                b = data[px]
                g = data[px + 1]
                r = data[px + 2]
                f.write(bytes([r, g, b]))
    return path

def analyze_ppm(path):
    """Quick check PPM content."""
    with open(path, 'rb') as f:
        f.readline(); dims = f.readline().strip(); f.readline()
        w, h = map(int, dims.split())
        data = f.read()
    non_black = 0; total = 0
    for i in range(0, len(data)//3, 50):
        r, g, b = data[i*3], data[i*3+1], data[i*3+2]
        if r > 8: non_black += 1
        total += 1
    return w, h, non_black*100/total


os.makedirs('/tmp/comi-hd-ss', exist_ok=True)

print('=== COMI-HD Xlib Key Test ===')

# Find game window
print('Finding game window...')
win = find_game_window()
if not win:
    print('ERROR: Game window not found!')
    sys.exit(1)

geom = win.get_geometry()
name = win.get_wm_name()
print(f'Found: {name} ({geom.width}x{geom.height})')

# Set input focus
win.set_input_focus(X.RevertToParent, X.CurrentTime)
d.sync()
print('Focus set')

# Phase 1: Initial capture
print('\nPhase 1: Initial state...')
time.sleep(1)
w, h, pc = analyze_ppm(capture_window(root, '/tmp/comi-hd-ss/xlib_initial.ppm'))
print(f'  Initial: {pc:.1f}% non-black')

# Phase 2: Send ESCs to navigate
print('\nPhase 2: Sending 30× ESC...')
for i in range(30):
    send_key_xtest('Escape')
    time.sleep(0.3)
    if (i+1) % 10 == 0:
        print(f'  {i+1}/30 ESCs sent')

time.sleep(2)
w, h, pc = analyze_ppm(capture_window(root, '/tmp/comi-hd-ss/xlib_after_esc.ppm'))
print(f'  After ESCs: {pc:.1f}% non-black')

# Phase 3: Enter key
print('\nPhase 3: Press Enter...')
send_key_xtest('Return')
time.sleep(5)
w, h, pc = analyze_ppm(capture_window(root, '/tmp/comi-hd-ss/xlib_after_enter.ppm'))
print(f'  After Enter: {pc:.1f}% non-black')

# Phase 4: Right-click to open inventory
print('\nPhase 4: Right-click...')
# Use XTest for button events
xtest.fake_input(d, X.MotionNotify, 0, detail=0, root=X.NONE, child=X.NONE, root_x=364, root_y=244, event_x=364, event_y=244)
d.sync()
time.sleep(0.1)
xtest.fake_input(d, X.ButtonPress, 3)  # Button 3 = right
d.sync()
time.sleep(0.05)
xtest.fake_input(d, X.ButtonRelease, 3)
d.sync()
time.sleep(3)
w, h, pc = analyze_ppm(capture_window(root, '/tmp/comi-hd-ss/xlib_inventory.ppm'))
print(f'  After RCLICK: {pc:.1f}% non-black')

# Phase 5: F12 screenshot
print('\nPhase 5: F12...')
send_key_xtest('F12')
time.sleep(2)
print('  F12 sent')

# Compare all screenshots
import hashlib
files = ['xlib_initial.ppm', 'xlib_after_esc.ppm', 'xlib_after_enter.ppm', 'xlib_inventory.ppm']
hashes = {}
for f in files:
    with open(f'/tmp/comi-hd-ss/{f}', 'rb') as fh:
        hashes[f] = hashlib.md5(fh.read()).hexdigest()[:12]

for f in files:
    print(f'  {f}: {hashes[f]}')

# Find which are identical
for i, f1 in enumerate(files):
    for f2 in files[i+1:]:
        if hashes[f1] == hashes[f2]:
            print(f'  ✗ {f1} == {f2} (keystroke had no effect)')
        else:
            print(f'  ✓ {f1} != {f2} (keystroke changed screen)')

print('\n=== DONE ===')
