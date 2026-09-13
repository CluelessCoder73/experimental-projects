@echo off
setlocal

rem ============================================================
rem Create a ZIP archive while excluding:
rem   1. Names beginning with a dot, which is commonly used for hidden files and folders
rem   2. Any folder named "older_versions", including its contents
rem   3. Files with the extensions .jpg and .png
rem
rem Notes:
rem   - Folder names are matched anywhere below the source folder.
rem   - Extension filters are recursive and case-insensitive.
rem   - Add more exclusions by adding more -xr! switches.
rem ============================================================

rem Path to 7-Zip
set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"

rem Output ZIP file
set "OUTPUT=C:\GitHub.zip"

rem Folder to archive
set "SOURCE=C:\Users\User\Documents\GitHub\*"

"%SEVENZIP%" a "%OUTPUT%" "%SOURCE%" ^
    -xr!.* ^
    -xr!older_versions ^
    -xr!*.jpg ^
    -xr!*.png

if errorlevel 1 (
    echo Failed to create the archive.
) else (
    echo Archive created successfully:
    echo "%OUTPUT%"
)

pause
endlocal
