# Requer as imagens :atividade ja construidas. Nao configura cliente de IA.
$ErrorActionPreference = 'Stop'
$lab = $PSScriptRoot
$dockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
$dockerExe = if ($dockerCommand) { $dockerCommand.Source } else { Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe' }
function Invoke-Docker {
    param([string[]]$Arguments)
    # Windows PowerShell 5 interpreta stderr nativo como ErrorRecord.
    $preferencia = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $dockerExe @Arguments
        $codigoSaida = $LASTEXITCODE
    } finally { $ErrorActionPreference = $preferencia }
    if ($codigoSaida -ne 0) { throw "Docker terminou com codigo $codigoSaida" }
}
function Test-MCP {
    param([string]$Modulo, [string]$Etapa)
    Invoke-Docker -Arguments @('run','--rm','--network','mcp-atividade-lab',
        '--mount',"type=bind,source=$lab,target=/lab,readonly",
        '--mount',"type=bind,source=$lab\evidencias,target=/evidencias",
        '--mount',"type=bind,source=$lab\templates,target=/lab-templates,readonly",
        '-e','NUCLEI_TEMPLATES_PATH=/lab-templates',
        '-v',"mcp-atividade-${Modulo}-output:/app/output",
        "${Modulo}-mcp:atividade",'python','/lab/verificar_mcp.py',$Modulo,$Etapa)
}
$publico = Join-Path $lab 'site\backup-demo.txt'
$privado = Join-Path $lab 'backup-demo.txt'
if (-not (Test-Path -LiteralPath $publico)) { throw 'O arquivo ficticio deve estar em site/ para iniciar o ensaio.' }
if (Test-Path -LiteralPath $privado) { throw 'Ja existe backup-demo.txt fora de site/; revise antes de mover.' }
New-Item -ItemType Directory -Force -Path "$lab\evidencias" | Out-Null
Invoke-Docker -Arguments @('compose','-f',"$lab\compose.yaml",'up','-d','--wait','--wait-timeout','60')
$antes = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/backup-demo.txt'
if ($antes.StatusCode -ne 200 -or $antes.Content -notmatch 'LAB_MCP_EXPOSICAO_CONFIRMADA') { throw 'Resposta inicial inesperada' }
@{Status=[int]$antes.StatusCode; Body=$antes.Content} | ConvertTo-Json | Set-Content "$lab\evidencias\http-antes.json" -Encoding UTF8
Invoke-Docker -Arguments @('run','--rm','--mount',"type=bind,source=$lab,target=/lab,readonly",'nuclei-mcp:atividade','python','/lab/verificar_erro_nuclei.py')
Test-MCP -Modulo nmap -Etapa antes
Test-MCP -Modulo nuclei -Etapa antes
$movido = $false
try {
    Move-Item -LiteralPath $publico -Destination $privado
    $movido = $true
    $statusDepois = 0
    try { $statusDepois = [int](Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/backup-demo.txt').StatusCode }
    catch { if ($_.Exception.Response) { $statusDepois = [int]$_.Exception.Response.StatusCode } else { throw } }
    if ($statusDepois -ne 404) { throw "Esperado HTTP 404 depois da correcao, recebido $statusDepois" }
    @{Status=$statusDepois} | ConvertTo-Json | Set-Content "$lab\evidencias\http-depois.json" -Encoding UTF8
    Test-MCP -Modulo nuclei -Etapa depois
} finally {
    if ($movido) { Move-Item -LiteralPath $privado -Destination $publico }
}
$restaurado = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/backup-demo.txt'
if ($restaurado.StatusCode -ne 200) { throw 'Falha ao restaurar o cenario de demonstracao' }
$resumo = @{
    Data=(Get-Date -Format o); Resultado='aprovado'; HTTPAntes=200; HTTPDepois=404; HTTPRestaurado=200
    MCPNmap='service_scan validado, porta 8000 aberta'; MCPNuclei='1 exposicao antes; 0 depois'
    Regressoes='codigo de erro, stdin isolado e encerramento por timeout validados'
    LLM='nao configurada nem testada'; EstadoFinal='alvo ativo; arquivo ficticio restaurado para ensaio'
}
$resumo | ConvertTo-Json | Set-Content "$lab\evidencias\resumo.json" -Encoding UTF8
$resumo | ConvertTo-Json
