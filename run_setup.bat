@echo off
title Zenith Setup Wizard
cd /d "%~dp0electron_dashboard"
if exist ".\node_modules\.bin\electron.cmd" (
  call ".\node_modules\.bin\electron.cmd" . --setup
) else (
  call npx electron . --setup
)
