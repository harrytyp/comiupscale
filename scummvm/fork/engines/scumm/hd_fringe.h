/* ScummVM - Graphic Adventure Engine
 *
 * COMI HD fork: white fringe removal for AI-upscaled textures.
 *
 * RealESRGAN upscaling produces white/light halos along alpha edges
 * (the model invents bright pixels where the sprite meets transparency).
 * This removes them at load time: a pixel is cleared (alpha=0) only if
 * it is nearly white AND adjacent to a (semi-)transparent pixel
 * (alpha < 32). Passes run iteratively so the soft transition ring is
 * peeled off layer by layer. Pass 0 also clears fully opaque white pixels
 * directly on the edge (hard fringe line); later passes only touch
 * semi-transparent pixels, so opaque interior detail (eyes, shirts,
 * highlights) can never be eroded.
 */

#ifndef SCUMM_HD_FRINGE_H
#define SCUMM_HD_FRINGE_H

#include "common/scummsys.h"
#include "graphics/surface.h"

namespace Scumm {

// Minimum brightness for a pixel to count as white fringe.
#define HD_FRINGE_WHITE_MIN 190
// Neighbor alpha below this counts as "transparent edge".
#define HD_FRINGE_EDGE_ALPHA 32
// Maximum peel passes for the soft transition ring.
#define HD_FRINGE_MAX_PASSES 10

static inline void removeWhiteFringe(Graphics::Surface &surf) {
	if (surf.format.bytesPerPixel != 4 || !surf.getPixels() || surf.w <= 0 || surf.h <= 0)
		return;

	const int w = surf.w;
	const int h = surf.h;
	uint32 *px = (uint32 *)surf.getPixels();
	byte *origAlpha = new byte[w * h];

	int cleared = 0;
	for (int pass = 0; pass < HD_FRINGE_MAX_PASSES; pass++) {
		// Snapshot current alpha: decisions use the state at pass start,
		// so one pass cannot erode deeper than one layer.
		for (int i = 0; i < w * h; i++)
			origAlpha[i] = (px[i] >> 24) & 0xFF;

		int passCleared = 0;
		for (int y = 0; y < h; y++) {
			for (int x = 0; x < w; x++) {
				const int idx = y * w + x;
				const byte a = origAlpha[idx];
				if (a == 0)
					continue;
				// Only pass 0 may clear fully opaque white (hard fringe
				// line). Later passes restrict to semi-transparent pixels
				// so opaque interior content can never be eroded.
				if (pass > 0 && a == 255)
					continue;
				const uint32 p = px[idx];
				const byte r = p & 0xFF;
				const byte g = (p >> 8) & 0xFF;
				const byte b = (p >> 16) & 0xFF;
				if (r < HD_FRINGE_WHITE_MIN || g < HD_FRINGE_WHITE_MIN || b < HD_FRINGE_WHITE_MIN)
					continue;
				// Adjacent (4-neighborhood) to a (semi-)transparent pixel?
				bool edge = false;
				if (x > 0 && origAlpha[idx - 1] < HD_FRINGE_EDGE_ALPHA)
					edge = true;
				else if (x + 1 < w && origAlpha[idx + 1] < HD_FRINGE_EDGE_ALPHA)
					edge = true;
				else if (y > 0 && origAlpha[idx - w] < HD_FRINGE_EDGE_ALPHA)
					edge = true;
				else if (y + 1 < h && origAlpha[idx + w] < HD_FRINGE_EDGE_ALPHA)
					edge = true;
				if (edge) {
					px[idx] &= 0x00FFFFFF; // keep RGB, set alpha = 0
					passCleared++;
				}
			}
		}
		cleared += passCleared;
		if (passCleared == 0)
			break;
	}

	delete[] origAlpha;
	if (cleared)
		debug(2, "HdFringe: removed %d white fringe pixels (%dx%d)", cleared, w, h);
}

} // End of namespace Scumm

#endif
