// test_room_debug.cpp
// Quick debug tool to dump HD background and composite pixels for analysis.
// Compile: PATH="/c/msys64/mingw64/bin:$PATH" && g++ -std=c++17 -O2 -o test_room_debug.exe test_room_debug.cpp && ./test_room_debug.exe
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <algorithm>

struct rgba_t {
    uint8_t r,g,b,a;
    bool operator==(const rgba_t &o) const { return r==o.r&&g==o.g&&b==o.b&&a==o.a; }
};

struct ImageRGBA {
    int w,h;
    rgba_t *pixels;
    ImageRGBA(int w_,int h_,rgba_t fill={0,0,0,0}) : w(w_),h(h_) {
        pixels=new rgba_t[w*h]; for(int i=0;i<w*h;i++)pixels[i]=fill;
    }
    ~ImageRGBA(){delete[]pixels;}
    rgba_t&at(int x,int y){return pixels[y*w+x];}
    const rgba_t&at(int x,int y)const{return pixels[y*w+x];}
};

int main() {
    int hdW=2560, hdH=1920;
    ImageRGBA hd(hdW, hdH);
    
    // Same HD bg builder as test_room
    for (int y=0;y<hdH;y++) for(int x=0;x<hdW;x++) {
        uint8_t r=(uint8_t)((x*255/hdW+y*255/hdH)/4);
        uint8_t g=(uint8_t)((x*255/hdW)/2+64);
        uint8_t b=(uint8_t)((y*255/hdH)/2+128);
        if((x%128<2)||(y%128<2)){r=255;g=255;b=255;}
        if(x<400&&y<200){r=0;g=200;b=200;}
        hd.at(x,y)={r,g,b,0xFF};
    }
    
    printf("HD bg at (640,0):   (%d,%d,%d,%d)\n",hd.at(640,0).r,hd.at(640,0).g,hd.at(640,0).b,hd.at(640,0).a);
    printf("HD bg at (639,0):   (%d,%d,%d,%d)\n",hd.at(639,0).r,hd.at(639,0).g,hd.at(639,0).b,hd.at(639,0).a);
    printf("HD bg at (641,0):   (%d,%d,%d,%d)\n",hd.at(641,0).r,hd.at(641,0).g,hd.at(641,0).b,hd.at(641,0).a);
    printf("HD bg at (0,0):     (%d,%d,%d,%d)\n",hd.at(0,0).r,hd.at(0,0).g,hd.at(0,0).b,hd.at(0,0).a);
    printf("HD bg at (127,0):   (%d,%d,%d,%d)\n",hd.at(127,0).r,hd.at(127,0).g,hd.at(127,0).b,hd.at(127,0).a);
    printf("HD bg at (128,0):   (%d,%d,%d,%d)\n",hd.at(128,0).r,hd.at(128,0).g,hd.at(128,0).b,hd.at(128,0).a);
    printf("HD bg at (640,100): (%d,%d,%d,%d)\n",hd.at(640,100).r,hd.at(640,100).g,hd.at(640,100).b,hd.at(640,100).a);
    
    // Check scenario 9 HD offset
    printf("\nCamera scroll hdW=%d roomW=1280 xstart=320\n", hdW);
    int camOff = 320 * hdW / 1280; // = 640
    printf("camOff=%d\n", camOff);
    printf("HD at camOff=%d, y=0: (%d,%d,%d)\n", camOff, hd.at(camOff,0).r, hd.at(camOff,0).g, hd.at(camOff,0).b);
    
    // The output pixel at (0,0) should equal HD at (camOff, 0) = (640, 0)
    // If HD at (640,0) is white (grid line), output should be white
    
    // Check scenario 10: what palette index produces (58,222,18)?
    printf("\nPalette lookup for (58,222,18):\n");
    for (int idx = 0; idx < 256; idx++) {
        uint8_t r=(idx*37)&0xFF, g=(idx*71)&0xFF, b=(idx*113)&0xFF;
        if (r==58 && g==222 && b==18)
            printf("  idx=%d (%.2X): r=%d g=%d b=%d  MATCH\n", idx, idx, r, g, b);
    }
    printf("  (no exact match in auto palette)\n");
    
    // Check what color PAL_OBJ_HL (0x31) should be
    printf("\nPAL_OBJ_HL (0x31): default=(%d,%d,%d), should be overridden to (128,255,128)\n",
           (0x31*37)&0xFF, (0x31*71)&0xFF, (0x31*113)&0xFF);
    
    return 0;
}
