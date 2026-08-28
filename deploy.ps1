# Redeploy flight-finder to Fly.io. Run from anywhere:  .\deploy.ps1
# (Only rebuild the APK via PWABuilder if you change the app name, icon,
#  package id, or manifest display/orientation/theme.)
$ErrorActionPreference = "Stop"
$proj = $PSScriptRoot
$fly  = "$env:USERPROFILE\.fly\bin\flyctl.exe"

Push-Location $proj
try {
    & $fly deploy --config ./fly.toml --dockerfile ./Dockerfile `
        --app flight-finder-udi --remote-only
    Write-Host ""
    Write-Host "Deployed. Open the app on your phone to see the update." -ForegroundColor Green
    Write-Host "Live: https://flight-finder-udi.fly.dev/"
}
finally {
    Pop-Location
}
