# LumiLearn 学习笔记

> 记录 LumiLearn 项目开发过程中的学习心得、技术决策和问题解决方案。

## 模块索引

| 模块编号 | 标题 | 日期 | 状态 | 难度 |
|---------|------|------|------|------|
| 0.1 | 存储管理与磁盘空间优化 | 2026-06-01 | ✅ 完成 | ⭐⭐☆☆☆ |
| 0.2 | 文档管理与学习笔记体系 | 2026-06-01 | ✅ 完成 | ⭐⭐☆☆☆ |
| 4.1 | Whisper 语音识别入门 | 2026-06-01 | ✅ 完成 | ⭐⭐⭐☆☆ |
| 4.2 | PaddleOCR 文字识别入门 | 2026-06-01 | ✅ 完成 | ⭐⭐⭐☆☆ |
| 4.3 | Prompt工程：AI讲解内容自我审查 | 2026-06-01 | ✅ 完成 | ⭐⭐⭐⭐☆ |
| 5.1 | 前端录音 API 集成 | 2026-06-01 | ✅ 完成 | ⭐⭐⭐☆☆ |
| 5.2 | 文件上传 API 设计 | 2026-06-01 | ✅ 完成 | ⭐⭐⭐☆☆ |

## 笔记模板

新笔记请使用 [template.md](template.md) 作为起点。

## 快速命令

> 以下脚本位于 `archive/debug_scripts/auto_logger.py`（历史归档），如已删除则无需执行。

```bash
# 同步 Git 提交记录到开发日志
python archive/debug_scripts/auto_logger.py --sync

# 交互式关联 commit 到学习笔记
python archive/debug_scripts/auto_logger.py --link

# 查看开发报告
python archive/debug_scripts/auto_logger.py --report
```