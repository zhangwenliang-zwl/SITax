"""探测本地服务的 OpenAPI 规范与聊天端点。"""
import json
import urllib.request

BASE = "http://127.0.0.1:49374"
PASSWORD = "4UYaSm4Xs-i5UNuVLls1gsfO2VyTigj5BbNkWLp3M0A"


def get(path, accept_json=True):
    req = urllib.request.Request(BASE + path)
    req.add_header("Authorization", f"Bearer {PASSWORD}")
    if accept_json:
        req.add_header("Accept", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        body = resp.read()
        is_json = "json" in resp.headers.get("Content-Type", "")
        return resp.status, body, is_json
    except urllib.error.HTTPError as e:
        return e.code, e.read(), False
    except Exception as e:
        return -1, str(e).encode(), False


for path in ["/openapi.json", "/openapi", "/docs", "/api/openapi.json",
             "/v1/openapi.json", "/.well-known/openapi.json"]:
    status, body, is_json = get(path)
    print(f"{path} => {status} json={is_json} len={len(body)}")
    if is_json and status == 200:
        spec = json.loads(body)
        print("  paths:", list(spec.get("paths", {}).keys())[:30])
        break
