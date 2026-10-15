$ErrorActionPreference = 'Stop'
$dockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
$dockerExe = if ($dockerCommand) { $dockerCommand.Source } else { Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe' }
function Invoke-LabDocker {
    param([string[]]$Arguments)
    $preferencia = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $dockerExe @Arguments
        $codigoSaida = $LASTEXITCODE
    } finally { $ErrorActionPreference = $preferencia }
    if ($codigoSaida -ne 0) { throw "Docker terminou com codigo $codigoSaida" }
}
