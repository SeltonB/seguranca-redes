$ErrorActionPreference = 'Stop'
$lab = $PSScriptRoot
$repo = Join-Path (Split-Path $lab -Parent) 'mcp-security-hub-master\mcp-security-hub-master'
$utf8 = New-Object System.Text.UTF8Encoding($false)
foreach ($item in @(@{Nome='nmap'; Origem='reconnaissance\nmap-mcp'}, @{Nome='nuclei'; Origem='web-security\nuclei-mcp'})) {
    $destino = Join-Path $lab ('build\' + $item.Nome)
    New-Item -ItemType Directory -Force -Path $destino | Out-Null
    foreach ($arquivo in @('Dockerfile', 'server.py', 'requirements.txt')) {
        Copy-Item -LiteralPath (Join-Path (Join-Path $repo $item.Origem) $arquivo) -Destination (Join-Path $destino $arquivo) -Force
    }
    [IO.File]::WriteAllText((Join-Path $destino 'requirements.txt'), "mcp==1.30.0`npydantic==2.14.1`npydantic-settings==2.16.0`n", $utf8)
}
$nuclei = Join-Path $lab 'build\nuclei\server.py'
$codigo = [IO.File]::ReadAllText($nuclei)
$condicao = 'if process.returncode == 0 or len(result.findings) >= 0:'
if (-not $codigo.Contains($condicao)) { throw 'Condicao Nuclei mudou; revisar patch antes de construir.' }
$codigo = $codigo.Replace($condicao, 'if process.returncode == 0:')
# O laboratorio usa apenas o template local, sem atualizacoes ou Interactsh.
$codigo = $codigo.Replace('"-silent",', '"-silent", "-duc", "-ni",')
# O scanner nao deve ler o stdin reservado ao protocolo MCP.
$codigo = $codigo.Replace('stdout=asyncio.subprocess.PIPE,', "stdin=asyncio.subprocess.DEVNULL,`n            stdout=asyncio.subprocess.PIPE,")
$codigo = $codigo.Replace('except asyncio.TimeoutError:', "except asyncio.TimeoutError:`n        if process.returncode is None:`n            process.kill()`n            await process.communicate()")
[IO.File]::WriteAllText($nuclei, $codigo, $utf8)
Write-Output 'Contextos preparados em laboratorio-mcp/build; originais preservados.'
