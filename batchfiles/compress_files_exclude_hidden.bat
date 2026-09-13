@echo off
rem Set the path to 7-Zip, output path, & input folder
"C:\Program Files\7-Zip\7z.exe" a "C:\whatever.zip" "C:\New folder\*" -xr!.*
echo Archive created successfully!
pause
