"""Teste real de initialize/tools/list/tools/call sobre stdio dentro da imagem."""
import argparse
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('modulo', choices=['nmap', 'nuclei'])
    parser.add_argument('etapa', choices=['antes', 'depois'])
    args = parser.parse_args()
    params = StdioServerParameters(command=sys.executable, args=['/app/server.py'], env=dict(os.environ))
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=120)) as session:
            initialized = await session.initialize()
            listed = await session.list_tools()
            tool = 'service_scan' if args.modulo == 'nmap' else 'nuclei_scan'
            arguments = ({'target': 'alvo', 'ports': '8000', 'timeout': 60}
                         if args.modulo == 'nmap' else
                         {'target': 'http://alvo:8000', 'tags': ['lab'], 'rate_limit': 5, 'timeout': 60})
            result = await session.call_tool(tool, arguments)
            evidence = {
                'initialize': initialized.model_dump(mode='json'),
                'tools': [t.name for t in listed.tools],
                'call': {'name': tool, 'arguments': arguments},
                'response': result.model_dump(mode='json'),
            }
            Path('/evidencias').mkdir(exist_ok=True)
            Path(f'/evidencias/{args.modulo}-{args.etapa}.json').write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
            assert not result.isError, evidence
            payload = json.loads(next(c.text for c in result.content if c.type == 'text'))
            assert payload['status'] == 'completed', payload
            if args.modulo == 'nmap':
                assert any(str(p['port']) == '8000' for h in payload['hosts'] for p in h['open_ports']), payload
            else:
                found = any(f['template_id'] == 'lab-backup-exposto' for f in payload['findings'])
                assert found == (args.etapa == 'antes'), payload
            print(json.dumps({'modulo': args.modulo, 'etapa': args.etapa, 'tools': len(listed.tools),
                              'resultado': payload, 'validado': True}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
