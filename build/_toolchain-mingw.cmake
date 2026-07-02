# COMI-HD — CMake Toolchain for MinGW cross-compile
# Used by _build-sdl2-mingw.sh
#
# Points to the LLVM MinGW toolchain in build/install/llvm-mingw/

# Detect the toolchain path relative to this file's location
get_filename_component(_CMAKE_SCRIPT_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)
get_filename_component(_BUILD_DIR "${_CMAKE_SCRIPT_DIR}" REALPATH)
get_filename_component(_INSTALL_DIR "${_BUILD_DIR}/install" REALPATH)

set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

set(TOOLCHAIN_DIR "${_INSTALL_DIR}/llvm-mingw")

set(CMAKE_C_COMPILER   "${TOOLCHAIN_DIR}/bin/x86_64-w64-mingw32-gcc"   CACHE PATH "C compiler")
set(CMAKE_CXX_COMPILER "${TOOLCHAIN_DIR}/bin/x86_64-w64-mingw32-g++"   CACHE PATH "C++ compiler")
set(CMAKE_RC_COMPILER  "${TOOLCHAIN_DIR}/bin/x86_64-w64-mingw32-windres" CACHE PATH "RC compiler")

set(CMAKE_FIND_ROOT_PATH
    "${TOOLCHAIN_DIR}/x86_64-w64-mingw32"
    "${_INSTALL_DIR}/sdl2-mingw"
    "${_INSTALL_DIR}/mingw-prefix"
)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
