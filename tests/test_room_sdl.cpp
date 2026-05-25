// test_room_sdl.cpp
// Same test room as test_room.cpp but with an SDL2 window for visual inspection.
// Shows each scenario sequentially at the press of a key.
//
// Compile:
//   PATH="/c/msys64/mingw64/bin:$PATH" && g++ -std=c++17 -O2 -o test_room_sdl.exe test_room_sdl.cpp -I/c/msys64/mingw64/include -L/c/msys64/mingw64/lib -lSDL2
// Run:
//   ./test_room_sdl.exe

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <string>
#include <vector>
#include <algorithm>
#include <SDL.h>

// ============================================================
// Same types as test_room.cpp
// ============================================================

struct rgba_t {
    uint8_t r, g, b, a;
    bool operator==(const rgba_t &o) const { return r==o.r && g==o.g && b==o.b && a==o.a; }
    bool operator!=(const rgba_t &o) const { return !(*this == o); }
    uint32_t as_u32() const { return (uint32_t)r|((uint32_t)g<<8)|((uint32_t)b<<16)|((uint32_t)a<<24); }
};

struct Image8 {
    int w, h; uint8_t *pixels;
    Image8(int w_, int h_, uint8_t fill=0) : w(w_), h(h_) {
        pixels=new uint8_t[w*h]; memset(pixels,fill,w*h);
    }
    ~Image8(){delete[]pixels;}
    uint8_t&at(int x,int y){return pixels[y*w+x];}
    const uint8_t&at(int x,int y)const{return pixels[y*w+x];}
    void fill_rect(int x0,int y0,int x1,int y1,uint8_t v) {
        for(int y=std::max(0,y0);y<std::min(h,y1);y++)
            for(int x=std::max(0,x0);x<std::min(w,x1);x++) at(x,y)=v;
    }
    void fill_circle(int cx,int cy,int r,uint8_t v) {
        for(int dy=-r;dy<=r;dy++) for(int dx=-r;dx<=r;dx++)
            if(dx*dx+dy*dy<=r*r){int px=cx+dx,py=cy+dy;if(px>=0&&px<w&&py>=0&&py<h)at(px,py)=v;}
    }
};

struct ImageRGBA {
    int w, h; rgba_t *pixels;
    ImageRGBA(int w_,int h_,rgba_t fill={0,0,0,0}) : w(w_),h(h_) {
        pixels=new rgba_t[w*h]; for(int i=0;i<w*h;i++)pixels[i]=fill;
    }
    ~ImageRGBA(){delete[]pixels;}
    rgba_t&at(int x,int y){return pixels[y*w+x];}
    const rgba_t&at(int x,int y)const{return pixels[y*w+x];}
    void fill_rect(int x0,int y0,int x1,int y1,rgba_t v) {
        for(int y=std::max(0,y0);y<std::min(h,y1);y++)
            for(int x=std::max(0,x0);x<std::min(w,x1);x++) at(x,y)=v;
    }
    void fill_circle(int cx,int cy,int r,rgba_t v) {
        for(int dy=-r;dy<=r;dy++) for(int dx=-r;dx<=r;dx++)
            if(dx*dx+dy*dy<=r*r){int px=cx+dx,py=cy+dy;if(px>=0&&px<w&&py>=0&&py<h)at(px,py)=v;}
    }
    void draw_cursor(int x,int y,rgba_t color) {
        for(int i=0;i<12;i++) for(int j=i;j<12;j++) {
            int px=x+j,py=y+i;
            if(px>=0&&px<w&&py>=0&&py<h)at(px,py)=color;
        }
    }
    // Nearest-neighbor scale to new size
    void scale_to(const ImageRGBA &src) {
        for (int dy=0;dy<h;dy++) { int sy=dy*src.h/h;
            for (int dx=0;dx<w;dx++) { int sx=dx*src.w/w;
                at(dx,dy)=src.at(sx,sy);
            }
        }
    }
};

// ============================================================
// HD Compositor
// ============================================================

void composite_hd_frame(ImageRGBA &output, const ImageRGBA &hdBg, const Image8 &game,
                        const Image8 &cleanBg, const uint8_t *cleanValid,
                        const uint8_t *palette, int gameW, int gameH,
                        int roomW, int xstart) {
    int hdW=output.w, hdH=output.h;
    int64_t camOff=(int64_t)xstart*hdW/std::max(1,roomW);
    if(camOff<0)camOff=0; if(camOff>=hdW)camOff=hdW-1;
    int cOff=(int)camOff;
    for(int y=0;y<hdH;y++) {
        int64_t srcY=(int64_t)y*hdBg.h/hdH;
        if(srcY<0)srcY=0; if(srcY>=hdBg.h)srcY=hdBg.h-1;
        int cw=(int)std::min(hdW,hdBg.w-cOff);
        if(cw>0) {
            memcpy(&output.at(0,y),&hdBg.at(cOff,(int)srcY),cw*sizeof(rgba_t));
            if(cw<hdW)memset(&output.at(cw,y),0,(hdW-cw)*sizeof(rgba_t));
        } else memset(&output.at(0,y),0,hdW*sizeof(rgba_t));
    }
    int visW=std::min(gameW,game.w), visH=std::min(gameH,game.h);
    for(int dy=0;dy<hdH;dy++) {
        int sy=dy*visH/hdH; if(sy<0)sy=0; if(sy>=visH)sy=visH-1;
        for(int dx=0;dx<hdW;dx++) {
            int sx=dx*visW/hdW; if(sx<0)sx=0; if(sx>=visW)sx=visW-1;
            int gx=xstart+sx; if(gx<0)gx=0; if(gx>=game.w)gx=game.w-1;
            int gy=sy; if(gy<0)gy=0; if(gy>=game.h)gy=game.h-1;
            uint8_t curPix=game.at(gx,gy);
            bool isForeground=true;
            if(cleanValid&&sy<visH) {
                int pos=sy*visW+sx;
                if(cleanValid[pos]) isForeground=(curPix!=cleanBg.at(sx,sy));
            }
            if(isForeground) {
                const uint8_t *p=&palette[curPix*3];
                output.at(dx,dy)={p[0],p[1],p[2],0xFF};
            }
        }
    }
}

// ============================================================
// Test Room
// ============================================================

static constexpr uint8_t PAL_BG=0x10, PAL_ACTOR=0x20, PAL_ACTOR2=0x21;
static constexpr uint8_t PAL_OBJECT=0x30, PAL_OBJ_HL=0x31;
static constexpr uint8_t PAL_TEXT=0x40, PAL_VERB=0x50, PAL_VERB_HL=0x51;
static constexpr uint8_t PAL_BLAST=0x60;

struct TestRoom {
    int gameW=640, gameH=480, roomW=640, hdW=2560, hdH=1920;
    ImageRGBA hdBackground{hdW,hdH};
    Image8 gameScreen{gameW,gameH};
    Image8 cleanBg{gameW,gameH};
    uint8_t *cleanValid=nullptr;
    uint8_t palette[768];
    int frame=0, actorX=100, actorY=240, actorAnimFrame=0;
    bool objectHighlighted=false;
    int hoverVerbIndex=-1, cursorX=320, cursorY=240;
    std::string textLine; int textScroll=0, textY=20;
    int xstart=0; bool blastActive=false; int blastX=0,blastY=0,blastFrame=0;
    
    TestRoom(int rw=640) : roomW(rw) {
        cleanValid=new uint8_t[gameW*gameH]();
        build_palette(); build_hd_background(); build_room_image();
        save_clean_strips(0,roomW/8);
    }
    ~TestRoom(){delete[]cleanValid;}
    
    void build_palette() {
        for(int i=0;i<256;i++){palette[i*3]=(i*37)&0xFF;palette[i*3+1]=(i*71)&0xFF;palette[i*3+2]=(i*113)&0xFF;}
        palette[PAL_BG*3]=0x60;palette[PAL_BG*3+1]=0x60;palette[PAL_BG*3+2]=0x60;
        palette[PAL_ACTOR*3]=0xFF;palette[PAL_ACTOR*3+1]=0x20;palette[PAL_ACTOR*3+2]=0x20;
        palette[PAL_ACTOR2*3]=0xFF;palette[PAL_ACTOR2*3+1]=0x80;palette[PAL_ACTOR2*3+2]=0x20;
        palette[PAL_OBJECT*3]=0x20;palette[PAL_OBJECT*3+1]=0xFF;palette[PAL_OBJECT*3+2]=0x20;
        palette[PAL_OBJ_HL*3]=0x80;palette[PAL_OBJ_HL*3+1]=0xFF;palette[PAL_OBJ_HL*3+2]=0x80;
        palette[PAL_TEXT*3]=0xFF;palette[PAL_TEXT*3+1]=0xFF;palette[PAL_TEXT*3+2]=0xFF;
        palette[PAL_VERB*3]=0x40;palette[PAL_VERB*3+1]=0x40;palette[PAL_VERB*3+2]=0xFF;
        palette[PAL_VERB_HL*3]=0x80;palette[PAL_VERB_HL*3+1]=0x80;palette[PAL_VERB_HL*3+2]=0xFF;
        palette[PAL_BLAST*3]=0xFF;palette[PAL_BLAST*3+1]=0xFF;palette[PAL_BLAST*3+2]=0x00;
    }
    
    void build_hd_background() {
        for(int y=0;y<hdH;y++) for(int x=0;x<hdW;x++) {
            uint8_t r=(uint8_t)((x*255/hdW+y*255/hdH)/4);
            uint8_t g=(uint8_t)((x*255/hdW)/2+64);
            uint8_t b=(uint8_t)((y*255/hdH)/2+128);
            if((x%128<2)||(y%128<2)){r=255;g=255;b=255;}
            if(x<400&&y<200){r=100;g=200;b=220;}
            hdBackground.at(x,y)={r,g,b,0xFF};
        }
    }
    
    void build_room_image() {
        gameScreen.fill_rect(0,0,gameW,gameH,PAL_BG);
        gameScreen.fill_rect(0,400,gameW,gameH,0x11);
        gameScreen.fill_rect(0,0,80,400,0x12);
        gameScreen.fill_rect(20,80,60,180,0x13);
        gameScreen.fill_rect(300,380,500,400,0x14);
    }
    
    void save_clean_strips(int firstStrip, int numStrips) {
        for(int s=firstStrip;s<firstStrip+numStrips&&s*8<roomW;s++) {
            int roomX=s*8, dispX=roomX-xstart;
            for(int y=0;y<gameH&&y<gameScreen.h;y++)
                for(int x=0;x<8;x++) {
                    int dx=dispX+x;
                    if(dx>=0&&dx<cleanBg.w&&(roomX+x)<gameScreen.w) {
                        cleanBg.at(dx,y)=gameScreen.at(roomX+x,y);
                        cleanValid[y*cleanBg.w+dx]=1;
                    }
                }
        }
    }
    
    void copy_clean_to_game() {
        for(int y=0;y<gameH;y++) memcpy(&gameScreen.at(0,y),&cleanBg.at(0,y),gameW);
    }
    
    void reset_clean() { memset(cleanValid,0,gameW*gameH); save_clean_strips(0,roomW/8); }
    
    void fill_with_test_pattern() {
        copy_clean_to_game();
        uint8_t actorColor=(actorAnimFrame==0)?PAL_ACTOR:PAL_ACTOR2;
        gameScreen.fill_circle(actorX,actorY,24,actorColor);
        gameScreen.fill_circle(actorX+4,actorY-4,4,0x22);
        gameScreen.fill_circle(actorX-4,actorY-4,4,0x22);
        uint8_t objColor=objectHighlighted?PAL_OBJ_HL:PAL_OBJECT;
        gameScreen.fill_rect(540,380,580,420,objColor);
        gameScreen.fill_rect(545,385,575,415,0x32);
        if(!textLine.empty()){
            int tx=textScroll;
            for(size_t i=0;i<textLine.size()&&tx<gameW;i++) {
                if(tx>=0) gameScreen.fill_rect(tx,textY,tx+8,textY+12,PAL_TEXT);
                tx+=8;
            }
        }
        for(int i=0;i<4;i++){
            uint8_t vc=(i==hoverVerbIndex)?PAL_VERB_HL:PAL_VERB;
            int vx=i*(gameW/4);
            gameScreen.fill_rect(vx,gameH-48,vx+gameW/4-4,gameH-4,vc);
        }
        if(blastActive) gameScreen.fill_circle(blastX,blastY,20+blastFrame*2,PAL_BLAST);
    }
    
    void render(ImageRGBA &out) { composite_hd_frame(out,hdBackground,gameScreen,cleanBg,cleanValid,palette,gameW,gameH,roomW,xstart); }
    void render_with_cursor(ImageRGBA &out) {
        render(out);
        int cx=cursorX*out.w/gameW, cy=cursorY*out.h/gameH;
        out.draw_cursor(cx,cy,{0,0xFF,0xFF,0xFF});
    }
};

// ============================================================
// SDL display + keyboard control
// ============================================================

static const char *scenario_names[] = {
    "1: Room background only",
    "2: Actor rendering",
    "3: Actor animation (cycling)",
    "4: Hotspot / object highlight",
    "5: Verb rendering",
    "6: Text overlay",
    "7: Cursor overlay",
    "8: Blast effect",
    "9: Camera scrolling",
    "10: All layers combined",
    "Q: Quit"
};
static const int NUM_SCENARIOS = 10;

struct ScenarioState {
    int current = 0;
    bool auto_advance = false;
    int frame_counter = 0;
    TestRoom room{640};
    TestRoom wideRoom{1280};
    ImageRGBA display{2560, 1920};
    ImageRGBA scaled_display{1280, 960}; // window size
    SDL_Window *window = nullptr;
    SDL_Renderer *renderer = nullptr;
    SDL_Texture *texture = nullptr;
    
    bool init() {
        if (SDL_Init(SDL_INIT_VIDEO) < 0) { printf("SDL_Init failed: %s\n", SDL_GetError()); return false; }
        window = SDL_CreateWindow("COMI Test Room - HD Compositing Pipeline", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, 1280, 960, SDL_WINDOW_SHOWN);
        if (!window) { printf("SDL_CreateWindow failed: %s\n", SDL_GetError()); return false; }
        renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE);
        if (!renderer) { printf("SDL_CreateRenderer failed: %s\n", SDL_GetError()); return false; }
        texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_STREAMING, 1280, 960);
        if (!texture) { printf("SDL_CreateTexture failed: %s\n", SDL_GetError()); return false; }
        return true;
    }
    
    void setup_scenario(int n) {
        current = n;
        TestRoom &r = (n == 8) ? wideRoom : room;
        
        // Reset everything
        memset(r.cleanValid, 0, r.gameW * r.gameH);
        r.xstart = 0;
        r.actorX = 100; r.actorY = 240;
        r.objectHighlighted = false;
        r.hoverVerbIndex = -1;
        r.cursorX = 320; r.cursorY = 240;
        r.textLine = "";
        r.blastActive = false;
        r.frame = 0;
        
        // Room bg: rebuild room image fresh
        r.build_room_image();
        r.save_clean_strips(0, r.roomW / 8);
        
        switch (n) {
            case 1: break; // just room bg
            case 2: r.actorX = 300; r.actorY = 240; break;
            case 3: r.actorX = 300; r.actorY = 240; r.actorAnimFrame = 0; break;
            case 4: r.objectHighlighted = true; break;
            case 5: r.hoverVerbIndex = 2; break;
            case 6: r.textLine = "HELLO WORLD - TEST TEXT!"; r.textScroll = 60; break;
            case 7: r.cursorX = 400; r.cursorY = 300; break;
            case 8: r.blastActive = true; r.blastX = 400; r.blastY = 300; r.blastFrame = 4; break;
            case 9: // scrolling
                r.roomW = 1280; r.xstart = 320;
                r.build_room_image();
                r.save_clean_strips(r.xstart / 8, 80);
                break;
            case 10: // all layers
                r.actorX = 200; r.actorY = 200; r.actorAnimFrame = 0;
                r.objectHighlighted = true;
                r.hoverVerbIndex = 1;
                r.textLine = "FULL TEST"; r.textScroll = 80;
                r.cursorX = 480; r.cursorY = 180;
                r.blastActive = true; r.blastX = 500; r.blastY = 100; r.blastFrame = 5;
                break;
        }
        
        r.fill_with_test_pattern();
        if (n == 7 || n == 10) r.render_with_cursor(display);
        else r.render(display);
        
        if (n == 8) { // scroll animation - camera moves
            r.xstart = 0;
            r.build_room_image();
            r.save_clean_strips(0, 80);
        }
    }
    
    void advance_animation() {
        TestRoom &r = (current == 8) ? wideRoom : room;
        r.frame++;
        
        // Animate actor movement
        r.actorX = (r.actorX + 1) % (r.gameW - 64);
        if (r.frame % 15 == 0) r.actorAnimFrame ^= 1;
        
        // Animate scrolling room
        if (current == 8) {
            r.xstart = (int)((sin(r.frame * 0.02) + 1) * 0.5 * (r.roomW - r.gameW));
            r.build_room_image();
            r.save_clean_strips(r.xstart / 8, 80);
        }
        
        r.fill_with_test_pattern();
        if (current == 7 || current == 10) r.render_with_cursor(display);
        else r.render(display);
    }
    
    void present() {
        // Scale display to window size
        scaled_display.scale_to(display);
        
        // Update SDL texture
        SDL_UpdateTexture(texture, nullptr, scaled_display.pixels, 1280 * 4);
        SDL_RenderClear(renderer);
        SDL_RenderCopy(renderer, texture, nullptr, nullptr);
        SDL_RenderPresent(renderer);
    }
    
    void run() {
        setup_scenario(1);
        bool quit = false;
        Uint32 last_tick = SDL_GetTicks();
        
        while (!quit) {
            SDL_Event e;
            while (SDL_PollEvent(&e)) {
                if (e.type == SDL_QUIT) quit = true;
                if (e.type == SDL_KEYDOWN) {
                    switch (e.key.keysym.sym) {
                        case SDLK_1: case SDLK_KP_1: setup_scenario(1); break;
                        case SDLK_2: case SDLK_KP_2: setup_scenario(2); break;
                        case SDLK_3: case SDLK_KP_3: setup_scenario(3); break;
                        case SDLK_4: case SDLK_KP_4: setup_scenario(4); break;
                        case SDLK_5: case SDLK_KP_5: setup_scenario(5); break;
                        case SDLK_6: case SDLK_KP_6: setup_scenario(6); break;
                        case SDLK_7: case SDLK_KP_7: setup_scenario(7); break;
                        case SDLK_8: case SDLK_KP_8: setup_scenario(8); break;
                        case SDLK_9: case SDLK_KP_9: setup_scenario(9); break;
                        case SDLK_0: case SDLK_KP_0: setup_scenario(10); break;
                        case SDLK_q: case SDLK_ESCAPE: quit = true; break;
                        case SDLK_a: auto_advance = !auto_advance; break;
                        case SDLK_SPACE: advance_animation(); break;
                        case SDLK_RIGHT: setup_scenario((current % 10) + 1); break;
                        default: break;
                    }
                }
            }
            
            present();
            
            if (auto_advance) {
                Uint32 now = SDL_GetTicks();
                if (now - last_tick > 50) { // 20 fps
                    advance_animation();
                    last_tick = now;
                }
            }
            
            SDL_Delay(16); // ~60 fps
        }
    }
    
    ~ScenarioState() {
        if (texture) SDL_DestroyTexture(texture);
        if (renderer) SDL_DestroyRenderer(renderer);
        if (window) SDL_DestroyWindow(window);
        SDL_Quit();
    }
};

int main(int argc, char **argv) {
    printf("=== COMI Test Room: HD Compositing Pipeline ===\n");
    printf("Keys: 1-10 = scenario, SPACE = step anim, A = auto-animate\n");
    printf("       RIGHT = next scenario, Q/ESC = quit\n\n");
    printf("Scenarios:\n");
    for (auto n : scenario_names) printf("  %s\n", n);
    printf("\n");
    
    ScenarioState ss;
    if (!ss.init()) return 1;
    ss.run();
    return 0;
}
