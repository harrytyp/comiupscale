@echo off
REM Launch ScummVM HD fork
REM Adjust MSYS2_PATH if you installed MSYS2 to a different location.
REM Copy this file next to scummvm.exe and run it from any directory.

set "MSYS2_PATH=C:\msys64\mingw64\bin"
set "FORK_DIR=%~dp0"
for %%i in ("%FORK_DIR%..\..") do set "PROJECT_DIR=%%~fi"

set "PATH=%MSYS2_PATH%;%FORK_DIR%;%PATH%"

REM Create a temporary config with correct absolute paths
echo [scummvm] > "%TEMP%\scummvm-hd.ini"
echo versioninfo=2026.2.1git >> "%TEMP%\scummvm-hd.ini"
echo window_maximized=true >> "%TEMP%\scummvm-hd.ini"
echo. >> "%TEMP%\scummvm-hd.ini"
echo [comi] >> "%TEMP%\scummvm-hd.ini"
echo description=The Curse of Monkey Island (Windows/English) >> "%TEMP%\scummvm-hd.ini"
echo path=%PROJECT_DIR%\game >> "%TEMP%\scummvm-hd.ini"
echo hd_path=%PROJECT_DIR%\assets\upscaled >> "%TEMP%\scummvm-hd.ini"

"%FORK_DIR%scummvm.exe" --config="%TEMP%\scummvm-hd.ini"
