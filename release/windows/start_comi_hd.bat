@echo off
pushd %~dp0
scummvm.exe --config=scummvm.ini --path="%CD%\game" --renderer=opengl comi
if errorlevel 1 pause
popd
