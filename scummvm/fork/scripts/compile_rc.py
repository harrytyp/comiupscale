"""Generate dists/.deps/scummvm.d and compile dists/scummvm.rc manually.
Bypasses the MSYS2 sed bug in Makefile.common.
"""
import os, re, subprocess, sys

base = os.path.dirname(os.path.abspath(__file__))
rc_file = os.path.join(base, 'dists', 'scummvm.rc')
deps_dir = os.path.join(base, 'dists', '.deps')
deps_file = os.path.join(deps_dir, 'scummvm.d')
obj_file = os.path.join(base, 'dists', 'scummvm.o')

os.makedirs(deps_dir, exist_ok=True)

with open(rc_file) as f:
    content = f.read()

h_includes = re.findall(r'^#include\s+"([^"]+\.h)"', content, re.MULTILINE)
rh_includes = re.findall(r'^#include\s+"([^"]+\.rh)"', content, re.MULTILINE)
assets = re.findall(r'(FILE|ICON|RT_MANIFEST|DATA)\s+"([^"]+)"', content)

with open(deps_file, 'w') as f:
    f.write('dists/scummvm.o: dists/scummvm.rc config.h config.mk \\\n')
    for h in h_includes:
        if h not in ('winresrc.h', 'config.h'):
            f.write(f'    ./{h} \\\n')
    for rh in rh_includes:
        f.write(f'    {rh} \\\n')
    for _, path in assets:
        f.write(f'    ./{path} \\\n')

print(f'Generated: {deps_file}')
print(f'  .h: {len(h_includes)}, .rh: {len(rh_includes)}, assets: {len(assets)}')

# Run windres
result = subprocess.run(
    ['windres', '-I.', f'-I{base}', rc_file, '-o', obj_file],
    capture_output=True, text=True, cwd=base
)
if result.returncode == 0:
    print(f'Compiled: {obj_file}')
else:
    print(f'windres error: {result.stderr}')
    sys.exit(1)
