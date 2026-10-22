@echo off
echo ========================================================
echo  Secure P2P Client - Windows Standalone Executable Build
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH!
    echo Please install Python 3.9+ from https://python.org and ensure "Add Python to PATH" is checked.
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

echo.
echo [2/3] Building standalone Windows executable (SecureClient.exe)...
pyinstaller --onefile --windowed --noconfirm --paths src --name "SecureClient" main.py

echo.
if exist "dist\SecureClient.exe" (
    echo ========================================================
    echo [SUCCESS] Build completed!
    echo Your Windows application is located at:
    echo %CD%\dist\SecureClient.exe
    echo.
    echo Share SecureClient.exe with your friends on your LAN!
    echo ========================================================
) else (
    echo [ERROR] Build failed. Please inspect the log output above.
)

pause
