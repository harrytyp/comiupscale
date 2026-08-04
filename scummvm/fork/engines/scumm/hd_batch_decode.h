/* ScummVM - Graphic Adventure Engine
 * COMI HD: parallel PNG decode batch (Issue #14)
 *
 * Decodes a list of PNG files in parallel using SDL_Thread workers
 * with static partitioning (each thread decodes its own slice — no
 * shared state, no locks). The caller owns the resulting surfaces.
 *
 * PNG decode is the dominant cost of HD texture loading (~80-90%);
 * parallelizing it scales the room-enter prewarm across cores.
 */

#ifndef SCUMM_HD_BATCH_DECODE_H
#define SCUMM_HD_BATCH_DECODE_H

#include "common/array.h"
#include "common/fs.h"
#include "common/str.h"
#include "graphics/surface.h"

// SDL.h must be includable even in files where ScummVM's forbidden.h
// is active — mirror the gfx.cpp approach: define the escape hatch
// permanently (the only includers are the HD managers, which don't
// need forbidden.h's protection).
#define FORBIDDEN_SYMBOL_ALLOW_ALL
#include "SDL.h"

#include "image/png.h"

namespace Scumm {

struct HdDecodeJob {
	Common::String path;
	Graphics::Surface surface;  // filled by the worker (RGBA8888); caller frees
	bool ok;
};

static bool hdDecodeOne(const Common::String &path, Graphics::Surface &surf) {
	Common::FSNode fileNode(Common::Path(path, Common::Path::kNativeSeparator));
	if (!fileNode.exists())
		return false;
	Common::SeekableReadStream *stream = fileNode.createReadStream();
	if (!stream)
		return false;

	Image::PNGDecoder png;
	if (!png.loadStream(*stream)) {
		delete stream;
		return false;
	}
	delete stream;

	const Graphics::Surface *pngSurf = png.getSurface();
	if (!pngSurf)
		return false;

	surf.copyFrom(*pngSurf);

	// Convert 24-bit RGB to 32-bit RGBA if needed (same as loadPNG)
	if (surf.format.bytesPerPixel == 3) {
		Graphics::Surface conv;
		conv.create(surf.w, surf.h, Graphics::PixelFormat(4, 8, 8, 8, 8, 0, 8, 16, 24));
		const byte *src = (const byte *)surf.getPixels();
		byte *dst = (byte *)conv.getPixels();
		for (int i = 0; i < surf.w * surf.h; i++) {
			dst[i * 4 + 0] = src[i * 3 + 0];
			dst[i * 4 + 1] = src[i * 3 + 1];
			dst[i * 4 + 2] = src[i * 3 + 2];
			dst[i * 4 + 3] = 0xFF;
		}
		surf.free();
		surf.copyFrom(conv);
		conv.free();
	}
	return true;
}

struct HdDecodeWorkerArg {
	HdDecodeJob *jobs;
	int start;
	int end;
};

static int hdDecodeWorker(void *arg) {
	HdDecodeWorkerArg *a = (HdDecodeWorkerArg *)arg;
	for (int i = a->start; i < a->end; i++)
		a->jobs[i].ok = hdDecodeOne(a->jobs[i].path, a->jobs[i].surface);
	return 0;
}

static void hdDecodeBatch(Common::Array<HdDecodeJob> &jobs, int maxThreads = 4) {
	int n = jobs.size();
	if (n <= 1) {
		for (int i = 0; i < n; i++)
			jobs[i].ok = hdDecodeOne(jobs[i].path, jobs[i].surface);
		return;
	}
	if (maxThreads < 1)
		maxThreads = 1;
	int threads = MIN(maxThreads, n);

	Common::Array<HdDecodeWorkerArg> args;
	args.resize(threads);
	Common::Array<SDL_Thread *> handles;

	int chunk = (n + threads - 1) / threads;
	for (int t = 0; t < threads; t++) {
		int start = t * chunk;
		int end = MIN(n, start + chunk);
		if (start >= end)
			break;
		args[t].jobs = &jobs[0];
		args[t].start = start;
		args[t].end = end;
		SDL_Thread *th = SDL_CreateThread(hdDecodeWorker, "hd-decode", &args[t]);
		if (!th) {
			// Thread creation failed — decode this slice inline
			for (int i = start; i < end; i++)
				jobs[i].ok = hdDecodeOne(jobs[i].path, jobs[i].surface);
			continue;
		}
		handles.push_back(th);
	}
	for (uint i = 0; i < handles.size(); i++)
		SDL_WaitThread(handles[i], nullptr);
}

} // End of namespace Scumm

#endif // SCUMM_HD_BATCH_DECODE_H
