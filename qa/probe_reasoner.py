import os, json, requests
BASE = os.getenv("REASONER_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("REASONER_TOKEN", "")
timeout = int(os.getenv("REASONER_TIMEOUT", "30"))

def req(method, path, **kw):
    url = f"{BASE}{path if path.startswith('/') else '/'+path}"
    headers = {"X-Reasoner-Token": TOKEN, "Content-Type": "application/json"}
    r = requests.request(method, url, headers=headers, timeout=timeout, **kw)
    print("STATUS", r.status_code, url)
    print("RAW", r.text[:500])
    r.raise_for_status()
    return r.json()

print("== /health ==")
print(req("GET", "/health"))

print("== /status ==")
print(req("GET", "/status"))

print("== /v1/reason ==")
payload = {
  "dyad":"tantrum",
  "features":{"vad_fraction":0.42},
  "context":{"trigger":"transition"},
  "metrics":{"escalation_index":0.61},
  "history":[]
}
import sys
res = req("POST", "/v1/reason", data=json.dumps(payload))
print(json.dumps(res, indent=2))

# Exit with proper code for automation
ok = "tips" in res and res.get("model_used") == "gpt-oss:20b"
print(f"\n== RESULT ==")
print(f"SUCCESS: {ok}")
print(f"HAS_TIPS: {'tips' in res}")
print(f"MODEL_USED: {res.get('model_used', 'NONE')}")
sys.exit(0 if ok else 2)
