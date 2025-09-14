from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os, json, re, yaml, pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
INDEX = BASE / "templates_repo" / "index.json"

class ComposeRequest(BaseModel):
    description: str

class ComposeResponse(BaseModel):
    template_id: str
    summary: str
    workflow_json: dict
    required_secrets: list
    required_inputs: list

app = FastAPI(title="Automation Template Service")

def load_index():
    if not INDEX.exists():
        raise RuntimeError("Index not found. Run: python scripts/index_templates.py")
    return json.loads(INDEX.read_text(encoding="utf-8"))

def fuzzy_score(q: str, item) -> int:
    q = q.lower()
    score = 0
    fields = [
        " ".join(item.get("intents", [])),
        " ".join(item.get("tags", [])),
        item.get("name") or ""
    ]
    text = " ".join(fields).lower()
    for token in re.findall(r"[a-z0-9_-]+", q):
        if token in text: score += 2
    if "rss" in q and "rss" in text: score += 3
    if "telegram" in q and "telegram" in text: score += 3
    if "sheet" in q and "sheet" in text: score += 3
    if "webhook" in q and "webhook" in text: score += 3
    if "http" in q and "http" in text: score += 2
    return score

WHITELIST = {
    "cron": "n8n-nodes-base.cron",
    "rssFeedRead": "n8n-nodes-base.rssFeedRead",
    "telegram": "n8n-nodes-base.telegram",
    "httpRequest": "n8n-nodes-base.httpRequest",
    "googleSheets": "n8n-nodes-base.googleSheets",
    "if": "n8n-nodes-base.if",
    "function": "n8n-nodes-base.function",
    "webhook": "n8n-nodes-base.webhook",
}

def validate_workflow(wf: dict, nodes_whitelist: list, max_nodes: int = 15):
    assert "nodes" in wf and isinstance(wf["nodes"], list) and wf["nodes"], "nodes missing/empty"
    assert "connections" in wf, "connections missing"
    assert len(wf["nodes"]) <= max_nodes, f"too many nodes: {len(wf['nodes'])}>{max_nodes}"

    allowed_types = set(WHITELIST.get(k) for k in nodes_whitelist if k in WHITELIST)
    ids = set()
    for n in wf["nodes"]:
        t = n.get("type")
        assert isinstance(n.get("position"), list) and len(n["position"]) == 2, "node position invalid"
        assert n.get("name"), "node missing name"
        assert n.get("id"), "node missing id"
        assert n["id"] not in ids, "duplicate node id"
        ids.add(n["id"])
        if allowed_types:
            assert t in allowed_types, f"node type not allowed: {t}"

    def contains_plain_secret(v):
        if isinstance(v, str):
            if "={{$env." in v:
                return False
            if len(v) > 20 and re.search(r"[A-Za-z0-9]{20,}", v):
                return True
        if isinstance(v, dict):
            return any(contains_plain_secret(x) for x in v.values())
        if isinstance(v, list):
            return any(contains_plain_secret(x) for x in v)
        return False

    if contains_plain_secret(wf):
        raise AssertionError("plain secrets detected; use env placeholders like ={{$env.SECRET}}")

@app.get("/")
def root():
    # بدل 404؛ نوجه مباشرة لواجهة الاختبار
    return RedirectResponse(url="/docs")

@app.get("/health")
def health():
    try:
        cnt = load_index()["count"]
    except Exception:
        cnt = None
    return {"ok": True, "templates": cnt}

@app.get("/stats")
def stats():
    idx = load_index()
    tags = {}
    intents = {}
    for it in idx["items"]:
        for t in it.get("tags", []):
            tags[t] = tags.get(t, 0) + 1
        for i in it.get("intents", []):
            intents[i] = intents.get(i, 0) + 1
    return {"count": idx["count"], "tags": tags, "intents": intents}

@app.get("/workflows")
def search(q: str = ""):
    idx = load_index()
    if not q:
        return idx
    scored = []
    for it in idx["items"]:
        s = fuzzy_score(q, it)
        if s > 0:
            scored.append((s, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return {"query": q, "results": [it for _, it in scored[:20]]}

@app.get("/workflows/{template_id}")
def get_one(template_id: str):
    idx = load_index()
    for it in idx["items"]:
        if it["id"] == template_id:
            wf_path = os.path.join(it["path"], "workflow.json")
            return {"meta": it, "workflow_json": json.loads(open(wf_path, "r", encoding="utf-8").read())}
    raise HTTPException(status_code=404, detail="template not found")

@app.post("/compose", response_model=ComposeResponse)
def compose(body: ComposeRequest):
    idx = load_index()
    ranked = sorted(idx["items"], key=lambda it: fuzzy_score(body.description, it), reverse=True)
    if not ranked:
        raise HTTPException(status_code=404, detail="no template matched")
    best = ranked[0]

    wf_path = os.path.join(best["path"], "workflow.json")
    meta_path = os.path.join(best["path"], "meta.yaml")
    wf = json.loads(open(wf_path, "r", encoding="utf-8").read())
    meta = yaml.safe_load(open(meta_path, "r", encoding="utf-8"))

    # basic heuristics placeholders (لو حبيت توسّعها لاحقًا)
    required_inputs = [x["key"] for x in meta.get("inputs",{}).get("required",[])]
    required_secrets = meta.get("secrets", [])

    nodes_whitelist = meta.get("compat",{}).get("n8n",{}).get("nodes_whitelist", [])
    max_nodes = meta.get("constraints",{}).get("max_nodes", 15)
    try:
        validate_workflow(wf, nodes_whitelist, max_nodes)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=f"validation_error: {e}")

    summary = f"ملف n8n من القالب '{best['name']}'. اضبط المتغيرات البيئية المطلوبة: {', '.join(required_secrets)}. والمدخلات: {', '.join(required_inputs)}."
    return ComposeResponse(
        template_id=best["id"],
        summary=summary,
        workflow_json=wf,
        required_secrets=required_secrets,
        required_inputs=required_inputs
)
