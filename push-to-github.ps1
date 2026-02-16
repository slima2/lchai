# Push LCHAI v1 to https://github.com/slima2/lchai.git
# Ejecutar cuando no haya otros procesos git usando este repo (o tras borrar .git\index.lock).

$ErrorActionPreference = "Stop"
Set-Location "d:\Dropbox\PHD\LCHAI v1"

# Quitar lock si quedo de un proceso anterior
$lock = ".git\index.lock"
if (Test-Path $lock) {
    Remove-Item $lock -Force -ErrorAction SilentlyContinue
    if (Test-Path $lock) { Write-Host "Cierra otras ventanas/terminales que usen git y borra manualmente: $lock"; exit 1 }
}

# README ya creado; anadir todo el codigo
git add .
git commit -m "first commit"
git branch -M main
git remote remove origin 2>$null
git remote add origin https://github.com/slima2/lchai.git
git push -u origin main

Write-Host "Listo. Repo: https://github.com/slima2/lchai"
