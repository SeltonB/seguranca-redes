"""Prepara uma cópia do módulo original, com ajustes restritos a este laboratório."""
from pathlib import Path
import shutil

lab = Path(__file__).resolve().parent
source = lab.parent / "mcp-security-hub-master/mcp-security-hub-master/web-security/sqlmap-mcp"
dest = lab / "build/sqlmap"
dest.mkdir(parents=True, exist_ok=True)
for name in ("Dockerfile", "server.py", "requirements.txt"):
    shutil.copy2(source / name, dest / name)

(dest / "requirements.txt").write_text("mcp==1.30.0\npydantic==2.14.1\npydantic-settings==2.16.0\n", encoding="utf-8")
dockerfile = (dest / "Dockerfile").read_text(encoding="utf-8")
dockerfile = dockerfile.replace(
    "RUN git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git /opt/sqlmap &&",
    "ARG SQLMAP_COMMIT=ea8c6bdb63a3b2da1584f328836eb0d28116f7c4\n"
    "RUN git init /opt/sqlmap && cd /opt/sqlmap && "
    "git remote add origin https://github.com/sqlmapproject/sqlmap.git && "
    "git fetch --depth 1 origin ${SQLMAP_COMMIT} && git checkout --detach FETCH_HEAD &&",
)
(dest / "Dockerfile").write_text(dockerfile, encoding="utf-8")
code = (dest / "server.py").read_text(encoding="utf-8")

def replace(old, new):
    global code
    if old not in code:
        raise RuntimeError(f"Código original mudou; revisar patch: {old[:90]}")
    code = code.replace(old, new)

replace("import asyncio", "import asyncio\nimport csv\nfrom urllib.parse import urlsplit, parse_qs")
replace('    scan_id = str(uuid.uuid4())[:8]', '''    # Este servidor de demonstração aceita somente as duas instâncias locais.
    url = urlsplit(target)
    if (url.scheme != "http" or url.hostname not in {"portal-vulneravel", "portal-seguro"}
            or url.port != 8000 or url.path != "/api/cursos" or url.username or url.password
            or url.fragment or set(parse_qs(url.query)) != {"id"}):
        raise ValueError("Alvo fora do laboratório: use http://portal-vulneravel:8000/api/cursos?id=1 ou portal-seguro")
    if extra_args or level != 1 or risk != 1 or params not in (None, "id") or data:
        raise ValueError("Neste laboratório são permitidos apenas GET, parâmetro id, level=1 e risk=1")
    if dbms and dbms.lower() != "sqlite":
        raise ValueError("O portal utiliza SQLite")
    if scan_type == "dump" and (table != "perfis" or database != "SQLite_masterdb"
            or (columns and not set(columns) <= {"id", "nome", "email"})):
        raise ValueError("Extração limitada a SQLite_masterdb.perfis: id, nome e email fictícios")
    timeout = min(max(timeout or 180, 1), 300)
    params = "id"
    scan_id = str(uuid.uuid4())[:8]''')
replace('        "--batch",  # Non-interactive', '''        "--batch",  # Non-interactive
        "--disable-coloring", "--technique=BU", "--threads=1", "--delay=0.05",
        "--timeout=5", "--retries=0", "--dbms=SQLite", "--flush-session",
        "--fresh-queries",''')
replace('    try:\n        process = await asyncio.create_subprocess_exec(', '    process = None\n    try:\n        process = await asyncio.create_subprocess_exec(')
replace('            stdout=asyncio.subprocess.PIPE,', '            stdin=asyncio.subprocess.DEVNULL,\n            stdout=asyncio.subprocess.PIPE,')
replace('        if process.returncode == 0 or "sqlmap identified" in output.lower():', '        if process.returncode == 0:')
replace('        result.raw_output = output', '        result.raw_output = output + ("\\nSTDERR:\\n" + stderr.decode() if stderr else "")')
replace('                "columns": parsed["columns"],', '''                "columns": parsed["columns"],
                "dump_rows": [],''')
replace('            logger.info(\n                f"Scan {scan_id} completed:', '''            for csv_file in output_dir.rglob("*.csv"):
                if scan_type == "dump" and csv_file.stem == "perfis":
                    with csv_file.open(encoding="utf-8", errors="replace", newline="") as handle:
                        result.data["dump_rows"].extend(list(csv.DictReader(handle)))

            logger.info(
                f"Scan {scan_id} completed:''')
replace('    except asyncio.TimeoutError:\n', '''    except asyncio.TimeoutError:
        if process is not None and process.returncode is None:
            process.kill()
            await process.communicate()
''')
replace('    finally:\n        active_scans.discard(scan_id)', '''    finally:
        if process is not None and process.returncode is None:
            process.kill()
            await process.communicate()
        active_scans.discard(scan_id)''')
replace('                        "injectable": is_vulnerable,', '''                        "status": result.status,
                        "error": result.error,
                        "injectable": is_vulnerable if result.status == "completed" else None,''')
# As fases subsequentes também podem receber o cookie da sessão de teste.
replace('                    "database": {', '''                    "cookie": {"type": "string", "description": "Cookie de sessão do laboratório"},
                    "database": {''')
replace('                scan_type="enumerate",', '                scan_type="enumerate",\n                cookie=arguments.get("cookie"),')
replace('                scan_type="dump",', '                scan_type="dump",\n                cookie=arguments.get("cookie"),')
compile(code, str(dest / "server.py"), "exec")
(dest / "server.py").write_text(code, encoding="utf-8")
print("SQLMap 1.10 preparado; original preservado; alvos e extração limitados ao portal.")
