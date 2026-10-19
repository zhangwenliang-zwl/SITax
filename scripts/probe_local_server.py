"""探测 OpenCode 本地服务 API。"""
import json
import urllib.request

BASE = "http://127.0.0.1:49374"
PASSWORD = "4UYaSm4Xs-i5UNuVLls1gsfO2VyTigj5BbNkWLp3M0A"


def probe(path, method="GET", auth=True, payload=None):
    url = BASE + path
    data = None
    headers = {}
    if auth:
        headers["Authorization"] = f"Bearer {PASSWORD}"
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        body = resp.read()[:500]
        print(f"{method} {path} => {resp.status}: {body[:300]!r}")
    except urllib.error.HTTPError as e:
        print(f"{method} {path} => {e.code}: {e.read()[:300]!r}")
    except Exception as e:
        print(f"{method} {path} => 错误: {e}")


probe("/")
probe("/health")
probe("/v1/models")
probe("/models")
probe("/session")
probe("/config")
probe("/v1/chat/completions", "POST", payload={
    "model": "ling-3.1-flash-free",
    "messages": [{"role": "user", "content": "你好"}],
})
