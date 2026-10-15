"""Regressao: erro do executavel nao pode virar completed com zero achados."""
import asyncio
import json
import sys
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, '/app')
import server


async def main():
    process = AsyncMock()
    process.returncode = 2
    process.communicate.return_value = (b'', b'erro simulado de template')
    with patch.object(server.asyncio, 'create_subprocess_exec', return_value=process) as launch:
        result = await server.run_nuclei_scan('http://alvo:8000')
    assert launch.call_args.kwargs['stdin'] == asyncio.subprocess.DEVNULL
    assert result.status == 'failed', result
    assert 'erro simulado' in result.error, result
    timed_process = AsyncMock()
    timed_process.returncode = None
    timed_process.kill = Mock()
    timed_process.communicate.side_effect = [asyncio.TimeoutError(), (b'', b'')]
    with patch.object(server.asyncio, 'create_subprocess_exec', return_value=timed_process):
        timed_result = await server.run_nuclei_scan('http://alvo:8000', timeout=1)
    assert timed_result.status == 'timeout', timed_result
    timed_process.kill.assert_called_once()
    print(json.dumps({'regressao': 'erro_nuclei', 'status': result.status, 'validado': True}))


asyncio.run(main())
