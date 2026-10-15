# Execução do laboratório MCP

Ensaio concluído em 14/10/2026, às 13:52 (America/Sao_Paulo); conferência pelo Inspector concluída na sequência.

## Resultados observados

| Verificação | Resultado |
|---|---|
| Build Nmap / Nuclei | Imagens `nmap-mcp:atividade` e `nuclei-mcp:atividade` construídas |
| Versões dos scanners | Nmap 7.99; Nuclei 3.7.0 |
| Alvo | Contêiner Linux com healthcheck aprovado, publicado somente em 127.0.0.1:8080 |
| Template | Validado pelo Nuclei |
| MCP Nmap | initialize, tools/list (7 ferramentas), tools/call service_scan: porta 8000 aberta, serviço HTTP |
| MCP Nuclei antes | initialize, tools/list (6 ferramentas), tools/call nuclei_scan: 1 achado medium, lab-backup-exposto |
| Correção | Arquivo fictício movido para fora da raiz web; HTTP mudou de 200 para 404 |
| MCP Nuclei depois | 0 achados, status completed |
| Restauração | Arquivo recolocado em site/; HTTP 200; pronto para repetir a demonstração |
| Inspector CLI no Windows | Listagem Nmap e chamada Nuclei concluídas, incluindo 1 achado no cenário restaurado |
| Regressões do wrapper | Erro do executável retorna failed; stdin isolado; timeout encerra o subprocesso |
| LLM / Claude Desktop | Não configurados nem testados, conforme solicitado |

Os testes usam alvos e dados fictícios locais. O resultado confirma esta exposição específica e o fluxo técnico MCP; não comprova a integração com uma LLM nem uma avaliação de segurança completa.

## Alterações necessárias para funcionar

- `preparar.ps1` copia os módulos para `build/`, fixa MCP 1.30.0/Pydantic 2.14.1/pydantic-settings 2.16.0 e aplica patches somente nessas cópias.
- Nuclei: removida a condição que aceitava qualquer contagem de achados como sucesso.
- Nuclei: stdin do executável definido como DEVNULL. Herdar o canal MCP causava espera de entrada e timeout; após a mudança o scan local concluiu em aproximadamente meio segundo.
- Nuclei: subprocesso encerrado e recolhido em timeout; atualizações e Interactsh desativados para o laboratório com template local.
- Compose: adicionado healthcheck HTTP.
- Cliente de teste Python: encaminha explicitamente o ambiente ao subprocesso MCP.
- Inspector: `--env=NUCLEI_TEMPLATES_PATH=/lab-templates` evita conflito com a opção `-e` do próprio Inspector; `npx.cmd` evita o bloqueio de scripts do PowerShell.

O projeto descompactado foi preservado. Avisos de depreciação de configuração Pydantic e da linha v1 do Inspector permanecem, sem impedir os testes realizados.

## Evidências

- [Resumo automatizado](evidencias/resumo.json)
- [Chamada MCP Nmap](evidencias/nmap-antes.json)
- [Chamada MCP Nuclei antes](evidencias/nuclei-antes.json)
- [Chamada MCP Nuclei depois](evidencias/nuclei-depois.json)
- [HTTP antes](evidencias/http-antes.json) e [HTTP depois](evidencias/http-depois.json)
- [Inspector Nmap](evidencias/inspector-nmap.log) e [Inspector Nuclei](evidencias/inspector-nuclei.log)
- [Build Nmap](evidencias/build-nmap.log) e [build Nuclei](evidencias/build-nuclei.log)
- [Identificação das imagens](evidencias/imagens.txt)
- [Dependências Nmap](evidencias/nmap-requirements.lock) e [dependências Nuclei](evidencias/nuclei-requirements.lock)

Resultados brutos dos scanners também foram exportados para `evidencias/raw-nmap/` e `evidencias/raw-nuclei/`. Os IDs presentes nas respostas MCP identificam os arquivos do ensaio final; essas pastas também podem conter saídas de tentativas anteriores. `evidencias/` e `build/` são ignorados pelo Git e permanecem disponíveis localmente.

## Repetir ou encerrar

Na pasta `seguranca-redes`, com Docker Desktop iniciado:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\laboratorio-mcp\testar.ps1
```

O script deixa o alvo ativo e restaura o arquivo fictício após testar a correção. Ele atualiza os JSONs de evidência; os logs do Inspector pertencem à execução manual de validação. Para parar o alvo:

```powershell
docker compose -f .\laboratorio-mcp\compose.yaml down
```

As imagens e os volumes de resultados permanecem para os próximos ensaios.
