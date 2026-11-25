$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $projectRoot '.venv/Scripts/python.exe'
$pythonw = Join-Path $projectRoot '.venv/Scripts/pythonw.exe'
$taskName = 'Data Monitoring Platform - Bajs Collector'

if (-not (Test-Path -LiteralPath $pythonw -PathType Leaf)) {
    throw 'Create .venv and install the project first. See README.md.'
}

Push-Location $projectRoot
try {
    & $python -m data_monitoring check-config | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'The Python environment or configuration could not be loaded.'
    }
} finally {
    Pop-Location
}

$userName = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$taskAction = @{
    Execute = $pythonw
    WorkingDirectory = $projectRoot
    Argument = '-m data_monitoring watch --keep-awake --log-file data/bajs-collector.log'
}
$taskSettings = @{
    AllowStartIfOnBatteries = $true
    DontStopIfGoingOnBatteries = $true
    ExecutionTimeLimit = [TimeSpan]::Zero
    MultipleInstances = 'IgnoreNew'
    RestartCount = 3
    RestartInterval = (New-TimeSpan -Minutes 1)
}
$task = @{
    TaskName = $taskName
    TaskPath = '\'
    Action = (New-ScheduledTaskAction @taskAction)
    Trigger = (New-ScheduledTaskTrigger -AtLogOn -User $userName)
    Principal = (New-ScheduledTaskPrincipal -UserId $userName -LogonType Interactive -RunLevel Limited)
    Settings = (New-ScheduledTaskSettingsSet @taskSettings)
}

$existingTask = Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue
if ($existingTask.State -eq 'Running') {
    Stop-ScheduledTask -InputObject $existingTask
}

Register-ScheduledTask @task -Force | Out-Null
Start-ScheduledTask -TaskName $taskName -TaskPath '\'
Get-ScheduledTask -TaskName $taskName -TaskPath '\' | Select-Object TaskName, State
