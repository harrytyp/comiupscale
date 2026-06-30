@echo off
REM COMI-Upscaled — Start Script (Windows)
REM 
REM 1. Edit GAME_PATH below to your COMI game folder
REM 2. Run this batch file

set SCUMMVM_DIR=%~dp0
set GAME_PATH=C:\Pfad\zu\COMI  REM ← Bitte anpassen!

start "" "%SCUMMVM_DIR%\scummvm.exe" ^
    --config="%SCUMMVM_DIR%\scummvm.ini" ^
    --path="%GAME_PATH%" ^
    --renderer=opengl ^
    comi
