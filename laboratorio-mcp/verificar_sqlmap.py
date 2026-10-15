"""Regressões do wrapper: falha/timeout não podem virar ausência de vulnerabilidade."""
import asyncio
import importlib.util
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

spec = importlib.util.spec_from_file_location("sqlmap_server", "/app/server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class Process:
    def __init__(self, code=1, timeout=False):
        self.returncode = None if timeout else code
        self.timeout = timeout
        self.killed = False

    async def communicate(self):
        if self.timeout and not self.killed:
            raise asyncio.TimeoutError()
        return b"", b"falha simulada"

    def kill(self):
        self.killed = True
        self.returncode = -9


async def main():
    target = "http://portal-vulneravel:8000/api/cursos?id=1"
    proc = Process()
    with patch.object(server.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)) as spawn:
        result = await server.run_sqlmap_scan(target)
        assert result.status == "failed", result
        assert spawn.call_args.kwargs["stdin"] == asyncio.subprocess.DEVNULL
    proc = Process(timeout=True)
    with patch.object(server.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)):
        result = await server.run_sqlmap_scan(target, timeout=1)
        assert result.status == "timeout" and proc.killed
        text = await server.call_tool("sql_test", {"target": target, "param": "id"})
        payload = json.loads(text[0].text)
        assert payload["status"] != "completed" and payload["injectable"] is None
    for kwargs in [{"target": "https://example.com/?id=1"}, {"target": target, "risk": 3},
                   {"target": target, "scan_type": "dump", "database": "SQLite_masterdb", "table": "usuarios"}]:
        with patch.object(server.asyncio, "create_subprocess_exec", AsyncMock()) as spawn:
            try:
                await server.run_sqlmap_scan(**kwargs)
            except ValueError:
                pass
            else:
                raise AssertionError(kwargs)
            spawn.assert_not_called()
    Path("/evidencias/regressoes-sqlmap.json").write_text(json.dumps({"status": "aprovado", "verificado": ["falha", "timeout", "stdin", "sql_test inconclusivo", "escopo local", "risco limitado", "extracao limitada"]}), encoding="utf-8")
    print("Regressoes SQLMap: aprovadas")


asyncio.run(main())
