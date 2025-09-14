\
import os, json, yaml, hashlib, re

BASE = os.path.dirname(os.path.dirname(__file__))
WF_DIR = os.path.join(BASE, "templates_repo", "workflows")
INDEX = os.path.join(BASE, "templates_repo", "index.json")

def slug(s: str) -> str:
    s = re.sub(r"\s+", "_", s.strip().lower())
    return re.sub(r"[^a-z0-9_]+","", s)

def main():
    items = []
    for root, dirs, files in os.walk(WF_DIR):
        if "meta.yaml" in files and "workflow.json" in files:
            meta_path = os.path.join(root, "meta.yaml")
            wf_path = os.path.join(root, "workflow.json")
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = yaml.safe_load(f)
            with open(wf_path, "r", encoding="utf-8") as f:
                wf = json.load(f)
            mid = meta.get("id") or slug(os.path.basename(root))
            item = {
                "id": mid,
                "path": root,
                "name": meta.get("name"),
                "intents": meta.get("intents", []),
                "tags": meta.get("tags", []),
                "inputs": meta.get("inputs", {}),
                "outputs": meta.get("outputs", {}),
                "secrets": meta.get("secrets", []),
                "compat": meta.get("compat", {}),
                "constraints": meta.get("constraints", {}),
                "hash": hashlib.sha256(json.dumps(wf, sort_keys=True).encode()).hexdigest()
            }
            items.append(item)
    idx = {"count": len(items), "items": items}
    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    print(f"Indexed {len(items)} templates -> {INDEX}")

if __name__ == "__main__":
    main()
