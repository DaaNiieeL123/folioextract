@echo off
cd /d %~dp0\..\..
echo ====================================================
echo Construyendo FolioExtract (pywebview + React + FastAPI)
echo ====================================================

echo.
echo [1/3] Compilando frontend React...
call npm --prefix frontend run build
if %errorlevel% neq 0 (
    echo Error durante la compilacion del frontend.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] Empaquetando ejecutable FolioExtract.exe...
python scripts\build\build_exe.py
if %errorlevel% neq 0 (
    echo Error durante la compilacion del ejecutable.
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Build completado.
echo El ejecutable se encuentra en: dist\FolioExtract\FolioExtract.exe
echo.
pause
