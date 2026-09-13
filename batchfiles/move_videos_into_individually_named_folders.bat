::==========================================================================
:: move_videos_into_individually_named_folders.bat - USER GUIDE
::==========================================================================
:: PURPOSE:
::   Automatically moves each video file in the current directory 
::   into its own individually named folder.
::
:: SUPPORTED VIDEO FORMATS:
::   - MP4, MKV, AVI, MOV, M4V, M2TS, MTS, TS
::   - WMV, ASF, FLV, WEBM, 3GP, OGV, VOB
::   - MPG, MPEG, M2V
::
:: IMPORTANT SAFETY INSTRUCTIONS:
:: 1. ALWAYS backup your files before running this script
:: 2. Run ONLY in the specific directory containing video files
:: 3. Do NOT modify files during script execution
::
:: EXECUTION STEPS:
:: - Double-click batch file
:: - Confirm two warning prompts
:: - Wait for operation to complete
::
:: WHAT THE SCRIPT DOES:
:: - Creates a new folder for each video file
:: - Moves corresponding video file into its folder
:: - Skips hidden files and the batch file itself
::
::   NOTE: If 2 (or more) videos have the same name 
::   (but different extensions), they will both be 
::   placed in the same folder.
::
:: TROUBLESHOOTING:
:: - Ensure you have write permissions in the directory
:: - Close any applications using the video files
::
:: CAUTION: USE AT YOUR OWN RISK
::==========================================================================
@echo off
setlocal enabledelayedexpansion

:: First confirmation dialog
choice /c yn /m "WARNING: This will move all video files in current directory to individual folders. Continue?"
if errorlevel 2 (
    echo Operation canceled
    exit /b
)

:: Second confirmation dialog
choice /c yn /m "Are you ABSOLUTELY sure?"
if errorlevel 2 (
    echo Operation canceled
    exit /b
)

:: Set supported video formats (modify as needed)
set "extensions=*.mp4 *.mkv *.avi *.mov *.m4v *.m2ts *.mts *.ts *.wmv *.asf *.flv *.webm *.3gp *.ogv *.vob *.mpg *.mpeg *.m2v"

:: Process files
for %%f in (%extensions%) do (
    if not "%%~f"=="%~nx0" (
        if not "%%~af"=="*h*" (
            echo Processing %%f...
            mkdir "%%~nf" 2>nul
            move /Y "%%f" "%%~nf" >nul
            if errorlevel 1 (
                echo Failed to move %%f
            ) else (
                echo Moved %%f to %%~nf\
            )
        )
    )
)

:: Completion message
echo.
if errorlevel 1 (
    echo Operation completed with errors
) else (
    echo Operation completed successfully
)
pause
