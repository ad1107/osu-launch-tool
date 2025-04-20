@echo off
setlocal

set SCRIPT_NAME=main.py
set BASE_NAME=main
set APP_NAME=osu!LaunchTool
set ICON_NAME=logo.ico

set /p ver="Enter version number (e.g., 1.0.0): "
if "%ver%"=="" (
    echo [ERROR] Version number cannot be empty.
    goto :error_exit
)
cls

echo [INFO] Checking for Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Please ensure Python is installed and added to PATH.
    goto :error_exit
)

echo [INFO] Ensuring Nuitka and required packages are installed...
pip install --upgrade nuitka zstandard ordered-set || (
    echo [ERROR] Failed to install/update Nuitka or its dependencies.
    goto :error_exit
)
cls

echo [INFO] Building executable with Nuitka (this may take some time)...

python -m nuitka ^
    --onefile ^
    --standalone ^
    --windows-console-mode=disable ^
    --windows-uac-admin ^
    --enable-plugin=tk-inter ^
    --include-package-data=customtkinter ^
    --windows-icon-from-ico="%ICON_NAME%" ^
    --output-filename="%APP_NAME%-%ver%.exe" ^
    "%SCRIPT_NAME%"

:: Check if Nuitka build failed
if errorlevel 1 (
    echo [ERROR] Nuitka build process failed. Check the output above for details.
    goto :error_exit
)
cls

if not exist "%APP_NAME%-%ver%.exe" (
    echo [ERROR] Build seemed to succeed, but the final executable "%APP_NAME%-%ver%.exe" was not found.
    goto :error_exit
)

echo [INFO] Cleaning up build artifacts...
if exist "%BASE_NAME%.build" rmdir /s /q "%BASE_NAME%.build"
if exist "%BASE_NAME%.onefile-build" rmdir /s /q "%BASE_NAME%.onefile-build"
if exist "%BASE_NAME%.dist" rmdir /s /q "%BASE_NAME%.dist"
del /q *.pyi > nul 2>&1
del /q *.nuitka > nul 2>&1

cls
echo [SUCCESS] Build complete: %APP_NAME%-%ver%.exe
echo Located in the project root directory.
goto :end

:error_exit
echo [INFO] Build process terminated due to errors.
pause
exit /b 1

:end
pause
exit /b 0