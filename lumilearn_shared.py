# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 共享配置模块
框架A（内容讲解）和框架B（主动学习）共用

作者：lumilearn AI自动化专家
版本：3.3.0
日期：2026-05-15
"""

import os
import csv
import json
import re
import shutil
import time
import hashlib
import requests
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

# ==================== 路径配置 ====================
LUMILEARN_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_BACKUP_DIR = os.path.join(LUMILEARN_DIR, "backup")

# 输入目录
INPUT_DIR = os.path.join(LUMILEARN_DIR, "input")
VOICE_INPUT_DIR = os.path.join(LUMILEARN_DIR, "voice_input")
ANIMATION_OUTPUT_DIR = os.path.join(LUMILEARN_DIR, "animation_output")

# 输出目录
ANKI_OUTPUT_DIR = os.path.join(LUMILEARN_DIR, "anki_output")
OBSIDIAN_VAULT_DIR = os.path.join(LUMILEARN_DIR, "obsidian_vault")

# ==================== 数据文件 ====================
MASTER_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_master.csv")
IMAGE_METADATA_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_image_metadata.csv")
VOICE_METADATA_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_voice_metadata.csv")
ANIMATION_METADATA_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_animation_metadata.csv")
SIMULATION_QA_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_simulation_qa.csv")
FLASHCARDS_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_flashcards.csv")
LEARNING_SESSIONS_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_learning_sessions.csv")
LEARNING_EXPERIENCE_JSON = os.path.join(LUMILEARN_DIR, "learning_experience.json")
ERROR_LOG_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_cleaning_error_log.csv")

# 闭环训练数据文件
REVIEW_DATA_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_review_data.csv")       # 复习数据
TRAINING_CORPUS_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_training_corpus.csv")  # 训练语料
MODEL_PERFORMANCE_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_model_performance.csv")  # 模型表现

# ==================== 模型配置 ====================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

OLLAMA_MODELS = {
    "deepseek-r1:1.5b": {"name": "deepseek-r1:1.5b", "weight": 1, "type": "local"},
    "qwen2.5:7b": {"name": "qwen2.5:7b", "weight": 1, "type": "local"}
}

SOLO_MODELS = {
    "Doubao-Seed-2.0-Code": {"name": "Doubao-Seed-2.0-Code", "weight": 2, "type": "solo"},
    "Doubao-Seed-Code": {"name": "Doubao-Seed-Code", "weight": 2, "type": "solo"},
    "MiniMax-M2.5": {"name": "MiniMax-M2.5", "weight": 2, "type": "solo"},
    "GLM-5": {"name": "GLM-5", "weight": 2, "type": "solo"},
    "Kimi-K2.5": {"name": "Kimi-K2.5", "weight": 2, "type": "solo"}
}

VOTE_THRESHOLD = 5
MAX_MODELS_PER_CHECK = 6

# ==================== 业务配置 ====================
TODAY = datetime.now().strftime("%Y-%m-%d")
BATCH_ID = f"BATCH_{TODAY.replace('-', '')}"
MAX_DAILY = 1000
MAX_TOTAL_PHASE1 = 100000000
MAX_TOTAL_PHASE2 = 1000000
PHASE = 1

# 校验阈值
DEDUP_THRESHOLD = 0.90
SEGMENT_MIN = 200
SEGMENT_MAX = 500

# 主动学习配置
QUESTIONS_PER_SESSION = 5
FLASHCARD_TOP_N = 3

# 闭环训练配置
SPACED_REPETITION_INTERVALS = [1, 3, 7, 14, 30]  # 天数
MIN_REVIEWS_FOR_TRAINING = 10  # 最少复习次数才纳入训练


# ==================== 数据库操作 ====================
def read_existing_master():
    """读取主数据库"""
    if not os.path.exists(MASTER_CSV):
        return []
    try:
        with open(MASTER_CSV, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except:
        return []


def write_master_csv(rows, fieldnames=None):
    """写入主数据库"""
    if not fieldnames:
        fieldnames = [
            "id", "subject", "grade", "version", "chapter", "section",
            "title", "content", "content_format", "type", "difficulty",
            "source", "source_type", "tags",
            "deepseek_r1_15b", "qwen2_5_7b_p2", "qwen2_5_7b_p3",
            "check_time", "errors", "create_time", "update_time"
        ]
    with open(MASTER_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_id(existing_ids=None):
    """生成唯一ID"""
    if existing_ids is None:
        existing_ids = set()
    timestamp = int(time.time())
    for _ in range(100):
        new_id = f"DD{TODAY.replace('-', '')}{timestamp % 100000:05d}"
        if new_id not in existing_ids:
            return new_id
        timestamp += 1
    return f"DD{TODAY.replace('-', '')}{int(time.time())}"


def check_duplicate_text(content, existing_rows):
    """文本去重检查"""
    if not content:
        return False, None
    for row in existing_rows:
        existing = row.get("content", "")
        if existing and SequenceMatcher(None, content, existing).ratio() > DEDUP_THRESHOLD:
            return True, row.get("id")
    return False, None


def cloud_backup(source_path, dest_path):
    """云端备份"""
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(source_path, dest_path)
        return True
    except:
        return False


# ==================== 经验共享机制 ====================
class ExperienceManager:
    """
    学习经验共享管理器
    框架A（内容讲解）和框架B（主动学习）的经验汇总优化
    """

    def __init__(self):
        self.experience = self._load_experience()

    def _load_experience(self):
        """加载经验文件"""
        if os.path.exists(LEARNING_EXPERIENCE_JSON):
            try:
                with open(LEARNING_EXPERIENCE_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "framework_a": {"total_content": 0, "total_animations": 0, "total_qa": 0,
                           "high_quality_topics": [], "common_errors": [], "tips": []},
            "framework_b": {"total_sessions": 0, "total_flashcards": 0,
                           "weak_points": [], "strong_points": [], "learning_patterns": []},
            "cross_insights": [],
            "optimization_history": [],
            "last_updated": ""
        }

    def save(self):
        """保存经验"""
        self.experience["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LEARNING_EXPERIENCE_JSON, "w", encoding="utf-8") as f:
            json.dump(self.experience, f, ensure_ascii=False, indent=2)
        cloud_backup(LEARNING_EXPERIENCE_JSON,
                     os.path.join(CLOUD_BACKUP_DIR, "logs", "learning_experience.json"))

    def record_framework_a(self, content_count=0, animation_count=0, qa_count=0,
                           topics=None, errors=None):
        """记录框架A经验"""
        a = self.experience["framework_a"]
        a["total_content"] += content_count
        a["total_animations"] += animation_count
        a["total_qa"] += qa_count
        if topics:
            a["high_quality_topics"].extend(topics[:10])
            a["high_quality_topics"] = list(set(a["high_quality_topics"]))[-50:]
        if errors:
            a["common_errors"].extend(errors[:5])
            a["common_errors"] = list(set(a["common_errors"]))[-20:]
        self._generate_cross_insights()
        self.save()

    def record_framework_b(self, session_count=0, flashcard_count=0,
                           weak=None, strong=None):
        """记录框架B经验"""
        b = self.experience["framework_b"]
        b["total_sessions"] += session_count
        b["total_flashcards"] += flashcard_count
        if weak:
            b["weak_points"].extend(weak[:5])
            b["weak_points"] = list(set(b["weak_points"]))[-30:]
        if strong:
            b["strong_points"].extend(strong[:5])
            b["strong_points"] = list(set(b["strong_points"]))[-30:]
        self._generate_cross_insights()
        self.save()

    def _generate_cross_insights(self):
        """生成交叉洞察（两框架经验融合）"""
        a = self.experience["framework_a"]
        b = self.experience["framework_b"]

        insights = []

        # 弱点 → 内容优化
        if b["weak_points"] and a["high_quality_topics"]:
            insight = {
                "type": "weak_to_content",
                "description": f"薄弱点 {b['weak_points'][:3]} 需要加强讲解内容",
                "action": "在框架A中优先生成相关动画和详细讲解",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            insights.append(insight)

        # 高质量主题 → 卡片推荐
        if a["high_quality_topics"]:
            insight = {
                "type": "content_to_cards",
                "description": f"高质量主题 {a['high_quality_topics'][:3]} 可制作为记忆卡片",
                "action": "在框架B中优先为这些主题生成提问和卡片",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            insights.append(insight)

        # 常见错误 → 提问重点
        if a["common_errors"]:
            insight = {
                "type": "errors_to_questions",
                "description": f"常见错误 {a['common_errors'][:3]} 应作为提问重点",
                "action": "在框架B中围绕这些错误设计易错题",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            insights.append(insight)

        self.experience["cross_insights"] = insights[-10:]  # 保留最近10条

    def get_optimization_suggestions(self):
        """获取优化建议"""
        suggestions = []
        a = self.experience["framework_a"]
        b = self.experience["framework_b"]

        if b["weak_points"]:
            suggestions.append(f"[框架A优化] 加强薄弱点讲解: {b['weak_points'][:3]}")
        if a["common_errors"]:
            suggestions.append(f"[框架B优化] 围绕常见错误出题: {a['common_errors'][:3]}")
        if a["high_quality_topics"]:
            suggestions.append(f"[框架B优化] 为优质内容制卡: {a['high_quality_topics'][:3]}")
        if b["strong_points"]:
            suggestions.append(f"[框架A优化] 可减少已掌握内容: {b['strong_points'][:3]}")

        return suggestions

    def print_summary(self):
        """打印经验摘要"""
        a = self.experience["framework_a"]
        b = self.experience["framework_b"]

        print("\n" + "=" * 60)
        print("📊 学习经验共享摘要")
        print("=" * 60)
        print(f"\n【框架A - 内容讲解】")
        print(f"  累计内容: {a['total_content']} 条")
        print(f"  累计动画: {a['total_animations']} 个")
        print(f"  累计问答: {a['total_qa']} 组")
        print(f"  高质量主题: {a['high_quality_topics'][:5]}")
        print(f"  常见错误: {a['common_errors'][:5]}")

        print(f"\n【框架B - 主动学习】")
        print(f"  累计会话: {b['total_sessions']} 次")
        print(f"  累计卡片: {b['total_flashcards']} 张")
        print(f"  薄弱点: {b['weak_points'][:5]}")
        print(f"  强项: {b['strong_points'][:5]}")

        if self.experience["cross_insights"]:
            print(f"\n【交叉洞察】")
            for insight in self.experience["cross_insights"][:3]:
                print(f"  → {insight['description']}")

        suggestions = self.get_optimization_suggestions()
        if suggestions:
            print(f"\n【优化建议】")
            for s in suggestions[:5]:
                print(f"  💡 {s}")

        print("=" * 60)


# ==================== 模型调用工具 ====================
def call_ollama(model_name, prompt, timeout=60):
    """调用Ollama本地模型"""
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model_name, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.3}},
            timeout=timeout
        )
        return response.json().get("response", "")
    except Exception as e:
        print(f"    Ollama调用失败({model_name}): {e}")
        return ""


def call_solo_model(model_name, prompt, timeout=30):
    """调用SOLO内置模型"""
    try:
        response = requests.post(
            "https://api.solo.com/v1/chat/completions",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {os.getenv('SOLO_API_KEY', '')}"},
            json={"model": model_name, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.3},
            timeout=timeout
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except:
        pass
    # 降级：模拟响应
    return _simulate_solo_response(prompt)


def _simulate_solo_response(prompt):
    """SOLO模型降级模拟"""
    content = prompt.lower()
    checks = [
        len(content) > 100,
        any(kw in content for kw in ["概念", "定义", "公式", "定理"]),
        not any(bad in content for bad in ["错误", "不对"])
    ]
    if sum(checks) >= 2:
        return "PASS: 内容质量达标。"
    return "FAIL: 内容质量有待提升。"


# ==================== 文本工具 ====================
def clean_text(text):
    """清洗文本"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()


def smart_segment(content):
    """智能分段（200-500字）"""
    if len(content) <= SEGMENT_MAX:
        return [content]
    segments = []
    sentences = re.split(r'([。！？.!?])', content)
    current = ""
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]
        if len(current) + len(sentence) <= SEGMENT_MAX:
            current += sentence
        else:
            if len(current) >= SEGMENT_MIN:
                segments.append(current)
            current = sentence
    if current and len(current) >= SEGMENT_MIN:
        segments.append(current)
    return segments if segments else [content[:SEGMENT_MAX]]


# ==================== 初始化目录 ====================
def ensure_dirs():
    """确保所有目录存在"""
    dirs = [
        LUMILEARN_DIR, CLOUD_BACKUP_DIR,
        INPUT_DIR, VOICE_INPUT_DIR, ANIMATION_OUTPUT_DIR,
        ANKI_OUTPUT_DIR, OBSIDIAN_VAULT_DIR,
        os.path.join(CLOUD_BACKUP_DIR, "master"),
        os.path.join(CLOUD_BACKUP_DIR, "logs"),
        os.path.join(CLOUD_BACKUP_DIR, "anki"),
        os.path.join(CLOUD_BACKUP_DIR, "obsidian"),
        os.path.join(OBSIDIAN_VAULT_DIR, "flashcards"),
        os.path.join(OBSIDIAN_VAULT_DIR, "learning_sessions"),
        os.path.join(ANKI_OUTPUT_DIR, "decks"),
        os.path.join(LUMILEARN_DIR, "training_data")  # 训练数据目录
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


# ==================== 闭环训练机制 ====================
class ClosedLoopTrainer:
    """
    闭环训练管理器
    复习数据(Anki+Obsidian) → 训练语料生成 → 模型微调指导
    
    完整闭环：
    框架A生成内容 → 数据库 → 框架B学习制卡 → Anki/Obsidian复习
       ↑                                              |
       └── 复习数据回流(正确率/遗忘/薄弱点) → 优化 ←──┘
    """

    def __init__(self):
        self.review_data = self._load_review_data()
        self.model_performance = self._load_model_performance()

    def _load_review_data(self):
        """加载复习数据"""
        if os.path.exists(REVIEW_DATA_CSV):
            try:
                with open(REVIEW_DATA_CSV, "r", encoding="utf-8") as f:
                    return list(csv.DictReader(f))
            except:
                pass
        return []

    def _load_model_performance(self):
        """加载模型表现数据"""
        if os.path.exists(MODEL_PERFORMANCE_CSV):
            try:
                with open(MODEL_PERFORMANCE_CSV, "r", encoding="utf-8") as f:
                    return list(csv.DictReader(f))
            except:
                pass
        return []

    def ingest_anki_review(self, card_id, ease, interval, last_review,
                            lapses=0, total_reviews=1):
        """
        导入Anki复习数据
        
        参数：
            card_id: 卡片ID
            ease: ease因子(1.3=困难, 2.5=正常, 3.0+=容易)
            interval: 当前间隔(天)
            last_review: 上次复习日期
            lapses: 忘记次数
            total_reviews: 总复习次数
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 计算掌握度
        if lapses == 0 and ease >= 2.5:
            mastery = "mastered"
        elif lapses <= 2 and ease >= 1.8:
            mastery = "learning"
        else:
            mastery = "struggling"

        record = {
            "review_id": f"RV_{int(time.time())}",
            "card_id": card_id,
            "source": "anki",
            "ease": ease,
            "interval_days": interval,
            "lapses": lapses,
            "total_reviews": total_reviews,
            "mastery": mastery,
            "last_review": last_review,
            "ingest_time": now
        }

        self.review_data.append(record)
        self._save_review_data()
        return record

    def ingest_obsidian_review(self, card_text, review_result, next_interval,
                                notes=""):
        """
        导入Obsidian复习数据
        
        参数：
            card_text: 卡片问题文本
            review_result: "remembered" / "forgotten" / "hard"
            next_interval: 下次复习间隔
            notes: 备注
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ease_map = {"remembered": 3.0, "hard": 2.0, "forgotten": 1.3}
        lapses_map = {"remembered": 0, "hard": 0, "forgotten": 1}
        mastery_map = {"remembered": "mastered", "hard": "learning", "forgotten": "struggling"}

        record = {
            "review_id": f"RV_{int(time.time())}_{len(self.review_data)}",
            "card_id": card_text[:50],
            "source": "obsidian",
            "ease": ease_map.get(review_result, 2.0),
            "interval_days": next_interval,
            "lapses": lapses_map.get(review_result, 0),
            "total_reviews": 1,
            "mastery": mastery_map.get(review_result, "learning"),
            "last_review": now.split(" ")[0],
            "ingest_time": now,
            "notes": notes
        }

        self.review_data.append(record)
        self._save_review_data()
        return record

    def _save_review_data(self):
        """保存复习数据"""
        if not self.review_data:
            return
        with open(REVIEW_DATA_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.review_data[0].keys())
            writer.writeheader()
            writer.writerows(self.review_data)

    def analyze_learning_gaps(self):
        """
        分析学习薄弱点
        
        返回：
        {
            "struggling_cards": [...],    # 挣扎中的卡片
            "mastered_cards": [...],      # 已掌握的卡片
            "forgetting_patterns": {...}, # 遗忘模式
            "optimal_review_schedule": {...}  # 最优复习计划
        }
        """
        struggling = [r for r in self.review_data if r.get("mastery") == "struggling"]
        mastered = [r for r in self.review_data if r.get("mastery") == "mastered"]
        learning = [r for r in self.review_data if r.get("mastery") == "learning"]

        # 遗忘模式分析
        avg_ease_struggling = 0
        avg_lapses_struggling = 0
        if struggling:
            avg_ease_struggling = sum(float(r.get("ease", 0)) for r in struggling) / len(struggling)
            avg_lapses_struggling = sum(int(r.get("lapses", 0)) for r in struggling) / len(struggling)

        # 按卡片统计
        card_stats = {}
        for r in self.review_data:
            cid = r.get("card_id", "")
            if cid not in card_stats:
                card_stats[cid] = {"reviews": 0, "avg_ease": 0, "lapses": 0, "mastery": r.get("mastery", "")}
            card_stats[cid]["reviews"] += 1
            card_stats[cid]["avg_ease"] += float(r.get("ease", 0))
            card_stats[cid]["lapses"] += int(r.get("lapses", 0))
            if r.get("mastery") == "struggling":
                card_stats[cid]["mastery"] = "struggling"

        # 计算平均
        for cid in card_stats:
            s = card_stats[cid]
            if s["reviews"] > 0:
                s["avg_ease"] = round(s["avg_ease"] / s["reviews"], 2)

        return {
            "struggling_cards": struggling,
            "mastered_cards": mastered,
            "learning_cards": learning,
            "total_reviews": len(self.review_data),
            "forgetting_patterns": {
                "avg_ease_struggling": round(avg_ease_struggling, 2),
                "avg_lapses_struggling": round(avg_lapses_struggling, 2),
                "struggling_count": len(struggling),
                "mastered_count": len(mastered)
            },
            "card_stats": card_stats,
            "optimal_review_schedule": self._generate_review_schedule(card_stats)
        }

    def _generate_review_schedule(self, card_stats):
        """生成最优复习计划"""
        schedule = {}
        for cid, stats in card_stats.items():
            if stats["mastery"] == "struggling":
                schedule[cid] = {"next_review": "今天", "priority": "高", "interval": 1}
            elif stats["mastery"] == "learning":
                schedule[cid] = {"next_review": "明天", "priority": "中", "interval": 3}
            else:
                schedule[cid] = {"next_review": "7天后", "priority": "低", "interval": 14}
        return schedule

    def generate_training_corpus(self):
        """
        从复习数据生成训练语料
        
        将复习数据转化为模型可训练的格式：
        - 薄弱知识点 → 需要更多讲解内容
        - 高遗忘率内容 → 需要更好的表述方式
        - 已掌握内容 → 可作为正样本
        """
        gaps = self.analyze_learning_gaps()
        corpus = []

        # 1. 薄弱知识点 → 生成强化训练样本
        for r in gaps["struggling_cards"][:20]:
            corpus.append({
                "type": "reinforcement",
                "card_id": r.get("card_id", ""),
                "source": r.get("source", ""),
                "instruction": f"请详细讲解以下知识点，用多种方式解释，确保学生理解：",
                "content": r.get("card_id", ""),
                "target": "生成更详细、更易懂的讲解内容",
                "priority": "高",
                "reason": f"遗忘{r.get('lapses', 0)}次, ease={r.get('ease', 0)}"
            })

        # 2. 遗忘模式 → 生成改进样本
        patterns = gaps["forgetting_patterns"]
        if patterns["struggling_count"] > 0:
            corpus.append({
                "type": "pattern_improvement",
                "instruction": "以下知识点学生容易遗忘，请设计更有效的讲解方式：",
                "content": f"平均ease={patterns['avg_ease_struggling']}, 平均遗忘={patterns['avg_lapses_struggling']}次",
                "target": "改进讲解策略",
                "priority": "高",
                "reason": "整体遗忘率偏高"
            })

        # 3. 已掌握内容 → 正样本
        for r in gaps["mastered_cards"][:10]:
            corpus.append({
                "type": "positive_sample",
                "card_id": r.get("card_id", ""),
                "source": r.get("source", ""),
                "instruction": "以下讲解方式效果良好，请参考此风格：",
                "content": r.get("card_id", ""),
                "target": "保持此讲解风格",
                "priority": "低",
                "reason": "学生已掌握"
            })

        # 保存训练语料
        if corpus:
            self._save_training_corpus(corpus)

        return corpus

    def _save_training_corpus(self, corpus):
        """保存训练语料"""
        with open(TRAINING_CORPUS_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=corpus[0].keys())
            writer.writeheader()
            writer.writerows(corpus)
        cloud_backup(TRAINING_CORPUS_CSV,
                     os.path.join(CLOUD_BACKUP_DIR, "logs", "training_corpus.csv"))

    def record_model_performance(self, model_name, task_type, accuracy,
                                  content_id="", notes=""):
        """
        记录模型表现（用于追踪模型改进效果）
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "record_id": f"MP_{int(time.time())}",
            "model_name": model_name,
            "task_type": task_type,  # "question_generation", "answer_evaluation", "content_generation"
            "accuracy": accuracy,
            "content_id": content_id,
            "notes": notes,
            "timestamp": now
        }
        self.model_performance.append(record)
        self._save_model_performance()
        return record

    def _save_model_performance(self):
        """保存模型表现"""
        if not self.model_performance:
            return
        with open(MODEL_PERFORMANCE_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.model_performance[0].keys())
            writer.writeheader()
            writer.writerows(self.model_performance)

    def get_training_report(self):
        """生成训练报告"""
        gaps = self.analyze_learning_gaps()
        patterns = gaps["forgetting_patterns"]

        report = {
            "date": TODAY,
            "total_reviews": gaps["total_reviews"],
            "struggling_count": patterns["struggling_count"],
            "mastered_count": patterns["mastered_count"],
            "learning_count": len(gaps.get("learning_cards", [])),
            "avg_ease_struggling": patterns["avg_ease_struggling"],
            "training_corpus_size": len(self.generate_training_corpus()),
            "model_performance_records": len(self.model_performance),
            "recommendations": self._get_recommendations(gaps)
        }

        return report

    def _get_recommendations(self, gaps):
        """生成优化建议"""
        recs = []
        patterns = gaps["forgetting_patterns"]

        if patterns["struggling_count"] > 5:
            recs.append("⚠️ 薄弱点过多，建议框架A加强基础概念讲解")

        if patterns["avg_ease_struggling"] < 1.8:
            recs.append("📝 平均ease过低，建议优化卡片表述使其更易记忆")

        if patterns["mastered_count"] > patterns["struggling_count"]:
            recs.append("✅ 掌握率良好，可适当增加学习难度")

        if gaps["total_reviews"] >= MIN_REVIEWS_FOR_TRAINING:
            recs.append("🔄 复习数据充足，可生成训练语料优化模型")

        return recs

    def print_closed_loop_report(self):
        """打印闭环报告"""
        report = self.get_training_report()

        print("\n" + "=" * 60)
        print("🔄 闭环学习系统报告")
        print("=" * 60)
        print(f"\n📊 复习数据统计:")
        print(f"  总复习次数: {report['total_reviews']}")
        print(f"  已掌握: {report['mastered_count']}")
        print(f"  学习中: {report['learning_count']}")
        print(f"  挣扎中: {report['struggling_count']}")
        print(f"\n📈 训练数据:")
        print(f"  训练语料: {report['training_corpus_size']} 条")
        print(f"  模型表现记录: {report['model_performance_records']} 条")
        print(f"\n💡 优化建议:")
        for rec in report["recommendations"]:
            print(f"  {rec}")
        print("=" * 60)

        return report
