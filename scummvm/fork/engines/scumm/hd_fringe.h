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
#include "common/array.h"
#include "graphics/surface.h"

namespace Scumm {

// Minimum brightness for a pixel to count as white fringe.
#define HD_FRINGE_WHITE_MIN 190
// Neighbor alpha below this counts as "transparent edge".
#define HD_FRINGE_EDGE_ALPHA 32
// Maximum peel passes for the soft transition ring.
#define HD_FRINGE_MAX_PASSES 10

// Ist der Bildpunkt an (x,y) fast weiss (alle drei Kanaele ueber der Schwelle)?
static inline bool hdFringeWeiss(uint32 p) {
	return (p & 0xFF) >= HD_FRINGE_WHITE_MIN &&
	       ((p >> 8) & 0xFF) >= HD_FRINGE_WHITE_MIN &&
	       ((p >> 16) & 0xFF) >= HD_FRINGE_WHITE_MIN;
}

// Hat der Bildpunkt an (x,y) einen 4-Nachbarn mit Alpha unter der Randschwelle?
static inline bool hdFringeHatRand(const uint32 *px, int w, int h, int x, int y) {
	const size_t idx = (size_t)y * w + x;
	if (x > 0 && ((px[idx - 1] >> 24) & 0xFF) < HD_FRINGE_EDGE_ALPHA)
		return true;
	if (x + 1 < w && ((px[idx + 1] >> 24) & 0xFF) < HD_FRINGE_EDGE_ALPHA)
		return true;
	if (y > 0 && ((px[idx - (size_t)w] >> 24) & 0xFF) < HD_FRINGE_EDGE_ALPHA)
		return true;
	if (y + 1 < h && ((px[idx + (size_t)w] >> 24) & 0xFF) < HD_FRINGE_EDGE_ALPHA)
		return true;
	return false;
}

static inline void removeWhiteFringe(Graphics::Surface &surf) {
	if (surf.format.bytesPerPixel != 4 || !surf.getPixels() || surf.w <= 0 || surf.h <= 0)
		return;

	const int w = surf.w;
	const int h = surf.h;
	uint32 *px = (uint32 *)surf.getPixels();

	// Ein Rand kann nur an einem Bildpunkt sitzen, der einen 4-Nachbarn mit
	// Alpha < 32 hat, und ein neuer Rand entsteht nur dort, wo im Durchgang davor ein
	// Bildpunkt freigelegt wurde. Statt je Durchgang das ganze Bild zu lesen (frueher:
	// Alpha-Schnappschuss plus Vollbildschleife, bis zu zehnmal) laeuft deshalb nur der
	// erste Durchgang ueber das Bild, jeder weitere nur ueber die Nachbarschaft der
	// zuletzt freigelegten Punkte. Freigelegt wird gesammelt und am Ende eines
	// Durchgangs angewendet, damit alle Entscheidungen eines Durchgangs denselben Stand
	// sehen - genau wie der frueher benutzte Alpha-Schnappschuss.
	Common::Array<uint32> kandidaten;
	for (int y = 0; y < h; y++) {
		const uint32 *row = px + (size_t)y * w;
		for (int x = 0; x < w; x++) {
			const uint32 p = row[x];
			if (((p >> 24) & 0xFF) == 0)
				continue;
			if (!hdFringeWeiss(p))
				continue;
			if (hdFringeHatRand(px, w, h, x, y))
				kandidaten.push_back((uint32)((size_t)y * w + x));
		}
	}

	int cleared = 0;
	for (int pass = 0; pass < HD_FRINGE_MAX_PASSES && !kandidaten.empty(); pass++) {
		for (uint i = 0; i < kandidaten.size(); i++)
			px[kandidaten[i]] &= 0x00FFFFFF; // keep RGB, set alpha = 0
		cleared += (int)kandidaten.size();
		if (pass + 1 >= HD_FRINGE_MAX_PASSES)
			break;

		// Naechster Durchgang: nur die 4-Nachbarn der eben freigelegten Punkte. Ab
		// Durchgang 1 zaehlen allein halbdurchsichtige Punkte, damit deckende weisse
		// Innenflaechen (Augen, Hemd, Glanzlichter) nie erodiert werden. Doppelte
		// Kandidaten sind harmlos: der Punkt wird beim zweiten Mal als Alpha 0 erkannt
		// und uebersprungen.
		Common::Array<uint32> naechste;
		for (uint i = 0; i < kandidaten.size(); i++) {
			const int idx = (int)kandidaten[i];
			const int x = idx % w;
			const int y = idx / w;
			for (int d = 0; d < 4; d++) {
				const int nx = x + (d == 0 ? -1 : (d == 1 ? 1 : 0));
				const int ny = y + (d == 2 ? -1 : (d == 3 ? 1 : 0));
				if (nx < 0 || nx >= w || ny < 0 || ny >= h)
					continue;
				const size_t nidx = (size_t)ny * w + nx;
				const uint32 p = px[nidx];
				const byte a = (p >> 24) & 0xFF;
				if (a == 0 || a == 255)
					continue;
				if (!hdFringeWeiss(p))
					continue;
				if (!hdFringeHatRand(px, w, h, nx, ny))
					continue;
				naechste.push_back((uint32)nidx);
			}
		}
		kandidaten = naechste;
	}

	if (cleared)
		debug(2, "HdFringe: removed %d white fringe pixels (%dx%d)", cleared, w, h);
}

} // End of namespace Scumm

#endif
