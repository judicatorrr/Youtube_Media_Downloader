$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$MinMajor = 3
$MinMinor = 11
$FallbackPythonVersion = "3.12.10"

function Test-PythonExe([string]$Exe) {
    if (-not $Exe) { return $false }
    if (-not (Test-Path $Exe) -and -not (Get-Command $Exe -ErrorAction SilentlyContinue)) {
        return $false
    }

    try {
        $version = & $Exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        $parts = $version.Trim().Split(".")
        if ($parts.Count -lt 2) { return $false }

        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        return (($major -gt $MinMajor) -or (($major -eq $MinMajor) -and ($minor -ge $MinMinor)))
    }
    catch {
        return $false
    }
}

function Find-Python {
    $candidates = @()

    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $resolved = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $resolved) {
                $candidates += $resolved.Trim()
            }
        } catch {}
        try {
            $resolved = & py -3 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $resolved) {
                $candidates += $resolved.Trim()
            }
        } catch {}
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        $candidates += $python.Source
    }

    $candidates += @(
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python314\python.exe",
        "$env:ProgramFiles\Python313\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (Test-PythonExe $candidate) {
            return $candidate
        }
    }

    return $null
}

function Install-Python {
    Write-Host ""
    Write-Host "Python 3.11+ not found. Installing Python automatically..." -ForegroundColor Yellow

    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        try {
            & winget install `
                --id Python.Python.3.12 `
                -e `
                --silent `
                --accept-package-agreements `
                --accept-source-agreements

            $found = Find-Python
            if ($found) { return $found }
        }
        catch {
            Write-Host "winget installation failed, trying direct installer..." -ForegroundColor Yellow
        }
    }

    $arch = $env:PROCESSOR_ARCHITECTURE
    $asset = if ($arch -eq "ARM64") {
        "python-$FallbackPythonVersion-arm64.exe"
    } else {
        "python-$FallbackPythonVersion-amd64.exe"
    }

    $url = "https://www.python.org/ftp/python/$FallbackPythonVersion/$asset"
    $installer = Join-Path $env:TEMP $asset

    Write-Host "Downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

    Write-Host "Installing Python $FallbackPythonVersion..."
    $args = @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_pip=1",
        "Include_launcher=1",
        "Include_test=0",
        "Shortcuts=0"
    )

    $process = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
    Remove-Item $installer -Force -ErrorAction SilentlyContinue

    if ($process.ExitCode -ne 0) {
        throw "Python installer exited with code $($process.ExitCode)"
    }

    $found = Find-Python
    if (-not $found) {
        throw "Python installation completed, but python.exe could not be found."
    }
    return $found
}

try {
    $python = Find-Python
    if (-not $python) {
        $python = Install-Python
    }

    Write-Host "Python: $python" -ForegroundColor Green

    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

    if ((Test-Path $venvPython) -and -not (Test-PythonExe $venvPython)) {
        Write-Host "Old Python detected in .venv. Recreating environment..." -ForegroundColor Yellow
        Remove-Item ".venv" -Recurse -Force
    }

    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating virtual environment..."
        & $python -m venv ".venv"
        if ($LASTEXITCODE -ne 0) {
            throw "Could not create .venv"
        }
    }

    Write-Host "Installing/updating Python packages..."
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip update failed" }

    & $venvPython -m pip install -r "requirements.txt"
    if ($LASTEXITCODE -ne 0) { throw "requirements installation failed" }

    Write-Host ""
    Write-Host "Checking yt-dlp / FFmpeg / FFprobe / Deno..."
    & $venvPython "bootstrap_dependencies.py"

    Write-Host ""
    Write-Host "Starting YouTube Media Downloader..." -ForegroundColor Green
    & $venvPython "main.py"
}
catch {
    Write-Host ""
    Write-Host "Startup failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}
