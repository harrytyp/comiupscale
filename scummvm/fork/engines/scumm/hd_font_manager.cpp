/* ScummVM - Graphic Adventure Engine
 *
 * ScummVM is the legal property of its developers, whose names
 * are too numerous to list here. Please refer to the COPYRIGHT
 * file distributed with this source distribution.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#include "scumm/hd_font_manager.h"
#include "scumm/scumm.h"
#include "common/config-manager.h"
#include "common/debug.h"
#include "common/fs.h"
#include "image/png.h"

namespace Scumm {

// ── Tracing helper ────────────────────────────────────
#define HD_TRACE(path, exists) \
	do { \
		if (ConfMan.getBool("hd_trace", "comi")) \
			debug(0, "hd_trace: %s %s", (exists) ? "OK" : "MISS", (path).c_str()); \
	} while (0)

HdFontManager::HdFontManager(ScummEngine *vm)
	: _vm(vm), _enabled(false), _scale(4) {
	for (int i = 0; i < 5; i++) {
		_fonts[i].loaded = false;
		_fonts[i].surface.setPixels(nullptr);
	}
}

HdFontManager::~HdFontManager() {
	for (int i = 0; i < 5; i++) {
		if (_fonts[i].loaded && _fonts[i].surface.getPixels()) {
			_fonts[i].surface.free();
		}
	}
}

void HdFontManager::detectFontLayout(int fontSlot, int imgW, int imgH) {
	// COMI HD font sheets: 3584x3584 at 4x = 896x896 base.
	// Verified layout: 16x16 grid of 256 cells (ASCII order), each cell
	// 224x224 HD = 56x56 base pixels (896/16 = 56). Each cell has a black
	// glyph box on a blue/magenta checkerboard background.
	// cellW = 3584/16 = 224 HD.

	int baseW = imgW / _scale;
	int baseH = imgH / _scale;

	// The HD sheets are 16x16 cells regardless of base pixel size.
	_fonts[fontSlot].gridCols = 16;
	_fonts[fontSlot].gridRows = 16;
	_fonts[fontSlot].cellW = imgW / 16;
	_fonts[fontSlot].cellH = imgH / 16;

	debug(2, "HdFontManager: Font %d grid 16x16 cells of %dx%d HD (%dx%d base)",
		  fontSlot, _fonts[fontSlot].cellW, _fonts[fontSlot].cellH, baseW, baseH);
}

bool HdFontManager::loadFontSheet(int fontSlot) {
	if (fontSlot < 0 || fontSlot > 4)
		return false;

	if (_fonts[fontSlot].loaded)
		return true;

	Common::String path = _hdPath;
	path += Common::String::format("/fonts/FONT%d.NUT_chars.png", fontSlot);

	Common::FSNode fileNode(Common::Path(path, Common::Path::kNativeSeparator));
	if (!fileNode.exists()) {
		HD_TRACE(path, false);
		debug(2, "HdFontManager: Font sheet not found: %s", path.c_str());
		return false;
	}
	HD_TRACE(path, true);

	Common::SeekableReadStream *stream = fileNode.createReadStream();
	if (!stream) {
		debug(2, "HdFontManager: Failed to open %s", path.c_str());
		return false;
	}

	Image::PNGDecoder png;
	if (!png.loadStream(*stream)) {
		debug(2, "HdFontManager: Failed to decode PNG: %s", path.c_str());
		delete stream;
		return false;
	}
	delete stream;

	const Graphics::Surface *pngSurf = png.getSurface();
	if (!pngSurf) {
		debug(2, "HdFontManager: No surface from PNG decoder");
		return false;
	}

	_fonts[fontSlot].surface.copyFrom(*pngSurf);
	_fonts[fontSlot].loaded = true;
	png.destroy();

	detectFontLayout(fontSlot, _fonts[fontSlot].surface.w, _fonts[fontSlot].surface.h);

	debug(1, "HdFontManager: Loaded HD font %d: %dx%d, grid %dx%d cells of %dx%d",
		  fontSlot,
		  _fonts[fontSlot].surface.w, _fonts[fontSlot].surface.h,
		  _fonts[fontSlot].gridCols, _fonts[fontSlot].gridRows,
		  _fonts[fontSlot].cellW, _fonts[fontSlot].cellH);

	return true;
}

bool HdFontManager::init(const Common::String &hdPath) {
	_hdPath = hdPath;
	if (_hdPath.empty())
		return false;

	if (_hdPath.lastChar() == '/' || _hdPath.lastChar() == '\\')
		_hdPath.deleteLastChar();

	// Try to load at least one font sheet
	int loadedCount = 0;
	for (int i = 0; i < 5; i++) {
		if (loadFontSheet(i))
			loadedCount++;
	}

	_enabled = (loadedCount > 0);
	debug(1, "HdFontManager: Loaded %d/5 HD font sheets from %s/fonts/",
		  loadedCount, _hdPath.c_str());

	return _enabled;
}

bool HdFontManager::hasFont(int fontSlot) const {
	if (!_enabled || fontSlot < 0 || fontSlot > 4)
		return false;
	return _fonts[fontSlot].loaded;
}

bool HdFontManager::drawChar(int fontSlot, int chr, Graphics::Surface &dest, int x, int y, byte tR, byte tG, byte tB) {
	if (!_enabled || fontSlot < 0 || fontSlot > 4)
		return false;
	if (!_fonts[fontSlot].loaded)
		return false;

	const FontSheet &fs = _fonts[fontSlot];
	if (!fs.surface.getPixels())
		return false;

	int colIdx = chr % fs.gridCols;
	int row = chr / fs.gridCols;

	if (row >= fs.gridRows)
		return false;

	// Text color for tinting (computed in gfx.cpp Step 2.7, where the
	// engine palette is accessible). The HD sheets only provide the
	// glyph silhouette (black); we tint it with the game color so the
	// text matches the original look (yellow/white/etc).

	// The font sheets are pre-upscaled RGBA (3584x3584, 16x16 grid,
	// 224x224 cells). The glyph is LEFT-ALIGNED in each cell with the
	// actual glyph strokes on transparent background. Draw the glyph
	// bounding box 1:1 — NO rescaling, NO nearest-neighbour, NO
	// post-processing. The sheets are already at final HD resolution.
	int srcX = colIdx * fs.cellW;
	int srcY = row * fs.cellH;
	const int cellW = fs.cellW;
	const int cellH = fs.cellH;

	// Find the glyph bounding box (pixels with alpha > 128 — the LANCZOS
	// alpha upscale leaves faint alpha noise across the whole cell; only
	// the solid glyph pixels (alpha > 128) define the real bounding box)
	const Graphics::Surface &src = fs.surface;
	int minX = cellW, minY = cellH, maxX = -1, maxY = -1;
	for (int sy = 0; sy < cellH; sy++) {
		for (int sx = 0; sx < cellW; sx++) {
			uint32 p = *(uint32 *)src.getBasePtr(srcX + sx, srcY + sy);
			byte pa = (p >> src.format.aShift) & 0xFF;
			if (pa > 128) {
				if (sx < minX) minX = sx;
				if (sx > maxX) maxX = sx;
				if (sy < minY) minY = sy;
				if (sy > maxY) maxY = sy;
			}
		}
	}
	if (maxX < 0)
		return false;   // empty cell (e.g. space)

	int glyphW = maxX - minX + 1;
	// Draw from the cell TOP (y) down to the bottom-most ink pixel. The
	// pipeline preserves the frame's transparent top padding, so the ink
	// sits at the correct baseline position — no vertical offset needed.
	int glyphH = maxY + 1;

	// Clip to destination bounds
	int drawW = MIN(glyphW, dest.w - x);
	int drawH = MIN(glyphH, dest.h - y);
	if (drawW <= 0 || drawH <= 0)
		return false;

	// 1:1 blit from the glyph bbox to the destination
	for (int sy = 0; sy < drawH; sy++) {
		for (int sx = 0; sx < drawW; sx++) {
			int px = x + sx;
			int py = y + sy;
			if (px < 0 || px >= dest.w || py < 0 || py >= dest.h)
				continue;

			// Source pixel — 1:1 from the cell top (x offset from bbox)
			byte r, g, b, a;
			if (src.format.bytesPerPixel == 4) {
				uint32 p = *(uint32 *)src.getBasePtr(srcX + minX + sx, srcY + sy);
				r = (p >> src.format.rShift) & 0xFF;
				g = (p >> src.format.gShift) & 0xFF;
				b = (p >> src.format.bShift) & 0xFF;
				a = (p >> src.format.aShift) & 0xFF;
			} else if (src.format.bytesPerPixel == 3) {
				const byte *sPix = (const byte *)src.getBasePtr(srcX + minX + sx, srcY + sy);
				r = sPix[0];
				g = sPix[1];
				b = sPix[2];
				a = 0xFF;
			} else {
				continue;
			}

			// Skip transparent AND faint alpha noise (LANCZOS upscale
			// leaves weak alpha over the cell; only solid glyph pixels
			// are drawn)
			if (a < 128)
				continue;

			// Tint the FILL (white pixels) with the game text color; keep
			// the OUTLINE (black pixels) black. The pipeline encodes the
			// NUT glyphs as: outline=black, fill=white, transparent=alpha.
			// This matches the 8-bit renderer (Index 1 -> col, Index 0 -> 0).
			int lum = (r + g + b) / 3;
			if (lum < 60) {
				// Outline pixel: keep black
				r = 0;
				g = 0;
				b = 0;
				a = 255;
			} else {
				// Fill pixel: tint with text color
				r = tR;
				g = tG;
				b = tB;
				a = 255;
			}

			// Write to destination (use dest channel shifts)
			uint32 *dPix = (uint32 *)dest.getBasePtr(px, py);
			if (dest.format.bytesPerPixel == 4) {
				uint32 d = *dPix;
				byte dr = (d >> dest.format.rShift) & 0xFF;
				byte dg = (d >> dest.format.gShift) & 0xFF;
				byte db = (d >> dest.format.bShift) & 0xFF;

				if (a == 0xFF) {
					*dPix = (0xFF << dest.format.aShift)
						  | (r << dest.format.rShift)
						  | (g << dest.format.gShift)
						  | (b << dest.format.bShift);
				} else {
					uint inv = 255 - a;
					byte out_r = (r * a + dr * inv) / 255;
					byte out_g = (g * a + dg * inv) / 255;
					byte out_b = (b * a + db * inv) / 255;
					*dPix = (0xFF << dest.format.aShift)
						  | (out_r << dest.format.rShift)
						  | (out_g << dest.format.gShift)
						  | (out_b << dest.format.bShift);
				}
			}
		}
	}

	return true;
}

int HdFontManager::getCharWidth(int fontSlot, int chr) const {
	if (!_enabled || fontSlot < 0 || fontSlot > 4 || !_fonts[fontSlot].loaded)
		return 0;
	return _fonts[fontSlot].cellW;
}

int HdFontManager::getCharHeight(int fontSlot, int chr) const {
	if (!_enabled || fontSlot < 0 || fontSlot > 4 || !_fonts[fontSlot].loaded)
		return 0;
	return _fonts[fontSlot].cellH;
}

} // End of namespace Scumm
