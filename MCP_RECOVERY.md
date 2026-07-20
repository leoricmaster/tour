# MCP 恢复指南

> AI 读：拿到新机器 + 这个项目目录后，按本文档恢复 6 个 MCP server。不要写脚本，逐节执行即可。

## 0. 30 秒判断

```bash
node -v && npm -v && ls .trae/mcp.json
```

- `.trae/mcp.json` 缺失 → 第 5 节
- 文件存在但 MCP 不工作 → 第 4 节

## 1. 固定路径（不可改）

| 资源 | 路径 |
|---|---|
| MCP 配置 | `<项目根>/.trae/mcp.json` |
| 12306 二进制 | `~/.local/share/12306-mcp/node_modules/.bin/12306-mcp` |
| 途牛 / RollingGo | 远程 HTTP，无本地二进制 |

> 不要用 `npx -y 12306-mcp` 启动。重装到本地固定路径，否则每次 TRAE 重启都要重新拉 195MB。

## 2. 用户机器信息

- HTTP 代理：`127.0.0.1:7897`（可选，外网/下载用）
- 用户偏好：项目级配置，不进 TRAE 全局

## 3. 装 12306（一次性）

```bash
mkdir -p ~/.local/share/12306-mcp && cd ~/.local/share/12306-mcp
npm init -y > /dev/null
# 出网失败时加：npm_config_https_proxy=http://127.0.0.1:7897
npm install --no-audit --no-fund 12306-mcp
```

验证：`~/.local/share/12306-mcp/node_modules/.bin/12306-mcp` 存在。

> Node ≥ 20 可改 `npm install -g 12306-mcp`，command 写 `12306-mcp`。Node 18 走本地路径，stdio MCP 协议 OK（CLI 解析可能因 commander@14 报错，不影响使用）。

## 4. 诊断（已有配置但 server 启不来）

```bash
LATEST=$(ls -td "$HOME/.config/Trae CN/logs/"2*/ | head -n 1)
grep -E "Fail to start|Unauthorized|streamable" "$LATEST/window1/exthost/mcp-servers-host.log" | tail -n 30
```

| 症状 | 修复 |
|---|---|
| RollingGo `streamable Unauthorized` | `Authorization` 是 `${env:XXX}` 占位符 → TRAE 不支持，写明文 Key |
| 12306 完全不出现 | `~/.local/share/12306-mcp/` 缺失 → 跑第 3 节 |
| 12306 command not found | 路径不对 → 用绝对路径 |
| 途牛反复 `terminated` | 正常重连，忽略 |

端点验证：

```bash
# 途牛
curl -sS -X POST -H "apikey: <key>" -H "Content-Type: application/json" --max-time 15 \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"p","version":"0"}}}' \
  https://openapi.tuniu.cn/mcp/hotel

# RollingGo
curl -sS -X POST -H "Authorization: Bearer <key>" -H "Content-Type: application/json" --max-time 15 \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"p","version":"0"}}}' \
  https://mcp.rollinggo.cn/mcp

# 12306（stdio）
cd ~/.local/share/12306-mcp && node -e '
const {spawn}=require("child_process");
const c=spawn("./node_modules/.bin/12306-mcp",{stdio:["pipe","pipe","pipe"]});
c.stdout.on("data",d=>process.stdout.write(d));
c.stdin.write(JSON.stringify({jsonrpc:"2.0",id:1,method:"initialize",params:{protocolVersion:"2025-03-26",capabilities:{},clientInfo:{name:"p",version:"0"}}})+"\n");
setTimeout(()=>{c.kill();process.exit(0)},5000);
'
```

## 5. 全量安装（全新机器）

1. 用户把 `.trae/mcp.json` 拷贝到项目根（通常 git/scp/rsync 自动同步，除非 `.trae/` 被排除）。
2. 跑第 3 节装 12306。
3. 跑第 4 节三个端点验证。
4. 告诉用户**完全退出并重启 TRAE**（启动时才读 mcp.json，热重载不全有效）。

## 6. 期望配置

`.trae/mcp.json` 包含 6 个 server，**所有 Key 必须用真实值替换 `<...>` 占位符**：

```json
{
  "mcpServers": {
    "tuniu-order":   { "type": "streamableHttp", "url": "https://openapi.tuniu.cn/mcp/order",   "headers": { "apikey": "<TUNIU_APIKEY>" } },
    "tuniu-hotel":   { "type": "streamableHttp", "url": "https://openapi.tuniu.cn/mcp/hotel",   "headers": { "apikey": "<TUNIU_APIKEY>" } },
    "tuniu-flight":  { "type": "streamableHttp", "url": "https://openapi.tuniu.cn/mcp/flight",  "headers": { "apikey": "<TUNIU_APIKEY>" } },
    "RollingGo-Hotel":  { "type": "streamableHttp", "url": "https://mcp.rollinggo.cn/mcp",        "headers": { "Authorization": "Bearer <ROLLINGGO_APIKEY>" } },
    "RollingGo-Flight": { "type": "streamableHttp", "url": "https://mcp.rollinggo.cn/mcp/flight", "headers": { "Authorization": "Bearer <ROLLINGGO_APIKEY>" } },
    "12306": { "type": "stdio", "command": "/home/lancer/.local/share/12306-mcp/node_modules/.bin/12306-mcp" }
  }
}
```

**AI 必须向用户索要以下密钥**（不要凭印象生成或留空）：

| 占位符 | 来源 |
|---|---|
| `<TUNIU_APIKEY>` | 途牛开放平台 → 后台申请 |
| `<ROLLINGGO_APIKEY>` | https://rollinggo.store/apply 申请 |

## 7. 工具名规范

TRAE 注册名是 `mcp_<key>`：

| 配置 key | 注册名 |
|---|---|
| `tuniu-hotel` | `mcp_tuniu-hotel` |
| `RollingGo-Flight` | `mcp_RollingGo-Flight` |
| `12306` | `mcp_12306` |

## 8. 文档维护规则

**适用范围**：本项目未来新增/删除/更换任何 MCP server。

1. **新增 MCP**：
   - 在第 6 节配置块追加 server 定义
   - 在第 1 节路径表追加（若需要本地二进制）
   - 在第 7 节工具名表追加
   - 在第 4 节端点验证追加 curl 探针
   - 如需本地二进制安装步骤，在第 3 节追加
2. **删除 MCP**：上面四处同步删除
3. **更换 Key**：永远用占位符 `<...>`，由用户提供实际值
4. **不要写脚本**：保持纯文档，AI 读完按节执行
5. **文风**：简洁精炼，命令优先，少解释
6. **不要在文档里写真实 Key**：只写占位符

## 9. 已知坑

1. TRAE 不支持 `${env:XXX}` 占位符 → 必须写明文
2. TRAE 不支持 `${HOME}` 占位符 → stdio command 必须绝对路径
3. TRAE 只在启动时读 mcp.json → 改完必须完全重启
4. 途牛 `SSE stream disconnected: terminated` → 正常重连，忽略
5. 12306-mcp 依赖 Node ≥ 20（commander@14）→ Node 18 下 CLI 解析可能报错，stdio MCP 调用不受影响
6. 12306 访问 `kyfw.12306.cn` → 国内域名，若有强制全局代理需白名单