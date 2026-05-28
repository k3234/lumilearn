# LumiLearn V4 天虹机器部署指南

## 环境信息
- **天虹机器**: R7-7840HS + Radeon 780M GPU
- **IP地址**: 192.168.2.63
- **系统**: Windows 11

---

## 一、部署步骤

### 1. 复制文件到天虹
将以下文件从华硕机器复制到天虹机器 `D:\LumiLearn\`:

```
F:\LumiLearn\
├── lumilearn_model_v4_skills\   (472MB)
├── lumilearn_model.py
├── lumilearn_api_server.py
├── unified_api_gateway.py
├── Dockerfile.v4
├── Dockerfile.gateway
└── docker-compose.yml
```

### 2. 安装依赖 (天虹上执行)
```powershell
pip install torch flask numpy requests
```

### 3. 配置防火墙 (管理员权限)
```powershell
# 开放端口 11435, 11436, 11437
New-NetFirewallRule -DisplayName "LumiLearn-Gateway" -Direction Inbound -LocalPort 11435 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "LumiLearn-V4" -Direction Inbound -LocalPort 11436 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "LumiLearn-Ollama" -Direction Inbound -LocalPort 11437 -Protocol TCP -Action Allow
```

### 4. 启动服务 (天虹上执行)
```powershell
cd D:\LumiLearn

# 设置环境变量
$env:HOST = "0.0.0.0"
$env:MODEL_DIR = "lumilearn_model_v4_skills\best_model"
$env:MODEL_NAME = "lumilearn-v4-skills"
$env:PORT = "11436"

# 启动V4 API (终端1)
python lumilearn_api_server.py

# 启动网关 (终端2)
$env:GATEWAY_PORT = "11435"
$env:LUMILEARN_URL = "http://localhost:11436"
$env:OLLAMA_URL = "http://localhost:11437"
python unified_api_gateway.py
```

---

## 二、远程访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **统一网关** | http://192.168.2.63:11435 | 推荐使用，自动路由 |
| V4 API | http://192.168.2.63:11436 | V4直连 |
| Ollama | http://192.168.2.63:11437 | Ollama直连 |

---

## 三、客户端调用示例

### Python
```python
import requests

def call_v4(prompt):
    url = "http://192.168.2.63:11435/api/generate"
    resp = requests.post(url, json={
        "model": "lumilearn-v4-skills",
        "prompt": prompt,
        "stream": False
    })
    return resp.json()["response"]

print(call_v4("解释牛顿第一定律"))
```

### curl
```bash
# 查看模型
curl http://192.168.2.63:11435/api/tags

# 调用V4
curl http://192.168.2.63:11435/api/generate -d '{"model":"lumilearn-v4-skills","prompt":"你好"}'
```

---

## 四、华硕机器配置

在华硕机器上修改Ollama配置，指向天虹:

```powershell
# 设置环境变量
$env:OLLAMA_HOST = "192.168.2.63:11437"

# 或修改统一网关配置
$env:OLLAMA_URL = "http://192.168.2.63:11437"
```

---

## 五、验证部署

在其他机器上执行:
```bash
curl http://192.168.2.63:11435/api/tags
```

预期返回:
```json
{
  "models": [
    {"name": "lumilearn-v4-skills"},
    {"name": "qwen2.5:7b"},
    {"name": "deepseek-r1:1.5b"}
  ]
}
```
