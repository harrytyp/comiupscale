#include "common/scummsys.h"
#include "common/fs.h"
#include "common/file.h"
#include "image/png.h"
#include "graphics/surface.h"
#include "graphics/pixelformat.h"
#include "common/debug.h"

int main() {
    // Open the costume PNG
    Common::FSNode fileNode(Common::Path("/opt/data/local/comi-hd-final/hd/costumes/LFLF_0009_AKOS_0025_aframe_192.png", Common::Path::kNativeSeparator));
    Common::SeekableReadStream *stream = fileNode.createReadStream();
    if (!stream) {
        printf("Failed to open file\n");
        return 1;
    }
    
    Image::PNGDecoder png;
    if (!png.loadStream(*stream)) {
        printf("Failed to decode PNG\n");
        delete stream;
        return 1;
    }
    delete stream;
    
    const Graphics::Surface *surf = png.getSurface();
    if (!surf) {
        printf("No surface\n");
        return 1;
    }
    
    printf("Surface: %dx%d bpp=%d\n", surf->w, surf->h, surf->format.bytesPerPixel);
    printf("Format: rShift=%d gShift=%d bShift=%d aShift=%d\n",
        surf->format.rShift, surf->format.gShift, surf->format.bShift, surf->format.aShift);
    printf("aBits=%d rBits=%d gBits=%d bBits=%d\n",
        surf->format.aBits, surf->format.rBits, surf->format.gBits, surf->format.bBits);
    
    // Check pixel (0,0) - should be transparent: RGBA=(255,255,252,0)
    const byte *pixels = (const byte *)surf->getPixels();
    int pitch = surf->pitch;
    int bpp = surf->format.bytesPerPixel;
    
    // Read pixel at (0,0) as raw bytes
    const byte *p00 = pixels + 0 * pitch + 0 * bpp;
    printf("\nPixel (0,0) raw bytes: ");
    for (int i = 0; i < bpp; i++) printf("%02x ", p00[i]);
    printf("\n");
    
    // Read as uint32
    uint32 pixel = *(const uint32 *)p00;
    printf("Pixel (0,0) as uint32: 0x%08x\n", pixel);
    
    // Extract channels using format
    uint8 a, r, g, b;
    surf->format.colorToARGB(pixel, a, r, g, b);
    printf("colorToARGB: a=%d r=%d g=%d b=%d\n", a, r, g, b);
    printf("  Expected:   a=0  r=255 g=255 b=252\n");
    
    // Check a known opaque pixel - sample a few pixels
    printf("\nSampling pixels:\n");
    for (int y = 100; y < 110; y++) {
        for (int x = 100; x < 110; x++) {
            const byte *px = pixels + y * pitch + x * bpp;
            uint32 val = *(const uint32 *)px;
            surf->format.colorToARGB(val, a, r, g, b);
            if (a > 0 && a < 255) {
                printf("  Semi-transparent pixel at (%d,%d): a=%d r=%d g=%d b=%d\n", x, y, a, r, g, b);
            }
        }
    }
    
    // Scan for transparent pixels
    int transCount = 0;
    int semiCount = 0;
    int opaqueCount = 0;
    for (int y = 0; y < MIN(surf->h, 100); y++) {
        for (int x = 0; x < MIN(surf->w, 100); x++) {
            const byte *px = pixels + y * pitch + x * bpp;
            uint32 val = *(const uint32 *)px;
            surf->format.colorToARGB(val, a, r, g, b);
            if (a == 0) transCount++;
            else if (a == 255) opaqueCount++;
            else semiCount++;
        }
    }
    printf("\nFirst 100x100 pixels: transparent=%d semi=%d opaque=%d\n", transCount, semiCount, opaqueCount);
    
    // Now test the DEST format
    Graphics::PixelFormat rgbaFmt(4, 8, 8, 8, 8, 0, 8, 16, 24);
    uint32 dstPix = rgbaFmt.ARGBToColor(a, r, g, b);
    printf("Dest pixel for transparent: dst=0x%08x alpha=%d\n", dstPix, (dstPix >> 24) & 0xFF);
    
    delete stream;
    return 0;
}
