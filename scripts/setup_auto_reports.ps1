# PowerShell script to set up automatic Trackman report generation
# This sets up a file watcher for a specific game/series

param(
    [Parameter(Mandatory=$true)]
    [string]$WatchDirectory,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputDirectory,
    
    [string]$Pitcher,
    [string]$Opponent,
    [string]$Game,
    [string]$Date
)

Write-Host "Setting up automatic Trackman report generation..." -ForegroundColor Green
Write-Host "Watch Directory: $WatchDirectory" -ForegroundColor Cyan
Write-Host "Output Directory: $OutputDirectory" -ForegroundColor Cyan

# Build command
$cmd = "python scripts\watch_trackman.py `"$WatchDirectory`" --output `"$OutputDirectory`""

if ($Pitcher) {
    $cmd += " --pitcher `"$Pitcher`""
}
if ($Opponent) {
    $cmd += " --opponent `"$Opponent`""
}
if ($Game) {
    $cmd += " --game `"$Game`""
}
if ($Date) {
    $cmd += " --date `"$Date`""
}

Write-Host "`nStarting file watcher..." -ForegroundColor Yellow
Write-Host "Drop Trackman CSV files into: $WatchDirectory" -ForegroundColor Yellow
Write-Host "Reports will be generated in: $OutputDirectory" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

# Run the watcher
Invoke-Expression $cmd

