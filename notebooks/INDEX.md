# LumiLearn 教学笔记本索引

> 由 notebook_generator.py 基于 learn-shit 风格自动生成

## 已生成笔记本

| 主题 | 知识点 | 难度 | 生成日期 | Notion |
|------|--------|------|----------|--------|
| [complex_numbers](complex_numbers/complex_numbers.ipynb) | 复数定义/四则运算/复平面/共轭复数/模与辐角 | 高一 | 2026-05-30 | 未同步 |
| [vectors](vectors/vectors.ipynb) | 向量定义/加减法/数乘/数量积/坐标表示 | 高一 | 2026-05-30 | 未同步 |
| [functions](functions/functions.ipynb) | 定义域/值域/单调性/奇偶性/反函数 | 高一 | 2026-05-30 | 未同步 |

## 使用方式

### 在 Jupyter 中打开
```bash
jupyter notebook notebooks/
```

### 用 notebook_generator 生成新笔记本
```bash
python scripts/notebook_generator.py --topic "complex_numbers"
python scripts/notebook_generator.py --all
python scripts/notebook_generator.py --list
```

### 同步到 Notion（需配置 NOTION_API_TOKEN）
```bash
python scripts/notion_sync.py --check
python scripts/notion_sync.py --setup
python scripts/notion_sync.py --sync "notebooks/complex_numbers/complex_numbers.ipynb"
```

## 待生成主题
- 概率与统计
- 三角函数
- 数列
- 圆锥曲线