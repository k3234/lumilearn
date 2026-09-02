# LumiLearn — AI-Powered Education for Everyone

> **AI Transforming the Educational Paradigm and Enhancing AI Literacy**

## Project Overview

LumiLearn is an open-source, multi-agent AI education platform built from scratch by a high school student. Its core mission is **"computing power equity"** — making AI-powered teaching accessible on low-spec hardware without requiring expensive GPUs.

**Built with:** Python 3.10+, Ollama (local LLM), Flask, SQLite, pure Python BM25 retrieval, self-developed 8M-parameter Transformer.

**Runs on:** A standard 4GB RAM laptop with no dedicated GPU.

## SDGs Alignment

| SDG | Target | Contribution |
|-----|--------|--------------|
| **SDG 4** — Quality Education | Ensure inclusive and equitable quality education | Low-cost AI tutoring for underserved schools |
| **SDG 9** — Industry, Innovation & Infrastructure | Build resilient infrastructure & promote innovation | Zero-dependency RAG, self-developed model pipeline |
| **SDG 10** — Reduced Inequalities | Reduce inequality within and among countries | "Computing power equity" — AI on old laptops |
| **SDG 17** — Partnerships | Strengthen implementation means | MIT-licensed open source, community-driven |

## Core Technologies

### 1. Self-Developed Transformer (8M Parameters)
- Full training pipeline: BPE tokenizer → data preparation → GPT-2 style training → inference
- Trained entirely on CPU (~23 min for full training)
- 26+ tokens/sec inference speed on standard hardware
- Suitable for classroom demonstrations and educational scenarios

### 2. Multi-Agent Teaching Pipeline (Feynman Method)
- **FeynmanTeacher Agent**: Generates structured explanations following the 5-step Feynman technique (introduce → conflict → model → derive → test)
- **SelfCritique Agent**: Evaluates output quality (0-100 score) with automatic retry on low scores
- **CoachAgent**: Provides personalized learning recommendations based on student performance
- Agents collaborate via LangGraph workflow with timeout and token budget controls

### 3. Pure Python RAG Knowledge Base
- 1,166 published knowledge entries across math, physics, and chemistry
- Zero external dependencies: BM25 ranking with synonym expansion
- Automatic knowledge node structuring via pipeline (coarse segmentation → fine-grained → validation)
- 5/5 retrieval accuracy on verified test cases

### 4. Low-Spec Hardware Adaptation
- **Peak memory**: 1.77 GB (1.5B model Q8_0 quantized)
- **CPU-only**: No CUDA, no GPU required
- **Minimum specs**: 4GB RAM, 4-core CPU, 5GB disk
- **One-click deployment**: `curl ... | bash` or `irm ... | iex`

## System Architecture

```
┌────────────────────────────────────────────────────┐
│  Frontend (Static Templates)                        │
│  classroom.html │ lumiterm.html │ admin.html        │
├────────────────────────────────────────────────────┤
│  API Gateway (Flask Blueprints)                     │
│  /api/learn │ /api/analytics │ /api/admin/*         │
├────────────────────────────────────────────────────┤
│  Business Logic (Framework)                         │
│  FeynmanEngine │ RAG Retrieval │ Security Gateway   │
├────────────────────────────────────────────────────┤
│  Multi-Agent Orchestration                          │
│  FeynmanAgent → SelfCritique → CoachAgent           │
├────────────────────────────────────────────────────┤
│  Model Inference Layer                              │
│  Ollama (local) │ Cloud API │ Self-developed 8M model│
└────────────────────────────────────────────────────┘
```

## Key Achievements

| Metric | Value |
|--------|-------|
| RAG Knowledge Base | 1,166 entries, 5/5 recall rate |
| CPU Inference Speed | 26+ tokens/sec (8M model) |
| Test Coverage | 591 pytest cases (569 passed) |
| Peak Memory | 1.77 GB |
| Deployment Time | < 10 seconds (one-liner) |
| Security Audit | 100% clean (zero credential leaks) |

## Use Cases

### Math: Pythagorean Theorem
- 5-step Feynman teaching: real-world scenario → cognitive conflict → mathematical model → derivation → self-test
- RAG sources cited for each explanation
- Automatic quality scoring with retry

### Physics: Newton's Second Law
- Multi-agent collaboration: teaching → assessment → coaching
- Student explanation evaluated, mastery level determined
- Personalized next-topic recommendations

### Chemistry: Covalent Bonds
- Knowledge retrieval from structured chemical facts
- Interactive Q&A with adaptive difficulty

## TRL Assessment (Technology Readiness Level)

**Current TRL: 6** — System prototype demonstrated in relevant environment

**Evidence:**
1. ✅ Fully functional web application deployed on remote server (Tianhong cloud, CPU-only)
2. ✅ 7 service ports operational simultaneously (classroom, API, admin, analytics, teacher, student, analytics dashboard)
3. ✅ Real browser walkthrough: 23/23 checks passed with real model inference
4. ✅ Learning sessions completed end-to-end: guide → student response → AI adjustment → logging
5. ✅ Multi-agent pipeline verified: Feynman 5 steps + scoring + recommendations in 56.9s
6. ✅ RAG retrieval verified on 1,166 knowledge entries
7. ✅ Docker Compose deployment working
8. ✅ One-click install script tested on Linux and Windows

**Next steps to TRL 7:** Real classroom deployment with student users for extended period.

## How to Run

```bash
# One-click install (Linux/macOS)
curl -fsSL https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.sh | bash

# Or Docker
docker compose up -d

# Access
# Admin panel: http://localhost:18080
# Teacher portal: http://localhost:5001
# Student learning: http://localhost:5010
```

## Repository

- **GitHub**: https://github.com/k3234/lumilearn
- **License**: MIT
- **Language**: Python 3.10+

## Contact

Developed by a high school student as a passion project to make AI education accessible to all.
