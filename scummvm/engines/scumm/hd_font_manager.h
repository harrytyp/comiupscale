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

#ifndef SCUMM_HD_FONT_MANAGER_H
#define SCUMM_HD_FONT_MANAGER_H

#include "common/str.h"
#include "graphics/surface.h"

namespace Scumm {

class ScummEngine;

/**
 * Manages HD replacement font glyph sheets for COMI.
 *
 * COMI uses NUT font files (FONT0.NUT through FONT4.NUT).
 * Each font has a chars.png glyph sheet at original resolution (896x896).
 * The HD version is at 3584x3584 (4x upscale).
 *
 * The glyph sheet is a grid of characters. For COMI's 8x16 font:
 *   - 112 columns × 56 rows = 6272 glyphs per sheet (16x16 grid cells)
 *   - Each glyph cell: 8x16 pixels at 1x, 32x64 at 4x
 *
 * This manager loads and caches the HD font sheets and provides
 * per-glyph blitting for the charset renderer.
 */
class HdFontManager {
public:
	HdFontManager(ScummEngine *vm);
	~HdFontManager();

	/** Initialize by loading HD font sheets from hd/fonts/ directory. */
	bool init(const Common::String &hdPath);

	/** Check if an HD font sheet is available for the given font slot (0-4). */
	bool hasFont(int fontSlot) const;

	/**
	 * Blit a single HD character glyph onto a destination surface.
	 * x,y are in HD space (already scaled).
	 * Returns true if the glyph was drawn from HD source.
	 */
	bool drawChar(int fontSlot, int chr, Graphics::Surface &dest, int x, int y);

	/**
	 * Get the dimensions of a glyph in HD space.
	 */
	int getCharWidth(int fontSlot, int chr) const;
	int getCharHeight(int fontSlot, int chr) const;

	/** Returns true if HD font mode is active. */
	bool isEnabled() const { return _enabled; }

	/** Returns the font scale factor (4 for COMI). */
	int getScale() const { return _scale; }

private:
	struct FontSheet {
		Graphics::Surface surface;
		bool loaded;
		int gridCols;   // characters per row
		int gridRows;   // rows per sheet
		int cellW;      // glyph width in pixels (at HD resolution)
		int cellH;      // glyph height in pixels (at HD resolution)
	};

	ScummEngine *_vm;
	bool _enabled;
	int _scale;

	Common::String _hdPath;
	FontSheet _fonts[5]; // FONT0 through FONT4

	/**
	 * Load a single HD font sheet from file.
	 * fontSlot: 0-4
	 * filename example: FONT0.NUT_chars.png
	 */
	bool loadFontSheet(int fontSlot);

	/**
	 * Determine grid and cell sizes for a COMI font slot.
	 * COMI uses fixed 8x16 glyphs for all fonts, though some
	 * may have different layouts. We detect from the file size.
	 */
	void detectFontLayout(int fontSlot, int imgW, int imgH);
};

} // End of namespace Scumm

#endif
