"""Validação ponta a ponta dos scanners por MCP, sem simular a LLM."""
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    module = sys.argv[1]
    params = StdioServerParameters(command=sys.executable, args=["/app/server.py"], env=dict(os.environ))
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=360)) as session:
            await session.initialize()
            listed = await session.list_tools()
            Path(f"/evidencias/{module}-tools.json").write_text(listed.model_dump_json(indent=2), encoding="utf-8")

            async def call(label, tool, arguments):
                response = await session.call_tool(tool, arguments)
                evidence = {"tool": tool, "arguments": arguments, "response": response.model_dump(mode="json")}
                Path(f"/evidencias/{module}-{label}.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
                assert not response.isError, evidence
                payload = json.loads(next(c.text for c in response.content if c.type == "text"))
                assert payload["status"] == "completed", payload
                raw = await session.call_tool("get_scan_results", {"scan_id": payload["scan_id"], "include_raw": True})
                Path(f"/evidencias/{module}-{label}-raw.json").write_text(raw.model_dump_json(indent=2), encoding="utf-8")
                print(json.dumps({"modulo": module, "etapa": label, "scan_id": payload["scan_id"], "status": payload["status"]}), flush=True)
                return payload

            for mode in ("vulneravel", "seguro"):
                host = f"portal-{mode}"
                if module == "nmap":
                    result = await call(mode, "service_scan", {"target": host, "ports": "8000", "timeout": 120})
                    assert any(str(p["port"]) == "8000" for h in result["hosts"] for p in h["open_ports"]), result
                elif module == "nuclei":
                    result = await call(mode, "nuclei_scan", {"target": f"http://{host}:8000", "tags": ["portal"], "rate_limit": 5, "timeout": 90})
                    found = {f["template_id"] for f in result["findings"]}
                    assert found == ({"lab-portal-idor", "lab-portal-admin"} if mode == "vulneravel" else set()), result
                elif module == "sqlmap":
                    result = await call(mode, "sql_scan", {"target": f"http://{host}:8000/api/cursos?id=1", "params": "id", "level": 1, "risk": 1, "timeout": 240})
                    assert bool(result["vulnerabilities"]) == (mode == "vulneravel"), result
                else:
                    raise ValueError(module)
            if module == "sqlmap":
                result = await call("extracao", "sql_dump", {"target": "http://portal-vulneravel:8000/api/cursos?id=1", "database": "SQLite_masterdb", "table": "perfis", "columns": ["id", "nome", "email"], "timeout": 240})
                rows = result["data"]["dump_rows"]
                assert len(rows) == 3 and any(r.get("email") == "bruno@campus.example" for r in rows), result
    print(f"MCP {module}: validado", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
