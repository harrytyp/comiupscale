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

#define FORBIDDEN_SYMBOL_ALLOW_ALL

#include "scumm/hd_batch_decode.h"
#include "scumm/hd_asset_manager.h"
#include "scumm/hd_costume_manager.h"
#include "scumm/hd_fringe.h"
#include "scumm/scumm.h"
#include "common/config-manager.h"
#include "common/debug.h"
#include "common/fs.h"
#include "image/png.h"

#include <chrono>

namespace Scumm {

// ── Tracing helper ────────────────────────────────────
#define HD_TRACE(path, exists) \
	do { \
		if (ConfMan.getBool("hd_trace", "comi")) \
			warning("hd_trace: %s %s", (exists) ? "OK" : "MISS", (path).c_str()); \
	} while (0)

HdCostumeManager::HdCostumeManager(ScummEngine *vm)
	: _vm(vm), _enabled(false), _lruCounter(0), _asyncMutex(SDL_CreateMutex()),
	  _asyncThread(nullptr), _asyncBusy(false) {
}

HdCostumeManager::~HdCostumeManager() {
	if (_asyncThread) {
		SDL_WaitThread(_asyncThread, nullptr);
		_asyncThread = nullptr;
	}
	for (uint i = 0; i < _asyncDone.size(); i++)
		_asyncDone[i].surface.free();
	_asyncDone.clear();
	if (_asyncMutex) {
		SDL_DestroyMutex(_asyncMutex);
		_asyncMutex = nullptr;
	}
	for (Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash>::iterator it = _textureCache.begin();
		 it != _textureCache.end(); ++it) {
		it->_value.surface.free();
	}
	_textureCache.clear();
	_availableCostumes.clear();
}

Common::String HdCostumeManager::buildCostumePath(int akosId, int akosSub, int frame) const {
	Common::String path = _hdPath;
	// Parameters: akosId=AKOS number, akosSub=LFLF owner
	// Filename format: LFLF_XXXX_AKOS_XXXX_aframe_X.png → LFLF_{lflf}_AKOS_{akos}_{frame}.png
	path += Common::String::format("/costumes/LFLF_%04d_AKOS_%04d_aframe_%d.png", akosSub, akosId, frame);
	return path;
}

// Zaehler fuer die Perf-Messung (Backlog 11): wie oft ein Kostuembild aus dem
// Zwischenspeicher kommt und wie oft wirklich dekodiert wird. Nur Ausgabe, kein Verhalten.
static int s_kostuemTreffer = 0;
static int s_kostuemDekode = 0;

// Aufteilung des Dekodepfads je Cel (Backlog 11, Schritt 10): die Summe "laden" aus gfx.cpp
// sagt nur, DASS ein Cel 45 ms kostet. Diese Posten sagen, welcher Teil davon der PNG-Dekode
// ist und welcher die Nacharbeit (Loecher fuellen, Zeilenbereiche, zwei Kopien).
static uint64 s_usPng = 0, s_usFill = 0, s_usCopy = 0, s_usDest = 0, s_usPrune = 0;
static uint64 s_usDekode = 0, s_usKonv = 0, s_usFringe = 0;
static uint64 s_pngPix = 0;

static inline uint64 hdCmUsNow() {
	return (uint64)std::chrono::duration_cast<std::chrono::microseconds>(
	       std::chrono::steady_clock::now().time_since_epoch()).count();
}

void hdCostumeLoadDetail(uint64 &pngUs, uint64 &fillUs, uint64 &copyUs,
                         uint64 &destUs, uint64 &pruneUs, uint64 &pixels,
                         uint64 &decodeUs, uint64 &convUs, uint64 &fringeUs) {
	pngUs = s_usPng;
	fillUs = s_usFill;
	copyUs = s_usCopy;
	destUs = s_usDest;
	pruneUs = s_usPrune;
	pixels = s_pngPix;
	decodeUs = s_usDekode;
	convUs = s_usKonv;
	fringeUs = s_usFringe;
}

// Aufteilung der Posten, die hdCelLoadImage selbst misst. Wird nur gefuellt, wenn der
// Aufrufer eine Struktur uebergibt (Hauptpfad); im Vorlade-Thread bleibt sie nullptr,
// damit die globalen Zaehler nicht aus vier Threads gleichzeitig beschrieben werden.
struct HdCelLoadDetail {
	uint64 dekode, konv, fringe;
};

// Bild laden und aufbereiten: PNG-Dekode, Umwandlung in RGBA8888, Randfarben-Heuristik,
// Fransen. Reine Funktion auf einer lokalen Flaeche - dafuer im Vorlade-Thread benutzbar.
static bool hdCelLoadImage(const Common::String &path, Graphics::Surface &surf, HdCelLoadDetail *detail) {
	Common::FSNode fileNode(Common::Path(hdNativePath(path), Common::Path::kNativeSeparator));
	if (!fileNode.exists()) {
		if (detail)
			HD_TRACE(path, false);
		return false;
	}
	if (detail)
		HD_TRACE(path, true);

	Common::SeekableReadStream *stream = fileNode.createReadStream();
	if (!stream) {
		debug(2, "HdCostumeManager: Failed to open %s", path.c_str());
		return false;
	}

	Image::PNGDecoder png;
	const uint64 tDek = hdCmUsNow();
	if (!png.loadStream(*stream)) {
		debug(2, "HdCostumeManager: Failed to decode PNG: %s", path.c_str());
		delete stream;
		return false;
	}
	if (detail)
		detail->dekode += hdCmUsNow() - tDek;
	delete stream;

	const Graphics::Surface *pngSurf = png.getSurface();
	if (!pngSurf) {
		debug(2, "HdCostumeManager: No surface from PNG decoder");
		return false;
	}

	Graphics::PixelFormat rgbaFmt(4, 8, 8, 8, 8, 0, 8, 16, 24);
	surf.create(pngSurf->w, pngSurf->h, rgbaFmt);

	// Convert PNG surface to RGBA, preserving alpha when available
	// PNGs generated by extract_costumes_fixed.py have proper alpha channel
	// (fill pixels = transparent). The border-color heuristic below is only
	// a fallback for PNGs without alpha (3-byte RGB).
	// Formatzeile nur im Hauptpfad: ein static bool aus vier Threads waere ein Datenrennen.
	if (detail) {
		static bool s_fmtGemeldet = false;
		if (!s_fmtGemeldet) {
			s_fmtGemeldet = true;
			::warning("hdperf: cel-png quelle bpp=%d a=%d r=%d g=%d b=%d (Verschiebung, 0=fehlt)",
		          pngSurf->format.bytesPerPixel, pngSurf->format.aShift, pngSurf->format.rShift,
		          pngSurf->format.gShift, pngSurf->format.bShift);
		}
	}
	const uint64 tKonv = hdCmUsNow();
	const Graphics::PixelFormat &qf = pngSurf->format;
	const bool gleichesFormat = qf.bytesPerPixel == 4 && qf.aShift == 24 && qf.rShift == 0 &&
	                            qf.gShift == 8 && qf.bShift == 16 && qf.aLoss == 0 &&
	                            qf.rLoss == 0 && qf.gLoss == 0 && qf.bLoss == 0;
	if (gleichesFormat) {
		// Die Cel-PNGs kommen bereits als RGBA8888 in genau der Zielanordnung (gemessen:
		// bpp=4 a=24 r=0 g=8 b=16). Zeilenweise kopieren statt jedes Pixel durch
		// colorToARGB und ARGBToColor zu schicken - dieselben Bytes, ein Bruchteil der Zeit.
		for (int y = 0; y < pngSurf->h; y++)
			memcpy(surf.getBasePtr(0, y), pngSurf->getBasePtr(0, y), (size_t)pngSurf->w * 4);
	} else {
		for (int y = 0; y < pngSurf->h; y++) {
			const byte *src = (const byte *)pngSurf->getBasePtr(0, y);
			uint32 *dst = (uint32 *)surf.getBasePtr(0, y);
			for (int x = 0; x < pngSurf->w; x++) {
				uint32 pixel = *(const uint32 *)(src + x * pngSurf->format.bytesPerPixel);
				uint8 r, g, b, a;
				pngSurf->format.colorToARGB(pixel, a, r, g, b);
				dst[x] = rgbaFmt.ARGBToColor(a, r, g, b);
			}
		}
	}
	if (detail)
		detail->konv += hdCmUsNow() - tKonv;
				// Border-color heuristic: only for PNGs WITHOUT alpha channel
	// (PNGs with alpha already have correct transparency baked in)
	if (pngSurf->format.bytesPerPixel < 4) {
		Common::HashMap<uint32, int> borderColors;
		int sw = pngSurf->w;
		int sh = pngSurf->h;
		const byte *srcData = (const byte *)pngSurf->getPixels();
		int srcPitch = pngSurf->pitch;

		// Top row
		for (int x = 0; x < sw; x++) {
			int off = x * pngSurf->format.bytesPerPixel;
			uint32 key = srcData[off] | (srcData[off+1] << 8) | (srcData[off+2] << 16);
			borderColors[key]++;
		}
		// Bottom row
		for (int x = 0; x < sw; x++) {
			int off = (sh - 1) * srcPitch + x * pngSurf->format.bytesPerPixel;
			uint32 key = srcData[off] | (srcData[off+1] << 8) | (srcData[off+2] << 16);
			borderColors[key]++;
		}
		// Left column
		for (int y = 0; y < sh; y++) {
			int off = y * srcPitch;
			uint32 key = srcData[off] | (srcData[off+1] << 8) | (srcData[off+2] << 16);
			borderColors[key]++;
		}
		// Right column
		for (int y = 0; y < sh; y++) {
			int off = y * srcPitch + (sw - 1) * pngSurf->format.bytesPerPixel;
			uint32 key = srcData[off] | (srcData[off+1] << 8) | (srcData[off+2] << 16);
			borderColors[key]++;
		}

		// Find most common border color = background
		uint32 bgKey = 0;
		int bgCount = 0;
		for (Common::HashMap<uint32, int>::iterator it = borderColors.begin();
			 it != borderColors.end(); ++it) {
			if (it->_value > bgCount) {
				bgCount = it->_value;
				bgKey = it->_key;
			}
		}
		byte bgR = bgKey & 0xFF;
		byte bgG = (bgKey >> 8) & 0xFF;
		byte bgB = (bgKey >> 16) & 0xFF;

		// Set alpha=0 for all pixels matching background color
		int transparentPixels = 0;
		for (int y = 0; y < surf.h; y++) {
			uint32 *row = (uint32 *)surf.getBasePtr(0, y);
			for (int x = 0; x < surf.w; x++) {
				uint32 pix = row[x];
				byte r = pix & 0xFF;
				byte g = (pix >> 8) & 0xFF;
				byte b = (pix >> 16) & 0xFF;
				if (r == bgR && g == bgG && b == bgB) {
					row[x] = pix & 0x00FFFFFF; // set alpha=0
					transparentPixels++;
				}
			}
		}

		if (ConfMan.getBool("hd_trace", "comi")) {
			int sw2 = surf.w;
			int sh2 = surf.h;
			warning("hd_trace: loadPNG %dx%d bg=(%d,%d,%d) transparent=%d/%d",
				sw2, sh2, bgR, bgG, bgB, transparentPixels, sw2 * sh2);
		}
	}

	// Remove white fringe halos from AI upscaling (alpha-edge artifacts).
	const uint64 tFringe = hdCmUsNow();
	removeWhiteFringe(surf);
	if (detail)
		detail->fringe += hdCmUsNow() - tFringe;

	png.destroy();
	return true;
}

// Hauptpfad: wie bisher, mit den globalen Postenzaehlern der Perf-Messung.
bool HdCostumeManager::loadPNG(const Common::String &path, Graphics::Surface &surf) {
	HdCelLoadDetail d = {0, 0, 0};
	const bool ok = hdCelLoadImage(path, surf, &d);
	s_usDekode += d.dekode;
	s_usKonv += d.konv;
	s_usFringe += d.fringe;
	return ok;
}

void HdCostumeManager::hdCostumeStats(int &treffer, int &dekode) {
	treffer = s_kostuemTreffer;
	dekode = s_kostuemDekode;
}

bool HdCostumeManager::init(const Common::String &hdPath) {
	_hdPath = hdPath;
	if (_hdPath.empty())
		return false;

	// Trim trailing separator
	if (_hdPath.lastChar() == '/' || _hdPath.lastChar() == '\\')
		_hdPath.deleteLastChar();

	Common::String costumesDir = _hdPath + "/costumes";
	Common::FSNode dirNode(Common::Path(hdNativePath(costumesDir), Common::Path::kNativeSeparator));
	if (!dirNode.exists() || !dirNode.isDirectory()) {
		debug(1, "HdCostumeManager: costumes directory not found at %s, HD costumes disabled", costumesDir.c_str());
		_enabled = false;
		return false;
	}

	// Scan for available costume PNGs
	Common::FSList files;
	if (!dirNode.getChildren(files, Common::FSNode::kListFilesOnly)) {
		_enabled = false;
		return false;
	}

	int count = 0;
	for (Common::FSList::iterator it = files.begin(); it != files.end(); ++it) {
		Common::String name = it->getName();
		// Pattern: LFLF_{akos:04d}_AKOS_{sub:04d}_aframe_{frame}.png
		if (!name.hasPrefixIgnoreCase("LFLF_") || !name.hasSuffixIgnoreCase(".png"))
			continue;

		int lflfOwner = 0, akosNumber = 0, frame = 0;
		// Filename: LFLF_XXXX_AKOS_XXXX_aframe_XXXXX.png
		//   LFLF_0087_AKOS_0439_aframe_0.png → lflfOwner=87, akosNumber=439, frame=0
		if (sscanf(name.c_str(), "LFLF_%d_AKOS_%d_aframe_%d", &lflfOwner, &akosNumber, &frame) >= 3) {
			CostumeKey key;
			key.akosId = akosNumber;  // AKOS resource ID (0439) is the primary key
			key.akosSub = lflfOwner;  // LFLF owner (0087) is the sub-group
			key.frame = frame;
			_availableCostumes[key] = true;
			count++;

			// Build per-AKOS sub list (akosId is the AKOS resource number)
			if (!_akosSubs.contains(akosNumber)) {
				_akosSubs[akosNumber] = Common::List<int>();
			}
			Common::List<int> &subs = _akosSubs[akosNumber];
			bool found = false;
			for (Common::List<int>::iterator si = subs.begin(); si != subs.end(); ++si) {
				if (*si == lflfOwner) { found = true; break; }
			}
			if (!found)
				subs.push_back(lflfOwner);
		}
	}

	_enabled = (count > 0);
	debug(1, "HdCostumeManager: Registered %d HD costume frames from %s", count, costumesDir.c_str());
	if (_enabled)
		warning("hd_trace: HdCostumeManager: %d HD costume frames available", count);
	return _enabled;
}

bool HdCostumeManager::hasCostumeId(int akosId) const {
	if (!_enabled)
		return false;
	return _akosSubs.find(akosId) != _akosSubs.end();
}

bool HdCostumeManager::hasCostume(int akosId, int frame) const {
	if (!_enabled)
		return false;

	// Find the available subs for this AKOS
	typename Common::HashMap<int, Common::List<int> >::const_iterator subsIt = _akosSubs.find(akosId);
	if (subsIt == _akosSubs.end())
		return false;

	for (Common::List<int>::const_iterator si = subsIt->_value.begin(); si != subsIt->_value.end(); ++si) {
		// Try direct frame lookup first, then modulo-wrap around available frames
		CostumeKey key;
		key.akosId = akosId;
		key.akosSub = *si;
		key.frame = frame;
		if (_availableCostumes.contains(key)) {
			HD_TRACE(buildCostumePath(akosId, *si, frame), true);
			return true;
		}
		// Not found — find total frames for this AKOS+sub and wrap via modulo
		int maxFrame = -1;
		for (Common::HashMap<CostumeKey, bool, CostumeKeyHash>::const_iterator it = _availableCostumes.begin();
		     it != _availableCostumes.end(); ++it) {
			if (it->_key.akosId == akosId && it->_key.akosSub == *si)
				maxFrame = MAX(maxFrame, it->_key.frame);
		}
		if (maxFrame >= 0) {
			int wrapped = frame % (maxFrame + 1);
			key.frame = wrapped;
			if (_availableCostumes.contains(key)) {
				Common::String p = buildCostumePath(akosId, *si, wrapped);
				HD_TRACE(p, true);
				warning("hd_trace: costume %04d frame %d → wrapped %d", akosId, frame, wrapped);
				return true;
			}
		}
	}
	// Diagnose: welches Kostüm/Cel in HD fehlt. Ohne diese Zeile war nur bekannt, DASS
	// eine Figur in 8 Bit gezeichnet wird (Raum 86: 8,65 Prozent), nicht welche.
	{
		FILE *cf = fopen("/opt/data/projects/comi-hd/work/dumps/hd_costume_miss.log", "a");
		if (cf) {
			fprintf(cf, "MISS akos=%d frame=%d subs=%d\n", akosId, frame,
			        (int)(subsIt->_value.size()));
			fclose(cf);
		}
	}
	return false;
}

int HdCostumeManager::preloadCostumeRange(int akosId, int from, int to) {
	// Der Satz geht durch denselben Pfad wie ein Einzelbild (Lochfuellung, Fransen,
	// Zeilenbereiche). Vorher dekodierte diese Stelle nur das PNG: die Eintraege im
	// Zwischenspeicher hatten keine Zeilenbereiche und waren nicht nachbearbeitet -
	// gemessen Raum 84 7 ms je Bild langsamer und sichtbar anders als dasselbe Cel
	// ueber loadCostume.
	return hdPreloadCels(akosId, from, to, 0x7fffffff, 4);
}

// ── Vorladesatz beim Raumeintritt (Aufgabe 11, Schritt 11) ───────────────
// Anlass: im Zeichenweg kostet der Erstzugriff eines Cels rund 25 ms, und ein Raum
// braucht 103 davon (gemessen Raum 84). Der 12-ms-Vorlauf neben dem Bild kann das
// nicht aufholen, deshalb bezahlt jedes der ersten 150 Bilder einen Dekode.
// Hier wird der ganze Satz einer Figur beim Raumeintritt vorbereitet: PNG-Dekode,
// Umwandlung, Fransen, Lochfuellung und Zeilenbereiche laufen im Worker (reine
// Funktionen auf einer lokalen Flaeche), nur das Eintragen in den Zwischenspeicher
// passiert im Hauptthread.
static void hdComputeRowSpans(const Graphics::Surface &surf, Common::Array<uint16> &first,
                              Common::Array<uint16> &last);

struct HdCelJob {
	Common::String path;
	Graphics::Surface surf;
	Common::Array<uint16> rowFirst;
	Common::Array<uint16> rowLast;
	bool ok;
};

struct HdCelWorkerArg {
	HdCelJob *jobs;
	int start;
	int end;
};

static int hdCelWorker(void *arg) {
	HdCelWorkerArg *a = (HdCelWorkerArg *)arg;
	for (int i = a->start; i < a->end; i++) {
		HdCelJob &j = a->jobs[i];
		j.ok = hdCelLoadImage(j.path, j.surf, nullptr);
		if (!j.ok)
			continue;
		hdFillAlphaHoles(j.surf, 3);
		hdComputeRowSpans(j.surf, j.rowFirst, j.rowLast);
	}
	return 0;
}

static void hdCelBatch(Common::Array<HdCelJob> &jobs, int maxThreads) {
	const int n = jobs.size();
	if (n <= 0)
		return;
	if (n == 1 || maxThreads < 2) {
		for (int i = 0; i < n; i++) {
			HdCelJob &j = jobs[i];
			j.ok = hdCelLoadImage(j.path, j.surf, nullptr);
			if (j.ok) {
				hdFillAlphaHoles(j.surf, 3);
				hdComputeRowSpans(j.surf, j.rowFirst, j.rowLast);
			}
		}
		return;
	}
	const int threads = MIN(maxThreads, n);
	Common::Array<HdCelWorkerArg> args;
	args.resize(threads);
	Common::Array<SDL_Thread *> handles;
	const int chunk = (n + threads - 1) / threads;
	for (int t = 0; t < threads; t++) {
		const int start = t * chunk;
		const int end = MIN(n, start + chunk);
		if (start >= end)
			break;
		args[t].jobs = &jobs[0];
		args[t].start = start;
		args[t].end = end;
		SDL_Thread *th = SDL_CreateThread(hdCelWorker, "hd-cel", &args[t]);
		if (!th) {
			for (int i = start; i < end; i++) {
				HdCelJob &j = jobs[i];
				j.ok = hdCelLoadImage(j.path, j.surf, nullptr);
				if (j.ok) {
					hdFillAlphaHoles(j.surf, 3);
					hdComputeRowSpans(j.surf, j.rowFirst, j.rowLast);
				}
			}
			continue;
		}
		handles.push_back(th);
	}
	for (uint i = 0; i < handles.size(); i++)
		SDL_WaitThread(handles[i], nullptr);
}

int HdCostumeManager::preloadCostumeSet(int akosId, int maxFrames, int threads) {
	return hdPreloadCels(akosId, 0, 0x7fffffff, maxFrames, threads);
}

// Gemeinsamer Kern beider Vorladearten: sammelt die noch fehlenden Cels im Bereich,
// bereitet sie in hdCelBatch (mehrere Threads) vollstaendig auf und traegt sie ein.
int HdCostumeManager::hdPreloadCels(int akosId, int from, int to, int maxFrames, int threads) {
	if (!_enabled || maxFrames <= 0 || !_akosSubs.contains(akosId))
		return 0;
	Common::Array<CostumeKey> keys;
	for (Common::HashMap<CostumeKey, bool, CostumeKeyHash>::const_iterator it = _availableCostumes.begin();
	     it != _availableCostumes.end(); ++it) {
		if (it->_key.akosId != akosId)
			continue;
		if (it->_key.frame < from || it->_key.frame > to)
			continue;
		if (_textureCache.contains(it->_key))
			continue;
		keys.push_back(it->_key);
	}
	// Nach Bildnummer sortieren: die Hashmap liefert eine beliebige Reihenfolge, und der
	// Deckel maxFrames wuerde sonst zufaellig greifen.
	Common::sort(keys.begin(), keys.end(), [](const CostumeKey &a, const CostumeKey &b) {
		if (a.frame != b.frame)
			return a.frame < b.frame;
		return a.akosSub < b.akosSub;
	});
	if ((int)keys.size() > maxFrames)
		keys.resize(maxFrames);
	if (keys.empty())
		return 0;

	Common::Array<HdCelJob> jobs;
	jobs.resize(keys.size());
	for (uint i = 0; i < keys.size(); i++) {
		jobs[i].path = buildCostumePath(akosId, keys[i].akosSub, keys[i].frame);
		jobs[i].ok = false;
	}
	hdCelBatch(jobs, threads);

	int loaded = 0;
	for (uint i = 0; i < jobs.size(); i++) {
		if (jobs[i].ok) {
			TextureCacheEntry entry;
			entry.surface.copyFrom(jobs[i].surf);
			entry.rowFirst = jobs[i].rowFirst;
			entry.rowLast = jobs[i].rowLast;
			entry.lastUsed = ++_lruCounter;
			_textureCache[keys[i]] = entry;
			loaded++;
		}
		jobs[i].surf.free();
	}
	if (loaded)
		pruneCache();
	return loaded;
}

// ── Asynchroner Vorlauf (Aufgabe 11, Weg (b)) ───────────────────────────────
// Warum ein eigener Thread: der Vorlauf im Bildtakt benutzt nur die Restzeit bis
// 33 ms. In einem kalten Raum kostet das Bild 100 ms, die Restzeit ist damit null
// und der Vorlauf steht still - jedes Cel muss der Zeichenweg selbst dekodieren
// (Raum 84: 103 Erstzugriffe). Denselben Betrag frueher im selben Thread zu
// verbrauchen aendert die Summe nicht; erst ein zweiter Thread holt die Dekodes
// aus dem Bildtakt heraus.
static int hdAsyncThunk(void *arg) {
	((HdCostumeManager *)arg)->hdAsyncRun();
	return 0;
}

// A/B aus Aufgabe 11 Schritt 18: Zahl der Threads im Hintergrund-Worker. Vorgabe bleibt 4;
// HD_PF_THREADS=2 prueft, ob die Konkurrenz um die vier Kerne der Posten ist.
static int hdAsyncThreads() {
	static const int n = getenv("HD_PF_THREADS") ? MAX(1, atoi(getenv("HD_PF_THREADS"))) : 4;
	return n;
}

void HdCostumeManager::hdAsyncRun() {
	Common::Array<CostumeKey> keys;
	SDL_LockMutex(_asyncMutex);
	keys = _asyncKeys;
	SDL_UnlockMutex(_asyncMutex);

	const int n = keys.size();
	Common::Array<HdCelJob> jobs;
	jobs.resize(n);
	for (int i = 0; i < n; i++) {
		jobs[i].path = buildCostumePath(keys[i].akosId, keys[i].akosSub, keys[i].frame);
		jobs[i].ok = false;
	}
	hdCelBatch(jobs, hdAsyncThreads());

	SDL_LockMutex(_asyncMutex);
	for (int i = 0; i < n; i++) {
		if (!jobs[i].ok)
			continue;
		AsyncResult r;
		r.key = keys[i];
		r.surface = jobs[i].surf;          // Besitz wandert, jobs[i].surf wird nicht mehr freigegeben
		r.rowFirst = jobs[i].rowFirst;
		r.rowLast = jobs[i].rowLast;
		_asyncDone.push_back(r);
	}
	_asyncKeys.clear();
	_asyncBusy = false;
	SDL_UnlockMutex(_asyncMutex);
}

int HdCostumeManager::requestAsync(int akosId, int fromFrame, int maxFrames) {
	if (!_enabled || maxFrames <= 0 || !_akosSubs.contains(akosId))
		return 0;
	if (_asyncBusy)
		return 0;

	// Rahmen dieses Kostuems sortiert, wie preloadNext sie einmal aufbaut.
	if (!_framesByCostume.contains(akosId)) {
		Common::Array<int> frames;
		for (Common::HashMap<CostumeKey, bool, CostumeKeyHash>::const_iterator it = _availableCostumes.begin();
		     it != _availableCostumes.end(); ++it) {
			if (it->_key.akosId != akosId)
				continue;
			if (Common::find(frames.begin(), frames.end(), it->_key.frame) == frames.end())
				frames.push_back(it->_key.frame);
		}
		Common::sort(frames.begin(), frames.end());
		_framesByCostume[akosId] = frames;
	}
	Common::Array<int> &frames = _framesByCostume[akosId];
	if (frames.empty())
		return 0;

	int start = 0;
	for (uint i = 0; i < frames.size(); i++) {
		if (frames[i] >= fromFrame) {
			start = (int)i;
			break;
		}
	}

	Common::Array<CostumeKey> keys;
	SDL_LockMutex(_asyncMutex);
	for (uint k = 0; k < frames.size() && (int)keys.size() < maxFrames; k++) {
		const int frame = frames[(start + k) % frames.size()];
		bool schonDone = false;
		for (uint i = 0; i < _asyncDone.size(); i++)
			if (_asyncDone[i].key.akosId == akosId && _asyncDone[i].key.frame == frame)
				schonDone = true;
		if (schonDone)
			continue;
		for (Common::List<int>::const_iterator si = _akosSubs[akosId].begin(); si != _akosSubs[akosId].end(); ++si) {
			CostumeKey key;
			key.akosId = akosId;
			key.akosSub = *si;
			key.frame = frame;
			if (_textureCache.contains(key))
				continue;
			keys.push_back(key);
			if ((int)keys.size() >= maxFrames)
				break;
		}
	}
	if (keys.empty()) {
		SDL_UnlockMutex(_asyncMutex);
		return 0;
	}
	_asyncKeys = keys;
	_asyncBusy = true;
	SDL_UnlockMutex(_asyncMutex);

	_asyncThread = SDL_CreateThread(hdAsyncThunk, "hd-async", this);
	if (!_asyncThread) {
		SDL_LockMutex(_asyncMutex);
		_asyncBusy = false;
		_asyncKeys.clear();
		SDL_UnlockMutex(_asyncMutex);
		return 0;
	}
	return keys.size();
}

int HdCostumeManager::pumpAsync() {
	if (!_enabled)
		return 0;
	if (!_asyncBusy && _asyncThread) {
		// Thread ist fertig: Handle einsammeln, damit er nicht liegen bleibt.
		SDL_WaitThread(_asyncThread, nullptr);
		_asyncThread = nullptr;
	}
	if (_asyncDone.empty())
		return 0;

	int loaded = 0;
	SDL_LockMutex(_asyncMutex);
	for (uint i = 0; i < _asyncDone.size(); i++) {
		AsyncResult &r = _asyncDone[i];
		if (_textureCache.contains(r.key)) {
			r.surface.free();      // der Zeichenweg war schneller
			continue;
		}
		TextureCacheEntry entry;
		entry.surface = r.surface;   // Zeiger wandert, keine Vollbildkopie
		entry.rowFirst = r.rowFirst;
		entry.rowLast = r.rowLast;
		entry.lastUsed = ++_lruCounter;
		_textureCache[r.key] = entry;
		loaded++;
	}
	_asyncDone.clear();
	SDL_UnlockMutex(_asyncMutex);
	if (loaded)
		pruneCache();
	return loaded;
}

int HdCostumeManager::asyncPending() {
	int n = (int)_asyncDone.size() + (int)_asyncKeys.size();
	return n;
}

bool HdCostumeManager::getRowSpans(int akosId, int frame, const uint16 **first,
                                   const uint16 **last, int *rows) const {
	*first = nullptr;
	*last = nullptr;
	*rows = 0;
	if (!_enabled || !_akosSubs.contains(akosId))
		return false;
	for (Common::List<int>::const_iterator si = _akosSubs[akosId].begin(); si != _akosSubs[akosId].end(); ++si) {
		int loadFrame = frame;
		if (!_availableCostumes.contains(CostumeKey{akosId, *si, frame})) {
			const uint64 maxKey = ((uint64)(uint32)akosId << 32) | (uint32)*si;
			Common::HashMap<uint64, int>::const_iterator mfc = _maxFrameCache.find(maxKey);
			int maxFrame = (mfc != _maxFrameCache.end()) ? mfc->_value : -1;
			if (maxFrame >= 0)
				loadFrame = frame % (maxFrame + 1);
			else
				continue;
		}
		CostumeKey key;
		key.akosId = akosId;
		key.akosSub = *si;
		key.frame = loadFrame;
		Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash>::const_iterator it = _textureCache.find(key);
		if (it == _textureCache.end() || it->_value.rowFirst.empty())
			continue;
		*first = it->_value.rowFirst.begin();
		*last = it->_value.rowLast.begin();
		*rows = (int)it->_value.rowFirst.size();
		return true;
	}
	return false;
}

bool HdCostumeManager::isFrameCached(int akosId, int frame) const {
	for (Common::HashMap<int, Common::List<int>>::const_iterator it = _akosSubs.begin(); it != _akosSubs.end(); ++it) {
		if (it->_key != akosId)
			continue;
		for (Common::List<int>::const_iterator si = it->_value.begin(); si != it->_value.end(); ++si) {
			if (!_textureCache.contains(CostumeKey{akosId, *si, frame}))
				return false;
		}
	}
	return true;
}

// Time-sliced prefetch: load ONE uncached frame of a costume per call
// (Issue #14 v2). Called between frames for visible actors — animations
// cycle through their frames, so after one or two cycles the whole
// animation is cached and the render path never hits a cache miss.
int HdCostumeManager::preloadNext(int akosId) {
	if (!_enabled)
		return 0;
	if (!_akosSubs.contains(akosId))
		return 0;

	// Lazily build the sorted frame list for this costume
	if (!_framesByCostume.contains(akosId)) {
		Common::Array<int> frames;
		for (Common::HashMap<CostumeKey, bool, CostumeKeyHash>::const_iterator it = _availableCostumes.begin();
		     it != _availableCostumes.end(); ++it) {
			if (it->_key.akosId != akosId)
				continue;
			if (Common::find(frames.begin(), frames.end(), it->_key.frame) == frames.end())
				frames.push_back(it->_key.frame);
		}
		Common::sort(frames.begin(), frames.end());
		_framesByCostume[akosId] = frames;
		_preloadCursor[akosId] = 0;
	}

	Common::Array<int> &frames = _framesByCostume[akosId];
	if (frames.empty())
		return 0;

	int &cursor = _preloadCursor[akosId];
	int start = cursor;
	Graphics::Surface tmp;
	do {
		int frame = frames[cursor];
		cursor = (cursor + 1) % frames.size();
		// Skip if ALL subs of this frame are already cached
		bool allCached = true;
		for (Common::List<int>::const_iterator si = _akosSubs[akosId].begin(); si != _akosSubs[akosId].end(); ++si) {
			if (!_textureCache.contains(CostumeKey{akosId, *si, frame})) {
				allCached = false;
				break;
			}
		}
		if (allCached)
			continue;
		if (loadCostume(akosId, frame, tmp)) {
			tmp.free();
			return 1;
		}
	} while (cursor != start);
	return 0;
}

// Erste und letzte Spalte mit Deckung je Zeile bestimmen. Reine Kosten beim Laden,
// dafuer spart das Zeichnen danach die durchsichtigen Raender jeder Zeile.
static void hdComputeRowSpans(const Graphics::Surface &surf, Common::Array<uint16> &first, Common::Array<uint16> &last) {
	first.clear();
	last.clear();
	if (surf.w <= 0 || surf.h <= 0 || !surf.getPixels())
		return;
	first.resize(surf.h);
	last.resize(surf.h);
	const bool hasAlpha = surf.format.bytesPerPixel == 4;
	for (int y = 0; y < surf.h; y++) {
		const uint32 *row = (const uint32 *)surf.getBasePtr(0, y);
		int f = -1, l = -2;
		for (int x = 0; x < surf.w; x++) {
			uint32 pix = row[x];
			uint8 a = hasAlpha ? (uint8)((pix >> 24) & 0xFF) : 255;
			if (a > 0) {
				if (f < 0)
					f = x;
				l = x;
			}
		}
		first[y] = (uint16)(f < 0 ? 1 : f);
		last[y] = (uint16)(f < 0 ? 0 : l);
	}
}

// Fuellt kleine Loecher in der Deckkraft. Die Kostuem-PNGs haben im Inneren
// zusammenhaengender Flaechen durchsichtige Pixel (Artefakt der Extraktion); im Spiel
// erscheinen sie als loechrige Segel. Gefuellt wird nur, was von mindestens zwei Seiten
// deckend umgeben ist — der aeussere Rand bleibt damit erhalten, und die Rueckholung des
// Hintergrunds an durchsichtigen Stellen greift weiterhin nur aussen.
void hdFillAlphaHoles(Graphics::Surface &s, int passes) {
	if (s.format.bytesPerPixel != 4)
		return;
	const int w = s.w, h = s.h;
	if (w < 3 || h < 3)
		return;
	// Kandidatengetriebene Fassung: Durchgang 1 scannt das Bild einmal. Danach kann ein Pixel
	// nur dann neu fuellbar werden, wenn einer seiner vier Nachbarn gerade deckend geworden
	// ist - die weiteren Durchgaenge pruefen deshalb nur die Nachbarschaft der zuletzt
	// gefuellten Pixel statt jedes Mal das ganze Bild (gemessen: 13,8 -> 3,4 ms je Cel).
	// Markiert wird je Durchgang in einer Liste, angewendet erst danach; innerhalb eines
	// Durchgangs kaskadiert also nichts, genau wie in der alten Fassung.
	Common::Array<uint32> letzte, neuIdx, neuFarbe;
	for (int pass = 0; pass < passes; pass++) {
		neuIdx.clear();
		neuFarbe.clear();
		if (pass == 0) {
			for (int y = 1; y + 1 < h; y++) {
				const uint32 *row = (const uint32 *)s.getBasePtr(0, y);
				const uint32 *up = (const uint32 *)s.getBasePtr(0, y - 1);
				const uint32 *dn = (const uint32 *)s.getBasePtr(0, y + 1);
				for (int x = 1; x + 1 < w; x++) {
					if ((row[x] >> 24) >= 128)
						continue;
					const uint32 nb[4] = { row[x - 1], row[x + 1], up[x], dn[x] };
					int n = 0;
					uint32 summe = 0;
					for (int k = 0; k < 4; k++)
						if ((nb[k] >> 24) >= 128) {
							summe = nb[k];
							n++;
						}
					if (n >= 2) {
						neuIdx.push_back((uint32)((size_t)y * w + x));
						neuFarbe.push_back(summe);
					}
				}
			}
		} else {
			const int dx[4] = { -1, 1, 0, 0 };
			const int dy[4] = { 0, 0, -1, 1 };
			for (uint i = 0; i < letzte.size(); i++) {
				const int lx = (int)(letzte[i] % w);
				const int ly = (int)(letzte[i] / w);
				for (int k = 0; k < 4; k++) {
					const int x = lx + dx[k], y = ly + dy[k];
					if (x < 1 || y < 1 || x + 1 >= w || y + 1 >= h)
						continue;
					const uint32 *row = (const uint32 *)s.getBasePtr(0, y);
					if ((row[x] >> 24) >= 128)
						continue;
					const uint32 nb[4] = { row[x - 1], row[x + 1],
					                       ((const uint32 *)s.getBasePtr(0, y - 1))[x],
					                       ((const uint32 *)s.getBasePtr(0, y + 1))[x] };
					int n = 0;
					uint32 summe = 0;
					for (int j = 0; j < 4; j++)
						if ((nb[j] >> 24) >= 128) {
							summe = nb[j];
							n++;
						}
					if (n >= 2) {
						neuIdx.push_back((uint32)((size_t)y * w + x));
						neuFarbe.push_back(summe);
					}
				}
			}
		}
		if (neuIdx.empty())
			break;
		for (uint i = 0; i < neuIdx.size(); i++) {
			uint32 *row = (uint32 *)s.getBasePtr(0, (int)(neuIdx[i] / w));
			row[neuIdx[i] % w] = neuFarbe[i];
		}
		letzte = neuIdx;
	}
}

bool HdCostumeManager::loadCostume(int akosId, int frame, Graphics::Surface &dest,
                                   const Graphics::Surface **cachedOut,
                                   const uint16 **rowFirstOut, const uint16 **rowLastOut,
                                   int *spanRowsOut) {
	if (rowFirstOut)
		*rowFirstOut = nullptr;
	if (rowLastOut)
		*rowLastOut = nullptr;
	if (spanRowsOut)
		*spanRowsOut = 0;
	if (!_enabled)
		return false;


	// Search all available subs for this AKOS ID
	if (!_akosSubs.contains(akosId))
		return false;

	for (Common::List<int>::const_iterator si = _akosSubs[akosId].begin(); si != _akosSubs[akosId].end(); ++si) {
		int loadFrame = frame;

		// If exact frame doesn't exist, wrap via modulo
		if (!_availableCostumes.contains(CostumeKey{akosId, *si, frame})) {
			// Hoechsten Rahmen einmal je (akosId, sub) ermitteln und merken. Ohne den
			// Zwischenspeicher lief hier fuer jedes Koerperteil jedes Bildes eine Suche
			// ueber die komplette Liste der vorhandenen Kostueme.
			const uint64 maxKey = ((uint64)(uint32)akosId << 32) | (uint32)*si;
			int maxFrame = -1;
			Common::HashMap<uint64, int>::const_iterator mfc = _maxFrameCache.find(maxKey);
			if (mfc != _maxFrameCache.end()) {
				maxFrame = mfc->_value;
			} else {
				for (Common::HashMap<CostumeKey, bool, CostumeKeyHash>::const_iterator it = _availableCostumes.begin();
				     it != _availableCostumes.end(); ++it) {
					if (it->_key.akosId == akosId && it->_key.akosSub == *si)
						maxFrame = MAX(maxFrame, it->_key.frame);
				}
				_maxFrameCache[maxKey] = maxFrame;
			}
			if (maxFrame >= 0)
				loadFrame = frame % (maxFrame + 1);
			else
				continue;
		}

		CostumeKey key;
		key.akosId = akosId;
		key.akosSub = *si;
		key.frame = loadFrame;

		// Check cache first
		Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash>::iterator cacheIt = _textureCache.find(key);
		if (cacheIt != _textureCache.end()) {
			s_kostuemTreffer++;
			cacheIt->_value.lastUsed = ++_lruCounter;
			// Zeilenbereiche des Eintrags, den wir wirklich zurueckgeben.
			if (rowFirstOut && !cacheIt->_value.rowFirst.empty()) {
				*rowFirstOut = cacheIt->_value.rowFirst.begin();
				*rowLastOut = cacheIt->_value.rowLast.begin();
				*spanRowsOut = (int)cacheIt->_value.rowFirst.size();
			}
			// Wer nur zeichnen will, bekommt den Zeiger auf die Flaeche im Cache und
			// spart sich die Kopie. Vorher wurde hier bei jedem Treffer kopiert.
			if (cachedOut) {
				*cachedOut = &cacheIt->_value.surface;
				return true;
			}
			dest.copyFrom(cacheIt->_value.surface);
			return true;
		}

		Common::String path = buildCostumePath(akosId, *si, loadFrame);
		Graphics::Surface surf;
		const uint64 tPng = hdCmUsNow();
		if (!loadPNG(path, surf))
			continue;
		s_usPng += hdCmUsNow() - tPng;
		s_pngPix += (uint64)surf.w * surf.h;
		s_kostuemDekode++;
		// Loecher in der Deckkraft schliessen, bevor das Bild in den Zwischenspeicher geht.
		// 3 Durchgaenge reichen fuer kleine Loecher. Ein Test mit 200 Durchgaengen (grosse
		// Loecher, z. B. LFLF_0086_AKOS_0438 mit 30,3 Prozent innen) hat die Messung NICHT
		// verbessert (Raum 86: 8,72 Prozent unveraendert) und den Lauf verlangsamt
		// (80 -> 44 Bilder). Deshalb zurueck auf 3; die Loecher sind nicht die Ursache.
		const uint64 tFill = hdCmUsNow();
		hdFillAlphaHoles(surf, 3);
		s_usFill += hdCmUsNow() - tFill;

		TextureCacheEntry entry;
		const uint64 tCopy = hdCmUsNow();
		entry.surface.copyFrom(surf);
		entry.lastUsed = ++_lruCounter;
		hdComputeRowSpans(entry.surface, entry.rowFirst, entry.rowLast);
		s_usCopy += hdCmUsNow() - tCopy;
		_textureCache[key] = entry;
		// Bereiche aus dem Eintrag im Zwischenspeicher nehmen, nicht aus der lokalen Kopie:
		// nur dessen Felder bleiben gueltig.
		if (rowFirstOut) {
			TextureCacheEntry &neu = _textureCache[key];
			if (!neu.rowFirst.empty()) {
				*rowFirstOut = neu.rowFirst.begin();
				*rowLastOut = neu.rowLast.begin();
				*spanRowsOut = (int)neu.rowFirst.size();
			}
		}
		const uint64 tDest = hdCmUsNow();
		dest.copyFrom(surf);
		surf.free();
		s_usDest += hdCmUsNow() - tDest;
		const uint64 tPrune = hdCmUsNow();
		pruneCache();
		s_usPrune += hdCmUsNow() - tPrune;
		return true;
	}
	return false;
}

void HdCostumeManager::pruneCache() {
	// Byte-budget LRU: evict oldest entries only while the total cache
	// size exceeds the budget. With 1.5 GB, the current + previous room's
	// costumes stay cached — switching back doesn't reload anything.
	while (true) {
		uint32 total = 0;
		for (Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash>::const_iterator it = _textureCache.begin();
		     it != _textureCache.end(); ++it)
			total += it->_value.surface.w * it->_value.surface.h * 4;
		if (total <= _cacheBudgetBytes)
			break;
		// Find least recently used
		CostumeKey oldestKey = _textureCache.begin()->_key;
		int oldestTime = _lruCounter;
		for (Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash>::iterator it = _textureCache.begin();
		     it != _textureCache.end(); ++it) {
			if (it->_value.lastUsed < oldestTime) {
				oldestTime = it->_value.lastUsed;
				oldestKey = it->_key;
			}
		}
		_textureCache[oldestKey].surface.free();
		_textureCache.erase(oldestKey);
	}
}

} // End of namespace Scumm
