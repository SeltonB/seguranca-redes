. (Join-Path $PSScriptRoot 'docker-comum.ps1')
$lab = $PSScriptRoot
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$evidence = Join-Path $lab "evidencias\portal\$runId"
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$compose = @('compose','-f',"$lab\compose.yaml",'-f',"$lab\compose.portal.yaml")
Invoke-LabDocker -Arguments ($compose + @('up','-d','--wait','--wait-timeout','60','portal-vulneravel','portal-seguro'))
$mounts = @('--mount',"type=bind,source=$lab,target=/lab,readonly",'--mount',"type=bind,source=$evidence,target=/evidencias")
try {
    Invoke-LabDocker -Arguments (@('run','--rm','--network','mcp-atividade-lab') + $mounts + @('portal-mcp:atividade','python','/lab/verificar_portal.py'))
    Invoke-LabDocker -Arguments (@('run','--rm') + $mounts + @('sqlmap-mcp:atividade','python','/lab/verificar_sqlmap.py'))
    foreach ($module in @('nmap','nuclei','sqlmap')) {
        Invoke-LabDocker -Arguments (@('run','--rm','--network','mcp-atividade-lab') + $mounts + @(
            '--mount',"type=bind,source=$lab\templates,target=/lab-templates,readonly",'--env=NUCLEI_TEMPLATES_PATH=/lab-templates',
            '-v',"mcp-atividade-${module}-output:/app/output","${module}-mcp:atividade",'python','/lab/verificar_portal_mcp.py',$module))
    }
    @{Data=(Get-Date -Format o);Resultado='aprovado';HTTP='44 verificacoes';MCP='Nmap, Nuclei e SQLMap';
      IDOR='detectado / bloqueado';Administracao='exposta / bloqueada';SQL='injecao detectada / nao detectada';
      Extracao='3 perfis ficticios';LLM='novos cenarios aguardam execucao pelo usuario'} |
      ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'resumo.json') -Encoding UTF8
} finally {
    Invoke-LabDocker -Arguments ($compose + @('logs','--no-color','portal-vulneravel','portal-seguro')) |
      Set-Content -LiteralPath (Join-Path $evidence 'portal.log') -Encoding UTF8
}
Write-Output "Evidencias: $evidence"
