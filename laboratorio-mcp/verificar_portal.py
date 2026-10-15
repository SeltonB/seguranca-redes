"""Testes HTTP reais: ataques controlados e operações legítimas nos dois cenários."""
import http.cookiejar
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor

checks = []


def client():
    return build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(opener, base, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = Request(base + path, data=body, headers={"Content-Type": "application/json"} if body else {})
    try:
        response = opener.open(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())


def check(label, actual, expected):
    checks.append({"teste": label, "obtido": actual, "esperado": expected, "aprovado": actual == expected})
    if actual != expected:
        raise AssertionError(checks[-1])


try:
    for mode in ("vulneravel", "seguro"):
        base = f"http://portal-{mode}:8000"
        anon, ana, bruno, admin = [client() for _ in range(4)]
        prefix = mode + ": "
        check(prefix + "health", request(anon, base, "/health")[0], 200)
        check(prefix + "sem login / documento", request(anon, base, "/api/documentos/102")[0], 401)
        check(prefix + "sem login / admin", request(anon, base, "/api/admin/resumo")[0], 401)
        check(prefix + "senha incorreta", request(anon, base, "/api/login", {"login": "ana", "senha": "incorreta"})[0], 401)
        for name, opener in [("ana", ana), ("bruno", bruno), ("admin", admin)]:
            check(prefix + "login " + name, request(opener, base, "/api/login", {"login": name, "senha": "CampusLab!2026"})[0], 200)
        check(prefix + "documento de Ana", request(ana, base, "/api/documentos/101")[1]["dono_id"], 1)
        check(prefix + "documento de Bruno", request(bruno, base, "/api/documentos/102")[1]["dono_id"], 2)
        status, content = request(ana, base, "/api/documentos/102")
        check(prefix + "IDOR / status", status, 200 if mode == "vulneravel" else 404)
        check(prefix + "IDOR / evidencia", "LAB_DOCUMENTO_BRUNO" in json.dumps(content), mode == "vulneravel")
        check(prefix + "IDOR inverso", request(bruno, base, "/api/documentos/101")[0], 200 if mode == "vulneravel" else 404)
        check(prefix + "objeto inexistente", request(ana, base, "/api/documentos/999")[0], 404)
        check(prefix + "listagem limitada ao dono", [d["id"] for d in request(ana, base, "/api/documentos")[1]["documentos"]], [101])
        check(prefix + "aluno no admin", request(ana, base, "/api/admin/resumo")[0], 200 if mode == "vulneravel" else 403)
        check(prefix + "administrador autorizado", len(request(admin, base, "/api/admin/resumo")[1]["perfis"]), 3)
        check(prefix + "consulta legitima", len(request(anon, base, "/api/cursos?id=1")[1]["cursos"]), 1)
        check(prefix + "catalogo completo", len(request(anon, base, "/api/cursos")[1]["cursos"]), 3)
        query = urlencode({"id": "1 OR 1=1"})
        check(prefix + "SQL altera filtro", len(request(anon, base, "/api/cursos?" + query)[1]["cursos"]), 3 if mode == "vulneravel" else 0)
        query = urlencode({"id": "-1 UNION ALL SELECT id,nome,email FROM perfis"})
        content = request(anon, base, "/api/cursos?" + query)[1]
        check(prefix + "SQL vaza email ficticio", "bruno@campus.example" in json.dumps(content), mode == "vulneravel")
        check(prefix + "logout", request(ana, base, "/api/logout", {})[0], 200)
        check(prefix + "sem acesso depois do logout", request(ana, base, "/api/documentos/101")[0], 401)
finally:
    Path("/evidencias/http-portal.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"testes": len(checks), "aprovados": sum(c["aprovado"] for c in checks)}))
