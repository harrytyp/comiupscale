@echo off
pushd %~dp0
scummvm.exe --config=scummvm.ini --path=game --renderer=opengl --record-mode=playback --record-file-name=%1 comi
if errorlevel 1 pause
popd
