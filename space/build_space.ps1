# Assemble the Hugging Face Space folder from your Obelus repo.
# Usage (from C:\dev\clauselens):  .\space\build_space.ps1
param([string]$Repo = "C:\dev\clauselens", [string]$Out = "C:\dev\obelus-space")
$ErrorActionPreference = "Stop"
if (-not (Test-Path "$Repo\src\api.py")) { throw "api.py not found in $Repo\src" }
if (-not (Test-Path "$Repo\web\index.html")) { throw "web\index.html not found in $Repo" }

New-Item -ItemType Directory -Force "$Out\src", "$Out\web" | Out-Null
foreach ($f in "service.py","api.py","limits.py","extract.py","llm.py","chunk.py","baseline_bm25.py","evaluate.py") {
    Copy-Item "$Repo\src\$f" "$Out\src\$f" -Force
}
Copy-Item "$Repo\web\index.html" "$Out\web\index.html" -Force
Copy-Item "$Repo\requirements.txt" "$Out\requirements.txt" -Force
Copy-Item "$Repo\space\README.md" "$Out\README.md" -Force

# Same Dockerfile, plus demo mode switched on (smaller inputs, per-visitor and daily limits).
$d = (Get-Content "$Repo\Dockerfile" -Raw) -replace "EXPOSE 8080", "ENV OBELUS_DEMO=1`nEXPOSE 8080"
[System.IO.File]::WriteAllText("$Out\Dockerfile", $d, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Space folder ready: $Out"
