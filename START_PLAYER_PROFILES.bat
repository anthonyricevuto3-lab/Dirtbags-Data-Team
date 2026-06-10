@echo off
echo ========================================
echo Long Beach State Dirtbags
echo Player Profile System
echo ========================================
echo.
echo This will:
echo   1. Process all CSV files in 'RawCSVs' folder
echo   2. Create/update player profiles
echo   3. Generate PDF reports for each player
echo   4. Watch for new CSV files automatically
echo.
echo Drop CSV files into the 'RawCSVs' folder to process them.
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

python scripts\process_player_profiles.py

pause

