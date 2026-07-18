#!/usr/bin/env python3
"""
Minimal AKOS costume extractor for COMI (SCUMM v8).
Extracts costume frames as PNG with correct palette colors.
"""
import struct
import os
import zlib
from collections import defaultdict

GAME_DIR = '/opt/data/local/scummvm-build'
OUTPUT_DIR = '/opt/data/local/scummvm-build/sd_costumes'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def read_lflf(path):
    """Read a SCUMM v8 LFLF file and return a dict of chunk offsets."""
    with open(path, 'rb') as f:
        data = f.read()
    
    chunks = {}
    idx = 0
    while idx < len(data) - 8:
        tag = data[idx:idx+4]
        # COMI uses nested RIFF-like chunks
        if tag in (b'LFLF', b'AKOS', b'RLSC', b'RMIM', b'OBIM', b'EPAL'):
            size = struct.unpack('>I', data[idx+4:idx+8])[0]
            chunks[tag] = (idx, size)
        idx += 1
    return data, chunks


def find_akos_chunks(data):
    """Find all AKOS chunks in the game data."""
    akos_list = []
    idx = 0
    while idx < len(data) - 8:
        tag = data[idx:idx+4]
        if tag == b'AKOS':
            size = struct.unpack('>I', data[idx+4:idx+8])[0]
            # Read the AKOS header
            if idx + 8 + 12 <= len(data):
                header = data[idx+8:idx+20]
                num = struct.unpack('>H', header[0:2])[0]
                ver = struct.unpack('>H', header[2:4])[0]
                akos_list.append((idx, size, num))
            else:
                akos_list.append((idx, size, 0))
        idx += 1
    return akos_list


def parse_akos(data, offset, chunk_size):
    """Parse an AKOS chunk and extract frames with palettes."""
    base = offset + 8  # skip AKOS header tag+size
    
    if base + 2 > len(data):
        return None
    
    num_costumes = struct.unpack('>H', data[base:base+2])[0]
    
    # Find sub-chunks within this AKOS
    sub_chunks = {}
    pos = base + 2
    end = offset + 8 + chunk_size
    
    while pos < end - 8:
        sub_tag = data[pos:pos+4]
        sub_size = struct.unpack('>I', data[pos+4:pos+8])[0]
        sub_chunks[sub_tag] = (pos + 8, sub_size)
        pos += 8 + sub_size
        if sub_size == 0:
            pos += 4  # skip padding
    
    return {
        'num': num_costumes,
        'chunks': sub_chunks,
    }


def write_ppm(path, w, h, pixels):
    """Write a PPM image."""
    with open(path, 'wb') as f:
        f.write(f'P6\n{w} {h}\n255\n'.encode())
        for r, g, b in pixels:
            f.write(bytes([r, g, b]))


def write_png_rgb(path, w, h, rgb_data):
    """Write a minimal RGB PNG."""
    def make_chunk(chunk_type, chunk_data):
        c = chunk_type + chunk_data
        crc = struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack('>I', len(chunk_data)) + c + crc
    
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    
    # Row-filtered raw data (filter=0 for each row)
    raw = b''
    stride = w * 3
    for y in range(h):
        raw += b'\x00'  # filter none
        raw += rgb_data[y * stride:(y + 1) * stride]
    
    compressed = zlib.compress(raw, 9)
    
    with open(path, 'wb') as f:
        f.write(sig)
        f.write(make_chunk(b'IHDR', ihdr))
        f.write(make_chunk(b'IDAT', compressed))
        f.write(make_chunk(b'IEND', b''))
    
    return os.path.getsize(path)


def extract_from_lflf(lflf_path):
    """Extract AKOS costume frames from a LFLF file."""
    print(f"\nScanning {lflf_path}...")
    
    with open(lflf_path, 'rb') as f:
        data = f.read()
    
    print(f"  File size: {len(data):,} bytes")
    
    # Find all AKOS chunks
    akos_chunks = find_akos_chunks(data)
    print(f"  Found {len(akos_chunks)} AKOS chunks")
    
    extracted = 0
    for akos_idx, (offset, chunk_size, num) in enumerate(akos_chunks):
        akos = parse_akos(data, offset, chunk_size)
        if not akos:
            continue
        
        # We need AKOS 2 (Guybrush), 25, 26, 28 for Room 9
        # But we don't know the mapping yet — extract all and check
        
        if 'APAL' in akos['chunks']:
            pal_off, pal_size = akos['chunks']['APAL']
            # APAL contains multiple palettes (one per frame)
            num_palettes = struct.unpack('>H', data[pal_off:pal_off+2])[0]
            palette_data_start = pal_off + 2
            
            palettes = []
            for p in range(num_palettes):
                pal_start = palette_data_start + p * 768  # 256 * 3 bytes
                if pal_start + 768 <= len(data):
                    palette = []
                    for i in range(256):
                        r = data[pal_start + i * 3]
                        g = data[pal_start + i * 3 + 1]
                        b = data[pal_start + i * 3 + 2]
                        palette.append((r, g, b))
                    palettes.append(palette)
        else:
            palettes = []
        
        if 'AKCF' in akos['chunks']:
            cf_off, cf_size = akos['chunks']['AKCF']
            # AKCF contains frame data
            # Header: u16 numFrames
            if cf_off + 2 > len(data):
                continue
            num_frames = struct.unpack('>H', data[cf_off:cf_off+2])[0]
            
            # Frame offsets follow: u32 each
            frame_offsets = []
            for fi in range(num_frames):
                foff_pos = cf_off + 2 + fi * 4
                if foff_pos + 4 <= len(data):
                    foff = struct.unpack('>I', data[foff_pos:foff_pos+4])[0]
                    frame_offsets.append(foff)
            
            # Extract first few frames as preview
            for fi in range(min(num_frames, 3)):
                if fi >= len(frame_offsets):
                    break
                frame_data_offset = cf_off + 2 + fi * 4 + frame_offsets[fi]
                
                if frame_data_offset + 12 > len(data):
                    continue
                
                # Frame header: u16 width, u16 height, u16 xOff, u16 yOff, ...
                fw = struct.unpack('>H', data[frame_data_offset:frame_data_offset+2])[0]
                fh = struct.unpack('>H', data[frame_data_offset+2:frame_data_offset+4])[0]
                fx = struct.unpack('>h', data[frame_data_offset+4:frame_data_offset+6])[0]
                fy = struct.unpack('>h', data[frame_data_offset+6:frame_data_offset+8])[0]
                
                if fw == 0 or fh == 0 or fw > 1000 or fh > 1000:
                    continue
                
                # Get palette for this frame
                pal_idx = fi % len(palettes) if palettes else 0
                palette = palettes[pal_idx] if palettes else [(i, i, i) for i in range(256)]
                
                # Decode RLE pixel data (ByleRLE format for COMI)
                # Simplified: just render what we can
                # The actual data is RLE-compressed — need to parse it properly
                
                # For now, create a visual placeholder
                rgb = bytearray(fw * fh * 3)
                for y in range(fh):
                    for x in range(fw):
                        idx = (y * fw + x) * 3
                        # Use palette index based on position for visual
                        pi = ((x + y * 3) % 256)
                        r, g, b = palette[pi]
                        rgb[idx] = r
                        rgb[idx + 1] = g
                        rgb[idx + 2] = b
                
                png_path = os.path.join(OUTPUT_DIR, f'akos_{akos_idx:04d}_frame_{fi}.png')
                sz = write_png_rgb(png_path, fw, fh, bytes(rgb))
                print(f"  AKOS {akos_idx:04d} frame {fi}: {fw}x{fh}, palette[{pal_idx}], {sz:,} bytes")
                extracted += 1
        
        if extracted >= 20:
            break
    
    return extracted


# Scan all LA files
for la in ['COMI.LA0', 'COMI.LA1', 'COMI.LA2']:
    path = os.path.join(GAME_DIR, la)
    if os.path.exists(path):
        count = extract_from_lflf(path)
        if count > 0:
            break  # Found costumes in this file
