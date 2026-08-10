#!/usr/bin/env python3
"""
LumiLearn 本地数据库管理模块
基于 SQLite，零依赖、零配置、单文件存储

功能模块：
  A. 用户管理       — 教师/学生多用户支持
  B. 教学内容管理   — 知识图谱、训练数据、题目库
  C. 学习记录追踪   — 会话、答题记录、每日统计、学习进度
  D. 模型训练管理   — 实验记录、检查点、训练指标

用法示例：
    from framework.database import db

    db.init()                         # 首次初始化（自动建库建表）

    # 用户管理
    teacher = db.add_user("王老师", role="teacher")
    student = db.add_user("小明", role="student")

    # 教师录入教学内容
    db.add_training_data(
        subject="数学", chapter="勾股定理",
        title="直角三角形的边长关系",
        content="勾股定理：a² + b² = c²...",
        difficulty="基础"
    )

    # 录入题目
    db.add_question(
        subject="数学", topic="乘法",
        question="3×7=?", correct_answer="21",
        difficulty=2
    )

    # 记录答题
    sid = db.start_session(user_id=2, subject="数学")
    db.record_answer(
        session_id=sid, user_id=2,
        question="3×7=?", user_answer="18", correct_answer="21",
        topic="乘法", subject="数学", time_spent=12.5
    )
    db.end_session(sid)

    # 查询
    mistakes = db.get_mistakes(user_id=2, subject="数学")
    progress = db.get_progress(user_id=2)

    # 模型训练
    exp_id = db.add_experiment("AirLLM-3B", preset="airllm_3b")
    db.add_checkpoint(exp_id, step=100, tag="best", val_loss=1.73)
    db.finish_experiment(exp_id, best_val_loss=1.73, total_steps=500)
"""
import os
import json
import sqlite3
import threading
import time
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path


# ============================================================
# 数据库路径配置
# ============================================================

def _get_db_path() -> str:
    """获取数据库文件路径，支持环境变量配置"""
    env_path = os.environ.get("LUMILEARN_DB_PATH")
    if env_path:
        return env_path
    # 默认放在项目根目录
    project_root = Path(__file__).parent.parent
    return str(project_root / "lumilearn.db")


# ============================================================
# 建表 SQL
# ============================================================

_SCHEMA = """
-- ============================================================
-- A. 用户管理
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    role        TEXT DEFAULT 'student',     -- teacher / student
    avatar      TEXT DEFAULT '',
    username    TEXT DEFAULT '',
    password_hash TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- 学习报告（GOAI Web 生成）
CREATE TABLE IF NOT EXISTS learning_reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    topic       TEXT NOT NULL,
    report_json TEXT DEFAULT '{}',
    score       REAL DEFAULT 0.0,
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_learning_reports_user ON learning_reports(user_id);

-- ============================================================
-- B. 教学内容管理
-- ============================================================

CREATE TABLE IF NOT EXISTS subjects (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT UNIQUE NOT NULL,
    icon  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,            -- geometry/algebra/physics/functions/statistics
    difficulty      INTEGER DEFAULT 1,        -- 1-5
    animation_type  TEXT DEFAULT 'auto',
    description     TEXT DEFAULT '',
    prereqs         TEXT DEFAULT '[]'         -- JSON数组: ["triangle_basics"]
);

CREATE TABLE IF NOT EXISTS training_data (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    subject             TEXT NOT NULL,
    chapter             TEXT NOT NULL,
    title               TEXT NOT NULL,
    content             TEXT NOT NULL,
    grade               TEXT DEFAULT '高中',
    content_type        TEXT DEFAULT '概念定义',
    difficulty          TEXT DEFAULT '基础',
    keywords            TEXT DEFAULT '',
    prerequisites       TEXT DEFAULT '',
    learning_objectives TEXT DEFAULT '',
    common_mistakes     TEXT DEFAULT '',
    source              TEXT DEFAULT 'manual',
    source_type         TEXT DEFAULT 'manual',
    quality_score       REAL DEFAULT 0.0,
    word_count          INTEGER DEFAULT 0,
    hash                TEXT DEFAULT '',
    version             INTEGER DEFAULT 1,
    status              TEXT DEFAULT 'draft', -- draft/reviewed/published
    created_at          TEXT DEFAULT (datetime('now','localtime')),
    updated_at          TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS questions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id    TEXT DEFAULT '',
    subject         TEXT NOT NULL,
    topic           TEXT DEFAULT '',
    question        TEXT NOT NULL,
    correct_answer  TEXT NOT NULL,
    explanation     TEXT DEFAULT '',
    difficulty      INTEGER DEFAULT 2,        -- 1基础/2进阶/3挑战
    question_type   TEXT DEFAULT 'short',     -- short/multiple/essay
    options         TEXT DEFAULT '',           -- JSON: 选择题选项
    created_by      INTEGER DEFAULT 1,        -- 录入教师 user_id
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- C. 学习记录追踪
-- ============================================================

CREATE TABLE IF NOT EXISTS sessions (
    id                TEXT PRIMARY KEY,        -- 'session_1718000000'
    user_id           INTEGER NOT NULL,
    subject           TEXT DEFAULT '',
    start_time        REAL NOT NULL,
    end_time          REAL,
    questions_answered INTEGER DEFAULT 0,
    correct_count     INTEGER DEFAULT 0,
    focus_score       REAL DEFAULT 0.0,
    duration_minutes  REAL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT DEFAULT '',
    user_id         INTEGER NOT NULL,
    question        TEXT NOT NULL,
    user_answer     TEXT DEFAULT '',
    correct_answer  TEXT DEFAULT '',
    is_correct      INTEGER DEFAULT 0,        -- 0错 1对
    topic           TEXT DEFAULT '',
    subject         TEXT DEFAULT '',
    hints_used      INTEGER DEFAULT 0,
    time_spent      REAL DEFAULT 0.0,
    gave_up         INTEGER DEFAULT 0,
    timestamp       REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS daily_stats (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    date              TEXT NOT NULL,           -- '2026-06-14'
    total_time        REAL DEFAULT 0.0,       -- 秒
    questions_answered INTEGER DEFAULT 0,
    correct_count     INTEGER DEFAULT 0,
    topics_studied    TEXT DEFAULT '[]',       -- JSON数组
    max_focus_score   REAL DEFAULT 0.0,
    UNIQUE(user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS progress (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    node_id     TEXT NOT NULL,
    mastery     REAL DEFAULT 0.0,             -- 0-1 掌握度
    attempts    INTEGER DEFAULT 0,
    total_time  REAL DEFAULT 0.0,             -- 秒
    last_study  REAL,                          -- timestamp
    UNIQUE(user_id, node_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (node_id) REFERENCES knowledge_nodes(id)
);

-- ============================================================
-- D. 模型训练管理
-- ============================================================

CREATE TABLE IF NOT EXISTS experiments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    preset        TEXT DEFAULT '',
    status        TEXT DEFAULT 'running',     -- running/completed/failed
    config_json   TEXT DEFAULT '',
    output_dir    TEXT DEFAULT '',
    best_val_loss REAL,
    total_steps   INTEGER DEFAULT 0,
    started_at    TEXT DEFAULT (datetime('now','localtime')),
    finished_at   TEXT
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id   INTEGER NOT NULL,
    step            INTEGER NOT NULL,
    tag             TEXT DEFAULT '',          -- best/final/step_N
    train_loss      REAL,
    val_loss        REAL,
    learning_rate   REAL,
    grad_norm       REAL,
    file_path       TEXT NOT NULL,
    file_size_mb    REAL,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);

CREATE TABLE IF NOT EXISTS training_metrics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL,
    step          INTEGER NOT NULL,
    train_loss    REAL,
    val_loss      REAL,
    learning_rate REAL,
    grad_norm     REAL,
    step_time     REAL,
    logged_at     TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);

-- ============================================================
-- E. 待审核录入区
-- ============================================================

CREATE TABLE IF NOT EXISTS submissions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,             -- content / question / handwriting
    -- 提交内容（结构化字段，type=content/question 时填写）
    subject         TEXT DEFAULT '',
    chapter         TEXT DEFAULT '',
    title           TEXT DEFAULT '',
    content         TEXT DEFAULT '',
    question        TEXT DEFAULT '',
    correct_answer  TEXT DEFAULT '',
    explanation     TEXT DEFAULT '',
    topic           TEXT DEFAULT '',
    difficulty      TEXT DEFAULT '基础',
    content_type    TEXT DEFAULT '概念定义',
    grade           TEXT DEFAULT '高中',
    keywords        TEXT DEFAULT '',
    -- 关联手写记录（type=handwriting 时填写）
    handwriting_id  INTEGER DEFAULT NULL,
    -- 提交元信息
    source          TEXT DEFAULT 'manual',    -- manual / handwriting / ocr / ai_generated
    submitted_by    INTEGER DEFAULT 1,        -- 提交者 user_id
    submitted_by_name TEXT DEFAULT '',         -- 提交者姓名（冗余便于展示）
    -- 审核状态
    status          TEXT DEFAULT 'pending',   -- pending / approved / rejected / published
    review_comment  TEXT DEFAULT '',           -- 审核意见
    reviewed_by     INTEGER DEFAULT 0,        -- 审核人 user_id
    reviewed_at     TEXT,
    -- 时间戳
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (submitted_by) REFERENCES users(id),
    FOREIGN KEY (handwriting_id) REFERENCES handwriting_records(id)
);

-- ============================================================
-- F. 手写录入记录
-- ============================================================

CREATE TABLE IF NOT EXISTS handwriting_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    -- 原始手写数据
    image_path      TEXT DEFAULT '',          -- 手写图片文件路径
    strokes_json    TEXT DEFAULT '[]',        -- 笔画数据（JSON数组，每笔含点坐标序列）
    -- OCR 识别结果
    ocr_text        TEXT DEFAULT '',          -- OCR 识别出的文本
    ocr_confidence  REAL DEFAULT 0.0,         -- OCR 平均置信度
    ocr_details     TEXT DEFAULT '[]',        -- OCR 逐行详情（JSON）
    -- 识别后编辑的文本（用户可能修正OCR结果）
    edited_text     TEXT DEFAULT '',          -- 用户修正后的文本
    -- 元信息
    device          TEXT DEFAULT '',          -- 录入设备标识
    note            TEXT DEFAULT '',          -- 备注
    -- 关联提交（如有）
    submission_id   INTEGER DEFAULT 0,        -- 关联的 submission id
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ============================================================
-- 索引（加速常用查询）
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_training_data_subject ON training_data(subject);
CREATE INDEX IF NOT EXISTS idx_training_data_status ON training_data(status);
CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject);
CREATE INDEX IF NOT EXISTS idx_questions_knowledge ON questions(knowledge_id);
CREATE INDEX IF NOT EXISTS idx_answers_user ON answers(user_id);
CREATE INDEX IF NOT EXISTS idx_answers_session ON answers(session_id);
CREATE INDEX IF NOT EXISTS idx_answers_subject ON answers(subject);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_user ON progress(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, date);
CREATE INDEX IF NOT EXISTS idx_checkpoints_exp ON checkpoints(experiment_id);
CREATE INDEX IF NOT EXISTS idx_metrics_exp ON training_metrics(experiment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_submitter ON submissions(submitted_by);
CREATE INDEX IF NOT EXISTS idx_handwriting_user ON handwriting_records(user_id);

-- ============================================================
-- G. 教学任务管理
-- ============================================================

CREATE TABLE IF NOT EXISTS teaching_tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    subject         TEXT NOT NULL,
    grade           TEXT DEFAULT '高中',
    description     TEXT DEFAULT '',
    task_type       TEXT DEFAULT 'learn',     -- learn/exercise/review/assignment
    knowledge_ids   TEXT DEFAULT '[]',        -- JSON数组: 关联知识点ID
    data_ids        TEXT DEFAULT '[]',        -- JSON数组: 关联training_data IDs
    question_ids    TEXT DEFAULT '[]',        -- JSON数组: 关联questions IDs
    difficulty      TEXT DEFAULT '基础',
    target_score    INTEGER DEFAULT 60,
    time_limit      INTEGER DEFAULT 30,
    source          TEXT DEFAULT 'teacher',   -- teacher/auto_ai/manual
    source_detail   TEXT DEFAULT '',
    status          TEXT DEFAULT 'draft',     -- draft/active/completed/archived
    published_at    TEXT,
    created_by      INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS task_assignments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    status          TEXT DEFAULT 'assigned',  -- assigned/in_progress/completed/skipped
    score           REAL DEFAULT 0.0,
    time_spent      REAL DEFAULT 0.0,
    started_at      REAL,
    completed_at    REAL,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(task_id, user_id),
    FOREIGN KEY (task_id) REFERENCES teaching_tasks(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS task_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id   INTEGER NOT NULL,
    step_order      INTEGER NOT NULL,
    step_type       TEXT NOT NULL,
    question_id     INTEGER DEFAULT 0,
    is_correct      INTEGER DEFAULT 0,
    answer_text     TEXT DEFAULT '',
    points_earned   REAL DEFAULT 0.0,
    time_spent      REAL DEFAULT 0.0,
    completed_at    TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (assignment_id) REFERENCES task_assignments(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_subject ON teaching_tasks(subject);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON teaching_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON teaching_tasks(created_by);
CREATE INDEX IF NOT EXISTS idx_assignments_task ON task_assignments(task_id);
CREATE INDEX IF NOT EXISTS idx_assignments_user ON task_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_assignments_status ON task_assignments(status);
CREATE INDEX IF NOT EXISTS idx_task_progress_assignment ON task_progress(assignment_id);

-- ============================================================
-- H. 学生端：思考记录 / AI学习会话 / 概念理解
-- ============================================================

CREATE TABLE IF NOT EXISTS student_thoughts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    session_id      TEXT DEFAULT '',
    task_id         INTEGER DEFAULT 0,
    -- 思考内容
    thought_type    TEXT DEFAULT 'question',  -- question/idea/hint/conclusion
    question        TEXT DEFAULT '',          -- 学生的问题（引导性问题）
    idea            TEXT DEFAULT '',          -- 学生的想法/假设
    conclusion      TEXT DEFAULT '',          -- 学生的结论
    -- 上下文
    related_knowledge TEXT DEFAULT '',        -- 关联知识点
    related_question TEXT DEFAULT '',         -- 关联题目
    -- AI 反馈
    ai_feedback     TEXT DEFAULT '',          -- AI 生成的反馈/提示
    ai_follow_up    TEXT DEFAULT '',          -- AI 的跟进问题
    -- 元信息
    effort_level    TEXT DEFAULT 'normal',    -- low/normal/high
    correctness_hint TEXT DEFAULT 'neutral',  -- wrong/partial/correct/neutral
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS ai_student_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    task_id         INTEGER DEFAULT 0,
    topic           TEXT DEFAULT '',
    session_type    TEXT DEFAULT 'exploration', -- exploration/practice/quiz/review
    status          TEXT DEFAULT 'active',     -- active/completed/paused/failed
    -- 学习轨迹
    total_thoughts  INTEGER DEFAULT 0,
    correct_count   INTEGER DEFAULT 0,
    wrong_count     INTEGER DEFAULT 0,
    hints_used      INTEGER DEFAULT 0,
    time_spent      REAL DEFAULT 0.0,
    -- AI 状态
    agent_model     TEXT DEFAULT '',
    agent_status    TEXT DEFAULT '',
    last_agent_response TEXT DEFAULT '',
    -- 时间戳
    started_at      REAL NOT NULL,
    ended_at        REAL,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (task_id) REFERENCES teaching_tasks(id)
);

CREATE TABLE IF NOT EXISTS concept_understanding (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    node_id         TEXT NOT NULL,
    -- 理解状态
    understanding   REAL DEFAULT 0.0,         -- 0.0-1.0 理解度
    state           TEXT DEFAULT 'unknown',   -- unknown/learning/mastered/difficult
    -- 错误模式
    error_patterns  TEXT DEFAULT '[]',        -- JSON数组: 常见错误类型
    misconception   TEXT DEFAULT '',          -- 误解描述
    -- 学习过程
    attempts        INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0,
    wrong_attempts  INTEGER DEFAULT 0,
    total_time      REAL DEFAULT 0.0,
    last_interaction REAL,
    -- AI 评估
    ai_assessment   TEXT DEFAULT '',          -- AI 对该学生理解水平的评估
    recommended_action TEXT DEFAULT '',       -- AI 推荐的教学动作
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(user_id, node_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (node_id) REFERENCES knowledge_nodes(id)
);

CREATE INDEX IF NOT EXISTS idx_thoughts_user ON student_thoughts(user_id);
CREATE INDEX IF NOT EXISTS idx_thoughts_session ON student_thoughts(session_id);
CREATE INDEX IF NOT EXISTS idx_thoughts_task ON student_thoughts(task_id);
CREATE INDEX IF NOT EXISTS idx_ai_sessions_user ON ai_student_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_sessions_task ON ai_student_sessions(task_id);
CREATE INDEX IF NOT EXISTS idx_concept_user ON concept_understanding(user_id);
CREATE INDEX IF NOT EXISTS idx_concept_node ON concept_understanding(node_id);

-- ============================================================
-- I. 学习成果检测系统
-- ============================================================

CREATE TABLE IF NOT EXISTS learning_workflows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    workflow_id     TEXT NOT NULL,            -- 工作流标识（如 'pythagorean_master'）
    workflow_name   TEXT DEFAULT '',          -- 工作流名称
    current_step    INTEGER DEFAULT 0,        -- 当前步骤序号
    total_steps     INTEGER DEFAULT 0,        -- 总步骤数
    status          TEXT DEFAULT 'active',    -- active/completed/paused
    started_at      REAL NOT NULL,            -- 开始时间戳
    completed_at    REAL,                     -- 完成时间戳
    duration_total  REAL DEFAULT 0.0,         -- 总用时（秒）
    score_earned    REAL DEFAULT 0.0,         -- 已获得分数
    score_max       REAL DEFAULT 100.0,       -- 满分
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_workflows_user ON learning_workflows(user_id);
CREATE INDEX IF NOT EXISTS idx_workflows_status ON learning_workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_workflow ON learning_workflows(workflow_id);

CREATE TABLE IF NOT EXISTS output_detections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    workflow_id     TEXT DEFAULT '',          -- 关联工作流
    detection_type  TEXT DEFAULT 'quiz',      -- quiz/essay/project/peer_review
    prompt          TEXT DEFAULT '',          -- 检测题目/提示
    user_output     TEXT DEFAULT '',          -- 用户输出
    score           REAL DEFAULT 0.0,         -- 检测得分
    feedback        TEXT DEFAULT '',          -- 检测反馈
    guiding_records TEXT DEFAULT '[]',        -- JSON: 引导记录数组
    reinforced      INTEGER DEFAULT 0,        -- 是否已强化
    detected_at     TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_detections_user ON output_detections(user_id);
CREATE INDEX IF NOT EXISTS idx_detections_workflow ON output_detections(workflow_id);
CREATE INDEX IF NOT EXISTS idx_detections_type ON output_detections(detection_type);

-- ============================================================
-- K. 管理员与 Agent 管理系统
-- ============================================================

CREATE TABLE IF NOT EXISTS admins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name  TEXT DEFAULT '',
    role          TEXT DEFAULT 'super_admin',  -- super_admin / operator
    is_active     INTEGER DEFAULT 1,
    last_login_at TEXT,
    created_at    TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);

CREATE TABLE IF NOT EXISTS agents (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id       TEXT UNIQUE NOT NULL,
    name           TEXT NOT NULL,
    agent_type     TEXT NOT NULL,             -- feynman / detector / adaptive / chat
    description    TEXT DEFAULT '',
    config         TEXT DEFAULT '{}',         -- JSON 配置
    status         TEXT DEFAULT 'stopped',    -- running / stopped / error
    last_heartbeat TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(agent_type);

CREATE TABLE IF NOT EXISTS system_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    level      TEXT DEFAULT 'info',           -- debug/info/warning/error
    module     TEXT DEFAULT '',
    message    TEXT DEFAULT '',
    detail     TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_created ON system_logs(created_at);

-- 模型推理过程记录库：供管理员检查、教师查看、模型自查使用
CREATE TABLE IF NOT EXISTS reasoning_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT 0,            -- 学生用户 id（0 表示未登录/匿名）
    session_id TEXT DEFAULT '',           -- 会话标识
    mode TEXT DEFAULT 'feynman',          -- feynman / chat / goai
    topic TEXT DEFAULT '',                -- 学习主题
    step_order INTEGER DEFAULT 0,         -- 费曼步骤序号 1-5（非费曼为 0）
    step_name TEXT DEFAULT '',            -- 费曼步骤名
    model_used TEXT DEFAULT '',           -- 使用的模型
    prompt TEXT DEFAULT '',               -- 输入 prompt（完整）
    input_context TEXT DEFAULT '',        -- 前序对话摘要
    output TEXT DEFAULT '',               -- 模型输出
    latency_ms INTEGER DEFAULT 0,         -- 推理耗时毫秒
    status TEXT DEFAULT 'success',        -- success / error
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_reasoning_user ON reasoning_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_session ON reasoning_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_topic ON reasoning_logs(topic);
CREATE INDEX IF NOT EXISTS idx_reasoning_created ON reasoning_logs(created_at);

CREATE TABLE IF NOT EXISTS api_keys (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key_name   TEXT NOT NULL,
    api_key    TEXT UNIQUE NOT NULL,
    scope      TEXT DEFAULT 'read',           -- read / write / admin
    is_active  INTEGER DEFAULT 1,
    last_used_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_api_keys_scope ON api_keys(scope);

-- ============================================================
-- L. 组织架构（学校库/年级库/班级库/学生绑定）
-- ============================================================

CREATE TABLE IF NOT EXISTS schools (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS grades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id   INTEGER NOT NULL,
    name        TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(school_id, name),
    FOREIGN KEY (school_id) REFERENCES schools(id)
);

CREATE TABLE IF NOT EXISTS classes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    grade_id    INTEGER NOT NULL,
    name        TEXT NOT NULL,
    teacher_id  INTEGER DEFAULT 0,          -- 班主任 user_id
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(grade_id, name),
    FOREIGN KEY (grade_id) REFERENCES grades(id)
);

CREATE TABLE IF NOT EXISTS class_students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(class_id, user_id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_grades_school ON grades(school_id);
CREATE INDEX IF NOT EXISTS idx_classes_grade ON classes(grade_id);
CREATE INDEX IF NOT EXISTS idx_classes_teacher ON classes(teacher_id);
CREATE INDEX IF NOT EXISTS idx_class_students_class ON class_students(class_id);
CREATE INDEX IF NOT EXISTS idx_class_students_user ON class_students(user_id);
"""


# ============================================================
# 预置学科数据
# ============================================================

_DEFAULT_SUBJECTS = [
    "数学", "英语", "语文", "物理", "化学", "生物",
    "历史", "地理", "政治", "信息技术", "编程", "AI基础",
]

# 预置知识图谱（来自 adaptive_learning.py 的 KNOWLEDGE_GRAPH）
_DEFAULT_KNOWLEDGE_NODES = [
    ("triangle_basics", "三角形基础", "geometry", 1, "geometry", "三角形的定义、分类、内角和", "[]"),
    ("pythagorean", "勾股定理", "geometry", 2, "geometry", "直角三角形的边长关系", '["triangle_basics"]'),
    ("circle_area", "圆面积", "geometry", 2, "geometry", "圆的面积公式推导", '["triangle_basics"]'),
    ("cosine_rule", "余弦定理", "geometry", 3, "geometry", "任意三角形的边长与角度关系", '["pythagorean"]'),
    ("quadratic_formula", "求根公式", "algebra", 2, "formula", "一元二次方程的求根公式推导", "[]"),
    ("completing_square", "配方法", "algebra", 2, "formula", "通过配方解二次方程", '["quadratic_formula"]'),
    ("polynomial", "多项式运算", "algebra", 3, "formula", "多项式的加减乘除和因式分解", '["quadratic_formula"]'),
    ("linear_function", "一次函数", "functions", 1, "functions", "y=kx+b 的图像与性质", "[]"),
    ("quadratic_function", "二次函数", "functions", 2, "functions", "y=ax²+bx+c 的图像与性质", '["linear_function","quadratic_formula"]'),
    ("free_fall", "自由落体", "physics", 2, "physics", "匀加速直线运动", '["quadratic_function"]'),
    ("light_refraction", "光的折射", "physics", 3, "physics", "斯涅尔定律与折射现象", '["triangle_basics"]'),
    ("mean_median", "均值与中位数", "statistics", 1, "statistics", "描述性统计基础", "[]"),
    ("normal_distribution", "正态分布", "statistics", 3, "statistics", "正态分布的性质与应用", '["mean_median"]'),
]


# ============================================================
# 数据库管理器
# ============================================================

class DatabaseManager:
    """
    LumiLearn 数据库管理器

    单例模式，全局共享一个连接。
    首次调用 init() 时自动建库建表并填充默认数据。

    用法：
        from framework.database import db
        db.init()  # 初始化（仅需一次）
        db.add_user("小明")
    """

    def __init__(self):
        self._db_path: Optional[str] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._initialized = False
        # 多线程安全：Flask threaded=True 下多个请求线程共享同一连接
        self._lock = threading.RLock()

    # ============================================================
    # 连接与初始化
    # ============================================================

    @property
    def db_path(self) -> str:
        if self._db_path is None:
            self._db_path = _get_db_path()
        return self._db_path

    @property
    def conn(self) -> sqlite3.Connection:
        """获取数据库连接（懒初始化）"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row  # 返回字典式行
            self._conn.execute("PRAGMA journal_mode=WAL")  # 并发读不阻塞
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def init(self, db_path: Optional[str] = None) -> str:
        """
        初始化数据库（建库 + 建表 + 填充默认数据）

        参数：
            db_path: 自定义数据库路径（覆盖环境变量）

        返回：
            数据库文件路径

        用法：
            db.init()                           # 使用默认/环境变量路径
            db.init("/custom/path/lumilearn.db") # 自定义路径
        """
        if db_path:
            self._db_path = db_path
            # 关闭旧连接，重新连接新路径
            if self._conn:
                self._conn.close()
                self._conn = None

        # 确保目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        # 执行建表
        self.conn.executescript(_SCHEMA)
        # 迁移：为已存在的 users 表补充 username/password_hash 列
        self._migrate_users_columns()
        self.conn.commit()

        # 填充默认数据（仅首次）
        self._seed_defaults()

        self._initialized = True
        return self.db_path

    def _migrate_users_columns(self):
        """迁移：老库 users 表缺少 username/password_hash 列时补充"""
        try:
            cols = [r["name"] for r in self._query("PRAGMA table_info(users)")]
            if "username" not in cols:
                self.conn.execute("ALTER TABLE users ADD COLUMN username TEXT DEFAULT ''")
            if "password_hash" not in cols:
                self.conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")
            # 老库可能缺 learning_reports 表（CREATE TABLE IF NOT EXISTS 已兜底）
        except Exception as e:
            logger = __import__("logging").getLogger("lumilearn.database")
            logger.warning(f"迁移 users 表列失败（可忽略）: {e}")

    def _seed_defaults(self):
        """填充默认数据（学科、知识图谱），仅首次执行"""
        # 检查是否已有数据
        count = self.conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        if count == 0:
            for name in _DEFAULT_SUBJECTS:
                self.conn.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
            self.conn.commit()

        count = self.conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        if count == 0:
            for node in _DEFAULT_KNOWLEDGE_NODES:
                self.conn.execute(
                    "INSERT OR IGNORE INTO knowledge_nodes "
                    "(id, name, category, difficulty, animation_type, description, prereqs) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    node
                )
            self.conn.commit()

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行单条SQL并返回cursor"""
        with self._lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def _query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """查询并返回字典列表"""
        with self._lock:
            cur = self.conn.execute(sql, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def _query_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        """查询单条记录"""
        rows = self._query(sql, params)
        return rows[0] if rows else None

    # ============================================================
    # A. 用户管理
    # ============================================================

    def add_user(self, name: str, role: str = "student", avatar: str = "",
                 username: str = "", password: str = "") -> Dict:
        """
        添加用户

        参数：
            name:  用户名
            role:  角色（teacher / student）
            avatar: 头像标识
            username: 登录用户名（GOAI Web 登录用）
            password: 登录密码明文（自动哈希存储）

        返回：
            新用户信息字典
        """
        from werkzeug.security import generate_password_hash
        # 未指定 username 时默认使用 name
        login_name = username or name
        password_hash = generate_password_hash(password) if password else ""
        cur = self._execute(
            "INSERT INTO users (name, role, avatar, username, password_hash) VALUES (?, ?, ?, ?, ?)",
            (name, role, avatar, login_name, password_hash)
        )
        return {"id": cur.lastrowid, "name": name, "role": role,
                "username": login_name, "has_password": bool(password)}

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """按登录用户名查找用户（username 或 name 均可匹配）"""
        return self._query_one(
            "SELECT * FROM users WHERE username = ? OR name = ?",
            (username, username)
        )

    def verify_user_login(self, username: str, password: str) -> Optional[Dict]:
        """
        校验用户登录

        参数：
            username: 用户名
            password: 密码明文

        返回：
            用户信息字典；失败返回 None
        """
        from werkzeug.security import check_password_hash
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not user.get("password_hash"):
            return None
        if check_password_hash(user["password_hash"], password):
            return user
        return None

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """重置用户密码"""
        from werkzeug.security import generate_password_hash
        cur = self._execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user_id)
        )
        return cur.rowcount > 0

    def get_user(self, user_id: int) -> Optional[Dict]:
        """获取用户信息"""
        return self._query_one("SELECT * FROM users WHERE id = ?", (user_id,))

    def get_users(self, role: Optional[str] = None) -> List[Dict]:
        """
        获取用户列表

        参数：
            role: 筛选角色（teacher / student / None=全部）
        """
        if role:
            return self._query("SELECT * FROM users WHERE role = ? ORDER BY name", (role,))
        return self._query("SELECT * FROM users ORDER BY name")

    def delete_user(self, user_id: int) -> bool:
        """删除用户（同时删除其学习记录）"""
        self._execute("DELETE FROM answers WHERE user_id = ?", (user_id,))
        self._execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        self._execute("DELETE FROM daily_stats WHERE user_id = ?", (user_id,))
        self._execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
        self._execute("DELETE FROM learning_reports WHERE user_id = ?", (user_id,))
        cur = self._execute("DELETE FROM users WHERE id = ?", (user_id,))
        return cur.rowcount > 0

    # ============================================================
    # C0. 学习报告（GOAI Web 生成）
    # ============================================================

    def add_learning_report(self, user_id: int, topic: str,
                            report: Dict, score: float = 0.0) -> Dict:
        """保存一份 GOAI 学习报告"""
        cur = self._execute(
            "INSERT INTO learning_reports (user_id, topic, report_json, score) VALUES (?, ?, ?, ?)",
            (user_id, topic, json.dumps(report, ensure_ascii=False), score)
        )
        return {"id": cur.lastrowid, "user_id": user_id, "topic": topic}

    def get_learning_reports(self, user_id: int = None, limit: int = 50) -> List[Dict]:
        """获取学习报告列表（可按用户筛选）"""
        if user_id:
            rows = self._query(
                "SELECT * FROM learning_reports WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            )
        else:
            rows = self._query(
                "SELECT * FROM learning_reports ORDER BY id DESC LIMIT ?",
                (limit,)
            )
        for r in rows:
            try:
                r["report"] = json.loads(r.get("report_json", "{}"))
            except Exception:
                r["report"] = {}
            r.pop("report_json", None)
        return rows

    def get_learning_report(self, report_id: int) -> Optional[Dict]:
        """获取单份学习报告"""
        r = self._query_one(
            "SELECT * FROM learning_reports WHERE id = ?", (report_id,)
        )
        if r:
            try:
                r["report"] = json.loads(r.get("report_json", "{}"))
            except Exception:
                r["report"] = {}
            r.pop("report_json", None)
        return r

    # ============================================================
    # B1. 知识图谱管理
    # ============================================================

    def add_knowledge_node(
        self, node_id: str, name: str, category: str,
        difficulty: int = 1, animation_type: str = "auto",
        description: str = "", prereqs: List[str] = None
    ) -> Dict:
        """
        添加知识图谱节点

        参数：
            node_id:       唯一标识（如 'pythagorean'）
            name:          显示名称
            category:      分类（geometry/algebra/physics/functions/statistics）
            difficulty:    难度 1-5
            animation_type: 动画类型
            description:   描述
            prereqs:       前置知识点ID列表
        """
        if prereqs is None:
            prereqs = []
        self._execute(
            "INSERT OR REPLACE INTO knowledge_nodes "
            "(id, name, category, difficulty, animation_type, description, prereqs) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node_id, name, category, difficulty, animation_type, description, json.dumps(prereqs))
        )
        return {"id": node_id, "name": name}

    def get_knowledge_nodes(self, category: Optional[str] = None) -> List[Dict]:
        """
        获取知识图谱节点列表

        参数：
            category: 按分类筛选（可选）
        """
        if category:
            nodes = self._query(
                "SELECT * FROM knowledge_nodes WHERE category = ? ORDER BY difficulty",
                (category,)
            )
        else:
            nodes = self._query("SELECT * FROM knowledge_nodes ORDER BY category, difficulty")
        # 解析 prereqs JSON
        for n in nodes:
            n["prereqs"] = json.loads(n.get("prereqs", "[]"))
        return nodes

    def get_knowledge_node(self, node_id: str) -> Optional[Dict]:
        """获取单个知识点详情"""
        node = self._query_one("SELECT * FROM knowledge_nodes WHERE id = ?", (node_id,))
        if node:
            node["prereqs"] = json.loads(node.get("prereqs", "[]"))
        return node

    # ============================================================
    # B2. 教学内容管理（训练数据）
    # ============================================================

    def add_training_data(
        self,
        subject: str,
        chapter: str,
        title: str,
        content: str,
        grade: str = "高中",
        content_type: str = "概念定义",
        difficulty: str = "基础",
        keywords: str = "",
        prerequisites: str = "",
        learning_objectives: str = "",
        common_mistakes: str = "",
        source: str = "manual",
        source_type: str = "manual",
        status: str = "draft",
    ) -> Dict:
        """
        添加一条教学内容（训练数据）

        教师本地录入教学内容的主要接口。

        参数：
            subject:       学科（数学/物理/化学...）
            chapter:       章节
            title:         标题
            content:       正文内容
            grade:         年级（初一~大学/通用）
            content_type:  内容类型（概念定义/公式推导/例题解析/练习题/知识总结/实验说明/学科历史/解题方法）
            difficulty:    难度（入门/基础/中等/困难/专家）
            keywords:      关键词（逗号分隔）
            prerequisites: 前置知识
            learning_objectives: 学习目标
            common_mistakes: 常见错误
            source:        来源标识
            source_type:   来源类型
            status:        状态（draft/reviewed/published）

        返回：
            新记录信息（含 id）
        """
        word_count = len(content)
        cur = self._execute(
            """INSERT INTO training_data
            (subject, chapter, title, content, grade, content_type, difficulty,
             keywords, prerequisites, learning_objectives, common_mistakes,
             source, source_type, word_count, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (subject, chapter, title, content, grade, content_type, difficulty,
             keywords, prerequisites, learning_objectives, common_mistakes,
             source, source_type, word_count, status)
        )
        return {"id": cur.lastrowid, "title": title, "subject": subject}

    def get_training_data(
        self,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        status: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """
        查询教学内容列表

        所有参数可选，组合筛选。

        参数：
            subject:    按学科筛选
            chapter:    按章节筛选（模糊匹配）
            status:     按状态筛选（draft/reviewed/published）
            difficulty: 按难度筛选
            limit:      返回条数上限
            offset:     分页偏移
        """
        sql = "SELECT * FROM training_data WHERE 1=1"
        params = []
        if subject:
            sql += " AND subject = ?"
            params.append(subject)
        if chapter:
            sql += " AND chapter LIKE ?"
            params.append(f"%{chapter}%")
        if status:
            sql += " AND status = ?"
            params.append(status)
        if difficulty:
            sql += " AND difficulty = ?"
            params.append(difficulty)
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return self._query(sql, tuple(params))

    def get_training_record(self, record_id: int) -> Optional[Dict]:
        """获取单条教学内容"""
        return self._query_one("SELECT * FROM training_data WHERE id = ?", (record_id,))

    def update_training_data(self, record_id: int, **fields) -> bool:
        """
        更新教学内容

        用法：
            db.update_training_data(5, status="published", difficulty="中等")
        """
        if not fields:
            return False
        # 白名单允许更新的字段
        allowed = {
            "subject", "chapter", "title", "content", "grade",
            "content_type", "difficulty", "keywords", "prerequisites",
            "learning_objectives", "common_mistakes", "source", "source_type",
            "quality_score", "status", "version",
        }
        updates = []
        params = []
        for k, v in fields.items():
            if k in allowed:
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return False
        # 自动更新 word_count 和 updated_at
        if "content" in fields:
            updates.append("word_count = ?")
            params.append(len(fields["content"]))
        updates.append("updated_at = datetime('now','localtime')")
        params.append(record_id)
        cur = self._execute(
            f"UPDATE training_data SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        return cur.rowcount > 0

    def delete_training_data(self, record_id: int) -> bool:
        """删除教学内容"""
        cur = self._execute("DELETE FROM training_data WHERE id = ?", (record_id,))
        return cur.rowcount > 0

    def count_training_data(self, subject: Optional[str] = None) -> int:
        """统计教学内容数量"""
        if subject:
            return self._query_one(
                "SELECT COUNT(*) as n FROM training_data WHERE subject = ?", (subject,)
            )["n"]
        return self._query_one("SELECT COUNT(*) as n FROM training_data")["n"]

    # ============================================================
    # B3. 题目库管理
    # ============================================================

    def add_question(
        self,
        subject: str,
        question: str,
        correct_answer: str,
        topic: str = "",
        knowledge_id: str = "",
        explanation: str = "",
        difficulty: int = 2,
        question_type: str = "short",
        options: Optional[List[str]] = None,
        created_by: int = 1,
    ) -> Dict:
        """
        添加题目

        参数：
            subject:        学科
            question:       题目内容
            correct_answer:  正确答案
            topic:          主题（如"乘法"、"方程"）
            knowledge_id:   关联知识点ID
            explanation:    解析说明
            difficulty:     难度 1基础/2进阶/3挑战
            question_type:  题型 short短答/multiple选择/essay论述
            options:        选择题选项列表（仅 multiple 类型）
            created_by:     录入教师 user_id
        """
        options_json = json.dumps(options, ensure_ascii=False) if options else ""
        cur = self._execute(
            """INSERT INTO questions
            (knowledge_id, subject, topic, question, correct_answer, explanation,
             difficulty, question_type, options, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (knowledge_id, subject, topic, question, correct_answer, explanation,
             difficulty, question_type, options_json, created_by)
        )
        return {"id": cur.lastrowid, "question": question}

    def get_questions(
        self,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        knowledge_id: Optional[str] = None,
        difficulty: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        查询题目列表

        所有参数可选，组合筛选。
        """
        sql = "SELECT * FROM questions WHERE 1=1"
        params = []
        if subject:
            sql += " AND subject = ?"
            params.append(subject)
        if topic:
            sql += " AND topic LIKE ?"
            params.append(f"%{topic}%")
        if knowledge_id:
            sql += " AND knowledge_id = ?"
            params.append(knowledge_id)
        if difficulty:
            sql += " AND difficulty = ?"
            params.append(difficulty)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        results = self._query(sql, tuple(params))
        for q in results:
            q["options"] = json.loads(q["options"]) if q.get("options") else []
        return results

    def delete_question(self, question_id: int) -> bool:
        """删除题目"""
        cur = self._execute("DELETE FROM questions WHERE id = ?", (question_id,))
        return cur.rowcount > 0

    # ============================================================
    # C1. 学习会话管理
    # ============================================================

    def start_session(self, user_id: int, subject: str = "") -> str:
        """
        开始一次学习会话

        返回：
            会话ID字符串（如 'session_1718000000'）
        """
        session_id = f"session_{int(time.time())}"
        self._execute(
            "INSERT INTO sessions (id, user_id, subject, start_time) VALUES (?, ?, ?, ?)",
            (session_id, user_id, subject, time.time())
        )
        return session_id

    def end_session(
        self,
        session_id: str,
        questions_answered: int = 0,
        correct_count: int = 0,
        focus_score: float = 0.0,
    ) -> Optional[Dict]:
        """
        结束学习会话

        返回：
            会话摘要信息
        """
        session = self._query_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if not session:
            return None

        end_time = time.time()
        duration = (end_time - session["start_time"]) / 60  # 分钟

        self._execute(
            """UPDATE sessions SET
            end_time = ?, questions_answered = ?, correct_count = ?,
            focus_score = ?, duration_minutes = ?
            WHERE id = ?""",
            (end_time, questions_answered, correct_count, focus_score, duration, session_id)
        )

        # 更新每日统计
        date_str = time.strftime("%Y-%m-%d", time.localtime(session["start_time"]))
        total_time = end_time - session["start_time"]
        self._upsert_daily_stats(
            user_id=session["user_id"],
            date=date_str,
            add_time=total_time,
            add_questions=questions_answered,
            add_correct=correct_count,
            focus_score=focus_score,
        )

        return {
            "session_id": session_id,
            "duration_minutes": round(duration, 1),
            "questions_answered": questions_answered,
            "correct_count": correct_count,
            "focus_score": round(focus_score, 2),
        }

    def get_sessions(
        self, user_id: int, subject: Optional[str] = None, limit: int = 20
    ) -> List[Dict]:
        """获取用户的学习会话列表"""
        sql = "SELECT * FROM sessions WHERE user_id = ?"
        params = [user_id]
        if subject:
            sql += " AND subject = ?"
            params.append(subject)
        sql += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        return self._query(sql, tuple(params))

    # ============================================================
    # C2. 答题记录管理
    # ============================================================

    def record_answer(
        self,
        question: str,
        user_answer: str,
        correct_answer: str = "",
        topic: str = "",
        subject: str = "",
        user_id: int = 1,
        session_id: str = "",
        hints_used: int = 0,
        time_spent: float = 0.0,
        gave_up: bool = False,
    ) -> Dict:
        """
        记录一次答题

        核心学习记录接口。自动判断对错。

        参数：
            question:       题目内容
            user_answer:    用户答案
            correct_answer: 正确答案
            topic:          主题
            subject:        学科
            user_id:        用户ID
            session_id:     关联会话ID
            hints_used:     使用提示次数
            time_spent:     答题时长（秒）
            gave_up:        是否放弃

        返回：
            {"is_correct": bool, "answer_id": int, "hint": str}
        """
        # 判断对错
        is_correct = 0
        if correct_answer:
            user_clean = user_answer.strip().lower().replace(" ", "")
            correct_clean = correct_answer.strip().lower().replace(" ", "")
            is_correct = 1 if user_clean == correct_clean else 0

        cur = self._execute(
            """INSERT INTO answers
            (session_id, user_id, question, user_answer, correct_answer,
             is_correct, topic, subject, hints_used, time_spent, gave_up, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, question, user_answer, correct_answer,
             is_correct, topic, subject, hints_used, time_spent, 1 if gave_up else 0, time.time())
        )

        # 如果关联了会话，更新会话统计
        if session_id:
            self._execute(
                """UPDATE sessions SET
                questions_answered = questions_answered + 1,
                correct_count = correct_count + ?
                WHERE id = ?""",
                (is_correct, session_id)
            )

        hint = self._generate_hint(topic, is_correct)
        return {"is_correct": bool(is_correct), "answer_id": cur.lastrowid, "hint": hint}

    def get_mistakes(
        self,
        user_id: int,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        获取错题记录

        参数：
            user_id: 用户ID
            subject: 按学科筛选（可选）
            topic:   按主题筛选（可选）
            limit:   返回条数
        """
        sql = "SELECT * FROM answers WHERE user_id = ? AND is_correct = 0"
        params = [user_id]
        if subject:
            sql += " AND subject = ?"
            params.append(subject)
        if topic:
            sql += " AND topic LIKE ?"
            params.append(f"%{topic}%")
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        return self._query(sql, tuple(params))

    def get_answer_history(
        self, user_id: int, limit: int = 100
    ) -> List[Dict]:
        """获取用户答题历史（含对错）"""
        return self._query(
            "SELECT * FROM answers WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )

    def get_weak_topics(
        self, user_id: int, min_errors: int = 2
    ) -> List[Dict]:
        """
        分析薄弱知识点

        返回按错误率排序的薄弱主题列表
        """
        rows = self._query(
            """SELECT topic,
            COUNT(*) as total,
            SUM(is_correct) as correct,
            SUM(1 - is_correct) as wrong
            FROM answers WHERE user_id = ? AND topic != ''
            GROUP BY topic
            HAVING wrong >= ?
            ORDER BY (wrong * 1.0 / COUNT(*)) DESC""",
            (user_id, min_errors)
        )
        for r in rows:
            r["error_rate"] = round(r["wrong"] / max(r["total"], 1), 2)
        return rows

    def _generate_hint(self, topic: str, is_correct: bool) -> str:
        """根据答题结果生成提示"""
        if is_correct:
            return "回答正确！你是怎么想到的？"
        topic_lower = (topic or "").lower()
        if "面积" in topic_lower:
            return "再想想：面积公式是底×高÷2，你有没有用到这个公式？"
        if any(k in topic_lower for k in ["乘法", "乘", "×"]):
            return "提示：可以用乘法口诀或者分解计算"
        if any(k in topic_lower for k in ["除法", "除", "÷"]):
            return "检查一下：被除数÷除数=商，位置有没有弄混？"
        if "方程" in topic_lower:
            return "回忆一下：移项的时候要变号哦！"
        if "分数" in topic_lower:
            return "分数计算的关键：分母相同才能加减，不同要先通分！"
        return "差一点！再仔细想想推理过程"

    # ============================================================
    # C3. 每日统计
    # ============================================================

    def _upsert_daily_stats(
        self,
        user_id: int,
        date: str,
        add_time: float = 0,
        add_questions: int = 0,
        add_correct: int = 0,
        focus_score: float = 0.0,
    ):
        """更新或创建每日统计（内部方法）"""
        existing = self._query_one(
            "SELECT * FROM daily_stats WHERE user_id = ? AND date = ?",
            (user_id, date)
        )
        if existing:
            max_focus = max(existing["max_focus_score"], focus_score)
            self._execute(
                """UPDATE daily_stats SET
                total_time = total_time + ?,
                questions_answered = questions_answered + ?,
                correct_count = correct_count + ?,
                max_focus_score = ?
                WHERE user_id = ? AND date = ?""",
                (add_time, add_questions, add_correct, max_focus, user_id, date)
            )
        else:
            self._execute(
                """INSERT INTO daily_stats
                (user_id, date, total_time, questions_answered, correct_count, max_focus_score)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, date, add_time, add_questions, add_correct, focus_score)
            )

    def get_daily_stats(
        self, user_id: int, days: int = 30
    ) -> List[Dict]:
        """
        获取最近 N 天的每日统计

        参数：
            user_id: 用户ID
            days:    天数
        """
        return self._query(
            """SELECT * FROM daily_stats
            WHERE user_id = ?
            AND date >= date('now','localtime', ?)
            ORDER BY date DESC""",
            (user_id, f"-{days} days")
        )

    # ============================================================
    # C4. 学习进度（知识图谱掌握度）
    # ============================================================

    def record_progress(
        self,
        user_id: int,
        node_id: str,
        score: float = 1.0,
        time_spent: float = 0,
    ):
        """
        记录知识点学习进度

        使用指数移动平均更新掌握度：
        mastery = mastery * 0.7 + score * 0.3

        参数：
            user_id:    用户ID
            node_id:    知识点ID
            score:      本次学习得分 (0-1)
            time_spent: 学习时长（秒）
        """
        existing = self._query_one(
            "SELECT * FROM progress WHERE user_id = ? AND node_id = ?",
            (user_id, node_id)
        )
        if existing:
            alpha = 0.3
            new_mastery = existing["mastery"] * (1 - alpha) + score * alpha
            self._execute(
                """UPDATE progress SET
                mastery = ?, attempts = attempts + 1,
                total_time = total_time + ?, last_study = ?
                WHERE user_id = ? AND node_id = ?""",
                (new_mastery, time_spent, time.time(), user_id, node_id)
            )
        else:
            self._execute(
                """INSERT INTO progress
                (user_id, node_id, mastery, attempts, total_time, last_study)
                VALUES (?, ?, ?, 1, ?, ?)""",
                (user_id, node_id, score * 0.3, time_spent, time.time())
            )

    def get_progress(self, user_id: int = 1) -> Dict:
        """
        获取用户学习进度总览

        返回：
            {
                "total_nodes": 13,
                "studied": 5,
                "mastered": 2,
                "overall_progress": 15.4,
                "nodes": [...]
            }
        """
        total_nodes = self._query_one("SELECT COUNT(*) as n FROM knowledge_nodes")["n"]
        progress_rows = self._query(
            """SELECT p.*, k.name, k.category, k.difficulty
            FROM progress p
            JOIN knowledge_nodes k ON p.node_id = k.id
            WHERE p.user_id = ?""",
            (user_id,)
        )
        mastered = sum(1 for p in progress_rows if p["mastery"] >= 0.8)
        learning = sum(1 for p in progress_rows if 0.3 <= p["mastery"] < 0.8)
        return {
            "user_id": user_id,
            "total_nodes": total_nodes,
            "studied": len(progress_rows),
            "mastered": mastered,
            "learning": learning,
            "not_started": total_nodes - len(progress_rows),
            "overall_progress": round(mastered / max(total_nodes, 1) * 100, 1),
            "nodes": progress_rows,
        }

    # ============================================================
    # C5. 综合统计查询
    # ============================================================

    def get_stats(self, user_id: int = 1) -> Dict:
        """
        获取用户全局学习统计

        返回：
            {
                "total_answers": 100,
                "correct": 75,
                "wrong": 25,
                "accuracy": 75.0,
                "total_time_minutes": 120.5,
                "total_sessions": 8
            }
        """
        answer_stats = self._query_one(
            """SELECT
            COUNT(*) as total,
            SUM(is_correct) as correct,
            SUM(1 - is_correct) as wrong
            FROM answers WHERE user_id = ?""",
            (user_id,)
        )
        session_stats = self._query_one(
            "SELECT COUNT(*) as n, COALESCE(SUM(duration_minutes), 0) as total_time FROM sessions WHERE user_id = ?",
            (user_id,)
        )
        total = answer_stats["total"] or 0
        correct = answer_stats["correct"] or 0
        return {
            "total_answers": total,
            "correct": correct,
            "wrong": answer_stats["wrong"] or 0,
            "accuracy": round(correct / max(total, 1) * 100, 1),
            "total_time_minutes": round(session_stats["total_time"] or 0, 1),
            "total_sessions": session_stats["n"] or 0,
        }

    # ============================================================
    # D1. 训练实验管理
    # ============================================================

    def add_experiment(
        self,
        name: str,
        preset: str = "",
        config_json: str = "",
        output_dir: str = "",
    ) -> Dict:
        """
        记录一次训练实验

        参数：
            name:        实验名称
            preset:      预设名称（如 airllm_smoke）
            config_json: 完整配置JSON
            output_dir:  输出目录路径
        """
        cur = self._execute(
            "INSERT INTO experiments (name, preset, config_json, output_dir) VALUES (?, ?, ?, ?)",
            (name, preset, config_json, output_dir)
        )
        return {"id": cur.lastrowid, "name": name}

    def finish_experiment(
        self,
        experiment_id: int,
        best_val_loss: Optional[float] = None,
        total_steps: int = 0,
        status: str = "completed",
    ) -> bool:
        """标记实验完成"""
        cur = self._execute(
            """UPDATE experiments SET
            status = ?, best_val_loss = ?, total_steps = ?,
            finished_at = datetime('now','localtime')
            WHERE id = ?""",
            (status, best_val_loss, total_steps, experiment_id)
        )
        return cur.rowcount > 0

    def get_experiments(self, limit: int = 20) -> List[Dict]:
        """获取实验列表"""
        return self._query(
            "SELECT * FROM experiments ORDER BY started_at DESC LIMIT ?",
            (limit,)
        )

    def get_experiment(self, experiment_id: int) -> Optional[Dict]:
        """获取实验详情"""
        return self._query_one("SELECT * FROM experiments WHERE id = ?", (experiment_id,))

    # ============================================================
    # D2. 检查点管理
    # ============================================================

    def add_checkpoint(
        self,
        experiment_id: int,
        step: int,
        tag: str = "",
        file_path: str = "",
        train_loss: Optional[float] = None,
        val_loss: Optional[float] = None,
        learning_rate: Optional[float] = None,
        grad_norm: Optional[float] = None,
        file_size_mb: Optional[float] = None,
    ) -> Dict:
        """
        记录模型检查点

        参数：
            experiment_id: 关联实验ID
            step:          训练步数
            tag:           标签（best/final/step_N）
            file_path:     .pt文件路径
            train_loss:    训练损失
            val_loss:      验证损失
            learning_rate: 学习率
            grad_norm:     梯度范数
            file_size_mb:  文件大小（MB）
        """
        cur = self._execute(
            """INSERT INTO checkpoints
            (experiment_id, step, tag, train_loss, val_loss,
             learning_rate, grad_norm, file_path, file_size_mb)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (experiment_id, step, tag, train_loss, val_loss,
             learning_rate, grad_norm, file_path, file_size_mb)
        )
        return {"id": cur.lastrowid, "experiment_id": experiment_id, "step": step}

    def get_checkpoints(self, experiment_id: int) -> List[Dict]:
        """获取实验的所有检查点"""
        return self._query(
            "SELECT * FROM checkpoints WHERE experiment_id = ? ORDER BY step",
            (experiment_id,)
        )

    def get_best_checkpoint(self, experiment_id: int) -> Optional[Dict]:
        """获取实验的最佳检查点"""
        return self._query_one(
            "SELECT * FROM checkpoints WHERE experiment_id = ? AND tag = 'best'",
            (experiment_id,)
        )

    # ============================================================
    # D3. 训练指标管理
    # ============================================================

    def log_metric(
        self,
        experiment_id: int,
        step: int,
        train_loss: Optional[float] = None,
        val_loss: Optional[float] = None,
        learning_rate: Optional[float] = None,
        grad_norm: Optional[float] = None,
        step_time: Optional[float] = None,
    ):
        """
        记录一条训练指标（每步调用）

        用法：
            for step in range(max_steps):
                loss = train(...)
                db.log_metric(exp_id, step, train_loss=loss, learning_rate=lr)
        """
        self._execute(
            """INSERT INTO training_metrics
            (experiment_id, step, train_loss, val_loss, learning_rate, grad_norm, step_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (experiment_id, step, train_loss, val_loss, learning_rate, grad_norm, step_time)
        )

    def get_metrics(self, experiment_id: int) -> List[Dict]:
        """获取实验的完整训练指标"""
        return self._query(
            "SELECT * FROM training_metrics WHERE experiment_id = ? ORDER BY step",
            (experiment_id,)
        )

    def get_latest_metric(self, experiment_id: int) -> Optional[Dict]:
        """获取实验的最新指标"""
        return self._query_one(
            "SELECT * FROM training_metrics WHERE experiment_id = ? ORDER BY step DESC LIMIT 1",
            (experiment_id,)
        )

    # ============================================================
    # E. 待审核录入区
    # ============================================================

    def submit_content(
        self,
        subject: str,
        chapter: str,
        title: str,
        content: str,
        submitted_by: int = 1,
        submitted_by_name: str = "",
        difficulty: str = "基础",
        content_type: str = "概念定义",
        grade: str = "高中",
        keywords: str = "",
        source: str = "manual",
        handwriting_id: Optional[int] = None,
    ) -> Dict:
        """
        提交教学内容到待审核区

        任何来源（手动/手写/AI生成）的内容都先进待审核队列，
        教师审核通过后才发布到 training_data 正式表。
        """
        cur = self._execute(
            """INSERT INTO submissions
            (type, subject, chapter, title, content, difficulty, content_type,
             grade, keywords, source, submitted_by, submitted_by_name,
             handwriting_id, status)
            VALUES ('content', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (subject, chapter, title, content, difficulty, content_type,
             grade, keywords, source, submitted_by, submitted_by_name,
             handwriting_id)
        )
        return {"id": cur.lastrowid, "status": "pending"}

    def submit_question(
        self,
        subject: str,
        question: str,
        correct_answer: str,
        submitted_by: int = 1,
        submitted_by_name: str = "",
        topic: str = "",
        explanation: str = "",
        difficulty: str = "基础",
        source: str = "manual",
    ) -> Dict:
        """
        提交题目到待审核区

        参数：
            subject:        学科
            question:       题目内容
            correct_answer: 正确答案
            submitted_by:   提交者 user_id
            submitted_by_name: 提交者姓名
            topic:          主题
            explanation:    解析
            difficulty:     难度
            source:         来源
        """
        cur = self._execute(
            """INSERT INTO submissions
            (type, subject, question, correct_answer, explanation, topic,
             difficulty, source, submitted_by, submitted_by_name, status)
            VALUES ('question', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (subject, question, correct_answer, explanation, topic,
             difficulty, source, submitted_by, submitted_by_name)
        )
        return {"id": cur.lastrowid, "status": "pending"}

    def get_submissions(
        self,
        status: str = "pending",
        submitter_id: Optional[int] = None,
        submission_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        获取待审核提交列表

        参数：
            status:          筛选状态（pending/approved/rejected/published/all）
            submitter_id:    按提交者筛选
            submission_type: 按类型筛选（content/question/handwriting）
            limit:           返回条数
        """
        sql = "SELECT * FROM submissions WHERE 1=1"
        params = []
        if status and status != "all":
            sql += " AND status = ?"
            params.append(status)
        if submitter_id:
            sql += " AND submitted_by = ?"
            params.append(submitter_id)
        if submission_type:
            sql += " AND type = ?"
            params.append(submission_type)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return self._query(sql, tuple(params))

    def get_submission(self, submission_id: int) -> Optional[Dict]:
        """获取单条提交详情"""
        return self._query_one("SELECT * FROM submissions WHERE id = ?", (submission_id,))

    def review_submission(
        self,
        submission_id: int,
        approved: bool,
        reviewer_id: int,
        review_comment: str = "",
    ) -> Dict:
        """
        审核一条提交

        参数：
            submission_id:  提交ID
            approved:       True=通过, False=拒绝
            reviewer_id:    审核人 user_id
            review_comment: 审核意见

        返回：
            {"id": int, "status": "approved"/"rejected"}
        """
        sub = self.get_submission(submission_id)
        if not sub:
            return {"error": "提交不存在"}

        new_status = "approved" if approved else "rejected"
        self._execute(
            """UPDATE submissions SET
            status = ?, review_comment = ?, reviewed_by = ?,
            reviewed_at = datetime('now','localtime'),
            updated_at = datetime('now','localtime')
            WHERE id = ?""",
            (new_status, review_comment, reviewer_id, submission_id)
        )

        return {"id": submission_id, "status": new_status}

    def publish_submission(self, submission_id: int) -> Dict:
        """
        发布已审核通过的提交到正式表

        将 approved 的提交内容写入 training_data 或 questions 表，
        然后将提交状态改为 published。

        参数：
            submission_id: 提交ID

        返回：
            {"published": True, "target_table": "training_data"/"questions",
             "record_id": int}
        """
        sub = self.get_submission(submission_id)
        if not sub:
            return {"error": "提交不存在"}
        if sub["status"] != "approved":
            return {"error": f"当前状态为 {sub['status']}，仅 approved 状态可发布"}

        if sub["type"] == "content":
            result = self.add_training_data(
                subject=sub["subject"],
                chapter=sub["chapter"],
                title=sub["title"],
                content=sub["content"],
                grade=sub["grade"],
                content_type=sub["content_type"],
                difficulty=sub["difficulty"],
                keywords=sub["keywords"],
                source=sub["source"],
                source_type="submission",
                status="published",
            )
            target = "training_data"
        elif sub["type"] == "question":
            result = self.add_question(
                subject=sub["subject"],
                question=sub["question"],
                correct_answer=sub["correct_answer"],
                topic=sub["topic"],
                explanation=sub["explanation"],
                difficulty=int(sub["difficulty"]) if str(sub["difficulty"]).isdigit() else 2,
                created_by=sub["submitted_by"],
            )
            target = "questions"
        else:
            return {"error": f"未知提交类型: {sub['type']}"}

        self._execute(
            "UPDATE submissions SET status = 'published', "
            "updated_at = datetime('now','localtime') WHERE id = ?",
            (submission_id,)
        )

        return {
            "published": True,
            "target_table": target,
            "record_id": result.get("id"),
            "submission_id": submission_id,
        }

    def delete_submission(self, submission_id: int) -> bool:
        """删除提交"""
        cur = self._execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
        return cur.rowcount > 0

    def get_submission_stats(self) -> Dict:
        """获取待审核区统计信息"""
        rows = self._query(
            "SELECT status, COUNT(*) as n FROM submissions GROUP BY status"
        )
        stats = {r["status"]: r["n"] for r in rows}
        stats["total"] = sum(stats.values())
        return stats

    # ============================================================
    # F. 手写录入管理
    # ============================================================

    def add_handwriting(
        self,
        user_id: int,
        image_path: str = "",
        strokes: Optional[List] = None,
        ocr_text: str = "",
        ocr_confidence: float = 0.0,
        ocr_details: Optional[List] = None,
        edited_text: str = "",
        device: str = "",
        note: str = "",
    ) -> Dict:
        """
        添加一条手写录入记录

        典型流程：
          1. 用户在设备上手写 → 保存图片/笔画
          2. OCR 识别 → 得到 ocr_text
          3. 用户校对 → 填入 edited_text
          4. 提交到待审核区 → submit_content(source='handwriting')

        参数：
            user_id:        用户ID
            image_path:     手写图片文件路径
            strokes:        笔画数据（[[[{x,y},...],...],...] 每笔含点序列）
            ocr_text:       OCR 识别出的原始文本
            ocr_confidence: OCR 平均置信度 (0-1)
            ocr_details:    OCR 逐行详情列表
            edited_text:    用户修正后的文本（如果已校对）
            device:         录入设备标识
            note:           备注

        返回：
            {"id": int, "ocr_text": str}
        """
        strokes_json = json.dumps(strokes, ensure_ascii=False) if strokes else "[]"
        details_json = json.dumps(ocr_details, ensure_ascii=False) if ocr_details else "[]"

        cur = self._execute(
            """INSERT INTO handwriting_records
            (user_id, image_path, strokes_json, ocr_text, ocr_confidence,
             ocr_details, edited_text, device, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, image_path, strokes_json, ocr_text, ocr_confidence,
             details_json, edited_text, device, note)
        )
        hw_id = cur.lastrowid
        return {"id": hw_id, "ocr_text": ocr_text}

    def get_handwriting(self, handwriting_id: int) -> Optional[Dict]:
        """获取单条手写记录"""
        row = self._query_one(
            "SELECT * FROM handwriting_records WHERE id = ?",
            (handwriting_id,)
        )
        if row:
            row["strokes"] = json.loads(row.get("strokes_json", "[]"))
            row["ocr_details_parsed"] = json.loads(row.get("ocr_details", "[]"))
        return row

    def get_handwriting_list(
        self, user_id: Optional[int] = None, limit: int = 50
    ) -> List[Dict]:
        """
        获取手写记录列表

        参数：
            user_id: 按用户筛选（可选）
            limit:   返回条数
        """
        if user_id:
            rows = self._query(
                "SELECT * FROM handwriting_records WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            )
        else:
            rows = self._query(
                "SELECT * FROM handwriting_records ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        for r in rows:
            r["strokes"] = json.loads(r.get("strokes_json", "[]"))
            r["ocr_details_parsed"] = json.loads(r.get("ocr_details", "[]"))
        return rows

    def update_handwriting(self, handwriting_id: int, **fields) -> bool:
        """
        更新手写记录

        用法：
            db.update_handwriting(1, edited_text="修正后的文本", note="已校对")
        """
        allowed = {
            "image_path", "ocr_text", "ocr_confidence", "ocr_details",
            "edited_text", "device", "note", "submission_id",
        }
        updates = []
        params = []
        for k, v in fields.items():
            if k in allowed:
                if k == "ocr_details":
                    v = json.dumps(v, ensure_ascii=False)
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return False
        params.append(handwriting_id)
        cur = self._execute(
            f"UPDATE handwriting_records SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        return cur.rowcount > 0

    def delete_handwriting(self, handwriting_id: int) -> bool:
        """删除手写记录"""
        cur = self._execute(
            "DELETE FROM handwriting_records WHERE id = ?",
            (handwriting_id,)
        )
        return cur.rowcount > 0

    def submit_handwriting(
        self,
        user_id: int,
        image_path: str = "",
        strokes: Optional[List] = None,
        ocr_text: str = "",
        ocr_confidence: float = 0.0,
        ocr_details: Optional[List] = None,
        edited_text: str = "",
        device: str = "",
        note: str = "",
        subject: str = "",
        chapter: str = "",
        title: str = "",
        content: str = "",
        difficulty: str = "基础",
        content_type: str = "概念定义",
        grade: str = "高中",
        keywords: str = "",
        submitted_by_name: str = "",
    ) -> Dict:
        """
        一步到位：保存手写记录 + 提交到待审核区

        手写录入的完整流程接口，前端一键调用：
          1. 保存手写图片/笔画
          2. 记录 OCR 结果
          3. 自动提交到待审核区

        参数：
            user_id:        用户ID
            image_path:     手写图片路径
            strokes:        笔画数据
            ocr_text:       OCR识别文本
            ocr_confidence: OCR置信度
            ocr_details:    OCR详情
            edited_text:    用户修正后的文本
            device:         录入设备
            note:           备注
            subject~keywords: 提交到待审核区的内容字段
            submitted_by_name: 提交者姓名

        返回：
            {"handwriting_id": int, "submission_id": int, "status": "pending"}
        """
        # 1. 保存手写记录
        hw = self.add_handwriting(
            user_id=user_id,
            image_path=image_path,
            strokes=strokes,
            ocr_text=ocr_text,
            ocr_confidence=ocr_confidence,
            ocr_details=ocr_details,
            edited_text=edited_text,
            device=device,
            note=note,
        )
        hw_id = hw["id"]

        # 2. 提交到待审核区（优先使用 edited_text，其次 ocr_text）
        final_content = content or edited_text or ocr_text
        sub = self.submit_content(
            subject=subject,
            chapter=chapter,
            title=title or "手写录入",
            content=final_content,
            submitted_by=user_id,
            submitted_by_name=submitted_by_name,
            difficulty=difficulty,
            content_type=content_type,
            grade=grade,
            keywords=keywords,
            source="handwriting",
            handwriting_id=hw_id,
        )

        # 3. 回填手写记录的关联提交ID
        self.update_handwriting(hw_id, submission_id=sub["id"])

        return {
            "handwriting_id": hw_id,
            "submission_id": sub["id"],
            "status": "pending",
        }



    # ============================================================
    # G. 教学任务管理
    # ============================================================

    def create_task(
        self,
        title: str,
        subject: str,
        knowledge_ids: list = None,
        data_ids: list = None,
        question_ids: list = None,
        task_type: str = "learn",
        difficulty: str = "基础",
        grade: str = "高中",
        description: str = "",
        target_score: int = 60,
        time_limit: int = 30,
        source: str = "teacher",
        source_detail: str = "",
        created_by: int = 1,
    ) -> dict:
        """创建教学任务"""
        if knowledge_ids is None:
            knowledge_ids = []
        if data_ids is None:
            data_ids = []
        if question_ids is None:
            question_ids = []
        cur = self._execute(
            """INSERT INTO teaching_tasks
            (title, subject, grade, description, task_type, knowledge_ids, data_ids,
             question_ids, difficulty, target_score, time_limit, source, source_detail,
             created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, subject, grade, description, task_type,
             json.dumps(knowledge_ids), json.dumps(data_ids), json.dumps(question_ids),
             difficulty, target_score, time_limit, source, source_detail, created_by)
        )
        return {"id": cur.lastrowid, "title": title, "subject": subject}

    def get_task(self, task_id: int) -> dict:
        """获取单条任务详情"""
        task = self._query_one("SELECT * FROM teaching_tasks WHERE id = ?", (task_id,))
        if task:
            task["knowledge_ids"] = json.loads(task.get("knowledge_ids", "[]"))
            task["data_ids"] = json.loads(task.get("data_ids", "[]"))
            task["question_ids"] = json.loads(task.get("question_ids", "[]"))
        return task

    def get_tasks(self, subject=None, status=None, task_type=None, limit=50) -> list:
        """获取任务列表"""
        sql = "SELECT * FROM teaching_tasks WHERE 1=1"
        params = []
        if subject:
            sql += " AND subject = ?"
            params.append(subject)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if task_type:
            sql += " AND task_type = ?"
            params.append(task_type)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        tasks = self._query(sql, tuple(params))
        for t in tasks:
            t["knowledge_ids"] = json.loads(t.get("knowledge_ids", "[]"))
            t["data_ids"] = json.loads(t.get("data_ids", "[]"))
            t["question_ids"] = json.loads(t.get("question_ids", "[]"))
        return tasks

    def update_task(self, task_id: int, **fields) -> bool:
        """更新任务信息"""
        allowed = {
            "title", "description", "task_type", "difficulty", "target_score",
            "time_limit", "knowledge_ids", "data_ids", "question_ids",
            "status", "source_detail",
        }
        updates = []
        params = []
        for k, v in fields.items():
            if k in allowed:
                if k in ("knowledge_ids", "data_ids", "question_ids"):
                    v = json.dumps(v, ensure_ascii=False)
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return False
        params.append(task_id)
        cur = self._execute(
            f"UPDATE teaching_tasks SET {', '.join(updates)}, updated_at = datetime('now','localtime') WHERE id = ?",
            tuple(params)
        )
        return cur.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        """删除任务（级联删除关联的分配和进度）"""
        self._execute("DELETE FROM task_progress WHERE assignment_id IN (SELECT id FROM task_assignments WHERE task_id = ?)", (task_id,))
        self._execute("DELETE FROM task_assignments WHERE task_id = ?", (task_id,))
        cur = self._execute("DELETE FROM teaching_tasks WHERE id = ?", (task_id,))
        return cur.rowcount > 0

    def assign_task(self, task_id: int, user_id: int) -> dict:
        """为学生分配任务"""
        existing = self._query_one(
            "SELECT * FROM task_assignments WHERE task_id = ? AND user_id = ?",
            (task_id, user_id)
        )
        if existing:
            return {"assignment_id": existing["id"], "status": existing["status"]}
        cur = self._execute(
            "INSERT INTO task_assignments (task_id, user_id) VALUES (?, ?)",
            (task_id, user_id)
        )
        return {"assignment_id": cur.lastrowid, "status": "assigned"}

    def get_task_assignments(self, task_id=None, user_id=None, status=None) -> list:
        """获取任务分配列表"""
        sql = "SELECT * FROM task_assignments WHERE 1=1"
        params = []
        if task_id:
            sql += " AND task_id = ?"
            params.append(task_id)
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY created_at DESC"
        return self._query(sql, tuple(params))

    def start_task(self, assignment_id: int) -> bool:
        """开始执行任务"""
        cur = self._execute(
            "UPDATE task_assignments SET status = 'in_progress', started_at = ? WHERE id = ?",
            (time.time(), assignment_id)
        )
        return cur.rowcount > 0

    def complete_task(self, assignment_id: int, score: float = 0.0, time_spent: float = 0.0) -> bool:
        """完成任务"""
        cur = self._execute(
            """UPDATE task_assignments SET
            status = 'completed', score = ?, time_spent = ?,
            completed_at = ?
            WHERE id = ?""",
            (score, time_spent, time.time(), assignment_id)
        )
        return cur.rowcount > 0

    def skip_task(self, assignment_id: int) -> bool:
        """跳过任务"""
        cur = self._execute(
            "UPDATE task_assignments SET status = 'skipped', completed_at = ? WHERE id = ?",
            (time.time(), assignment_id)
        )
        return cur.rowcount > 0

    def record_task_step(
        self,
        assignment_id: int,
        step_order: int,
        step_type: str,
        question_id: int = 0,
        is_correct: bool = False,
        answer_text: str = "",
        points_earned: float = 0.0,
        time_spent: float = 0.0,
    ) -> dict:
        """记录任务执行进度"""
        cur = self._execute(
            """INSERT INTO task_progress
            (assignment_id, step_order, step_type, question_id, is_correct,
             answer_text, points_earned, time_spent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (assignment_id, step_order, step_type, question_id,
             1 if is_correct else 0, answer_text, points_earned, time_spent)
        )
        return {"id": cur.lastrowid, "step_order": step_order}

    def get_task_progress(self, assignment_id: int) -> list:
        """获取任务执行进度"""
        return self._query(
            "SELECT * FROM task_progress WHERE assignment_id = ? ORDER BY step_order",
            (assignment_id,)
        )

    def get_user_tasks(self, user_id: int, status: str = None) -> list:
        """获取用户的所有任务"""
        sql = """SELECT t.*, a.status as assignment_status, a.score, a.time_spent
                 FROM teaching_tasks t
                 JOIN task_assignments a ON t.id = a.task_id
                 WHERE a.user_id = ?"""
        params = [user_id]
        if status:
            sql += " AND a.status = ?"
            params.append(status)
        sql += " ORDER BY a.created_at DESC"
        tasks = self._query(sql, tuple(params))
        for t in tasks:
            t["knowledge_ids"] = json.loads(t.get("knowledge_ids", "[]"))
            t["data_ids"] = json.loads(t.get("data_ids", "[]"))
            t["question_ids"] = json.loads(t.get("question_ids", "[]"))
        return tasks

    def generate_task_from_knowledge(self, node_id: str, subject: str, difficulty: str = "基础") -> dict:
        """根据知识点自动生成教学任务"""
        node = self.get_knowledge_node(node_id)
        if not node:
            return {"error": f"知识点 {node_id} 不存在"}
        questions = self.get_questions(knowledge_id=node_id, limit=5)
        task = self.create_task(
            title=f"{node['name']}学习任务",
            subject=subject,
            knowledge_ids=[node_id],
            question_ids=[q["id"] for q in questions],
            task_type="learn",
            difficulty=difficulty,
            description=node["description"],
            source="auto_ai",
            source_detail=f"从知识点 {node_id} 自动生成",
        )
        return {
            "task_id": task["id"],
            "title": task["title"],
            "question_count": len(questions),
        }

    def generate_task_from_content(self, content_id: int, task_type: str = "exercise") -> dict:
        """根据教学内容自动生成任务"""
        content = self.get_training_record(content_id)
        if not content:
            return {"error": f"教学内容 #{content_id} 不存在"}
        task = self.create_task(
            title=f"{content['title']}练习任务",
            subject=content["subject"],
            data_ids=[content_id],
            task_type=task_type,
            difficulty=content["difficulty"],
            description=content["content"][:200] + "..." if len(content["content"]) > 200 else content["content"],
            source="auto_ai",
            source_detail=f"从教学内容 {content_id} 自动生成",
        )
        return {"task_id": task["id"], "title": task["title"]}

    def get_task_stats(self, user_id: int) -> dict:
        """获取用户任务统计"""
        total = self._query_one(
            "SELECT COUNT(*) as n FROM task_assignments WHERE user_id = ?", (user_id,)
        )["n"]
        completed = self._query_one(
            "SELECT COUNT(*) as n FROM task_assignments WHERE user_id = ? AND status = 'completed'",
            (user_id,)
        )["n"]
        avg_score = self._query_one(
            "SELECT AVG(score) as avg_score FROM task_assignments WHERE user_id = ? AND status = 'completed'",
            (user_id,)
        )["avg_score"] or 0
        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": round(completed / max(total, 1) * 100, 1),
            "average_score": round(avg_score, 1),
        }

    # ============================================================
    # H. 学生端：思考记录 / AI学习会话 / 概念理解
    # ============================================================

    def record_thought(
        self,
        user_id: int,
        thought_type: str = "question",
        question: str = "",
        idea: str = "",
        conclusion: str = "",
        session_id: str = "",
        task_id: int = 0,
        related_knowledge: str = "",
        related_question: str = "",
        ai_feedback: str = "",
        ai_follow_up: str = "",
        effort_level: str = "normal",
        correctness_hint: str = "neutral",
    ) -> Dict:
        """
        记录学生的思考过程

        典型使用场景：
          1. 学生遇到问题 → thought_type='question'
          2. 学生提出假设 → thought_type='idea'
          3. 学生得出答案 → thought_type='conclusion'
          4. 学生获得提示 → thought_type='hint'

        参数：
            thought_type:   思考类型 (question/idea/conclusion/hint)
            question:       学生的问题文本
            idea:           学生的想法/假设
            conclusion:     学生的结论
            session_id:     关联的学习会话
            task_id:        关联的任务ID
            related_knowledge: 关联知识点ID
            related_question:  关联题目ID
            ai_feedback:    AI 生成的反馈/提示
            ai_follow_up:   AI 的跟进问题
            effort_level:   努力程度 (low/normal/high)
            correctness_hint: 正确性提示 (wrong/partial/correct/neutral)
        """
        cur = self._execute(
            """INSERT INTO student_thoughts
            (user_id, session_id, task_id, thought_type, question, idea, conclusion,
             related_knowledge, related_question, ai_feedback, ai_follow_up,
             effort_level, correctness_hint)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, session_id, task_id, thought_type, question, idea, conclusion,
             related_knowledge, related_question, ai_feedback, ai_follow_up,
             effort_level, correctness_hint)
        )
        return {"id": cur.lastrowid, "type": thought_type}

    def get_thoughts(
        self,
        user_id: int = None,
        session_id: str = None,
        task_id: int = None,
        thought_type: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """获取学生思考记录列表"""
        sql = "SELECT * FROM student_thoughts WHERE 1=1"
        params = []
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        if task_id:
            sql += " AND task_id = ?"
            params.append(task_id)
        if thought_type:
            sql += " AND thought_type = ?"
            params.append(thought_type)
        sql += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)
        return self._query(sql, tuple(params))

    def update_thought_ai_feedback(self, thought_id: int, ai_feedback: str, ai_follow_up: str) -> bool:
        """更新 AI 反馈（学生思考后 AI 回复）"""
        cur = self._execute(
            """UPDATE student_thoughts
            SET ai_feedback = ?, ai_follow_up = ?, updated_at = datetime('now','localtime')
            WHERE id = ?""",
            (ai_feedback, ai_follow_up, thought_id)
        )
        return cur.rowcount > 0

    def get_thought_summary(self, user_id: int) -> Dict:
        """获取学生思考摘要统计"""
        rows = self._query(
            """SELECT thought_type, COUNT(*) as n,
            SUM(CASE WHEN correctness_hint = 'correct' THEN 1 ELSE 0 END) as correct_cnt,
            SUM(CASE WHEN correctness_hint = 'wrong' THEN 1 ELSE 0 END) as wrong_cnt,
            SUM(CASE WHEN correctness_hint = 'partial' THEN 1 ELSE 0 END) as partial_cnt
            FROM student_thoughts WHERE user_id = ?
            GROUP BY thought_type""",
            (user_id,)
        )
        total = self._query_one(
            "SELECT COUNT(*) as n FROM student_thoughts WHERE user_id = ?", (user_id,)
        )["n"]
        return {"total": total, "by_type": rows}

    # ---- AI 学习会话管理 ----

    def create_ai_session(
        self,
        user_id: int,
        topic: str = "",
        session_type: str = "exploration",
        task_id: int = None,
    ) -> Dict:
        """创建 AI 学习会话"""
        cur = self._execute(
            """INSERT INTO ai_student_sessions
            (user_id, task_id, topic, session_type, started_at)
            VALUES (?, ?, ?, ?, ?)""",
            (user_id, task_id, topic, session_type, time.time())
        )
        return {"id": cur.lastrowid, "status": "active"}

    def record_ai_session_event(
        self,
        session_id: int,
        user_input: str,
        agent_response: str,
        agent_model: str = "",
        event_type: str = "turn",
    ) -> Dict:
        """
        记录 AI 会话中的一轮交互

        参数：
            session_id:   会话ID
            user_input:   学生输入
            agent_response: AI 响应
            agent_model:  使用的模型
            event_type:   事件类型 (turn/thought/hint/feedback)
        """
        # 获取当前会话
        session = self._query_one("SELECT * FROM ai_student_sessions WHERE id = ?", (session_id,))
        if not session:
            return {"error": "会话不存在"}

        # 更新统计
        self._execute(
            """UPDATE ai_student_sessions SET
            total_thoughts = total_thoughts + 1,
            last_agent_response = ?,
            agent_status = ?,
            ended_at = CASE WHEN ? = 'completed' THEN ? ELSE ended_at END
            WHERE id = ?""",
            (agent_response, "active" if event_type != "completed" else "completed",
             event_type, time.time(), session_id)
        )
        return {"session_id": session_id, "event": event_type}

    def complete_ai_session(self, session_id: int, time_spent: float = 0.0) -> bool:
        """完成 AI 学习会话"""
        cur = self._execute(
            """UPDATE ai_student_sessions SET
            status = 'completed', ended_at = ?, time_spent = ?
            WHERE id = ?""",
            (time.time(), time_spent, session_id)
        )
        return cur.rowcount > 0

    def get_ai_sessions(self, user_id: int = None, status: str = None, limit: int = 20) -> List[Dict]:
        """获取 AI 学习会话列表"""
        sql = "SELECT * FROM ai_student_sessions WHERE 1=1"
        params = []
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        return self._query(sql, tuple(params))

    def get_ai_session_detail(self, session_id: int) -> Optional[Dict]:
        """获取 AI 会话详情"""
        return self._query_one("SELECT * FROM ai_student_sessions WHERE id = ?", (session_id,))

    def get_ai_session_thoughts(self, session_id: int, limit: int = 50) -> List[Dict]:
        """获取会话中的所有思考记录"""
        return self._query(
            "SELECT * FROM student_thoughts WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit)
        )

    # ---- 概念理解管理 ----

    def update_concept_understanding(
        self,
        user_id: int,
        node_id: str,
        understanding: float = 0.0,
        state: str = "unknown",
        error_patterns: List[str] = None,
        misconception: str = "",
        attempts: int = 0,
        correct_attempts: int = 0,
        wrong_attempts: int = 0,
        total_time: float = 0.0,
        ai_assessment: str = "",
        recommended_action: str = "",
    ) -> Dict:
        """
        更新知识点理解状态（首次创建，后续更新）

        参数：
            understanding:  理解度 0.0-1.0
            state:          理解状态 (unknown/learning/mastered/difficult)
            error_patterns: 错误模式列表
            misconception:  误解描述
            attempts:       尝试次数
            correct_attempts: 正确尝试次数
            wrong_attempts:   错误尝试次数
            total_time:     总学习时间（秒）
            ai_assessment:  AI 评估
            recommended_action: AI 推荐动作
        """
        if error_patterns is None:
            error_patterns = []

        # 检查是否已存在
        existing = self._query_one(
            "SELECT * FROM concept_understanding WHERE user_id = ? AND node_id = ?",
            (user_id, node_id)
        )

        if existing:
            cur = self._execute(
                """UPDATE concept_understanding SET
                understanding = ?, state = ?, error_patterns = ?, misconception = ?,
                attempts = ?, correct_attempts = ?, wrong_attempts = ?,
                total_time = total_time + ?, last_interaction = ?,
                ai_assessment = ?, recommended_action = ?,
                updated_at = datetime('now','localtime')
                WHERE user_id = ? AND node_id = ?""",
                (
                    understanding, state, json.dumps(error_patterns), misconception,
                    attempts, correct_attempts, wrong_attempts, total_time, time.time(),
                    ai_assessment, recommended_action, user_id, node_id
                )
            )
        else:
            cur = self._execute(
                """INSERT INTO concept_understanding
                (user_id, node_id, understanding, state, error_patterns, misconception,
                 attempts, correct_attempts, wrong_attempts, total_time,
                 last_interaction, ai_assessment, recommended_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id, node_id, understanding, state,
                    json.dumps(error_patterns), misconception,
                    attempts, correct_attempts, wrong_attempts, total_time,
                    time.time(), ai_assessment, recommended_action
                )
            )
        return {"user_id": user_id, "node_id": node_id, "understanding": understanding, "state": state}

    def increment_concept_attempts(
        self,
        user_id: int,
        node_id: str,
        is_correct: bool,
        time_spent: float = 0.0,
    ) -> Dict:
        """
        增加知识点尝试次数并更新理解度

        使用指数移动平均更新理解度：
          new_understanding = old * 0.7 + (is_correct ? 0.3 : -0.1)

        参数：
            user_id:    用户ID
            node_id:    知识点ID
            is_correct: 是否正确
            time_spent: 本次用时（秒）
        """
        existing = self._query_one(
            "SELECT * FROM concept_understanding WHERE user_id = ? AND node_id = ?",
            (user_id, node_id)
        )

        if existing:
            alpha = 0.3
            delta = 0.3 if is_correct else -0.1
            new_understanding = max(0.0, min(1.0, existing["understanding"] + delta))

            new_state = "unknown"
            if new_understanding >= 0.8:
                new_state = "mastered"
            elif new_understanding >= 0.5:
                new_state = "learning"
            elif new_understanding < 0.2:
                new_state = "difficult"
            else:
                new_state = "learning"

            self._execute(
                """UPDATE concept_understanding SET
                attempts = attempts + 1,
                correct_attempts = correct_attempts + ?,
                wrong_attempts = wrong_attempts + ?,
                total_time = total_time + ?,
                understanding = ?,
                state = ?,
                last_interaction = ?
                WHERE user_id = ? AND node_id = ?""",
                (1 if is_correct else 0, 1 if not is_correct else 0,
                 time_spent, new_understanding, new_state, time.time(), user_id, node_id)
            )
            return {"understanding": new_understanding, "state": new_state}
        else:
            # 首次尝试，创建记录
            new_understanding = 0.3 if is_correct else 0.1
            new_state = "mastered" if new_understanding >= 0.8 else "learning"
            self._execute(
                """INSERT INTO concept_understanding
                (user_id, node_id, understanding, state, attempts, correct_attempts,
                 wrong_attempts, total_time, last_interaction)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (user_id, node_id, new_understanding, new_state,
                 1 if is_correct else 0, 1 if not is_correct else 0,
                 time_spent, time.time())
            )
            return {"understanding": new_understanding, "state": new_state}

    def get_concept_progress(self, user_id: int) -> Dict:
        """获取用户对知识图谱的理解进度"""
        rows = self._query(
            """SELECT cu.*, kn.name, kn.category, kn.difficulty
            FROM concept_understanding cu
            JOIN knowledge_nodes kn ON cu.node_id = kn.id
            WHERE cu.user_id = ?""",
            (user_id,)
        )
        total = self._query_one("SELECT COUNT(*) as n FROM knowledge_nodes")["n"]
        studied = len(rows)
        mastered = sum(1 for r in rows if r["state"] == "mastered")
        learning = sum(1 for r in rows if r["state"] == "learning")
        difficult = sum(1 for r in rows if r["state"] == "difficult")
        return {
            "user_id": user_id,
            "total_nodes": total,
            "studied": studied,
            "mastered": mastered,
            "learning": learning,
            "difficult": difficult,
            "not_started": total - studied,
            "overall_progress": round(mastered / max(total, 1) * 100, 1),
            "nodes": rows,
        }

    def get_difficult_concepts(self, user_id: int, min_attempts: int = 3) -> List[Dict]:
        """获取需要重点关注的困难知识点"""
        rows = self._query(
            """SELECT * FROM concept_understanding
            WHERE user_id = ? AND state = 'difficult'
            ORDER BY understanding ASC LIMIT 10""",
            (user_id,)
        )
        return rows

    def get_learning_insights(self, user_id: int) -> Dict:
        """生成学生学习洞察报告"""
        # 获取思考记录
        thoughts = self.get_thoughts(user_id=user_id, limit=200)
        # 获取概念理解
        concept_prog = self.get_concept_progress(user_id)
        # 获取 AI 会话
        ai_sessions = self.get_ai_sessions(user_id=user_id, status="completed", limit=20)

        # 分析思考模式
        wrong_thoughts = [t for t in thoughts if t.get("correctness_hint") == "wrong"]
        hint_usage = sum(1 for t in thoughts if t.get("thought_type") == "hint")

        insights = {
            "user_id": user_id,
            "total_thoughts": len(thoughts),
            "wrong_ratio": round(len(wrong_thoughts) / max(len(thoughts), 1), 2),
            "hint_dependency": round(hint_usage / max(len(thoughts), 1), 2),
            "concept_progress": concept_prog,
            "ai_sessions_completed": len(ai_sessions),
            "recommendations": [],
        }

        # 生成推荐
        if concept_prog["difficult"] > 0:
            insights["recommendations"].append(
                f"有 {concept_prog['difficult']} 个困难知识点需要加强练习"
            )
        if insights["hint_dependency"] > 0.3:
            insights["recommendations"].append(
                "依赖提示较多，建议多尝试独立推理"
            )
        if insights["wrong_ratio"] > 0.5:
            insights["recommendations"].append(
                "错误率较高，建议先回顾基础概念"
            )
        if concept_prog["mastered"] == concept_prog["total_nodes"]:
            insights["recommendations"].append("所有知识点已掌握，可以进行挑战题！")

        return insights

    # ============================================================
    # J. 学习成果检测系统
    # ============================================================

    def create_learning_workflow(self, user_id: int, workflow_id: str, workflow_name: str = "") -> Dict:
        """
        创建学习工作流

        参数：
            user_id:        用户ID
            workflow_id:    工作流唯一标识
            workflow_name:  工作流名称（可选）

        返回：
            {"id": int, "workflow_id": str, "status": "active"}
        """
        cur = self._execute(
            """INSERT INTO learning_workflows
            (user_id, workflow_id, workflow_name, started_at)
            VALUES (?, ?, ?, ?)""",
            (user_id, workflow_id, workflow_name, time.time())
        )
        return {"id": cur.lastrowid, "workflow_id": workflow_id, "status": "active"}

    def update_workflow_step(self, workflow_id: int, step: int) -> bool:
        """
        更新工作流当前步骤

        参数：
            workflow_id: 工作流ID
            step:        新步骤序号

        返回：
            是否成功
        """
        cur = self._execute(
            """UPDATE learning_workflows
            SET current_step = ?
            WHERE id = ?""",
            (step, workflow_id)
        )
        return cur.rowcount > 0

    def complete_workflow(self, workflow_id: int, score: float = 100.0) -> Dict:
        """
        完成工作流

        参数：
            workflow_id: 工作流ID
            score:       获得分数（默认满分）

        返回：
            {"id": int, "status": "completed", "score": float}
        """
        cur = self._execute(
            """UPDATE learning_workflows
            SET status = 'completed', completed_at = ?, score_earned = ?
            WHERE id = ?""",
            (time.time(), score, workflow_id)
        )
        return {"id": workflow_id, "status": "completed", "score": score}

    def get_workflow(self, workflow_id: int) -> Optional[Dict]:
        """
        获取单个工作流详情

        参数：
            workflow_id: 工作流ID

        返回：
            工作流信息字典，不存在则返回 None
        """
        return self._query_one("SELECT * FROM learning_workflows WHERE id = ?", (workflow_id,))

    def get_user_workflows(self, user_id: int, status: str = None) -> List[Dict]:
        """
        获取用户的所有工作流

        参数：
            user_id: 用户ID
            status:  状态筛选（active/completed/paused，可选）

        返回：
            工作流列表
        """
        sql = "SELECT * FROM learning_workflows WHERE user_id = ?"
        params = [user_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY started_at DESC"
        return self._query(sql, tuple(params))

    def create_output_detection(self, user_id: int, detection_type: str = "quiz",
                                 prompt: str = "", workflow_id: str = "") -> Dict:
        """
        创建输出检测记录

        参数：
            user_id:        用户ID
            detection_type: 检测类型（quiz/essay/project/peer_review）
            prompt:         检测题目/提示
            workflow_id:    关联工作流标识（可选）

        返回：
            {"id": int, "status": "pending"}
        """
        cur = self._execute(
            """INSERT INTO output_detections
            (user_id, workflow_id, detection_type, prompt)
            VALUES (?, ?, ?, ?)""",
            (user_id, workflow_id, detection_type, prompt)
        )
        return {"id": cur.lastrowid, "status": "pending"}

    def update_detection_result(self, detection_id: int, score: float, feedback: str = "",
                                 user_output: str = "") -> bool:
        """
        更新检测结果

        参数：
            detection_id: 检测ID
            score:        检测得分
            feedback:     检测反馈
            user_output:  用户输出（可选）

        返回：
            是否成功
        """
        cur = self._execute(
            """UPDATE output_detections
            SET score = ?, feedback = ?, user_output = ?
            WHERE id = ?""",
            (score, feedback, user_output, detection_id)
        )
        return cur.rowcount > 0

    def add_guiding_record(self, detection_id: int, guide_type: str,
                            guide_content: str) -> Dict:
        """
        添加引导记录到检测

        参数：
            detection_id:  检测ID
            guide_type:    引导类型（hint/scaffold/question）
            guide_content: 引导内容

        返回：
            {"id": int, "detection_id": int}
        """
        det = self._query_one("SELECT * FROM output_detections WHERE id = ?", (detection_id,))
        if not det:
            return {"error": "检测不存在"}

        guiding_records = json.loads(det.get("guiding_records", "[]"))
        guiding_records.append({
            "type": guide_type,
            "content": guide_content,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        })

        cur = self._execute(
            "UPDATE output_detections SET guiding_records = ? WHERE id = ?",
            (json.dumps(guiding_records, ensure_ascii=False), detection_id)
        )
        return {"id": detection_id, "detection_id": detection_id}

    def mark_reinforced(self, detection_id: int) -> bool:
        """
        标记检测为已强化

        参数：
            detection_id: 检测ID

        返回：
            是否成功
        """
        cur = self._execute(
            "UPDATE output_detections SET reinforced = 1 WHERE id = ?",
            (detection_id,)
        )
        return cur.rowcount > 0

    def get_output_detection(self, detection_id: int) -> Optional[Dict]:
        """
        获取单个检测结果详情

        参数：
            detection_id: 检测ID

        返回：
            检测信息字典，不存在则返回 None
        """
        row = self._query_one(
            "SELECT * FROM output_detections WHERE id = ?", (detection_id,)
        )
        if row:
            row["guiding_records"] = json.loads(row.get("guiding_records", "[]"))
        return row

    def get_user_detections(self, user_id: int, detection_type: str = None,
                             status: str = None, limit: int = 50) -> List[Dict]:
        """
        获取用户的检测记录列表

        参数：
            user_id:        用户ID
            detection_type: 检测类型筛选（可选）
            status:         状态筛选（可选）
            limit:          返回条数

        返回：
            检测列表
        """
        sql = "SELECT * FROM output_detections WHERE user_id = ?"
        params = [user_id]
        if detection_type:
            sql += " AND detection_type = ?"
            params.append(detection_type)
        sql += " ORDER BY detected_at DESC LIMIT ?"
        params.append(limit)
        rows = self._query(sql, tuple(params))
        for r in rows:
            r["guiding_records"] = json.loads(r.get("guiding_records", "[]"))
        return rows

    def get_detection_summary(self, user_id: int) -> Dict:
        """
        获取用户检测统计摘要

        参数：
            user_id: 用户ID

        返回：
            {
                "total_detections": int,
                "completed": int,
                "avg_score": float,
                "reinforced_count": int,
                "by_type": [...]
            }
        """
        total = self._query_one(
            "SELECT COUNT(*) as n FROM output_detections WHERE user_id = ?",
            (user_id,)
        )["n"]

        avg_score = self._query_one(
            "SELECT AVG(score) as avg FROM output_detections WHERE user_id = ?",
            (user_id,)
        )["avg"] or 0.0

        reinforced = self._query_one(
            "SELECT COUNT(*) as n FROM output_detections WHERE user_id = ? AND reinforced = 1",
            (user_id,)
        )["n"]

        by_type = self._query(
            """SELECT detection_type, COUNT(*) as n, AVG(score) as avg_score
            FROM output_detections WHERE user_id = ?
            GROUP BY detection_type""",
            (user_id,)
        )

        return {
            "user_id": user_id,
            "total_detections": total,
            "completed": total,
            "avg_score": round(avg_score, 1),
            "reinforced_count": reinforced,
            "by_type": by_type,
        }

    # ============================================================
    # 数据导出（便于与现有文件系统交互）
    # ============================================================

    def export_training_data_jsonl(self, output_path: str, status: str = "published"):
        """
        将训练数据导出为 JSONL 文件（兼容现有训练管线）

        参数：
            output_path: 输出文件路径
            status:      只导出指定状态的数据（默认 published）
        """
        # 确保输出目录存在
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        records = self.get_training_data(status=status, limit=100000)
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                # 转换为训练管线的格式
                item = {
                    "subject": rec["subject"],
                    "chapter": rec["chapter"],
                    "title": rec["title"],
                    "content": rec["content"],
                    "content_type": rec["content_type"],
                    "difficulty": rec["difficulty"],
                    "keywords": rec["keywords"],
                    "source": rec["source"],
                }
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        return len(records)

    def export_answers_jsonl(self, output_path: str, user_id: Optional[int] = None):
        """将答题记录导出为 JSONL 文件"""
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        if user_id:
            answers = self._query(
                "SELECT * FROM answers WHERE user_id = ? ORDER BY timestamp",
                (user_id,)
            )
        else:
            answers = self._query("SELECT * FROM answers ORDER BY timestamp")
        with open(output_path, "w", encoding="utf-8") as f:
            for ans in answers:
                f.write(json.dumps(ans, ensure_ascii=False) + "\n")
        return len(answers)

    # ============================================================
    # 数据库维护
    # ============================================================

    def get_stats_overview(self) -> Dict:
        """获取数据库整体统计信息"""
        tables = [
            "users", "subjects", "knowledge_nodes", "training_data",
            "questions", "sessions", "answers", "daily_stats",
            "progress", "experiments", "checkpoints", "training_metrics",
            "submissions", "handwriting_records", "teaching_tasks",
            "task_assignments", "task_progress", "student_thoughts",
            "ai_student_sessions", "concept_understanding",
        ]
        stats = {}
        for table in tables:
            count = self._query_one(f"SELECT COUNT(*) as n FROM {table}")["n"]
            stats[table] = count
        stats["db_path"] = self.db_path
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        stats["db_size_mb"] = round(db_size / 1024 / 1024, 2)
        return stats

    def vacuum(self):
        """压缩数据库（清理碎片空间）"""
        self._execute("VACUUM")

    # ============================================================
    # Z1. 管理员管理
    # ============================================================

    def add_admin(self, username: str, password_hash: str,
                  display_name: str = "", role: str = "super_admin") -> Dict:
        cur = self._execute(
            "INSERT INTO admins (username, password_hash, display_name, role) VALUES (?, ?, ?, ?)",
            (username, password_hash, display_name, role)
        )
        return {"id": cur.lastrowid, "username": username, "role": role}

    def get_admin_by_username(self, username: str) -> Optional[Dict]:
        return self._query_one("SELECT * FROM admins WHERE username = ?", (username,))

    def get_admin(self, admin_id: int) -> Optional[Dict]:
        return self._query_one("SELECT * FROM admins WHERE id = ?", (admin_id,))

    def get_admins(self) -> List[Dict]:
        return self._query("SELECT * FROM admins ORDER BY id")

    def update_admin_login(self, admin_id: int) -> None:
        self._execute(
            "UPDATE admins SET last_login_at = datetime('now','localtime') WHERE id = ?",
            (admin_id,)
        )

    def set_admin_active(self, admin_id: int, is_active: int) -> bool:
        cur = self._execute("UPDATE admins SET is_active = ? WHERE id = ?", (is_active, admin_id))
        return cur.rowcount > 0

    def update_admin_password(self, admin_id: int, password_hash: str) -> bool:
        cur = self._execute("UPDATE admins SET password_hash = ? WHERE id = ?", (password_hash, admin_id))
        return cur.rowcount > 0

    # ============================================================
    # Z2. Agent 管理
    # ============================================================

    def register_agent(self, agent_id: str, name: str, agent_type: str,
                       description: str = "", config: str = "{}") -> Dict:
        cur = self._execute(
            "INSERT OR REPLACE INTO agents (agent_id, name, agent_type, description, config) VALUES (?, ?, ?, ?, ?)",
            (agent_id, name, agent_type, description, config)
        )
        return {"id": cur.lastrowid, "agent_id": agent_id}

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        return self._query_one("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))

    def get_agents(self, agent_type: Optional[str] = None) -> List[Dict]:
        if agent_type:
            return self._query("SELECT * FROM agents WHERE agent_type = ? ORDER BY id", (agent_type,))
        return self._query("SELECT * FROM agents ORDER BY id")

    def update_agent_status(self, agent_id: str, status: str) -> bool:
        cur = self._execute(
            "UPDATE agents SET status = ?, last_heartbeat = datetime('now','localtime') WHERE agent_id = ?",
            (status, agent_id)
        )
        return cur.rowcount > 0

    def update_agent_config(self, agent_id: str, config: str) -> bool:
        cur = self._execute("UPDATE agents SET config = ? WHERE agent_id = ?", (config, agent_id))
        return cur.rowcount > 0

    def delete_agent(self, agent_id: str) -> bool:
        cur = self._execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
        return cur.rowcount > 0

    # ============================================================
    # Z3. 系统日志
    # ============================================================

    def add_system_log(self, level: str, module: str, message: str, detail: str = "") -> int:
        cur = self._execute(
            "INSERT INTO system_logs (level, module, message, detail) VALUES (?, ?, ?, ?)",
            (level, module, message, detail)
        )
        return cur.lastrowid

    def get_system_logs(self, level: Optional[str] = None, limit: int = 100) -> List[Dict]:
        if level:
            return self._query(
                "SELECT * FROM system_logs WHERE level = ? ORDER BY id DESC LIMIT ?",
                (level, limit)
            )
        return self._query("SELECT * FROM system_logs ORDER BY id DESC LIMIT ?", (limit,))

    def clear_system_logs(self, older_than_days: int = 7) -> int:
        cur = self._execute(
            "DELETE FROM system_logs WHERE created_at < datetime('now', ?)",
            (f'-{older_than_days} days',)
        )
        return cur.rowcount

    # ============================================================
    # Z3.5 模型推理过程记录（reasoning_logs）
    # ============================================================

    def add_reasoning_log(self, user_id=0, session_id="", mode="feynman", topic="",
                          step_order=0, step_name="", model_used="", prompt="",
                          input_context="", output="", latency_ms=0, status="success") -> int:
        """
        记录一条模型推理过程日志

        参数：
            user_id:       学生用户 id（0 表示未登录/匿名）
            session_id:    会话标识
            mode:          模式（feynman / chat / goai）
            topic:         学习主题
            step_order:    费曼步骤序号 1-5（非费曼为 0）
            step_name:     费曼步骤名
            model_used:    使用的模型
            prompt:        输入 prompt（完整）
            input_context: 前序对话摘要
            output:        模型输出
            latency_ms:    推理耗时毫秒
            status:        success / error

        返回：
            新记录 id
        """
        cur = self._execute(
            """INSERT INTO reasoning_logs
               (user_id, session_id, mode, topic, step_order, step_name,
                model_used, prompt, input_context, output, latency_ms, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, session_id, mode, topic, step_order, step_name,
             model_used, prompt, input_context, output, latency_ms, status)
        )
        return cur.lastrowid

    def get_reasoning_logs(self, user_id=None, model=None, topic=None, mode=None,
                           session_id=None, start_date=None, end_date=None,
                           limit=100, offset=0) -> List[Dict]:
        """
        多条件筛选推理过程日志（条件为空则不参与过滤），按时间倒序

        参数：
            user_id:     按用户 id 筛选
            model:       按模型名筛选
            topic:       按学习主题筛选
            mode:        按模式筛选（feynman / chat / goai）
            session_id:  按会话标识筛选
            start_date:  起始时间（含），如 '2026-01-01 00:00:00'
            end_date:    结束时间（含）
            limit:       返回条数上限
            offset:      偏移量（分页）

        返回：
            字典列表，含 student_name（LEFT JOIN users 取学生姓名）
        """
        conds, params = [], []
        if user_id is not None:
            conds.append("r.user_id = ?")
            params.append(user_id)
        if model:
            conds.append("r.model_used = ?")
            params.append(model)
        if topic:
            conds.append("r.topic = ?")
            params.append(topic)
        if mode:
            conds.append("r.mode = ?")
            params.append(mode)
        if session_id:
            conds.append("r.session_id = ?")
            params.append(session_id)
        if start_date:
            conds.append("r.created_at >= ?")
            params.append(start_date)
        if end_date:
            conds.append("r.created_at <= ?")
            params.append(end_date)
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        params.extend([limit, offset])
        return self._query(
            f"""SELECT r.*, COALESCE(u.name, '') AS student_name
                FROM reasoning_logs r
                LEFT JOIN users u ON r.user_id = u.id
                {where}
                ORDER BY r.created_at DESC, r.id DESC
                LIMIT ? OFFSET ?""",
            tuple(params)
        )

    def get_reasoning_log_by_id(self, log_id: int) -> Optional[Dict]:
        """按 id 查询推理过程日志详情（含学生姓名）"""
        return self._query_one(
            """SELECT r.*, COALESCE(u.name, '') AS student_name
               FROM reasoning_logs r
               LEFT JOIN users u ON r.user_id = u.id
               WHERE r.id = ?""",
            (log_id,)
        )

    def get_reasoning_stats(self, days: int = 7) -> Dict:
        """
        统计推理过程日志

        参数：
            days: 最近天数过滤（0 表示不过滤）

        返回：
            {"total": 总数, "by_model": {模型名: 次数}, "by_step": {步骤名: 次数},
             "avg_latency_ms": 平均耗时, "error_count": 失败数}
        """
        conds, params = [], []
        if days and days > 0:
            conds.append("created_at >= datetime('now', ?)")
            params.append(f'-{days} days')
        where = ("WHERE " + " AND ".join(conds)) if conds else ""

        def _cond_sql(cond: str) -> str:
            """在现有时间过滤基础上追加一个 WHERE/AND 条件"""
            return where + " AND " + cond if where else "WHERE " + cond

        total = self._query_one(
            f"SELECT COUNT(*) AS n FROM reasoning_logs {where}", tuple(params)
        )["n"]
        by_model = {}
        no_model_cond = "model_used != ''"
        for row in self._query(
            f"SELECT model_used AS k, COUNT(*) AS n FROM reasoning_logs "
            f"{_cond_sql(no_model_cond)} GROUP BY model_used ORDER BY n DESC",
            tuple(params)
        ):
            by_model[row["k"]] = row["n"]
        by_step = {}
        no_step_cond = "step_name != ''"
        for row in self._query(
            f"SELECT step_name AS k, COUNT(*) AS n FROM reasoning_logs "
            f"{_cond_sql(no_step_cond)} GROUP BY step_name ORDER BY n DESC",
            tuple(params)
        ):
            by_step[row["k"]] = row["n"]
        avg_latency = self._query_one(
            f"SELECT AVG(latency_ms) AS v FROM reasoning_logs {where}", tuple(params)
        )["v"] or 0
        err_cond = "status = 'error'"
        error_count = self._query_one(
            f"SELECT COUNT(*) AS n FROM reasoning_logs {_cond_sql(err_cond)}",
            tuple(params)
        )["n"]
        return {
            "total": total,
            "by_model": by_model,
            "by_step": by_step,
            "avg_latency_ms": round(avg_latency, 1) if avg_latency else 0,
            "error_count": error_count,
        }

    # ============================================================
    # Z4. API 密钥管理
    # ============================================================

    def add_api_key(self, key_name: str, api_key: str, scope: str = "read") -> Dict:
        cur = self._execute(
            "INSERT INTO api_keys (key_name, api_key, scope) VALUES (?, ?, ?)",
            (key_name, api_key, scope)
        )
        return {"id": cur.lastrowid, "key_name": key_name, "api_key": api_key, "scope": scope}

    def get_api_keys(self, scope: Optional[str] = None) -> List[Dict]:
        if scope:
            return self._query("SELECT * FROM api_keys WHERE scope = ? ORDER BY id", (scope,))
        return self._query("SELECT * FROM api_keys ORDER BY id")

    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        key = self._query_one("SELECT * FROM api_keys WHERE api_key = ? AND is_active = 1", (api_key,))
        if key:
            self._execute(
                "UPDATE api_keys SET last_used_at = datetime('now','localtime') WHERE id = ?",
                (key["id"],)
            )
        return key

    def delete_api_key(self, api_key: str) -> bool:
        cur = self._execute("DELETE FROM api_keys WHERE api_key = ?", (api_key,))
        return cur.rowcount > 0

    # ============================================================
    # L. 组织架构管理（学校库/年级库/班级库）
    # ============================================================

    def add_school(self, name: str, description: str = "") -> Dict:
        """创建学校"""
        try:
            cur = self._execute(
                "INSERT INTO schools (name, description) VALUES (?, ?)",
                (name, description)
            )
            return {"id": cur.lastrowid, "name": name}
        except sqlite3.IntegrityError:
            return {"error": f"学校 '{name}' 已存在"}

    def get_schools(self) -> List[Dict]:
        """获取学校列表（含年级/班级数）"""
        rows = self._query("SELECT * FROM schools ORDER BY id")
        for s in rows:
            s["grade_count"] = self._query_one(
                "SELECT COUNT(*) as n FROM grades WHERE school_id = ?", (s["id"],)
            )["n"]
            s["class_count"] = self._query_one(
                """SELECT COUNT(*) as n FROM classes c
                   JOIN grades g ON c.grade_id = g.id
                   WHERE g.school_id = ?""", (s["id"],)
            )["n"]
        return rows

    def get_school(self, school_id: int) -> Optional[Dict]:
        return self._query_one("SELECT * FROM schools WHERE id = ?", (school_id,))

    def delete_school(self, school_id: int) -> bool:
        """删除学校（级联删除年级/班级/学生绑定）"""
        self._execute(
            "DELETE FROM class_students WHERE class_id IN "
            "(SELECT c.id FROM classes c JOIN grades g ON c.grade_id = g.id WHERE g.school_id = ?)",
            (school_id,)
        )
        self._execute(
            "DELETE FROM classes WHERE grade_id IN (SELECT id FROM grades WHERE school_id = ?)",
            (school_id,)
        )
        self._execute("DELETE FROM grades WHERE school_id = ?", (school_id,))
        cur = self._execute("DELETE FROM schools WHERE id = ?", (school_id,))
        return cur.rowcount > 0

    def add_grade(self, school_id: int, name: str) -> Dict:
        """创建年级"""
        try:
            cur = self._execute(
                "INSERT INTO grades (school_id, name) VALUES (?, ?)",
                (school_id, name)
            )
            return {"id": cur.lastrowid, "school_id": school_id, "name": name}
        except sqlite3.IntegrityError:
            return {"error": f"该校已存在年级 '{name}'"}

    def get_grades(self, school_id: Optional[int] = None) -> List[Dict]:
        """获取年级列表（含班级数）"""
        if school_id:
            rows = self._query(
                "SELECT * FROM grades WHERE school_id = ? ORDER BY id", (school_id,)
            )
        else:
            rows = self._query("SELECT * FROM grades ORDER BY school_id, id")
        for g in rows:
            g["class_count"] = self._query_one(
                "SELECT COUNT(*) as n FROM classes WHERE grade_id = ?", (g["id"],)
            )["n"]
        return rows

    def delete_grade(self, grade_id: int) -> bool:
        """删除年级（级联删除班级/学生绑定）"""
        self._execute(
            "DELETE FROM class_students WHERE class_id IN (SELECT id FROM classes WHERE grade_id = ?)",
            (grade_id,)
        )
        self._execute("DELETE FROM classes WHERE grade_id = ?", (grade_id,))
        cur = self._execute("DELETE FROM grades WHERE id = ?", (grade_id,))
        return cur.rowcount > 0

    def add_class(self, grade_id: int, name: str, teacher_id: int = 0) -> Dict:
        """创建班级（可指定班主任 teacher_id）"""
        try:
            cur = self._execute(
                "INSERT INTO classes (grade_id, name, teacher_id) VALUES (?, ?, ?)",
                (grade_id, name, teacher_id)
            )
            return {"id": cur.lastrowid, "grade_id": grade_id, "name": name}
        except sqlite3.IntegrityError:
            return {"error": f"该年级已存在班级 '{name}'"}

    def get_class(self, class_id: int) -> Optional[Dict]:
        return self._query_one("SELECT * FROM classes WHERE id = ?", (class_id,))

    def get_classes(
        self,
        grade_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        school_id: Optional[int] = None,
    ) -> List[Dict]:
        """获取班级列表（含学生数/班主任姓名/学校年级名）"""
        sql = """SELECT c.*,
                 g.name AS grade_name, g.school_id,
                 s.name AS school_name,
                 u.name AS teacher_name
                 FROM classes c
                 JOIN grades g ON c.grade_id = g.id
                 JOIN schools s ON g.school_id = s.id
                 LEFT JOIN users u ON c.teacher_id = u.id
                 WHERE 1=1"""
        params = []
        if grade_id:
            sql += " AND c.grade_id = ?"
            params.append(grade_id)
        if teacher_id:
            sql += " AND c.teacher_id = ?"
            params.append(teacher_id)
        if school_id:
            sql += " AND g.school_id = ?"
            params.append(school_id)
        sql += " ORDER BY s.id, g.id, c.id"
        rows = self._query(sql, tuple(params))
        for c in rows:
            c["student_count"] = self._query_one(
                "SELECT COUNT(*) as n FROM class_students WHERE class_id = ?", (c["id"],)
            )["n"]
        return rows

    def update_class(self, class_id: int, **fields) -> bool:
        """更新班级（name/teacher_id）"""
        allowed = {"name", "teacher_id"}
        updates = []
        params = []
        for k, v in fields.items():
            if k in allowed:
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return False
        params.append(class_id)
        cur = self._execute(
            f"UPDATE classes SET {', '.join(updates)} WHERE id = ?", tuple(params)
        )
        return cur.rowcount > 0

    def delete_class(self, class_id: int) -> bool:
        """删除班级（级联删除学生绑定）"""
        self._execute("DELETE FROM class_students WHERE class_id = ?", (class_id,))
        cur = self._execute("DELETE FROM classes WHERE id = ?", (class_id,))
        return cur.rowcount > 0

    # ---- 学生-班级绑定 ----

    def add_student_to_class(self, class_id: int, user_id: int) -> Dict:
        """把学生加入班级"""
        user = self.get_user(user_id)
        if not user:
            return {"error": f"用户 #{user_id} 不存在"}
        if user["role"] != "student":
            return {"error": f"用户 {user['name']} 不是学生角色"}
        try:
            cur = self._execute(
                "INSERT OR IGNORE INTO class_students (class_id, user_id) VALUES (?, ?)",
                (class_id, user_id)
            )
            if cur.rowcount == 0:
                return {"info": "该学生已在班级中"}
            return {"class_id": class_id, "user_id": user_id, "added": True}
        except sqlite3.IntegrityError as e:
            return {"error": f"加入失败: {e}"}

    def remove_student_from_class(self, class_id: int, user_id: int) -> bool:
        """把学生移出班级"""
        cur = self._execute(
            "DELETE FROM class_students WHERE class_id = ? AND user_id = ?",
            (class_id, user_id)
        )
        return cur.rowcount > 0

    def get_class_students(self, class_id: int) -> List[Dict]:
        """获取班级学生列表（含学习统计摘要）"""
        rows = self._query(
            """SELECT u.id, u.name, u.username, u.role, u.avatar, u.created_at,
               cs.created_at AS joined_at
               FROM class_students cs
               JOIN users u ON cs.user_id = u.id
               WHERE cs.class_id = ?
               ORDER BY u.name""",
            (class_id,)
        )
        for s in rows:
            s["stats"] = self.get_stats(s["id"])
            s["report_count"] = self._query_one(
                "SELECT COUNT(*) as n FROM learning_reports WHERE user_id = ?", (s["id"],)
            )["n"]
        return rows

    def get_student_classes(self, user_id: int) -> List[Dict]:
        """获取学生所在班级"""
        return self._query(
            """SELECT c.id, c.name AS class_name, g.name AS grade_name, s.name AS school_name
               FROM class_students cs
               JOIN classes c ON cs.class_id = c.id
               JOIN grades g ON c.grade_id = g.id
               JOIN schools s ON g.school_id = s.id
               WHERE cs.user_id = ?
               ORDER BY s.id, g.id, c.id""",
            (user_id,)
        )

    def get_students(self, teacher_id: Optional[int] = None) -> List[Dict]:
        """获取学生列表（教师可只看到自己班级的学生）"""
        sql = """SELECT DISTINCT u.id, u.name, u.username, u.role, u.avatar, u.created_at
                 FROM users u"""
        params = []
        if teacher_id:
            sql += """ JOIN class_students cs ON cs.user_id = u.id
                       JOIN classes c ON c.id = cs.class_id
                       WHERE u.role = 'student' AND c.teacher_id = ?"""
            params.append(teacher_id)
        else:
            sql += " WHERE u.role = 'student'"
        sql += " ORDER BY u.name"
        rows = self._query(sql, tuple(params))
        for s in rows:
            s["classes"] = self.get_student_classes(s["id"])
            s["stats"] = self.get_stats(s["id"])
            s["report_count"] = self._query_one(
                "SELECT COUNT(*) as n FROM learning_reports WHERE user_id = ?", (s["id"],)
            )["n"]
        return rows

    # ---- 教师端总览 ----

    def get_teacher_overview(self, teacher_id: int) -> Dict:
        """教师端总览统计（我的班级/学生/任务/报告）"""
        classes = self.get_classes(teacher_id=teacher_id)
        class_ids = [c["id"] for c in classes]
        student_count = 0
        if class_ids:
            placeholders = ",".join("?" * len(class_ids))
            student_count = self._query_one(
                f"SELECT COUNT(DISTINCT user_id) as n FROM class_students WHERE class_id IN ({placeholders})",
                tuple(class_ids)
            )["n"]

        task_stats = self._query_one(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active, "
            "SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed "
            "FROM teaching_tasks WHERE created_by = ?",
            (teacher_id,)
        ) or {}

        report_count = 0
        if class_ids:
            report_count = self._query_one(
                f"""SELECT COUNT(*) as n FROM learning_reports
                    WHERE user_id IN (SELECT DISTINCT user_id FROM class_students WHERE class_id IN ({placeholders}))""",
                tuple(class_ids)
            )["n"]

        return {
            "teacher_id": teacher_id,
            "class_count": len(classes),
            "student_count": student_count,
            "task_total": task_stats.get("total", 0),
            "task_active": task_stats.get("active", 0),
            "task_completed": task_stats.get("completed", 0),
            "report_count": report_count,
            "classes": classes,
        }

    # ---- 任务批量分配（按班级） ----

    def assign_task_to_class(self, task_id: int, class_id: int) -> Dict:
        """把任务分配给班级内所有学生"""
        students = self.get_class_students(class_id)
        assigned, skipped = [], []
        for s in students:
            # 已分配过的学生跳过
            if self.get_task_assignments(task_id=task_id, user_id=s["id"]):
                skipped.append(s["name"])
                continue
            result = self.assign_task(task_id, s["id"])
            if result.get("assignment_id"):
                assigned.append({"user_id": s["id"], "name": s["name"]})
            else:
                skipped.append(s["name"])
        return {
            "task_id": task_id,
            "class_id": class_id,
            "assigned": assigned,
            "assigned_count": len(assigned),
            "skipped": skipped,
        }

    def get_task_assignments_with_names(self, task_id: int) -> List[Dict]:
        """获取任务分配列表（含学生姓名/班级）"""
        rows = self._query(
            """SELECT a.*, u.name AS user_name, u.username
               FROM task_assignments a
               JOIN users u ON a.user_id = u.id
               WHERE a.task_id = ?
               ORDER BY a.created_at""",
            (task_id,)
        )
        return rows


# ============================================================
# 全局单例
# ============================================================

db = DatabaseManager()
