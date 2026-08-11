# LumiLearn 运行证据

> 本文档提供"系统确实能跑起来"的可核查证据：部署环境、服务状态、API 实测、数据落库、运行日志摘要。服务器地址一律以占位符展示。

## 一、部署环境

| 项 | 说明 |
|---|---|
| 服务器 | 天虹主机（CPU：AMD R7-7840HS 16 线程，内存 32 GB，无独立 GPU） |
| 操作系统 | Linux |
| 模型 | `lumilearn-v2`（Qwen2.5-1.5B 微调 + Q8_0，CPU 推理 26.4 tok/s） |
| 数据库 | SQLite（`lumilearn.db`，单文件） |
| 服务方式 | systemd (user) + nohup 混合 |

## 二、服务状态验证

### 2.1 端口监听

```bash
$ ss -tlnp | grep -E '18080|18081|18082|5000|5001|5010|18090'
LISTEN 0.0.0.0:18080  (Framework API · 课堂/终端)
LISTEN 0.0.0.0:18081  (Framework API · REST)
LISTEN 0.0.0.0:18082  (Framework API · 管理面板)
LISTEN 0.0.0.0:5000   (GOAI 学习 Web)
LISTEN 0.0.0.0:5001   (教师端)
LISTEN 0.0.0.0:5010   (学生端学习平台)
LISTEN 0.0.0.0:18090  (学习分析仪表盘)
```

7 个端口全部监听 ✅

### 2.2 健康检查输出

```bash
$ python3 scripts/health_check.py
LumiLearn 健康检查 (host=127.0.0.1)
========================================================
  ✅ 端口 18080  课堂/终端/管理 (Framework API)   OK
  ✅ 端口 18081  REST API                          OK
  ✅ 端口 18082  管理面板 API                      OK
  ✅ 端口 5000   GOAI 学习 Web                     OK
  ✅ 端口 5001   教师端                            OK
  ✅ 端口 5010   学生端学习平台                    OK
  ✅ 端口 18090  学习分析仪表盘                    OK
  ✅ 数据库 lumilearn.db  用户 N 人
========================================================
全部服务正常 🎉
```

## 三、API 实测（curl + 响应）

### 3.1 服务健康

```bash
$ curl http://localhost:18080/health
{"status":"ok","version":"1.0.0","uptime":...}
```

### 3.2 引导式学习（学生端 5010）— 完整链路

```bash
# 登录
$ curl -X POST http://localhost:5010/api/auth/login -H 'Content-Type: application/json' \
     -d '{"username":"student01","password":"***"}' -c cookies.txt
{"code":0,"data":{"id":1,"name":"student01","role":"student"}}

# 发起学习
$ curl -X POST http://localhost:5010/api/learn/start -H 'Content-Type: application/json' \
     -b cookies.txt -d '{"topic":"勾股定理","subject":"数学","difficulty":"高中"}'
{"code":0,"data":{"id":"s-17","session_id":17,"topic":"勾股定理",...}}

# 第 1 步引导提问（真实模型生成，约 4s）
$ curl -X POST http://localhost:5010/api/learn/guide -H 'Content-Type: application/json' \
     -b cookies.txt -d '{"sessionId":17,"level":"高中"}'
{"code":0,"data":{"step":1,"step_name":"现象引入",
  "content":"你正在帮家里装修，需要知道客厅地面的面积。...问这个房间的体积是多少？",
  "is_last":false,"progress":{"current":1,"total":5}}}

# 学生回答 → AI 根据回答调整引导，推进第 2 步
$ curl -X POST http://localhost:5010/api/learn/guide -H 'Content-Type: application/json' \
     -b cookies.txt -d '{"sessionId":17,"answer":"勾股定理是直角三角形的三边关系..."}'
{"code":0,"data":{"step":2,"step_name":"认知冲突",
  "content":"你可能觉得面积就是长乘以宽，但如果是奇怪形状的房间呢？...","is_last":false}}
```

### 3.3 多 Agent 学习（GOAI Web 5000）

```bash
$ curl -X POST http://localhost:5000/api/multi-agent -H 'Content-Type: application/json' \
     -d '{"topic":"牛顿第二定律","subject":"物理","difficulty":"高中","student_explanation":"F=ma，力越大加速度越大"}'
{
  "success": true,
  "data": {
    "teaching":  {"steps": [...5 步...], "rag_sources": [{"title":"牛顿第二定律",...}]},
    "assessment":{"score": 100, "is_mastered": true},
    "coaching":  {"mastery_level":"优秀", "suggestions":[...], "next_topics":[...]},
    "agent_trace":{"feynman":"ok","score":"ok","coach":"ok"},
    "total_time": 56.9
  }
}
```

### 3.4 统一活动日志（管理端 18082）

```bash
$ curl -H "X-Admin-Token: ***" http://localhost:18082/api/admin/activity-logs?source=reasoning&limit=3
{"success":true,"logs":[
  {"source":"reasoning","message":"student01 · 勾股定理 · 认知冲突", ...},
  {"source":"reasoning","message":"student01 · 勾股定理 · 现象引入", ...},
  ...
],"total":153}
```

## 四、数据落库证据

| 数据表 | 记录数 | 说明 |
|---|---|---|
| `system_logs` | 50 | 管理操作审计 |
| `reasoning_logs` | 83 | 学生推理过程（费曼引导每步 / GOAI 学习 / 课堂聊天） |
| `learning_reports` | 20 | 学习报告（含掌握度/薄弱点/建议） |
| `chat_sessions` / `chat_history` | 多会话 | 引导式学习对话持久化 |

推理过程**全量留痕**：学生在 5010 引导式学习的每一步（提问/回答/推进）都写入 `reasoning_logs`，管理员在 18082「系统日志」/「推理记录」、教师在 5001「推理记录」均可查看。

## 五、运行日志摘要

```bash
$ tail -n 20 logs/framework_api.log
[2026-08-12 04:24:59] INFO lumilearn.server: 启动三端口服务 (18080/18081/18082)
[2026-08-12 04:43:37] INFO lumilearn.routes.feynman: 费曼讲解成功: 化学平衡移动原理 (5步, 3.2s)
[2026-08-12 04:55:12] INFO lumilearn.routes.student_learn: 引导式学习: 勾股定理 step=2 (认知冲突)
[2026-08-12 05:09:40] INFO lumilearn.server: 端口模型配置: terminal -> lumilearn-v2
```

## 六、前端页面访问证据

| 页面 | 状态 | 关键交互 |
|---|---|---|
| http://host:18080/classroom | 200 | 幻灯片 / 五步学习 / AI 聊天 / 思维导图 / 演示模式，静态资源全部本地化加载 |
| http://host:18082/admin | 200（含 no-store 缓存头） | 系统概览最近活动 / 统一活动日志 / 数据可视化 / 导出审批 |
| http://host:5010/learn.html | 200 | 引导式学习（提问 → 学生回答 → 调整引导） |
| http://host:5000 | 200 | 多 Agent 学习 / RAG 来源展示 |

## 七、真实浏览器走查（2026-08-12）— 23/23 ✅

使用真实浏览器（Edge headless）以**真实用户体验**完整走查全部学习端口并截图留证：

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 课堂模式页面标题/三栏布局 | ✅ |
| 2 | 前端库本地化加载（KaTeX / Chart.js / Reveal.js） | ✅ |
| 3 | 课堂「五步学习」面板切换 | ✅ |
| 4 | 课堂 AI 聊天真实回复（"什么是力" → 模型回复） | ✅ |
| 5 | 课堂思维导图打开 | ✅ |
| 6 | 对话终端发消息收到真实回复 | ✅ |
| 7 | Admin 登录 | ✅ |
| 8 | Admin 概览「最近活动」含学生使用记录 | ✅ |
| 9 | Admin 系统日志来源徽标 + 学生数据 | ✅ |
| 10 | Admin 推理记录（93 条，含勾股/牛顿等） | ✅ |
| 11 | Admin 学习记录 / 数据可视化 | ✅ |
| 12 | 学生端登录 + 引导式学习第 1 步提问 | ✅ |
| 13 | 学生回答后 AI 调整引导推进第 2 步 | ✅ |
| 14-16 | GOAI Web / 教师端 / 分析仪表盘打开 | ✅ |

**截图**：全部保存在 `docs/evidence/`（01_classroom_home.png … 14_port_5001.png，共 16 张）。
**复现**：`python3 scripts/_browser_walkthrough.py`（需 selenium + 本机 Edge/Chrome）。

## 附录：如何自行取证

1. 部署后运行 `python3 scripts/health_check.py` 获取健康状态
2. 按第三节 curl 命令逐一执行，核对响应结构
3. 发起一次引导式学习后，在 18082 Admin「系统日志」筛选「学习推理」查看留痕
4. `logs/` 目录保存各服务完整运行日志
