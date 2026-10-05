"""Thin TigerGraph client: GSQL statements + RESTPP upserts/reads over HTTPS (basic auth)."""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
HOST = os.getenv("TG_HOST", "").rstrip("/")
GRAPH = os.getenv("TG_GRAPH", "OlympicsGraph")
AUTH = (os.getenv("TG_USERNAME"), os.getenv("TG_PASSWORD"))
_S = requests.Session()
_S.auth = AUTH
_token = {"value": None}


def _bearer():
    """RESTPP needs a bearer token; GSQL endpoints use basic auth. Token is requested once per process."""
    if not _token["value"]:
        r = requests.post(f"{HOST}/gsql/v1/tokens", json={"graph": GRAPH, "lifetime": "86400"}, auth=AUTH, timeout=30)
        r.raise_for_status()
        _token["value"] = r.json()["token"]
    return {"Authorization": f"Bearer {_token['value']}"}


def _rest(method: str, path: str, **kw):
    """Call a /restpp endpoint with bearer auth (explicit header overrides the session's basic auth)."""
    r = requests.request(method, f"{HOST}/restpp{path}", headers=_bearer(), timeout=kw.pop("timeout", 120), **kw)
    if r.status_code in (401, 403) and "REST-10016" in r.text or r.status_code == 401:
        _token["value"] = None
        r = requests.request(method, f"{HOST}/restpp{path}", headers=_bearer(), timeout=120, **kw)
    return r


def gsql(statements: str, timeout: int = 300) -> str:
    r = _S.post(f"{HOST}/gsql/v1/statements", data=statements.encode("utf-8"),
                headers={"Content-Type": "text/plain"}, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"GSQL {r.status_code}: {r.text[:500]}")
    return r.text


def upsert(vertices: dict | None = None, edges: dict | None = None, retries: int = 3):
    """vertices: {vtype: {id: {attr: value}}}; edges: {src_type: {src_id: {etype: {tgt_type: {tgt_id: {attrs}}}}}}"""
    payload = {}
    if vertices:
        payload["vertices"] = {t: {i: {k: {"value": v} for k, v in a.items()} for i, a in d.items()}
                               for t, d in vertices.items()}
    if edges:
        payload["edges"] = {
            st: {sid: {et: {tt: {tid: {k: {"value": v} for k, v in a.items()} for tid, a in tg.items()}
                             for tt, tg in te.items()} for et, te in ed.items()} for sid, ed in sd.items()}
            for st, sd in edges.items()}
    for attempt in range(retries):
        r = _rest("POST", f"/graph/{GRAPH}", json=payload)
        if r.status_code == 200 and not r.json().get("error"):
            return r.json()
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"upsert failed {r.status_code}: {r.text[:500]}")


def vertices(vtype: str, vid: str | None = None, filter: str | None = None, limit: int | None = None,
             select: str | None = None, sort: str | None = None):
    path = f"/graph/{GRAPH}/vertices/{vtype}" + (f"/{vid}" if vid else "")
    params = {k: v for k, v in dict(filter=filter, limit=limit, select=select, sort=sort).items() if v}
    r = _rest("GET", path, params=params)
    r.raise_for_status()
    return r.json().get("results", [])


def edges(vtype: str, vid: str, etype: str, target_type: str | None = None, filter: str | None = None):
    path = f"/graph/{GRAPH}/edges/{vtype}/{vid}/{etype}" + (f"/{target_type}" if target_type else "")
    r = _rest("GET", path, params={"filter": filter} if filter else None)
    r.raise_for_status()
    return r.json().get("results", [])


def run_query(name: str, **params):
    r = _rest("GET", f"/query/{GRAPH}/{name}", params=params)
    r.raise_for_status()
    return r.json().get("results", [])
