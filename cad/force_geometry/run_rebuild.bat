@echo off
set FREECAD_PYTHON=C:\Users\user\AppData\Local\Programs\FreeCAD 1.1\bin\python.exe
set SCRIPT=E:\Projects\REV\cad\force_geometry\rebuild.py
set OUTPUT=E:\Projects\REV\cad\source\force_geometry_rebuild

if exist "%OUTPUT%" rmdir /s /q "%OUTPUT%"

"%FREECAD_PYTHON%" "%SCRIPT%" --out "%OUTPUT%"
