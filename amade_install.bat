@echo off

REM Set variables for the GitHub repository and the output folder
set REPO_OWNER=JadKaedBey
set REPO_NAME=OperativoDataImportConsole
set BRANCH=main
set TARGET_DIR=%cd%\%REPO_NAME%

REM Download the GitHub repository as a ZIP file
echo Downloading the repository as a ZIP file...
powershell -Command "Invoke-WebRequest -Uri https://github.com/%REPO_OWNER%/%REPO_NAME%/archive/refs/heads/%BRANCH%.zip -OutFile %REPO_NAME%.zip"

REM Create a directory for the repository files
echo Creating directory %TARGET_DIR%...
mkdir %TARGET_DIR%

REM Extract the ZIP file to the target directory
echo Extracting the ZIP file...
powershell -Command "Expand-Archive -Path '%REPO_NAME%.zip' -DestinationPath '%TARGET_DIR%'"

REM Move all files and directories from the subfolder (e.g., "OperativoDataImportConsole-main") to the target directory
echo Moving files and folders...
xcopy "%TARGET_DIR%\%REPO_NAME%-%BRANCH%\*" "%TARGET_DIR%\" /E /H /Y

REM Delete the subfolder created by extraction
rd /S /Q "%TARGET_DIR%\%REPO_NAME%-%BRANCH%"

REM Delete the ZIP file
del /Q %REPO_NAME%.zip

REM Remove all files and folders except "amade" folder
echo Deleting everything except the amade folder...
for /D %%d in (%TARGET_DIR%\*) do (
    if /I "%%~nxd" neq "amade" rd /S /Q "%%d"
)
for %%f in (%TARGET_DIR%\*) do (
    if /I "%%~nxf" neq "amade" del /Q "%%f"
)

echo Operation completed successfully.

pause
