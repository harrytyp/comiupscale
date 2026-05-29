// test_room.cpp
// Standalone test of the full HD compositing pipeline in a simulated game room.
// Builds a test "world" with all rendering layers and auto-verifies each.
//
// Compile: 
//   PATH="/c/msys64/mingw64/bin:$PATH" && g++ -std=c++17 -O2 -o test_room.exe test_room.cpp
// Run:
//   ./test_room.exe --verify    # programmatic checks only, no window
//   ./test_room.exe --show      # + SDL2 window for visual inspection
//   ./test_room.exe --show-sdl  # + SDL2 with cursor overlay

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <string>
#include <vector>
#include <algorithm>

// ============================================================
// Minimal types
// ============================================================

struct rgba_t {
    uint8_t r, g, b, a;
    bool operator==(const rgba_t &o) const { return r==o.r && g==o.g && b==o.b && a==o.a; }
    bool operator!=(const rgba_t &o) const { return !(*this == o); }
    uint32_t as_u32() const { return (uint32_t)r | ((uint32_t)g<<8) | ((uint32_t)b<<16) | ((uint32_t)a<<24); }
    static rgba_t from_u32(uint32_t v) { return {uint8_t(v&0xFF), uint8_t((v>>8)&0xFF), uint8_t((v>>16)&0xFF), uint8_t((v>>24)&0xFF)}; }
};

struct Image8 {
    int w, h;
    uint8_t *pixels;
    Image8(int w_, int h_, uint8_t fill=0) : w(w_), h(h_) {
        pixels = new uint8_t[w * h];
        memset(pixels, fill, w * h);
    }
    Image8(const Image8 &) = delete;
    Image8 &operator=(const Image8 &) = delete;
    ~Image8() { delete[] pixels; }
    uint8_t &at(int x, int y) { return pixels[y * w + x]; }
    const uint8_t &at(int x, int y) const { return pixels[y * w + x]; }
    void fill_rect(int x0, int y0, int x1, int y1, uint8_t v) {
        for (int y=std::max(0,y0); y<std::min(h,y1); y++)
            for (int x=std::max(0,x0); x<std::min(w,x1); x++)
                at(x,y) = v;
    }
    void fill_circle(int cx, int cy, int r, uint8_t v) {
        for (int dy=-r; dy<=r; dy++)
            for (int dx=-r; dx<=r; dx++)
                if (dx*dx+dy*dy <= r*r) {
                    int px=cx+dx, py=cy+dy;
                    if (px>=0 && px<w && py>=0 && py<h) at(px,py)=v;
                }
    }
};

struct ImageRGBA {
    int w, h;
    rgba_t *pixels;
    ImageRGBA(int w_, int h_, rgba_t fill={0,0,0,0}) : w(w_), h(h_) {
        pixels = new rgba_t[w * h];
        for (int i=0; i<w*h; i++) pixels[i] = fill;
    }
    ImageRGBA(const ImageRGBA &) = delete;
    ImageRGBA &operator=(const ImageRGBA &) = delete;
    ~ImageRGBA() { delete[] pixels; }
    rgba_t &at(int x, int y) { return pixels[y * w + x]; }
    const rgba_t &at(int x, int y) const { return pixels[y * w + x]; }
    void fill_rect(int x0, int y0, int x1, int y1, rgba_t v) {
        for (int y=std::max(0,y0); y<std::min(h,y1); y++)
            for (int x=std::max(0,x0); x<std::min(w,x1); x++)
                at(x,y) = v;
    }
    // Draw a filled circle
    void fill_circle(int cx, int cy, int r, rgba_t v) {
        for (int dy=-r; dy<=r; dy++)
            for (int dx=-r; dx<=r; dx++)
                if (dx*dx+dy*dy <= r*r) {
                    int px=cx+dx, py=cy+dy;
                    if (px>=0 && px<w && py>=0 && py<h) at(px,py)=v;
                }
    }
    // Draw a simple arrow cursor shape
    void draw_cursor(int x, int y, rgba_t color) {
        // Simple 16x16 arrow
        for (int i=0; i<12; i++) {
            for (int j=i; j<12; j++) {
                int px=x+j, py=y+i;
                if (px>=0 && px<w && py>=0 && py<h) at(px,py)=color;
            }
        }
    }
    // Compare two images, return first mismatch
    bool compare(const ImageRGBA &other, int &diffX, int &diffY, rgba_t &got, rgba_t &expected) const {
        if (w!=other.w || h!=other.h) { diffX=diffY=-1; got={0,0,0,0}; expected={0,0,0,0}; return false; }
        for (int y=0; y<h; y++) for (int x=0; x<w; x++) {
            if (at(x,y) != other.at(x,y)) {
                diffX=x; diffY=y; got=at(x,y); expected=other.at(x,y); return false;
            }
        }
        return true;
    }
};

// ============================================================
// HD Compositing (same logic as ScummVM renderHDComposite)
// ============================================================

void composite_hd_frame(ImageRGBA &output,
                        const ImageRGBA &hdBg,
                        const Image8 &game,
                        const Image8 &cleanBg,
                        const uint8_t *cleanValid,
                        const uint8_t *palette,
                        int gameW, int gameH,
                        int roomW, int xstart)
{
    int hdW = output.w, hdH = output.h;
    
    // Step 1: Copy HD background with camera offset
    int64_t camOff = (int64_t)xstart * hdW / std::max(1, roomW);
    if (camOff < 0) camOff = 0;
    if (camOff >= hdW) camOff = hdW - 1;
    int cOff = (int)camOff;
    
    for (int y = 0; y < hdH; y++) {
        int64_t srcY = (int64_t)y * hdBg.h / hdH;
        if (srcY < 0) srcY = 0; if (srcY >= hdBg.h) srcY = hdBg.h - 1;
        int cw = (int)std::min(hdW, hdBg.w - cOff);
        if (cw > 0) {
            memcpy(&output.at(0,y), &hdBg.at(cOff,(int)srcY), cw * sizeof(rgba_t));
            if (cw < hdW) memset(&output.at(cw,y), 0, (hdW-cw)*sizeof(rgba_t));
        } else {
            memset(&output.at(0,y), 0, hdW*sizeof(rgba_t));
        }
    }
    
    // Step 2: Composite game content over HD background
    int visW = std::min(gameW, game.w);
    int visH = std::min(gameH, game.h);
    
    for (int dy = 0; dy < hdH; dy++) {
        int sy = dy * visH / hdH;
        if (sy < 0) sy = 0; if (sy >= visH) sy = visH - 1;
        for (int dx = 0; dx < hdW; dx++) {
            int sx = dx * visW / hdW;
            if (sx < 0) sx = 0; if (sx >= visW) sx = visW - 1;
            
            int gx = xstart + sx;
            if (gx < 0) gx = 0; if (gx >= game.w) gx = game.w - 1;
            int gy = sy;
            if (gy < 0) gy = 0; if (gy >= game.h) gy = game.h - 1;
            
            uint8_t curPix = game.at(gx, gy);
            
            bool isForeground = true;
            if (cleanValid && sy < visH) {
                int pos = sy * visW + sx;
                if (cleanValid[pos]) {
                    uint8_t cleanPix = cleanBg.at(sx, sy);
                    isForeground = (curPix != cleanPix);
                }
            }
            
            if (isForeground) {
                const uint8_t *p = &palette[curPix * 3];
                output.at(dx, dy) = {p[0], p[1], p[2], 0xFF};
            }
        }
    }
}

// ============================================================
// Test Room — a simulated game world with all rendering layers
// ============================================================

struct TestRoom {
    // Config
    int gameW = 640, gameH = 480;
    int roomW = 640;           // can be > gameW for scrolling rooms
    int hdW = 2560, hdH = 1920; // 4x scale
    int scale = 4;
    
    // Surfaces
    ImageRGBA hdBackground;    // HD background at native res
    Image8 gameScreen;         // game virtual screen (8-bit indexed)
    Image8 cleanBg;            // clean room background strips
    uint8_t *cleanValid;       // per-pixel valid mask
    uint8_t palette[768];      // 256 RGB palette entries
    
    // Game world elements
    // Palette indices reserved for each element type
    static constexpr uint8_t PAL_BG       = 0x10; // room background base
    static constexpr uint8_t PAL_ACTOR    = 0x20; // actor sprite
    static constexpr uint8_t PAL_ACTOR2   = 0x21; // actor frame 2
    static constexpr uint8_t PAL_OBJECT   = 0x30; // interactive object
    static constexpr uint8_t PAL_OBJ_HL   = 0x31; // highlighted object
    static constexpr uint8_t PAL_TEXT     = 0x40; // text
    static constexpr uint8_t PAL_VERB     = 0x50; // verb button
    static constexpr uint8_t PAL_VERB_HL  = 0x51; // highlighted verb
    static constexpr uint8_t PAL_BLAST    = 0x60; // blast effect
    static constexpr uint8_t PAL_CURSOR   = 0x70; // cursor
    
    // Game state
    int frame = 0;
    int actorX = 100, actorY = 240;
    int actorAnimFrame = 0;
    bool objectHighlighted = false;
    int hoverVerbIndex = -1;
    int cursorX = 320, cursorY = 240;
    std::string textLine;
    int textScroll = 0;
    int textY = 20;
    int xstart = 0;            // camera scroll offset
    bool blastActive = false;
    int blastX = 0, blastY = 0;
    int blastFrame = 0;
    
    // Test scenarios
    std::vector<std::string> results;
    
    TestRoom(int roomWidth = 640)
        : roomW(roomWidth)
        , hdBackground(hdW, hdH)
        , gameScreen(gameW, gameH)
        , cleanBg(gameW, gameH)
    {
        // Allocate valid mask
        cleanValid = new uint8_t[gameW * gameH];
        memset(cleanValid, 0, gameW * gameH);
        
        // Build palette — assign distinct colors to each element type
        // So we can verify which element rendered at each pixel
        build_palette();
        
        // Build HD background
        build_hd_background();
        
        // Build room image (clean background strips)
        build_room_image();
        
        // Copy room strips to clean bg
        save_clean_strips(0, gameW / 8);
    }
    
    ~TestRoom() { delete[] cleanValid; }
    
    void build_palette() {
        // Assign colors: we use full-brightness unique colors per element for easy verification
        for (int i = 0; i < 256; i++) {
            palette[i*3+0] = (i * 37) & 0xFF;
            palette[i*3+1] = (i * 71) & 0xFF;
            palette[i*3+2] = (i * 113) & 0xFF;
        }
        // Override specific element colors to known values
        // BG = gray
        palette[PAL_BG*3+0]=0x60; palette[PAL_BG*3+1]=0x60; palette[PAL_BG*3+2]=0x60;
        // Actor = red
        palette[PAL_ACTOR*3+0]=0xFF; palette[PAL_ACTOR*3+1]=0x20; palette[PAL_ACTOR*3+2]=0x20;
        palette[PAL_ACTOR2*3+0]=0xFF; palette[PAL_ACTOR2*3+1]=0x80; palette[PAL_ACTOR2*3+2]=0x20;
        // Object = green
        palette[PAL_OBJECT*3+0]=0x20; palette[PAL_OBJECT*3+1]=0xFF; palette[PAL_OBJECT*3+2]=0x20;
        palette[PAL_OBJ_HL*3+0]=0x80; palette[PAL_OBJ_HL*3+1]=0xFF; palette[PAL_OBJ_HL*3+2]=0x80;
        // Text = white
        palette[PAL_TEXT*3+0]=0xFF; palette[PAL_TEXT*3+1]=0xFF; palette[PAL_TEXT*3+2]=0xFF;
        // Verb = blue
        palette[PAL_VERB*3+0]=0x40; palette[PAL_VERB*3+1]=0x40; palette[PAL_VERB*3+2]=0xFF;
        palette[PAL_VERB_HL*3+0]=0x80; palette[PAL_VERB_HL*3+1]=0x80; palette[PAL_VERB_HL*3+2]=0xFF;
        // Blast = yellow
        palette[PAL_BLAST*3+0]=0xFF; palette[PAL_BLAST*3+1]=0xFF; palette[PAL_BLAST*3+2]=0x00;
        // Cursor = cyan (but drawn as overlay, not in palette)
    }
    
    void build_hd_background() {
        // Create a rich HD background: gradient from blue to teal, with grid lines
        for (int y = 0; y < hdH; y++) {
            for (int x = 0; x < hdW; x++) {
                // Diagonal gradient
                uint8_t r = (uint8_t)((x * 255 / hdW + y * 255 / hdH) / 4);
                uint8_t g = (uint8_t)((x * 255 / hdW) / 2 + 64);
                uint8_t b = (uint8_t)((y * 255 / hdH) / 2 + 128);
                // Add grid lines every 128 pixels
                if ((x % 128 < 2) || (y % 128 < 2)) { r=255; g=255; b=255; }
                // Add a distinctive logo area at top-left
                if (x < 400 && y < 200) { r=0; g=200; b=200; }
                hdBackground.at(x, y) = {r, g, b, 0xFF};
            }
        }
    }
    
    void build_room_image() {
        // Fill game screen with base color
        gameScreen.fill_rect(0, 0, gameW, gameH, PAL_BG);
        
        // Draw some "room features" using the base palette (these will be in clean bg)
        draw_room_decorations();
    }
    
    void draw_room_decorations() {
        // Floor at bottom
        gameScreen.fill_rect(0, 400, gameW, gameH, 0x11); // darker gray
        // Wall on left
        gameScreen.fill_rect(0, 0, 80, 400, 0x12); // lighter
        // Window in wall
        gameScreen.fill_rect(20, 80, 60, 180, 0x13); // even lighter
        // A path/road
        gameScreen.fill_rect(300, 380, 500, 400, 0x14); // path
    }
    
    void save_clean_strips(int firstStrip, int numStrips) {
        // Save strips from the game screen as clean reference
        // Strips are in ROOM coordinates, saved at display position = s*8 - xstart
        for (int s = firstStrip; s < firstStrip + numStrips && s * 8 < roomW; s++) {
            int roomX = s * 8;
            int dispX = roomX - xstart; // position in display space
            for (int y = 0; y < gameH && y < gameScreen.h; y++) {
                for (int x = 0; x < 8; x++) {
                    int dx = dispX + x;
                    if (dx >= 0 && dx < cleanBg.w && (roomX + x) < gameScreen.w) {
                        cleanBg.at(dx, y) = gameScreen.at(roomX + x, y);
                        cleanValid[y * cleanBg.w + dx] = 1;
                    }
                }
            }
        }
    }
    
    // ---- Frame simulation ----
    
    void reset_clean() {
        // Reset clean state for a new room load
        memset(cleanValid, 0, gameW * gameH);
        save_clean_strips(0, gameW / 8);
    }
    
    void simulate_frame() {
        frame++;
        
        // 1. Move actor
        actorX = (actorX + 2) % (gameW - 64);
        actorAnimFrame = (frame / 10) % 2; // toggle every 10 frames
        
        // 2. Camera scroll (if room wider than screen)
        if (roomW > gameW) {
            // Camera follows actor, clamped to room bounds
            int targetStart = actorX - gameW/2;
            if (targetStart < 0) targetStart = 0;
            if (targetStart > roomW - gameW) targetStart = roomW - gameW;
            xstart = targetStart;
        }
        
        // 3. Verb highlighting
        hoverVerbIndex = -1;
        if (cursorY >= gameH - 48 && cursorY < gameH) {
            int verbSlot = cursorX / (gameW / 4);
            if (verbSlot >= 0 && verbSlot < 4) hoverVerbIndex = verbSlot;
        }
        
        // 4. Object highlighting
        objectHighlighted = false;
        int objCX = 560, objCY = 400, objR = 20;
        int scaledCX = objCX * hdW / gameW, scaledCY = objCY * hdH / gameH;
        int scaledR = objR * hdW / gameW;
        int cdx = cursorX * hdW / gameW - scaledCX;
        int cdy = cursorY * hdH / gameH - scaledCY;
        if (cdx*cdx + cdy*cdy <= scaledR*scaledR) objectHighlighted = true;
        
        // 5. Build the game screen for this frame
        build_game_frame();
    }
    
    void build_game_frame() {
        // Start from clean room image
        copy_clean_to_game();
        
        // Draw actor
        uint8_t actorColor = (actorAnimFrame == 0) ? PAL_ACTOR : PAL_ACTOR2;
        gameScreen.fill_circle(actorX, actorY, 24, actorColor);
        // Actor's "eyes" — small dots that show orientation
        gameScreen.fill_circle(actorX+4, actorY-4, 4, 0x22);
        gameScreen.fill_circle(actorX-4, actorY-4, 4, 0x22);
        
        // Draw interactive object
        uint8_t objColor = objectHighlighted ? PAL_OBJ_HL : PAL_OBJECT;
        // A square object
        gameScreen.fill_rect(540, 380, 580, 420, objColor);
        gameScreen.fill_rect(545, 385, 575, 415, 0x32); // inner detail
        
        // Draw text overlay if there's text
        if (!textLine.empty()) {
            int tx = textScroll;
            for (size_t i = 0; i < textLine.size() && tx < gameW; i++) {
                if (tx >= 0) {
                    gameScreen.fill_rect(tx, textY, tx+8, textY+12, PAL_TEXT);
                }
                tx += 8;
            }
        }
        
        // Draw verbs at bottom
        for (int i = 0; i < 4; i++) {
            uint8_t vColor = (i == hoverVerbIndex) ? PAL_VERB_HL : PAL_VERB;
            int vx = i * (gameW / 4);
            gameScreen.fill_rect(vx, gameH - 48, vx + gameW/4 - 4, gameH - 4, vColor);
        }
        
        // Draw blast effect (if active)
        if (blastActive) {
            gameScreen.fill_circle(blastX, blastY, 20 + blastFrame * 2, PAL_BLAST);
        }
    }
    
    void copy_clean_to_game() {
        // Copy clean background to game screen
        for (int y = 0; y < gameH; y++) {
            for (int x = 0; x < gameW; x++) {
                gameScreen.at(x, y) = cleanBg.at(x, y);
            }
        }
    }
    
    // ---- Rendering ----
    
    void render(ImageRGBA &output) {
        composite_hd_frame(output, hdBackground, gameScreen, cleanBg, cleanValid,
                           palette, gameW, gameH, roomW, xstart);
    }
    
    void render_with_cursor(ImageRGBA &output) {
        render(output);
        // Draw cursor as an overlay (simulating OGL backend cursor)
        int cx = cursorX * hdW / gameW;
        int cy = cursorY * hdH / gameH;
        output.draw_cursor(cx, cy, {0, 0xFF, 0xFF, 0xFF}); // cyan cursor
    }
    
    // ---- Verification ----
    
    struct CheckResult {
        const char *name;
        bool passed;
        char detail[256];
    };
    
    CheckResult check_pixel(const char *name, const ImageRGBA &img, int x, int y, rgba_t expected) {
        CheckResult r = {name, false, ""};
        if (x < 0 || x >= img.w || y < 0 || y >= img.h) {
            snprintf(r.detail, sizeof(r.detail), "out of bounds (%d,%d) vs (%d,%d)", x, y, img.w, img.h);
            return r;
        }
        rgba_t got = img.at(x, y);
        if (got == expected) {
            r.passed = true;
            snprintf(r.detail, sizeof(r.detail), "OK");
        } else {
            snprintf(r.detail, sizeof(r.detail), "expected (%d,%d,%d,%d) got (%d,%d,%d,%d)",
                     expected.r, expected.g, expected.b, expected.a,
                     got.r, got.g, got.b, got.a);
        }
        return r;
    }
    
    void run_scenario_checks();
};

// ============================================================
// Test scenarios and checks
// ============================================================

void TestRoom::run_scenario_checks() {
    ImageRGBA output(hdW, hdH);
    ImageRGBA output_with_cursor(hdW, hdH);
    
    printf("\n=== Test Room Scenarios ===\n\n");
    
    // ---- Scenario 1: Room background only ----
    printf("--- Scenario 1: Room background only ---\n");
    {
        frame = 0;
        actorX = 100; actorY = 240;
        objectHighlighted = false;
        hoverVerbIndex = -1;
        textLine = "";
        blastActive = false;
        xstart = 0;
        
        build_game_frame();
        render(output);
        
        // HD bg should show in most of the screen
        int pass = 0, fail = 0;
        
        auto c1 = check_pixel("top-left HD bg corner", output, 10, 10, hdBackground.at(10, 10));
        if (c1.passed) pass++; else { fail++; printf("  FAIL: %s: %s\n", c1.name, c1.detail); }
        
        // Floor area should show HD bg (since floor matches clean)
        auto c2 = check_pixel("floor area HD bg", output, 200*4, 410*4, hdBackground.at(200*4, 410*4));
        if (c2.passed) pass++; else { fail++; printf("  FAIL: %s: %s\n", c2.name, c2.detail); }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario1_bg: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Scenario 2: Actor rendering ----
    printf("\n--- Scenario 2: Actor rendering ---\n");
    {
        actorX = 300; actorY = 240;
        actorAnimFrame = 0;
        build_game_frame();
        render(output);
        
        int pass = 0, fail = 0;
        
        // Actor should be visible at scaled position
        int ax = actorX * hdW / gameW;
        int ay = actorY * hdH / gameH;
        rgba_t expectedRed = {0xFF, 0x20, 0x20, 0xFF};
        auto c1 = check_pixel("actor center", output, ax, ay, expectedRed);
        if (c1.passed) pass++; else { fail++; printf("  FAIL: %s: %s\n", c1.name, c1.detail); }
        
        // Area outside actor should be HD bg
        auto c2 = check_pixel("outside actor (top-right)", output, hdW-10, 10, hdBackground.at(hdW-10, 10));
        if (c2.passed) pass++; else { fail++; printf("  FAIL: %s: %s\n", c2.name, c2.detail); }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario2_actor: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Scenario 3: Actor animation frame change ----
    printf("\n--- Scenario 3: Actor animation ---\n");
    {
        ImageRGBA frame1(hdW, hdH);
        ImageRGBA frame2(hdW, hdH);
        
        actorAnimFrame = 0;
        build_game_frame();
        render(frame1);
        
        actorAnimFrame = 1;
        build_game_frame();
        render(frame2);
        
        int pass = 0, fail = 0;
        
        // Frames should differ at actor position
        int ax = actorX * hdW / gameW;
        int ay = actorY * hdH / gameH;
        uint32_t u32_1 = frame1.at(ax, ay).as_u32();
        uint32_t u32_2 = frame2.at(ax, ay).as_u32();
        if (u32_1 != u32_2) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: actor animation: frames identical at (%d,%d): (%d,%d,%d) vs (%d,%d,%d)\n",
                   ax, ay, frame1.at(ax,ay).r, frame1.at(ax,ay).g, frame1.at(ax,ay).b,
                   frame2.at(ax,ay).r, frame2.at(ax,ay).g, frame2.at(ax,ay).b);
        }
        
        // HD bg outside actor should be identical across frames
        int bgx = hdW/2 + 200, bgy = hdH/4;
        if (frame1.at(bgx, bgy).as_u32() == frame2.at(bgx, bgy).as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: HD bg changed across frames at (%d,%d)\n", bgx, bgy);
        }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario3_animation: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Scenario 4: Object highlighting (hotspot) ----
    printf("\n--- Scenario 4: Hotspot / object highlight ---\n");
    {
        ImageRGBA unhighlighted(hdW, hdH);
        ImageRGBA highlighted(hdW, hdH);
        
        objectHighlighted = false;
        build_game_frame();
        render(unhighlighted);
        
        objectHighlighted = true;
        build_game_frame();
        render(highlighted);
        
        int pass = 0, fail = 0;
        
        // Object is at (540,380)-(580,420). Inner detail at (545,385)-(575,415).
        // Check outer-only area: (542, 395) = inside outer but outside inner
        int ox = 542 * hdW / gameW;
        int oy = 395 * hdH / gameH;
        if (unhighlighted.at(ox, oy).as_u32() != highlighted.at(ox, oy).as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: hotspot not changing when highlighted\n");
        }
        
        // Non-object area should be identical
        int nx = 100 * hdW / gameW, ny = 100 * hdH / gameH;
        if (unhighlighted.at(nx, ny).as_u32() == highlighted.at(nx, ny).as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: non-object area changed when highlighting hotspot\n");
        }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario4_hotspot: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Scenario 5: Verb rendering and highlighting ----
    printf("\n--- Scenario 5: Verbs ---\n");
    {
        ImageRGBA noHover(hdW, hdH);
        ImageRGBA hovered(hdW, hdH);
        
        hoverVerbIndex = -1;
        build_game_frame();
        render(noHover);
        
        hoverVerbIndex = 2; // third verb
        build_game_frame();
        render(hovered);
        
        int pass = 0, fail = 0;
        
        // Verb area at bottom
        int vy = (gameH - 24) * hdH / gameH;
        int vx = (2 * gameW / 4 + gameW/8) * hdW / gameW; // middle of third verb
        if (noHover.at(vx, vy).as_u32() != hovered.at(vx, vy).as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: verb highlight not visible\n");
        }
        
        // Non-verb area should be identical
        int nvy = 200 * hdH / gameH;
        if (noHover.at(vx, nvy).as_u32() == hovered.at(vx, nvy).as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: non-verb area changed when highlighting verb\n");
        }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario5_verbs: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Scenario 6: Text overlay ----
    printf("\n--- Scenario 6: Text ---\n");
    {
        ImageRGBA noText(hdW, hdH);
        ImageRGBA withText(hdW, hdH);
        
        textLine = "";
        build_game_frame();
        render(noText);
        
        textLine = "HELLO COMI TEST";
        textScroll = 50;
        build_game_frame();
        render(withText);
        
        int pass = 0, fail = 0;
        
        // Text area should differ
        int tx = (textScroll + 8) * hdW / gameW;
        int ty = (textY + 6) * hdH / gameH;
        if (noText.at(tx, ty).as_u32() != withText.at(tx, ty).as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: text overlay not visible\n");
        }
        
        // Text should be white (PAL_TEXT)
        rgba_t white = {0xFF, 0xFF, 0xFF, 0xFF};
        auto c = check_pixel("text is white", withText, tx, ty, white);
        if (c.passed) pass++; else { fail++; printf("  FAIL: text color: %s\n", c.detail); }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario6_text: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Scenario 7: Cursor overlay ----
    printf("\n--- Scenario 7: Cursor ---\n");
    {
        ImageRGBA noCursor(hdW, hdH);
        ImageRGBA withCursor(hdW, hdH);
        
        cursorX = 400; cursorY = 300;
        render(noCursor);
        render_with_cursor(withCursor);
        
        int pass = 0, fail = 0;
        
        // Cursor area should differ
        int cx = cursorX * hdW / gameW;
        int cy = cursorY * hdH / gameH;
        if (noCursor.at(cx+2, cy+2).as_u32() != withCursor.at(cx+2, cy+2).as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: cursor not visible\n");
        }
        
        // Cursor has cyan color
        rgba_t cyan = {0, 0xFF, 0xFF, 0xFF};
        auto c = check_pixel("cursor is cyan", withCursor, cx+2, cy+2, cyan);
        if (c.passed) pass++; else { fail++; printf("  FAIL: cursor color: %s\n", c.detail); }
        
        // Outside cursor area should be identical
        int ox = 10 * hdW / gameW, oy = 10 * hdH / gameH;
        if (noCursor.at(ox, oy).as_u32() == withCursor.at(ox, oy).as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: non-cursor area changed when cursor drawn\n");
        }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario7_cursor: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Scenario 8: Blast effect ----
    printf("\n--- Scenario 8: Blast effect ---\n");
    {
        ImageRGBA noBlast(hdW, hdH);
        ImageRGBA withBlast(hdW, hdH);
        
        blastActive = false;
        build_game_frame();
        render(noBlast);
        
        blastActive = true;
        blastX = 400; blastY = 300;
        blastFrame = 3;
        build_game_frame();
        render(withBlast);
        
        int pass = 0, fail = 0;
        
        // Blast area should differ
        int bx = blastX * hdW / gameW;
        int by = blastY * hdH / gameH;
        if (noBlast.at(bx, by).as_u32() != withBlast.at(bx, by).as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: blast effect not visible\n");
        }
        
        // Blast should be yellow
        rgba_t yellow = {0xFF, 0xFF, 0, 0xFF};
        auto c = check_pixel("blast is yellow", withBlast, bx, by, yellow);
        if (c.passed) pass++; else { fail++; printf("  FAIL: blast color: %s\n", c.detail); }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario8_blast: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Scenario 9: Scrolling / camera movement ----
    printf("\n--- Scenario 9: Camera scrolling ---\n");
    {
        // Use a wider room
        TestRoom wideRoom(1280);
        wideRoom.xstart = 0;
        wideRoom.build_game_frame();
        wideRoom.render(output);
        
        // Save output before scroll
        ImageRGBA beforeScroll(hdW, hdH);
        memcpy(beforeScroll.pixels, output.pixels, hdW*hdH*sizeof(rgba_t));
        
        // Scroll right
        wideRoom.xstart = 320;
        // Update clean strips for newly visible area
        // The clean strips were saved when xstart=0. After scroll, strips 40-119 are visible
        // (room coords 320-959). We need to save the newly visible strips.
        // For simplicity, re-save all visible strips
        wideRoom.save_clean_strips(wideRoom.xstart / 8, wideRoom.gameW / 8);
        wideRoom.build_game_frame();
        wideRoom.render(output);
        
        int pass = 0, fail = 0;
        
        // After scroll, left edge of output should show different HD background
        rgba_t before = beforeScroll.at(0, 0);
        rgba_t after = output.at(0, 0);
        if (before.as_u32() != after.as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: HD bg didn't shift after scroll\n");
        }
        
        // Verify the HD offset: xstart=320, roomW=1280, hdW=2560
        // Expected HD offset = 320 * 2560 / 1280 = 640
        // So output pixel (0,0) should match HD background at (640, 0)
        rgba_t expected = wideRoom.hdBackground.at(640, 0);
        if (after.as_u32() == expected.as_u32()) {
            pass++;
        } else {
            fail++;
            printf("  FAIL: scroll offset wrong: got (%d,%d,%d) expected (%d,%d,%d)\n",
                   after.r, after.g, after.b, expected.r, expected.g, expected.b);
        }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario9_scroll: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Scenario 10: Multiple layers composited together ----
    printf("\n--- Scenario 10: Full composite ---\n");
    {
        actorX = 200; actorY = 200; actorAnimFrame = 0;
        objectHighlighted = true;
        hoverVerbIndex = 1;
        textLine = "TEST";
        textScroll = 100;
        cursorX = 450; cursorY = 250;
        blastActive = true; blastX = 500; blastY = 100; blastFrame = 5;
        xstart = 0;
        
        build_game_frame();
        render_with_cursor(output_with_cursor);
        
        int pass = 0, fail = 0;
        
        // Check each layer is present
        
        // 1. HD bg in empty area
        rgba_t hdBgColor = hdBackground.at(50*hdW/gameW, 50*hdH/gameH);
        auto c1 = check_pixel("HD bg visible", output_with_cursor, 50*hdW/gameW, 50*hdH/gameH, hdBgColor);
        if (c1.passed) pass++; else { fail++; printf("  FAIL: %s\n", c1.detail); }
        
        // 2. Actor
        rgba_t actorColor = {0xFF, 0x20, 0x20, 0xFF};
        auto c2 = check_pixel("actor visible", output_with_cursor, actorX*hdW/gameW, actorY*hdH/gameH, actorColor);
        if (c2.passed) pass++; else { fail++; printf("  FAIL: %s\n", c2.detail); }
        
        // 3. Object (highlighted) — check outer area not inner detail
        rgba_t objHLColor = {0x80, 0xFF, 0x80, 0xFF};
        auto c3 = check_pixel("object highlighted", output_with_cursor, 542*hdW/gameW, 395*hdH/gameH, objHLColor);
        if (c3.passed) pass++; else { fail++; printf("  FAIL: %s\n", c3.detail); }
        
        // 4. Verb
        rgba_t verbHLColor = {0x80, 0x80, 0xFF, 0xFF};
        auto c4 = check_pixel("verb highlighted", output_with_cursor, (gameW/4+gameW/8)*hdW/gameW, (gameH-24)*hdH/gameH, verbHLColor);
        if (c4.passed) pass++; else { fail++; printf("  FAIL: %s\n", c4.detail); }
        
        // 5. Text
        rgba_t white = {0xFF, 0xFF, 0xFF, 0xFF};
        auto c5 = check_pixel("text visible", output_with_cursor, (textScroll+8)*hdW/gameW, (textY+6)*hdH/gameH, white);
        if (c5.passed) pass++; else { fail++; printf("  FAIL: %s\n", c5.detail); }
        
        // 6. Cursor
        rgba_t cyan = {0, 0xFF, 0xFF, 0xFF};
        auto c6 = check_pixel("cursor visible", output_with_cursor, cursorX*hdW/gameW+2, cursorY*hdH/gameH+2, cyan);
        if (c6.passed) pass++; else { fail++; printf("  FAIL: %s\n", c6.detail); }
        
        // 7. Blast
        rgba_t yellow = {0xFF, 0xFF, 0, 0xFF};
        auto c7 = check_pixel("blast visible", output_with_cursor, blastX*hdW/gameW, blastY*hdH/gameH, yellow);
        if (c7.passed) pass++; else { fail++; printf("  FAIL: %s\n", c7.detail); }
        
        printf("  %d/%d passed\n", pass, pass+fail);
        results.push_back(std::string("scenario10_composite: ") + (fail==0?"PASS":"FAIL"));
    }
    
    // ---- Summary ----
    printf("\n=== Summary ===\n");
    int totalPass = 0, totalFail = 0;
    for (auto &r : results) {
        printf("  %s\n", r.c_str());
        if (r.find("FAIL") != std::string::npos) totalFail++;
        else totalPass++;
    }
    printf("\n  %d scenarios passed, %d failed\n", totalPass, totalFail);
}

// ============================================================
// Main
// ============================================================

int main(int argc, char **argv) {
    bool showWindow = false;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--show") == 0 || strcmp(argv[i], "--show-sdl") == 0)
            showWindow = true;
    }
    
    printf("=== Test Room: Full HD Compositing Pipeline ===\n");
    printf("Game: %dx%d, HD: %dx%d, room: %dx\n", 640, 480, 2560, 1920, 640);
    
    TestRoom room(640); // normal room (non-scrolling)
    room.run_scenario_checks();
    
    // Save the final composite as a raw file for external analysis
    {
        TestRoom saver(640);
        saver.cursorX = 400; saver.cursorY = 300;
        saver.actorX = 200; saver.actorY = 200;
        saver.textLine = "TEST OUTPUT";
        saver.textScroll = 50;
        saver.build_game_frame();
        ImageRGBA final(saver.hdW, saver.hdH);
        saver.render_with_cursor(final);
        FILE *f = fopen("test_room_final.raw", "wb");
        if (f) {
            for (int y = 0; y < saver.hdH; y++)
                fwrite(&final.at(0, y), sizeof(rgba_t), saver.hdW, f);
            fclose(f);
            printf("\nFinal frame saved to test_room_final.raw (%dx%d RGBA)\n", saver.hdW, saver.hdH);
        }
    }
    
    return 0;
}
