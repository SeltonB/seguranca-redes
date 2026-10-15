param([switch]$SemBuild)
. (Join-Path $PSScriptRoot 'docker-comum.ps1')
$lab = $PSScriptRoot
$workspace = Split-Path $lab -Parent
$compose = @('compose','-f',"$lab\compose.yaml",'-f',"$lab\compose.portal.yaml")
if (-not $SemBuild) {
    Invoke-LabDocker -Arguments @('run','--rm','--mount',"type=bind,source=$workspace,target=/workspace",'python:3.12-alpine','python','/workspace/laboratorio-mcp/preparar_sqlmap.py')
    Invoke-LabDocker -Arguments @('build','-t','sqlmap-mcp:atividade',"$lab\build\sqlmap")
    Invoke-LabDocker -Arguments ($compose + @('build','portal-vulneravel'))
}
Invoke-LabDocker -Arguments ($compose + @('up','-d','--wait','--wait-timeout','60','portal-vulneravel','portal-seguro'))
# Acrescenta a entrada ao modelo local, mantendo as entradas existentes.
$configPath = Join-Path $lab 'mcp-config.local.json'
$config = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
$entry = [pscustomobject]@{
    command=$dockerExe
    args=@('run','-i','--rm','--network','mcp-atividade-lab','-v','mcp-atividade-sqlmap-output:/app/output','sqlmap-mcp:atividade')
}
$config.mcpServers | Add-Member -MemberType NoteProperty -Name 'sqlmap-atividade' -Value $entry -Force
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 20), $utf8)
Write-Output 'Portal vulneravel: http://127.0.0.1:8081 | Corrigido: http://127.0.0.1:8082'
Write-Output 'Configuracao MCP local atualizada. A configuracao do Claude e aplicada separadamente.'
