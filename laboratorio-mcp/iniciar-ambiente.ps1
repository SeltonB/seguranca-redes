# Executar depois de abrir o Docker Desktop. Reutiliza as imagens existentes.
. (Join-Path $PSScriptRoot 'docker-comum.ps1')
$lab = $PSScriptRoot
$compose = @('compose', '-f', "$lab\compose.yaml", '-f', "$lab\compose.portal.yaml")
Invoke-LabDocker -Arguments ($compose + @('up', '-d', '--no-build', '--wait', '--wait-timeout', '60'))
Invoke-LabDocker -Arguments ($compose + @('ps'))
foreach ($url in @('http://127.0.0.1:8080/', 'http://127.0.0.1:8081/health', 'http://127.0.0.1:8082/health')) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 10
    if ([int]$response.StatusCode -ne 200) { throw "Resposta inesperada em $url" }
    Write-Output "$url -> HTTP $([int]$response.StatusCode)"
}
Write-Output 'Alvos prontos. Abra o Claude Desktop para iniciar Nmap, Nuclei e SQLMap via MCP.'
Write-Output 'Se o Claude ja estava aberto antes do Docker, encerre-o completamente e abra novamente.'
