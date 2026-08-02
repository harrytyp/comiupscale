/* ScummVM - Graphic Adventure Engine
 *
 * COMI HD fork: white fringe removal for AI-upscaled textures.
 *
 * RealESRGAN upscaling produces white/light halos along alpha edges
 * (the model invents bright pixels where the sprite meets transparency).
 * This removes them at load time: a pixel is cleared (alpha=0) only if
 * it is nearly white AND directly adjacent to a (semi-)transparent pixel
 * (alpha < 32). This catches both hard white edges and the soft
 * semi-transparent transition ring the upscaler creates. Interior white
 * pixels (eyes, shirts, highlights) have no transparent neighbor and are
 * left untouched.
 *
 * The original alpha channel is snapshotted first, so clearing one pixel
 * cannot cascade into the object interior (no erosion).
 */

#ifndef SCUMM_HD_FRINGE_H
#define SCUMM_HD_FRINGE_H

#include "common/scummsys.h"
#include "graphics/surface.h"

namespace Scumm {

// Minimum brightness for a pixel to count as white fringe.
#define HD_FRINGE_WHITE_MIN 200
// Neighbor alpha below this counts as "transparent edge".
#define HD_FRINGE_EDGE_ALPHA 32

static inline void removeWhiteFringe(Graphics::Surface &surf) {
	if (surf.format.bytesPerPixel != 4 || !surf.getPixels() || surf.w <= 0 || surf.h <= 0)
		return;

	const int w = surf.w;
	const int h = surf.h;
	uint32 *px = (uint32 *)surf.getPixels();

	// Snapshot original alpha so the decision is based on the unmodified
	// image (prevents erosion chains into the object interior).
	byte *origAlpha = new byte[w * h];
	for (int i = 0; i < w * h; i++)
		origAlpha[i] = (px[i] >> 24) & 0xFF;

	int cleared = 0;
	for (int y = 0; y < h; y++) {
		for (int x = 0; x < w; x++) {
			const int idx = y * w + x;
			if (origAlpha[idx] == 0)
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
				cleared++;
			}
		}
	}

	delete[] origAlpha;
	if (cleared)
		debug(2, "HdFringe: removed %d white fringe pixels (%dx%d)", cleared, w, h);
}

} // End of namespace Scumm

#endif
