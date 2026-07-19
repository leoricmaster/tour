#!/usr/bin/env python3
"""途牛 MCP 简易客户端（Streamable HTTP + apikey header）。

用法：
  python3 tuniu_mcp_client.py order list-tools
  python3 tuniu_mcp_client.py order call order_list '{"orderType":"ALL","pageSize":5}'
"""
import json
import sys
import urllib.request
import urllib.error

APIKEY = "sk-0dcec9f349774dc0a5a70f377833c276"
ENDPOINTS = {
    "order": "https://openapi.tuniu.cn/mcp/order",
    "hotel": "https://openapi.tuniu.cn/mcp/hotel",
    "flight": "https://openapi.tuniu.cn/mcp/flight",
}


class MCPClient:
    def __init__(self, url: str, apikey: str):
        self.url = url
        self.session_id = None
        self.apikey = apikey

    def _request(self, payload: dict, timeout: int = 20) -> dict:
        body = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "apikey": self.apikey,
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id

        req = urllib.request.Request(self.url, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                sid = r.headers.get("mcp-session-id")
                if sid:
                    self.session_id = sid
                raw = r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            return {"_error": f"HTTP {e.code}", "_body": e.read().decode(errors="replace")}

        # 解析 SSE：形如 "event: message\ndata: {...}\n\n"
        for line in raw.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return {"_raw": raw}

    def initialize(self) -> dict:
        return self._request({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "tuniu-mcp-client", "version": "0.1.0"},
            },
        })

    def initialized(self):
        return self._request({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def list_tools(self) -> dict:
        return self._request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self._request({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    service, action, *rest = sys.argv[1:]
    if service not in ENDPOINTS:
        print(f"unknown service: {service}, choose from {list(ENDPOINTS)}"); sys.exit(1)

    client = MCPClient(ENDPOINTS[service], APIKEY)
    client.initialize()
    client.initialized()

    if action == "list-tools":
        print(json.dumps(client.list_tools(), ensure_ascii=False, indent=2))
    elif action == "call" and rest:
        name, args_json = rest[0], rest[1] if len(rest) > 1 else "{}"
        print(json.dumps(client.call_tool(name, json.loads(args_json)),
                         ensure_ascii=False, indent=2))
    else:
        print("usage: list-tools | call <tool_name> '<json_args>'")


if __name__ == "__main__":
    main()