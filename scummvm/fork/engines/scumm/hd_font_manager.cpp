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
#include "common/debug.h"
#include "common/fs.h"
#include "image/png.h"

namespace Scumm {

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
	// COMI standard: 8x16 pixel glyphs at 1x → 32x64 at 4x
	// 896x896 source = 112 cols x 56 rows
	// 3584x3584 HD = same grid

	int baseW = imgW / _scale;
	int baseH = imgH / _scale;

	// Try common COMI font sizes
	int tryCellW[] = {8, 16, 12, 10};
	int tryCellH[] = {16, 16, 12, 10};

	for (int i = 0; i < 4; i++) {
		if (baseW % tryCellW[i] == 0 && baseH % tryCellH[i] == 0) {
			_fonts[fontSlot].gridCols = baseW / tryCellW[i];
			_fonts[fontSlot].gridRows = baseH / tryCellH[i];
			_fonts[fontSlot].cellW = tryCellW[i] * _scale;
			_fonts[fontSlot].cellH = tryCellH[i] * _scale;
			debug(2, "HdFontManager: Font %d grid %dx%d cells of %dx%d (HD %dx%d)",
				  fontSlot, _fonts[fontSlot].gridCols, _fonts[fontSlot].gridRows,
				  _fonts[fontSlot].cellW, _fonts[fontSlot].cellH, imgW, imgH);
			return;
		}
	}

	// Fallback: assume 8x16
	_fonts[fontSlot].gridCols = baseW / 8;
	_fonts[fontSlot].gridRows = baseH / 16;
	_fonts[fontSlot].cellW = 8 * _scale;
	_fonts[fontSlot].cellH = 16 * _scale;

	debug(2, "HdFontManager: Font %d fallback grid %dx%d (8x16 base)", fontSlot,
		  _fonts[fontSlot].gridCols, _fonts[fontSlot].gridRows);
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
		debug(2, "HdFontManager: Font sheet not found: %s", path.c_str());
		return false;
	}

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

bool HdFontManager::drawChar(int fontSlot, int chr, Graphics::Surface &dest, int x, int y) {
	if (!_enabled || fontSlot < 0 || fontSlot > 4)
		return false;
	if (!_fonts[fontSlot].loaded)
		return false;

	const FontSheet &fs = _fonts[fontSlot];
	if (!fs.surface.getPixels())
		return false;

	int col = chr % fs.gridCols;
	int row = chr / fs.gridCols;

	if (row >= fs.gridRows)
		return false;

	// Source region in HD font sheet
	int srcX = col * fs.cellW;
	int srcY = row * fs.cellH;

	// Clip to destination bounds
	int drawW = MIN(fs.cellW, dest.w - x);
	int drawH = MIN(fs.cellH, dest.h - y);
	if (drawW <= 0 || drawH <= 0)
		return false;

	// Blit pixel by pixel from source to dest
	const Graphics::Surface &src = fs.surface;
	for (int sy = 0; sy < drawH; sy++) {
		for (int sx = 0; sx < drawW; sx++) {
			int px = x + sx;
			int py = y + sy;
			if (px < 0 || px >= dest.w || py < 0 || py >= dest.h)
				continue;

			// Source pixel
			byte r, g, b, a;
			if (src.format.bytesPerPixel == 4) {
				// RGBA source
				uint32 p = *(uint32 *)src.getBasePtr(srcX + sx, srcY + sy);
				r = (p >> 0) & 0xFF;
				g = (p >> 8) & 0xFF;
				b = (p >> 16) & 0xFF;
				a = (p >> 24) & 0xFF;
			} else if (src.format.bytesPerPixel == 3) {
				// RGB source — opaque
				const byte *sPix = (const byte *)src.getBasePtr(srcX + sx, srcY + sy);
				r = sPix[0];
				g = sPix[1];
				b = sPix[2];
				a = 0xFF;
			} else {
				continue;
			}

			// Skip fully transparent pixels
			if (a == 0)
				continue;

			// Write to destination (ARGB8888 expected by ScummVM)
			uint32 *dPix = (uint32 *)dest.getBasePtr(px, py);
			if (dest.format.bytesPerPixel == 4) {
				uint32 d = *dPix;
				byte dr = (d >> 0) & 0xFF;
				byte dg = (d >> 8) & 0xFF;
				byte db = (d >> 16) & 0xFF;
				byte da_ = (d >> 24) & 0xFF;

				if (a == 0xFF) {
					// Opaque: overwrite
					*dPix = (0xFF << 24) | (b << 16) | (g << 8) | r;
				} else {
					// Alpha blend
					uint inv = 255 - a;
					byte out_r = (r * a + dr * inv) / 255;
					byte out_g = (g * a + dg * inv) / 255;
					byte out_b = (b * a + db * inv) / 255;
					byte out_a = 0xFF;
					*dPix = (out_a << 24) | (out_b << 16) | (out_g << 8) | out_r;
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
