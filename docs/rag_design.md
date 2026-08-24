# LumiLearn RAG 知识库设计说明

> 日期：2026-08-12 · Day 3 开发
> 目标：让教学内容"有据可查"，从纯模型生成升级为"知识库检索增强 + 模型生成"。

---

## 一、设计原则

| 原则 | 说明 |
|---|---|
| **零外部依赖** | 不引入向量数据库（FAISS / chroma / milvus），不要求联网安装任何包，全部纯 Python 实现 |
| **轻量可部署** | 天虹服务器（CPU 环境）可直接运行；索引构建毫秒级 |
| **失败降级** | 检索失败/无匹配时返回空上下文，教学主流程绝不阻塞 |
| **数据本地化** | 索引数据全部来自本地 SQLite（`training_data` + `knowledge_nodes`），无隐私外泄 |

---

## 二、架构

```
training_data 表 (published) ─┐
knowledge_nodes 表            ├─→ 文档集合 ─→ 关键词倒排索引（内存）
                              │              ├─ term → [doc_idx → tf]
                              │              └─ doc_len / df 统计
学生提问 / 教学主题            ─→ tokenize ─→ BM25 简化打分 ─→ Top-K 结果
                                                              │
                                                              ▼
                                              FeynmanEngine prompt 注入
                                              （参考资料，仅参考不可照抄）
```

## 三、核心模块

`framework/services/knowledge_retrieval.py`

| 组件 | 说明 |
|---|---|
| `tokenize(text)` | 轻量中文分词：领域词典（约 180 个学科术语）精确匹配 + 字母数字连续段 + 中文 2-gram + 停用词过滤，上限 32 词 |
| `KnowledgeRetriever.build_index()` | 加载 `training_data(status=published)`（取 title/chapter/keywords/content 前 600 字）与 `knowledge_nodes`（name/category/description），构建倒排索引 |
| `search(query, top_k, subject)` | 简化 BM25：`score = Σ idf·(tf/(tf+0.75))`，idf 用对数平滑；可选学科过滤 |
| `format_rag_context(results)` | 将 Top-K 结果格式化为注入 prompt 的参考资料文本（默认 800 字上限） |
| `get_knowledge_retriever()` | 全局单例，索引惰性构建 + 内存缓存；`refresh()` 强制重建 |

## 四、与多 Agent 系统集成

`lumilearn_multi_agent.py` 的 **FeynmanTeacher.run()**：

```
1. retriever.search(topic, top_k=3)   → rag_sources（含 source/id/title/subject/score）
2. format_rag_context()               → rag_context 文本
3. engine.explain(topic, level, extra_context=rag_context)
   └─ 每步 prompt 注入"参考资料（仅作内容参考，不可直接照抄）"
4. 聚合报告 teaching.rag_sources 随报告返回并落库
```

`framework/engines/feynman_engine.py` 改动：
- `_build_feynman_prompt(..., extra_context=None)` 新增可选参数，非空时注入 prompt（截断 800 字）
- `explain(topic, level, extra_context="")` / `explain_step(..., extra_context="")` 透传
- 不传 extra_context 时行为与旧版完全一致（向后兼容）

## 五、检索 API

`lumilearn_web.py` 新增（需登录）：

| 端点 | 说明 |
|---|---|
| `GET/POST /api/knowledge/search?q=&top_k=&subject=` | 关键词检索，返回结果列表（含相关度 score） |
| `GET /api/knowledge/status` | 索引状态（文档数 / 词项数 / 构建时间） |

## 六、示例结果

本地验证（4 条注入数据 + 13 个知识点）：

```
查询「勾股定理」→ 勾股定理 (training_data) / 勾股定理 (knowledge_node)
查询「牛顿第二定律」→ 牛顿第二定律 (training_data)
查询「光合作用」→ 光合作用四阶段 (training_data)
```

天虹服务器 `training_data` 已导入 1152 条教学资源，检索覆盖更广。

## 七、局限与后续优化

| 局限 | 后续优化方向 |
|---|---|
| 2-gram 分词粒度较粗 | 引入 jieba 词典分词（可离线安装） |
| 无语义相似度 | 阶段二引入轻量 embedding（如 ONNX 本地模型） |
| 索引全内存 | 数据量大时可持久化到磁盘（shelve） |

---

*本模块为 Day 3 原型，符合"不引入向量数据库"的参赛约束，检索质量可通过扩充 training_data 持续提升。*
