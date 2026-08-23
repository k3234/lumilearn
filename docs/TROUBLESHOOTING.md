# LumiLearn 故障排查手册

> **适用版本**：V2.5 竞赛版（2026-08）
> **说明**：本手册记录常见故障、排查步骤与解决方案，覆盖部署、运行、演示三个阶段。

---

## 目录

1. [快速自检](#一快速自检)
2. [部署阶段故障](#二部署阶段故障)
3. [运行时故障](#三运行时故障)
4. [演示阶段故障](#四演示阶段故障)
5. [性能降级诊断](#五性能降级诊断)
6. [常用诊断命令](#六常用诊断命令)

---

## 一、快速自检

启动服务后，依次执行以下检查：

```bash
# 1. 进程状态
curl -s http://localhost:5010/health || echo "API 端口不通"
curl -s http://localhost:5000/health || echo "GOAI 端口不通"
curl -s http://localhost:18080/api/admin/health || echo "Admin 端口不通"

# 2. 模型状态
curl -s http://localhost:11434/api/tags | python3 -m json.tool

# 3. 数据库完整性
python3 -c "from framework.database import db; db.init(); print('DB OK')"
```

三项全通 → 基础部署正常，进入运行时检查。

---

## 二、部署阶段故障

### 2.1 Docker 启动失败

**症状**：`docker-compose up` 报 `service "ollama" condition: service_healthy` 超时

**排查**：
```bash
# 检查 Ollama 镜像
docker images | grep ollama

# 手动拉取 Ollama 镜像（国内网络可能需要代理）
docker pull ollama/ollama:latest

# 查看详细日志
docker logs lumilearn-ollama --tail 50
```

**解决**：
- 网络不通：设置 Docker 代理或手动 `docker pull` 后再 `docker-compose up`
- 磁盘不足：`docker system prune -a` 清理旧镜像

---

### 2.2 端口冲突

**症状**：服务启动报 `Address already in use`

**排查**：
```bash
# Windows
netstat -ano | findstr ":5010"
tasklist /fi "pid eq <PID>"

# Linux/Mac
lsof -i :5010
```

**解决**：
- 修改 `.env` 中的端口映射：
  ```
  API_PORT=5020
  GOAI_PORT=5010
  ```
- 或终止占用进程

---

### 2.3 环境变量缺失

**症状**：应用启动报 `SECRET_KEY` 或 `LUMILEARN_DB_PATH` 未定义

**排查**：
```bash
# 检查 .env 文件
cat .env | grep -v SECRET_KEY   # 其他变量可见，密钥被隐藏为安全
```

**解决**：
```bash
# 生成密钥
python3 -c "import secrets; print(secrets.token_hex(32))"
# 写入 .env 文件
```

---

### 2.4 SQLite 数据库损坏

**症状**：`sqlite3.OperationalError: database is locked` 或表不存在

**排查**：
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('lumilearn.db')
conn.execute('PRAGMA integrity_check')
for row in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\"):
    print(row[0])
"
```

**解决**：
- 轻度损坏：`PRAGMA integrity_check` 修复
- 严重损坏：备份 `lumilearn.db` 后重新 `db_admin.py init`

---

## 三、运行时故障

### 3.1 Ollama 模型不可用

**症状**：教学响应超时或返回空内容

**排查**：
```bash
# 检查 Ollama 运行状态
curl http://localhost:11434/api/tags

# 查看可用模型
docker exec lumilearn-ollama ollama list

# 拉取缺失模型（CPU 推荐 qwen2.5:1.5b）
docker exec lumilearn-ollama ollama pull qwen2.5:1.5b
```

**解决**：
- 模型未拉取：执行上述 pull 命令
- 模型名不匹配：检查 `.env` 中 `OLLAMA_MODEL` 配置

---

### 3.2 教师端页面空白

**症状**：访问 `/teacher` 页面加载后内容不显示

**排查**：
```bash
# 检查浏览器控制台（F12）是否有 CORS 错误
# 检查 API 端口
curl http://localhost:5010/api/feynman/status
```

**解决**：
- CORS 错误：确认浏览器访问地址在 `CORS_ALLOWED_ORIGINS` 白名单内
- API 端口不通：检查 `.env` 中 `API_PORT` 与 teacher 端口配置是否一致

---

### 3.3 学生端评分异常（全部 100 分）

**症状**：学生答题后反馈"掌握度 100%"，但实际回答错误

**原因**：Ollama 不可用时，`ScoreAgent` 无法调用模型，降级返回默认值

**排查**：
```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```

**解决**：
- 确保 Ollama 运行且模型可用
- Lite 模式下可手动指定评分逻辑（见 [五、性能降级诊断](#五性能降级诊断)）

---

### 3.4 错题未入库

**症状**：学生答错后，错题本为空

**排查**：
```bash
python3 -c "
from framework.database import db
mistakes = db.get_mistakes('student001')
print(f'错题数: {len(mistakes)}')
for m in mistakes[:3]:
    print(m['topic'], m['wrong_count'])
"
```

**解决**：
- `wrong_count` 字段未递增：检查 `record_answer` 调用是否传入正确 `is_correct=False`
- 数据库连接异常：重启服务后重试

---

## 四、演示阶段故障

### 4.1 演示流程随机性强

**症状**：现场演示时，学生可能选到未学习的知识点，导致流程断裂

**解决**：使用固定演示脚本（`scripts/demo_fix_scenario.sh`），预设教材与知识点，确保演示路径可复现

---

### 4.2 网络依赖导致演示中断

**症状**：现场无外网，云端 API 不可用，系统无法运行

**解决**：
- 演示前预装 Ollama 模型：`docker exec lumilearn-ollama ollama pull qwen2.5:1.5b`
- 切换到本地模型模式：`.env` 中设置 `OLLAMA_HOST=http://localhost:11434`
- 使用 Lite 模式启动：`python goai_web.py --mode lite`

---

### 4.3 演示环境数据清空

**症状**：重启服务后，所有学生数据、错题、学习记录消失

**原因**：数据存储在容器内 `/data/lumilearn.db`，重启容器后数据丢失（未挂载持久化卷）

**解决**：
- 使用 `docker-compose.yml` 默认配置（已挂载 `./data:/data`）
- 验证卷挂载：`docker volume ls | grep lumilearn`

---

## 五、性能降级诊断

### 5.1 CPU 负载过高

**症状**：系统响应延迟 > 30s，CPU 占用持续 > 90%

**排查**：
```bash
# 查看进程资源
top -p $(pgrep -f "goai_web.py" | head -1)

# 查看 Ollama 推理耗时
curl -s http://localhost:11434/api/ps | python3 -m json.tool
```

**解决**：
- 启用 Lite 模式：`--mode lite`，关闭教师端与分析仪表盘
- 降低并发：限制同时在线学生数
- 使用更小模型：切换 `qwen2.5:0.5b` 替代 `qwen2.5:1.5b`

---

### 5.2 内存溢出

**症状**：系统 OOM Kill，Flask 进程意外终止

**排查**：
```bash
# 查看当前内存使用
free -h
docker stats

# 检查 Python 进程内存
ps aux | grep python | head -5
```

**解决**：
- 启用 Lite 模式减少服务数量
- 限制 Ollama 模型并发：设置 `OLLAMA_NUM_PARALLEL=1`
- 监控日志保留策略：执行 `python3 -c "from framework.log_retention import run_log_retention_policy; print(run_log_retention_policy())"`

---

### 5.3 RAG 检索准确率下降

**症状**：学生提问后，系统返回内容不相关或空白

**排查**：
```bash
# 检查知识库索引状态
python3 -c "
from framework.services.knowledge_retrieval import get_knowledge_retriever
r = get_knowledge_retriever()
print('索引文档数:', len(r._index))
print('搜索结果:', r.search('勾股定理', top_k=3))
"
```

**解决**：
- 索引为空：重新导入文档（Admin 面板 → 教材管理 → 导入）
- 检索结果差：检查分词器词典是否覆盖学科关键词
- 乱码问题：确认文档编码为 UTF-8，使用 `parse_markdown()` 预处理

---

## 六、常用诊断命令

### 6.1 一键健康检查

```bash
python3 check_status.py
```

输出示例：
```
[API]      OK    http://localhost:5010
[GOAI]     OK    http://localhost:5000
[Teacher]  OK    http://localhost:5001
[Admin]    OK    http://localhost:18080
[Ollama]   OK    qwen2.5:1.5b
[DB]       OK    1247 条记录
[Tests]    47/47 passed
```

---

### 6.2 日志查询

```bash
# 系统日志（最近 50 条）
python3 -c "
from framework.database import db
for r in db._query('SELECT * FROM system_logs ORDER BY id DESC LIMIT 50'):
    print(r['level'], r['message'][:80])
"

# 推理日志（最近 10 条）
python3 -c "
from framework.database import db
for r in db._query('SELECT trace_id, model, latency_ms FROM reasoning_logs ORDER BY id DESC LIMIT 10'):
    print(r)
"
```

---

### 6.3 数据导出（备份）

```bash
# 导出完整数据库
cp lumilearn.db lumilearn_backup_$(date +%Y%m%d).db

# 导出测试报告
python3 docs/generate_compliance_report.py
```

---

## 附录：故障代码速查表

| 症状 | 可能原因 | 排查命令 |
|---|---|---|
| 页面 502 | API 端口未启动 | `curl localhost:5010/health` |
| 评分返回 100% | Ollama 不可用 | `curl localhost:11434/api/tags` |
| 错题为空 | `record_answer` 未调用 | 检查 `is_correct` 参数 |
| RAG 返回空 | 知识库未索引 | `get_knowledge_retriever()._index` |
| 内存 OOM | 日志未归档 | `run_log_retention_policy()` |
| 端口冲突 | 已有进程占用 | `netstat -ano \| findstr :5010` |
| Docker 启动慢 | 镜像未缓存 | `docker images \| grep ollama` |

---

*本手册随项目版本迭代更新，最后更新：2026-08-23*
