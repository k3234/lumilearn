# LumiLearn 参考文献（reference.md）

> 主要录入 OpenMAIC 论文信息与本项目引用的技术资料。
> 声明：OpenMAIC 论文信息以公开渠道可查为准，如有出入以官方发布为准。

## 一、OpenMAIC 论文信息

1. **MAIC（Multi-Agent Interactive Classroom）范式论文**
   - 标题：MAIC: 基于多智能体交互式课堂的教育大模型应用研究（以公开论文/项目文档为准）
   - 项目主页：https://open.maic.chat/
   - 相关开源仓库（如有）：OpenMAIC 相关 GitHub 仓库
   - 内容要点：由 AI 教师、AI 同学等多智能体组成虚拟课堂，围绕同一学习目标开展讲授、提问、讨论与测验的交互式学习。

> 说明：正式参赛材料引用时，应核对 OpenMAIC 官方发布的最新论文标题、作者与出处后再录入此处，避免引用版本错误。

## 二、本项目基于的基础技术

2. **Qwen2.5 系列**
   - 项目：Qwen2.5（阿里云通义千问开源系列）
   - 说明：本项目采用 Qwen2.5-1.5B 做 LoRA 微调，Qwen2.5-7B 作为费曼引导默认模型（Ollama 远程调用）。

3. **Ollama**
   - 项目：Ollama（本地大模型运行框架）
   - 说明：本地/远程 Ollama 服务作为默认推理容器，`http://localhost:11434`。

4. **GGUF 量化**
   - 说明：采用 Q8_0 量化格式部署微调模型（1.64GB），纯 CPU 可推理。

5. **rasbt/LLMs-from-scratch**
   - 仓库：https://github.com/rasbt/LLMs-from-scratch
   - 说明：自研 8M Transformer 的学习参考（BPE tokenizer、训练、推理）。

6. **llama.cpp**
   - 仓库：https://github.com/ggerganov/llama.cpp
   - 说明：本地推理与量化参考实现。

7. **费曼学习法**
   - 说明：本项目教学内核，落成五步可编排流程（现象引入→认知冲突→思维模型→自主推导→费曼测试）。

## 三、引用规范

- 报告与 README 中引用本文件时写作"参考文献见 `docs/reference.md`"；
- 涉及 OpenMAIC 论文的具体引用格式（作者、期刊/会议、年份）在提交正式材料前由开发者核实官方出处后补齐。
