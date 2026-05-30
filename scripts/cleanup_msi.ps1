#Requires -RunAsAdministrator
<#
.MSI C-Drive Cleanup Scanner
============================
Scans C:\ for video games and Ableton installations, reports sizes,
and optionally removes them after confirmation.

ELI5: Like pulling every circuit breaker in the panel one by one,
      reading the label, checking the amp draw, and ONLY cutting
      power to the ones you actually want off.

Usage:
    .\cleanup_msi.ps1              # Scan-only mode (default)
    .\cleanup_msi.ps1 -Execute     # Actually delete after confirming each item
#>
param(
    [switch]$Execute,
    [switch]$MoveToD,              # Move Steam/Epic libraries to D:\ instead of deleting
    [string]$MoveTarget = "D:\\Games"
)

$ErrorActionPreference = 'SilentlyContinue'
$host.UI.RawUI.WindowTitle = "MSI C-Drive Cleanup"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Get-FolderSize($Path) {
    if (-not (Test-Path $Path)) { return 0 }
    $bytes = (Get-ChildItem $Path -Recurse -Force -ErrorAction SilentlyContinue | 
        Measure-Object -Property Length -Sum).Sum
    return [math]::Round($bytes / 1GB, 2)
}

function Write-Header($Text) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-SizeLine($Name, $SizeGB, $Path) {
    $color = if ($SizeGB -gt 50) { 'Red' } elseif ($SizeGB -gt 10) { 'Yellow' } else { 'Green' }
    Write-Host ("  {0,-40} {1,8} GB  {2}" -f $Name, $SizeGB, $Path) -ForegroundColor $color
}

function Request-Confirmation($ItemName, $SizeGB, $Path) {
    if (-not $Execute) { return $false }
    Write-Host "`n>>> DELETE: $ItemName (${SizeGB} GB) at $Path" -ForegroundColor Red
    $resp = Read-Host "    Type 'yes' to permanently delete, anything else to skip"
    return ($resp -eq 'yes')
}

# ---------------------------------------------------------------------------
# Disk overview
# ---------------------------------------------------------------------------
Write-Header "C: Drive Overview"
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$freeGB  = [math]::Round($disk.FreeSpace / 1GB, 2)
$totalGB = [math]::Round($disk.Size / 1GB, 2)
$usedGB  = $totalGB - $freeGB
$pctFree = [math]::Round(($freeGB / $totalGB) * 100, 1)
Write-Host "  Total: ${totalGB} GB | Used: ${usedGB} GB | Free: ${freeGB} GB (${pctFree}%)"

if ($pctFree -lt 10) {
    Write-Host "  ⚠️  CRITICAL: Less than 10% free space remaining!" -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# Steam
# ---------------------------------------------------------------------------
Write-Header "Steam Games"
$steamPaths = @(
    "C:\Program Files (x86)\Steam\steamapps\common",
    "C:\Program Files\Steam\steamapps\common"
)
$steamTotal = 0
$steamGames = @()

foreach ($sp in $steamPaths) {
    if (Test-Path $sp) {
        Get-ChildItem $sp -Directory | ForEach-Object {
            $sz = Get-FolderSize $_.FullName
            $steamTotal += $sz
            $steamGames += [PSCustomObject]@{ Name = $_.Name; SizeGB = $sz; Path = $_.FullName }
        }
    }
}

if ($steamGames.Count -eq 0) {
    Write-Host "  No Steam library found on C:"
} else {
    Write-Host "  Found $($steamGames.Count) Steam game folders (${steamTotal} GB total)`n"
    $steamGames | Sort-Object SizeGB -Descending | ForEach-Object {
        Write-SizeLine $_.Name $_.SizeGB $_.Path
        if (Request-Confirmation "Steam game: $($_.Name)" $_.SizeGB $_.Path) {
            Remove-Item $_.Path -Recurse -Force
            Write-Host "    [DELETED]" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Epic Games
# ---------------------------------------------------------------------------
Write-Header "Epic Games"
$epicPath = "C:\Program Files\Epic Games"
$epicGames = @()
$epicTotal = 0

if (Test-Path $epicPath) {
    Get-ChildItem $epicPath -Directory | ForEach-Object {
        $sz = Get-FolderSize $_.FullName
        $epicTotal += $sz
        $epicGames += [PSCustomObject]@{ Name = $_.Name; SizeGB = $sz; Path = $_.FullName }
    }
}

if ($epicGames.Count -eq 0) {
    Write-Host "  No Epic Games installations found on C:"
} else {
    Write-Host "  Found $($epicGames.Count) Epic game folders (${epicTotal} GB total)`n"
    $epicGames | Sort-Object SizeGB -Descending | ForEach-Object {
        Write-SizeLine $_.Name $_.SizeGB $_.Path
        if (Request-Confirmation "Epic game: $($_.Name)" $_.SizeGB $_.Path) {
            Remove-Item $_.Path -Recurse -Force
            Write-Host "    [DELETED]" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# EA / Origin
# ---------------------------------------------------------------------------
Write-Header "EA / Origin Games"
$eaPaths = @(
    "C:\Program Files\EA Games",
    "C:\Program Files (x86)\EA Games",
    "C:\Program Files\Origin Games",
    "C:\Program Files (x86)\Origin Games"
)
$eaTotal = 0
$eaGames = @()

foreach ($ep in $eaPaths) {
    if (Test-Path $ep) {
        Get-ChildItem $ep -Directory | ForEach-Object {
            $sz = Get-FolderSize $_.FullName
            $eaTotal += $sz
            $eaGames += [PSCustomObject]@{ Name = $_.Name; SizeGB = $sz; Path = $_.FullName }
        }
    }
}

if ($eaGames.Count -eq 0) {
    Write-Host "  No EA/Origin games found on C:"
} else {
    Write-Host "  Found $($eaGames.Count) EA/Origin game folders (${eaTotal} GB total)`n"
    $eaGames | Sort-Object SizeGB -Descending | ForEach-Object {
        Write-SizeLine $_.Name $_.SizeGB $_.Path
        if (Request-Confirmation "EA/Origin game: $($_.Name)" $_.SizeGB $_.Path) {
            Remove-Item $_.Path -Recurse -Force
            Write-Host "    [DELETED]" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Battle.net
# ---------------------------------------------------------------------------
Write-Header "Battle.net Games"
$bnetPaths = @(
    "C:\Program Files (x86)\Battle.net",
    "C:\Program Files\Battle.net"
)
$bnetTotal = 0
$bnetGames = @()

foreach ($bp in $bnetPaths) {
    if (Test-Path $bp) {
        Get-ChildItem $bp -Directory | ForEach-Object {
            # Skip the launcher itself
            if ($_.Name -eq 'Battle.net Launcher') { return }
            $sz = Get-FolderSize $_.FullName
            $bnetTotal += $sz
            $bnetGames += [PSCustomObject]@{ Name = $_.Name; SizeGB = $sz; Path = $_.FullName }
        }
    }
}

if ($bnetGames.Count -eq 0) {
    Write-Host "  No Battle.net installations found on C:"
} else {
    Write-Host "  Found $($bnetGames.Count) Battle.net game folders (${bnetTotal} GB total)`n"
    $bnetGames | Sort-Object SizeGB -Descending | ForEach-Object {
        Write-SizeLine $_.Name $_.SizeGB $_.Path
        if (Request-Confirmation "Battle.net game: $($_.Name)" $_.SizeGB $_.Path) {
            Remove-Item $_.Path -Recurse -Force
            Write-Host "    [DELETED]" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Ubisoft Connect
# ---------------------------------------------------------------------------
Write-Header "Ubisoft Connect Games"
$ubiPaths = @(
    "C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\games",
    "C:\Program Files\Ubisoft\Ubisoft Game Launcher\games"
)
$ubiTotal = 0
$ubiGames = @()

foreach ($up in $ubiPaths) {
    if (Test-Path $up) {
        Get-ChildItem $up -Directory | ForEach-Object {
            $sz = Get-FolderSize $_.FullName
            $ubiTotal += $sz
            $ubiGames += [PSCustomObject]@{ Name = $_.Name; SizeGB = $sz; Path = $_.FullName }
        }
    }
}

if ($ubiGames.Count -eq 0) {
    Write-Host "  No Ubisoft games found on C:"
} else {
    Write-Host "  Found $($ubiGames.Count) Ubisoft game folders (${ubiTotal} GB total)`n"
    $ubiGames | Sort-Object SizeGB -Descending | ForEach-Object {
        Write-SizeLine $_.Name $_.SizeGB $_.Path
        if (Request-Confirmation "Ubisoft game: $($_.Name)" $_.SizeGB $_.Path) {
            Remove-Item $_.Path -Recurse -Force
            Write-Host "    [DELETED]" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Xbox / Game Pass
# ---------------------------------------------------------------------------
Write-Header "Xbox / Game Pass Games"
$xboxPaths = @(
    "C:\XboxGames",
    "C:\Program Files\WindowsApps"
)
$xboxTotal = 0
$xboxGames = @()

foreach ($xp in $xboxPaths) {
    if (Test-Path $xp) {
        Get-ChildItem $xp -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $sz = Get-FolderSize $_.FullName
            if ($sz -gt 0.5) {  # Filter tiny system folders
                $xboxTotal += $sz
                $xboxGames += [PSCustomObject]@{ Name = $_.Name; SizeGB = $sz; Path = $_.FullName }
            }
        }
    }
}

if ($xboxGames.Count -eq 0) {
    Write-Host "  No Xbox/Game Pass games found on C:"
} else {
    Write-Host "  Found $($xboxGames.Count) Xbox game folders (${xboxTotal} GB total)`n"
    $xboxGames | Sort-Object SizeGB -Descending | ForEach-Object {
        Write-SizeLine $_.Name $_.SizeGB $_.Path
        if (Request-Confirmation "Xbox game: $($_.Name)" $_.SizeGB $_.Path) {
            Remove-Item $_.Path -Recurse -Force
            Write-Host "    [DELETED]" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Ableton Live
# ---------------------------------------------------------------------------
Write-Header "Ableton Live Installations"
$abletonPaths = @(
    "C:\ProgramData\Ableton",
    "C:\Program Files\Ableton",
    "C:\Program Files (x86)\Ableton"
)
$abletonInstalls = @()
$abletonTotal = 0

foreach ($ap in $abletonPaths) {
    if (Test-Path $ap) {
        Get-ChildItem $ap -Directory | ForEach-Object {
            $sz = Get-FolderSize $_.FullName
            $abletonTotal += $sz
            $abletonInstalls += [PSCustomObject]@{ Name = $_.Name; SizeGB = $sz; Path = $_.FullName }
        }
    }
}

# Also check for Live application folders
Get-ChildItem "C:\Program Files" -Directory -Filter "Ableton Live*" | ForEach-Object {
    $sz = Get-FolderSize $_.FullName
    $abletonTotal += $sz
    $abletonInstalls += [PSCustomObject]@{ Name = $_.Name; SizeGB = $sz; Path = $_.FullName }
}
Get-ChildItem "C:\Program Files (x86)" -Directory -Filter "Ableton Live*" | ForEach-Object {
    $sz = Get-FolderSize $_.FullName
    $abletonTotal += $sz
    $abletonInstalls += [PSCustomObject]@{ Name = $_.Name; SizeGB = $sz; Path = $_.FullName }
}

if ($abletonInstalls.Count -eq 0) {
    Write-Host "  No Ableton installations found on C:"
} else {
    Write-Host "  Found $($abletonInstalls.Count) Ableton folders (${abletonTotal} GB total)`n"
    $abletonInstalls | Sort-Object SizeGB -Descending | ForEach-Object {
        Write-SizeLine $_.Name $_.SizeGB $_.Path
        if (Request-Confirmation "Ableton: $($_.Name)" $_.SizeGB $_.Path) {
            # Try to run official uninstaller first
            $uninstaller = Get-ChildItem $_.Path -Filter "unins*.exe" -Recurse | Select-Object -First 1
            if ($uninstaller) {
                Write-Host "    Running uninstaller: $($uninstaller.FullName)" -ForegroundColor Yellow
                Start-Process $uninstaller.FullName -ArgumentList "/SILENT" -Wait
            } else {
                Remove-Item $_.Path -Recurse -Force
            }
            Write-Host "    [REMOVED]" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Header "Summary"
$grandTotal = $steamTotal + $epicTotal + $eaTotal + $bnetTotal + $ubiTotal + $xboxTotal + $abletonTotal
Write-Host "  Total space identified: ${grandTotal} GB"
Write-Host "  Scan mode: $(if ($Execute) { 'EXECUTE (deletions enabled)' } else { 'SCAN-ONLY (no files deleted)' })"

if (-not $Execute) {
    Write-Host "`n  To actually delete items, re-run as Administrator with -Execute flag:" -ForegroundColor Yellow
    Write-Host "    .\cleanup_msi.ps1 -Execute" -ForegroundColor Yellow
}

Write-Host "`n  Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
