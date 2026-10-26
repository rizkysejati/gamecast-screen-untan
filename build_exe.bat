@echo off
cd /d "%~dp0"
echo === Membuat GameCast.exe ===
python -m pip install pyinstaller qrcode pillow
python -m PyInstaller --noconsole --onefile --name GameCast gamecast.py
if not exist dist\GameCast.exe (
  echo GAGAL membuat exe. Kirim pesan error di atas ke Claude.
  pause
  exit /b 1
)
if exist GameCast_Siap rmdir /s /q GameCast_Siap
mkdir GameCast_Siap
copy dist\GameCast.exe GameCast_Siap\ >nul
if exist scrcpy xcopy scrcpy GameCast_Siap\scrcpy\ /e /i /q >nul
if exist logo.png copy logo.png GameCast_Siap\ >nul
echo.
echo SELESAI. Folder siap pakai: GameCast_Siap
echo Copy folder itu ke laptop panitia, lalu klik dua kali GameCast.exe
pause
