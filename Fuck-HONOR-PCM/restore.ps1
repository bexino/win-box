# ---------------------------------------------------------------------------------
# Script Name: RestoreHonorSilentUpdate.ps1
# Description: One-click script to revert all blocker strategies and restore defaults
# ---------------------------------------------------------------------------------

# 1. Run as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    Exit
}

Write-Host "Running with Administrator privileges. Reverting blocker strategies..." -ForegroundColor Green

# 2. Revert Registry Values (Delete custom blocker keys)
$RegConfigs = @(
    @{ Path = "SOFTWARE\HONOR\MagicClaw\Setting"; Key = "IdleUpgrade" },
    @{ Path = "SOFTWARE\HONOR\AIAssistant\Setting\Local"; Key = "ServicePermission" },
    @{ Path = "SOFTWARE\HONOR\AIAssistant\Setting\Local"; Key = "AutoDownload" },
    @{ Path = "SOFTWARE\HONOR\HUNTERCAMP"; Key = "ServicePermission" },
    @{ Path = "SOFTWARE\HONOR\HUNTERCAMP"; Key = "AutoDownload" },
    @{ Path = "SOFTWARE\HONOR\AIAssistant\AISearch"; Key = "ServicePermission" },
    @{ Path = "SOFTWARE\HONOR\AIAssistant\AISearch"; Key = "AutoDownload" },
    @{ Path = "SOFTWARE\Microsoft\Windows\CurrentVersion\Hihonornote"; Key = "SuitsService" },
    @{ Path = "SOFTWARE\Microsoft\Windows\CurrentVersion\Hihonornote"; Key = "AgreeSilentUpdate" },
    @{ Path = "SOFTWARE\DataMigration\HonorLoginGuide"; Key = "Protocol" }
)

Write-Host "Reverting registry blocker policies..." -ForegroundColor Cyan
foreach ($config in $RegConfigs) {
    Remove-ItemProperty -Path "HKCU:\$($config.Path)" -Name $config.Key -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path "HKLM:\$($config.Path)" -Name $config.Key -ErrorAction SilentlyContinue
}
Write-Host "Registry policies reverted successfully." -ForegroundColor Green

# 3. Restore Hosts File
$HostsPath = "$env:windir\System32\drivers\etc\hosts"
$BackupPath = "$HostsPath.bak"

Write-Host "Restoring Hosts file configuration..." -ForegroundColor Cyan
if (Test-Path $BackupPath) {
    # If backup exists, copy it back to original
    Copy-Item -Path $BackupPath -Destination $HostsPath -Force
    Write-Host "Hosts file successfully restored from backup (hosts.bak)." -ForegroundColor Green
} else {
    # If backup doesn't exist, remove block lines manually
    if (Test-Path $HostsPath) {
        $HostsContent = Get-Content -Path $HostsPath -Raw -ErrorAction SilentlyContinue
        # Regex to remove block section
        $CleanedContent = $HostsContent -replace "(?ms)#\s*\[Honor\s+PCManager\s+Silent\s+Update\s+Block\].*?$" , ""
        Set-Content -Path $HostsPath -Value $CleanedContent.TrimEnd() -Force
        Write-Host "Block domains removed from Hosts file manually." -ForegroundColor Green
    }
}

# 4. Terminate active processes and restart services to apply changes
Write-Host "Restarting background services to apply changes..." -ForegroundColor Cyan
$ProcessNames = @("PCManager", "PCManagerTray", "HnUpdateService", "HnRSMService", "HnFrontNavigator", "HnMagicClawUI")
foreach ($proc in $ProcessNames) {
    Stop-Process -Name $proc -Force -ErrorAction SilentlyContinue
}

Stop-Service -Name "HnUpdateService" -Force -ErrorAction SilentlyContinue
Stop-Service -Name "HnRSMService" -Force -ErrorAction SilentlyContinue
ipconfig /flushdns | Out-Null

Write-Host "All blocker strategies reverted! Honor PCManager default behaviors restored." -ForegroundColor Green
Write-Host "Exiting in 3 seconds..." -ForegroundColor DarkGray
Start-Sleep -Seconds 3
