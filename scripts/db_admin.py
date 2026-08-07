#!/usr/bin/env python3
"""
LumiLearn 数据管理命令行工具

用法：
  python scripts/db_admin.py init                        # 初始化数据库
  python scripts/db_admin.py user list                   # 列出所有用户
  python scripts/db_admin.py user add 小王 student       # 添加用户
  python scripts/db_admin.py teacher                   # 教师工作台
  python scripts/db_admin.py student                   # 学生工作台
  python scripts/db_admin.py train --db                # 从数据库训练
  python scripts/db_admin.py stats                     # 统计概览
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接导入 database 模块，避免触发 framework/__init__.py 的完整导入链
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "lumilearn_database",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "framework", "database.py")
)
_lumilearn_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lumilearn_db)
db = _lumilearn_db.db


# ============================================================
# 子命令：初始化
# ============================================================
def cmd_init(args):
    """初始化数据库"""
    path = db.init(args.db_path)
    print(f"[OK] 数据库已初始化: {path}")
    print(f"[OK] 学科: {len(db._query('SELECT * FROM subjects'))}个")
    print(f"[OK] 知识点: {len(db.get_knowledge_nodes())}个")
    print(f"[OK] 用户: {len(db.get_users())}个")
    overview = db.get_stats_overview()
    print(f"\n[OK] 数据库大小: {overview['db_size_mb']}MB")


# ============================================================
# 子命令：用户管理
# ============================================================
def cmd_user(args):
    """用户管理"""
    if args.action == "list":
        users = db.get_users(role=args.role)
        if not users:
            print("暂无用户")
            return
        print(f"\n{'ID':<4} {'姓名':<8} {'角色':<6} {'创建时间'}")
        print("-" * 50)
        for u in users:
            print(f"{u['id']:<4} {u['name']:<8} {u['role']:<6} {u['created_at']}")

    elif args.action == "add":
        user = db.add_user(args.name, role=args.role or "student")
        print(f"[OK] 已添加用户: {user['name']} (role={user['role']}, id={user['id']})")

    elif args.action == "delete":
        ok = db.delete_user(args.id)
        print(f"[OK] 已删除用户 id={args.id}: {ok}")

    elif args.action == "search":
        users = db.get_users()
        if not users:
            print("暂无用户")
            return
        kw = args.keyword.lower()
        matches = [u for u in users if kw in u['name'].lower() or kw in u['role'].lower()]
        if not matches:
            print(f"未找到匹配 '{args.keyword}' 的用户")
            return
        print(f"\n搜索 '{args.keyword}' 找到 {len(matches)} 个:")
        print(f"{'ID':<4} {'姓名':<8} {'角色':<6} {'创建时间'}")
        print("-" * 50)
        for u in matches:
            print(f"{u['id']:<4} {u['name']:<8} {u['role']:<6} {u['created_at']}")


# ============================================================
# 子命令：教学内容管理
# ============================================================
def cmd_content(args):
    """教学内容管理"""
    if args.action == "list":
        records = db.get_training_data(
            subject=args.subject,
            status=args.status,
            difficulty=args.difficulty,
            limit=args.limit,
        )
        if not records:
            print("暂无教学内容")
            return
        print(f"\n共 {len(records)} 条:")
        for r in records:
            src_icon = "📝" if r["source"] == "handwriting" else "✍️"
            print(f"  {src_icon} #{r['id']} [{r['subject']}] {r['title']} | 难度:{r['difficulty']} | {r['status']}")
            print(f"      {r['content'][:60]}...")

    elif args.action == "add":
        record = db.add_training_data(
            subject=args.subject,
            chapter=args.chapter or "",
            title=args.title,
            content=args.content,
            grade=args.grade or "高中",
            difficulty=args.difficulty or "基础",
            source=args.source or "manual",
            status=args.status or "draft",
        )
        print(f"[OK] 已添加内容 #{record['id']}: {record['title']}")

    elif args.action == "publish":
        # 先批准再发布
        if args.submission_id:
            review = db.review_submission(args.submission_id, approved=True, reviewer_id=args.user_id or 1)
            print(f"[OK] 审核通过 #{args.submission_id}: {review['status']}")
            pub = db.publish_submission(args.submission_id)
            print(f"[OK] 已发布: {pub}")
        else:
            print("[提示] 请提供 --submission-id 以从待审核区发布")

    elif args.action == "count":
        total = db.count_training_data(subject=args.subject)
        by_status = db._query("SELECT status, COUNT(*) as n FROM training_data GROUP BY status")
        print(f"\n总内容数: {total}")
        print(f"按状态:")
        for r in by_status:
            print(f"  {r['status']}: {r['n']}条")


# ============================================================
# 子命令：题目管理
# ============================================================
def cmd_question(args):
    """题目管理"""
    if args.action == "list":
        questions = db.get_questions(
            subject=args.subject,
            difficulty=args.difficulty,
            limit=args.limit,
        )
        if not questions:
            print("暂无题目")
            return
        print(f"\n共 {len(questions)} 道:")
        for q in questions:
            print(f"  #{q['id']} [{q['subject']}] {q['question']}")
            print(f"      答案: {q['correct_answer']} | 难度:{q['difficulty']} | 主题:{q['topic']}")

    elif args.action == "add":
        q = db.add_question(
            subject=args.subject,
            question=args.question,
            correct_answer=args.answer,
            topic=args.topic or "",
            explanation=args.explanation or "",
            difficulty=int(args.difficulty) if args.difficulty else 2,
        )
        print(f"[OK] 已添加题目 #{q['id']}: {q['question'][:30]}...")

    elif args.action == "delete":
        ok = db.delete_question(args.id)
        print(f"[OK] 删除题目 #{args.id}: {ok}")


# ============================================================
# 子命令：待审核录入区
# ============================================================
def cmd_review(args):
    """待审核录入区"""
    if args.action == "list":
        subs = db.get_submissions(
            status=args.status or "pending",
            submission_type=args.type,
            limit=args.limit,
        )
        if not subs:
            print(f"暂无{args.status or 'pending'}状态的提交")
            return
        print(f"\n{'='*70}")
        print(f"  待审核录入区 ({args.status or 'pending'} 状态, 共 {len(subs)} 条)")
        print(f"{'='*70}")
        for s in subs:
            icon = {"pending": "⏳", "approved": "✅", "rejected": "❌", "published": "📦"}[s["status"]]
            print(f"\n{icon} #{s['id']} [{s['type']}] {s['title'] or s['question'][:25]}")
            print(f"   提交者: {s['submitted_by_name']} | 来源: {s['source']} | 学科: {s['subject']}")
            if s.get("content"):
                print(f"   内容: {s['content'][:80]}...")
            elif s.get("question"):
                print(f"   题目: {s['question'][:80]}...")
            if s.get("review_comment"):
                print(f"   审核意见: {s['review_comment']}")
            print(f"   时间: {s['created_at']}")

    elif args.action == "stats":
        stats = db.get_submission_stats()
        print(f"\n{'='*50}")
        print(f"  待审核录入区统计")
        print(f"{'='*50}")
        for k, v in stats.items():
            print(f"  {k}: {v}")

    elif args.action == "approve":
        review = db.review_submission(args.id, approved=True, reviewer_id=args.reviewer or 1)
        print(f"[OK] 已通过 #{args.id}: {review['status']}")

    elif args.action == "reject":
        review = db.review_submission(args.id, approved=False, reviewer_id=args.reviewer or 1, review_comment=args.comment or "")
        print(f"[OK] 已拒绝 #{args.id}: {review['status']}")
        if args.comment:
            print(f"      审核意见: {args.comment}")

    elif args.action == "publish":
        pub = db.publish_submission(args.id)
        if pub.get("published"):
            print(f"[OK] 已发布 #{args.id} → {pub['target_table']} #{pub['record_id']}")
        else:
            print(f"[错误] {pub.get('error')}")

    elif args.action == "delete":
        ok = db.delete_submission(args.id)
        print(f"[OK] 已删除 #{args.id}: {ok}")


# ============================================================
# 子命令：手写录入
# ============================================================
def cmd_handwriting(args):
    """手写录入管理"""
    if args.action == "list":
        hw_list = db.get_handwriting_list(user_id=args.user_id, limit=args.limit)
        if not hw_list:
            print("暂无手写记录")
            return
        print(f"\n共 {len(hw_list)} 条手写记录:")
        for hw in hw_list:
            status_icon = "✅" if hw.get("submission_id") else "⏳"
            print(f"  {status_icon} 手写#{hw['id']} | {hw['user_id']} | {hw['image_path']}")
            print(f"      OCR: {hw['ocr_text'][:40]}... (置信度:{hw['ocr_confidence']:.0%})")
            if hw['edited_text']:
                print(f"      校对: {hw['edited_text'][:40]}...")
            print(f"      笔画:{len(hw['strokes'])}笔 | 设备:{hw['device']} | 提交:{hw['submission_id']}")

    elif args.action == "add":
        # 模拟手写录入（无实际图片）
        hw = db.add_handwriting(
            user_id=args.user_id or 1,
            image_path=args.image_path or "data/handwriting/test.png",
            ocr_text=args.ocr_text or "",
            edited_text=args.edited_text or "",
            note=args.note or "",
            device=args.device or "",
        )
        print(f"[OK] 手写记录 #{hw['id']}: {hw['ocr_text'][:40]}...")

    elif args.action == "update":
        ok = db.update_handwriting(
            args.id,
            edited_text=args.edited_text or None,
            note=args.note or None,
        )
        print(f"[OK] 更新手写记录 #{args.id}: {ok}")


# ============================================================
# 子命令：学习统计
# ============================================================
def cmd_stats(args):
    """学习统计"""
    if args.user_id:
        user = db.get_user(args.user_id)
        if not user:
            print(f"[错误] 用户 id={args.user_id} 不存在")
            return
        print(f"\n{'='*50}")
        print(f"  用户: {user['name']} (id={user['id']}, role={user['role']})")
        print(f"{'='*50}")

        stats = db.get_stats(user_id=args.user_id)
        print(f"\n  答题统计:")
        print(f"    总答题数: {stats['total_answers']}")
        print(f"    正确: {stats['correct']} ({stats['accuracy']}%)")
        print(f"    错误: {stats['wrong']}")
        print(f"    学习时长: {stats['total_time_minutes']}分钟")
        print(f"    会话数: {stats['total_sessions']}")

        weak = db.get_weak_topics(user_id=args.user_id, min_errors=args.min_errors)
        if weak:
            print(f"\n  薄弱知识点 (错误率≥{(1-args.accuracy/100) if 'accuracy' in stats else 0.3}):")
            for w in weak:
                print(f"    ❌ {w['topic']}: 错误{w['wrong']}次, 总{w['total']}次, 错误率{w['error_rate']:.0%}")

        progress = db.get_progress(user_id=args.user_id)
        print(f"\n  知识图谱进度:")
        print(f"    已学习: {progress['studied']}/{progress['total_nodes']}")
        print(f"    已掌握: {progress['mastered']}")
        print(f"    学习中: {progress['learning']}")
        print(f"    未开始: {progress['not_started']}")
        print(f"    整体进度: {progress['overall_progress']}%")

        daily = db.get_daily_stats(user_id=args.user_id, days=args.days or 30)
        if daily:
            total_time = sum(d['total_time'] for d in daily) / 60
            print(f"\n  近{len(daily)}天学习:")
            print(f"    总时长: {total_time:.1f}分钟")
            print(f"    平均每日: {total_time/len(daily):.1f}分钟")

    else:
        overview = db.get_stats_overview()
        print(f"\n{'='*50}")
        print(f"  LumiLearn 数据库总览")
        print(f"{'='*50}")
        for k, v in overview.items():
            print(f"  {k}: {v}")


# ============================================================
# 子命令：教学任务管理
# ============================================================
def cmd_task(args):
    """教学任务管理"""
    if args.action == "list":
        tasks = db.get_tasks(limit=args.limit or 20)
        if not tasks:
            print("暂无教学任务")
            return
        print(f"\n共 {len(tasks)} 条任务:")
        for t in tasks:
            icon = "📝" if t['status'] == 'draft' else ("✅" if t['status'] == 'active' else "📦")
            print(f"  {icon} #{t['id']} [{t['subject']}] {t['title']} | 难度:{t['difficulty']} | {t['status']}")
            print(f"      {t['description'][:60]}..." if t.get('description') else "")

    elif args.action == "create":
        result = db.create_task(
            title=args.title or "",
            description=args.description or "",
            task_type=args.type or "exercise",
            subject=args.subject or "",
            difficulty=args.difficulty or "基础",
            node_id=args.node_id or "",
        )
        print(f"[OK] 已创建任务 #{result['id']}: {result['title']}")

    elif args.action == "delete":
        ok = db.delete_task(args.id)
        print(f"[OK] 已删除任务 #{args.id}: {ok}")

    elif args.action == "stats":
        stats = db.get_task_stats(args.user_id or 1)
        print(f"\n任务统计 (用户{stats['user_id']}):")
        print(f"  已完成: {stats['completed_tasks']}个")
        print(f"  平均分: {stats['avg_score']:.1f}")
        print(f"  完成率: {stats['completion_rate']:.0%}")


# ============================================================
# 子命令：训练数据导出
# ============================================================
def cmd_export(args):
    """导出训练数据"""
    if args.format == "jsonl":
        n = db.export_training_data_jsonl(args.output, status=args.status or "published")
        print(f"[OK] 已导出 {n} 条训练数据 → {args.output}")
    elif args.format == "answers":
        n = db.export_answers_jsonl(args.output, user_id=args.user_id)
        print(f"[OK] 已导出 {n} 条答题记录 → {args.output}")


# ============================================================
# 子命令：训练（从数据库读取）
# ============================================================
def cmd_train(args):
    """从数据库启动训练"""
    from framework.data import load_records_from_db
    from framework.config import get_preset_configs
    from framework.trainer import LumiLearnTrainer
    from framework.model import LumiLearnModel
    from framework.tokenizer import LumiLearnTokenizer

    print(f"\n{'='*50}")
    print(f"  从数据库加载训练数据")
    print(f"{'='*50}")

    records = load_records_from_db(db_path=args.db, status=args.status or "published")
    print(f"[OK] 从数据库加载 {len(records)} 条已发布教学内容")

    if not records:
        print("[警告] 数据库中没有已发布的教学内容，请先录入并发布内容")
        print("[提示] 运行: python scripts/db_admin.py teacher")
        return

    # 加载配置
    config = get_preset_configs().get(args.preset, "fast_test")

    # 创建模型和训练器
    model = LumiLearnModel(config.model)
    tokenizer = LumiLearnTokenizer(config.model.vocab_size)

    print(f"[OK] 模型参数: {model.get_param_count():,}")

    # 使用训练器训练
    trainer = LumiLearnTrainer(config, model, tokenizer, records)
    print(f"\n[OK] 训练配置:")
    print(f"  训练步数: {config.training.max_steps}")
    print(f"  批次大小: {config.training.batch_size}")
    print(f"  学习率:   {config.training.lr}")
    print(f"  梯度累积: {config.training.gradient_accumulation}")
    print(f"\n[OK] 训练记录将保存到: {trainer.log_dir}")


# ============================================================
# 子命令：Workflow 学习工作流
# ============================================================
def cmd_workflow(args):
    """Workflow 学习工作流管理"""
    if args.action == "start":
        result = db.create_learning_workflow(
            user_id=args.user_id or 1,
            workflow_id=args.workflow_id,
            workflow_name=args.name or "",
        )
        print(f"[OK] Workflow 已创建 #{result['id']}: workflow_id={args.workflow_id} {args.name or ''}")

    elif args.action == "submit":
        # 推进步骤
        wf = db.get_workflow(args.id)
        if not wf:
            print(f"[错误] Workflow #{args.id} 不存在")
            return
        current_step = wf.get("step", 0)
        next_step = current_step + 1
        ok = db.update_workflow_step(args.id, next_step)
        print(f"[OK] Workflow #{args.id} 步骤推进至 {next_step}: {ok}")

    elif args.action == "complete":
        result = db.complete_workflow(args.id, score=args.score or 100.0)
        print(f"[OK] Workflow #{args.id} 已标记完成: score={result['score']}")

    elif args.action == "list":
        workflows = db.get_user_workflows(user_id=args.user_id, status=args.status)
        if not workflows:
            print("暂无 Workflow 记录")
            return
        print(f"\n共 {len(workflows)} 条 Workflow:")
        for w in workflows:
            icon = {"active": "🔄", "completed": "✅", "paused": "⏸"}[w.get("status", "active")]
            print(f"  {icon} #{w['id']} | {w['workflow_id']} | {w.get('workflow_name','')} | "
                  f"步骤{w.get('step',0)} | score={w.get('score','')}")

    elif args.action == "status":
        wf = db.get_workflow(args.id)
        if not wf:
            print(f"[错误] Workflow #{args.id} 不存在")
            return
        print(f"\nWorkflow #{wf['id']}:")
        print(f"  workflow_id: {wf['workflow_id']}")
        print(f"  名称: {wf.get('workflow_name','')}")
        print(f"  用户ID: {wf['user_id']}")
        print(f"  状态: {wf.get('status','active')}")
        print(f"  步骤: {wf.get('step',0)}")
        print(f"  得分: {wf.get('score','N/A')}")
        print(f"  开始时间: {wf.get('started_at','')}")
        if wf.get('completed_at'):
            print(f"  完成时间: {wf['completed_at']}")


# ============================================================
# 子命令：管理员管理
# ============================================================
def cmd_admin(args):
    """管理员管理"""
    from framework.admin.auth import get_admin_auth
    from framework.admin.agents import get_agent_registry

    if args.action == "list":
        admins = db.get_admins()
        print(f"{'ID':<4} {'用户名':<12} {'角色':<12} {'最后登录':<20} 状态")
        for a in admins:
            print(f"{a['id']:<4} {a['username']:<12} {a['role']:<12} {(a['last_login_at'] or '-'):<20} {'启用' if a['is_active'] else '停用'}")
    elif args.action == "create":
        # 直接复用 get_admin_auth 的密码哈希逻辑
        from werkzeug.security import generate_password_hash
        db.add_admin(args.username, generate_password_hash(args.password),
                     display_name=args.name or args.username, role=args.role)
        print(f"[OK] 已创建管理员: {args.username} (role={args.role})")
    elif args.action == "reset-password":
        admin = db.get_admin_by_username(args.username)
        if not admin:
            print(f"[ERR] 管理员不存在: {args.username}")
            return
        from werkzeug.security import generate_password_hash
        db.update_admin_password(admin["id"], generate_password_hash(args.password))
        print(f"[OK] 已重置密码: {args.username}")
    elif args.action == "disable":
        admin = db.get_admin_by_username(args.username)
        if admin:
            db.set_admin_active(admin["id"], 0)
            print(f"[OK] 已停用: {args.username}")
    elif args.action == "agents":
        registry = get_agent_registry()
        for a in registry.list_agents():
            print(f"{a['agent_id']:<24} {a['name']:<16} {a['agent_type']:<10} {a['status']:<8} {'运行中' if a.get('running') else ''}")
    elif args.action == "agent-start":
        print(get_agent_registry().start(args.agent_id).get("message", ""))
    elif args.action == "agent-stop":
        print(get_agent_registry().stop(args.agent_id).get("message", ""))
    elif args.action == "logs":
        for log in db.get_system_logs(level=args.level, limit=args.limit):
            print(f"[{log['created_at']}] [{log['level']}] [{log['module']}] {log['message']}")
    else:
        print("未知操作")


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        prog="db_admin",
        description="LumiLearn 数据库管理工具",
    )
    parser.add_argument("--db", default=None, help="数据库文件路径")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init
    p_init = subparsers.add_parser("init", help="初始化数据库")
    p_init.add_argument("--db-path", default=None, help="自定义数据库路径")

    # user
    p_user = subparsers.add_parser("user", help="用户管理")
    p_user.add_argument("action", choices=["list", "add", "delete", "search"], help="操作")
    p_user.add_argument("--role", default="student", choices=["teacher", "student"], help="角色")
    p_user.add_argument("--name", help="用户名")
    p_user.add_argument("--id", type=int, help="用户ID")
    p_user.add_argument("--keyword", help="搜索关键词")

    # content
    p_content = subparsers.add_parser("content", help="教学内容管理")
    p_content.add_argument("action", choices=["list", "add", "publish", "count"])
    p_content.add_argument("--subject", help="学科")
    p_content.add_argument("--status", choices=["draft", "reviewed", "published"])
    p_content.add_argument("--difficulty", choices=["入门", "基础", "中等", "困难", "专家"])
    p_content.add_argument("--limit", type=int, default=20)
    p_content.add_argument("--title", help="标题")
    p_content.add_argument("--content", help="内容")
    p_content.add_argument("--chapter", help="章节")
    p_content.add_argument("--grade", default="高中")
    p_content.add_argument("--source", default="manual")
    p_content.add_argument("--submission-id", type=int, dest="submission_id")
    p_content.add_argument("--user-id", type=int, dest="user_id")

    # question
    p_question = subparsers.add_parser("question", help="题目管理")
    p_question.add_argument("action", choices=["list", "add", "delete"])
    p_question.add_argument("--subject", help="学科")
    p_question.add_argument("--difficulty", type=int, help="难度 1-3")
    p_question.add_argument("--limit", type=int, default=20)
    p_question.add_argument("--question", help="题目")
    p_question.add_argument("--answer", help="答案")
    p_question.add_argument("--topic", help="主题")
    p_question.add_argument("--explanation", help="解析")
    p_question.add_argument("--id", type=int, help="题目ID")

    # review
    p_review = subparsers.add_parser("review", help="待审核录入区")
    p_review.add_argument("action", choices=["list", "stats", "approve", "reject", "publish", "delete"])
    p_review.add_argument("--status", help="状态筛选")
    p_review.add_argument("--type", help="类型筛选 (content/question)")
    p_review.add_argument("--id", type=int, help="提交ID")
    p_review.add_argument("--reviewer", type=int, help="审核人ID")
    p_review.add_argument("--comment", help="审核意见")
    p_review.add_argument("--limit", type=int, default=50)

    # handwriting
    p_hw = subparsers.add_parser("handwriting", help="手写录入管理")
    p_hw.add_argument("action", choices=["list", "add", "update"])
    p_hw.add_argument("--user-id", type=int, help="用户ID")
    p_hw.add_argument("--image-path", dest="image_path", help="图片路径")
    p_hw.add_argument("--ocr-text", dest="ocr_text", help="OCR文本")
    p_hw.add_argument("--edited-text", dest="edited_text", help="校对文本")
    p_hw.add_argument("--device", help="录入设备")
    p_hw.add_argument("--note", help="备注")
    p_hw.add_argument("--limit", type=int, default=20)

    # stats
    p_stats = subparsers.add_parser("stats", help="学习统计")
    p_stats.add_argument("--user-id", type=int, dest="user_id", help="用户ID")
    p_stats.add_argument("--days", type=int, default=30)
    p_stats.add_argument("--min-errors", type=int, default=2)

    # export
    p_export = subparsers.add_parser("export", help="导出数据")
    p_export.add_argument("--format", choices=["jsonl", "answers"], default="jsonl")
    p_export.add_argument("--output", required=True, help="输出文件路径")
    p_export.add_argument("--user-id", type=int, dest="user_id")
    p_export.add_argument("--status", help="导出状态过滤")

    # train
    p_train = subparsers.add_parser("train", help="从数据库训练")
    p_train.add_argument("--preset", default="fast_test",
                         choices=["fast_test", "airllm_smoke", "airllm_1b", "scratch_medium"])
    p_train.add_argument("--status", default="published")

    # task
    p_task = subparsers.add_parser("task", help="任务管理")
    p_task.add_argument("action", choices=["list", "create", "delete", "stats"])
    p_task.add_argument("--user-id", type=int, dest="user_id")
    p_task.add_argument("--id", type=int, help="任务ID")
    p_task.add_argument("--subject", help="学科")
    p_task.add_argument("--status", help="状态 (draft/active/completed)")

    # thought
    p_thought = subparsers.add_parser("thought", help="学生思考记录")
    p_thought.add_argument("action", choices=["list", "add", "reply", "stats"])
    p_thought.add_argument("--user-id", type=int, dest="user_id")
    p_thought.add_argument("--type", default="question", choices=["question", "idea", "conclusion", "hint"])
    p_thought.add_argument("--question", help="问题文本")
    p_thought.add_argument("--idea", help="想法/假设")
    p_thought.add_argument("--conclusion", help="结论")
    p_thought.add_argument("--session-id", dest="session_id", help="会话ID")
    p_thought.add_argument("--task-id", type=int, dest="task_id")
    p_thought.add_argument("--knowledge", help="关联知识点")
    p_thought.add_argument("--effort", default="normal", choices=["low", "normal", "high"])
    p_thought.add_argument("--correct", default="neutral", choices=["wrong", "partial", "correct", "neutral"])
    p_thought.add_argument("--id", type=int, help="思考记录ID")
    p_thought.add_argument("--feedback", help="AI反馈")
    p_thought.add_argument("--followup", help="AI跟进问题")
    p_thought.add_argument("--limit", type=int, default=50)

    # ai_session
    p_ai = subparsers.add_parser("ai_session", help="AI学习会话")
    p_ai.add_argument("action", choices=["list", "start", "turn", "complete", "detail"])
    p_ai.add_argument("--user-id", type=int, dest="user_id")
    p_ai.add_argument("--topic", help="学习主题")
    p_ai.add_argument("--type", default="exploration", choices=["exploration", "practice", "quiz", "review"])
    p_ai.add_argument("--task-id", type=int, dest="task_id")
    p_ai.add_argument("--session-id", type=int, dest="session_id", help="会话ID (turn时)")
    p_ai.add_argument("--input-text", dest="input_text", help="学生输入")
    p_ai.add_argument("--response", help="AI响应")
    p_ai.add_argument("--model", default="qwen2.5:7b", help="模型")
    p_ai.add_argument("--duration", type=float, help="会话时长(秒)")
    p_ai.add_argument("--status", help="状态筛选")
    p_ai.add_argument("--limit", type=int, default=20)

    # concept
    p_concept = subparsers.add_parser("concept", help="概念理解跟踪")
    p_concept.add_argument("action", choices=["list", "update", "attempt", "progress", "difficult", "insights"])
    p_concept.add_argument("--user-id", type=int, dest="user_id")
    p_concept.add_argument("--node-id", dest="node_id", help="知识点ID")
    p_concept.add_argument("--understanding", type=float, help="理解度 0-1")
    p_concept.add_argument("--state", choices=["unknown", "learning", "mastered", "difficult"])
    p_concept.add_argument("--misconception", help="误解描述")
    p_concept.add_argument("--assessment", help="AI评估")
    p_concept.add_argument("--attempted", action="store_true", help="标记为已尝试")
    p_concept.add_argument("--correct", type=bool, nargs="?", const=True, help="是否正确")
    p_concept.add_argument("--time-spent", type=float, dest="time_spent", help="用时(秒)")
    p_concept.add_argument("--action", help="推荐动作")

    # workflow
    p_workflow = subparsers.add_parser("workflow", help="学习工作流管理")
    p_workflow.add_argument("action", choices=["start", "submit", "complete", "list", "status"])
    p_workflow.add_argument("--user-id", type=int, dest="user_id", help="用户ID")
    p_workflow.add_argument("--workflow-id", dest="workflow_id", help="工作流标识")
    p_workflow.add_argument("--name", help="工作流名称")
    p_workflow.add_argument("--id", type=int, help="工作流ID")
    p_workflow.add_argument("--score", type=float, help="完成得分")
    p_workflow.add_argument("--status", help="状态筛选")

    # admin
    p_admin = subparsers.add_parser("admin", help="管理员管理")
    p_admin.add_argument("action", choices=["list", "create", "reset-password", "disable", "agents", "agent-start", "agent-stop", "logs"])
    p_admin.add_argument("--username", default="")
    p_admin.add_argument("--password", default="")
    p_admin.add_argument("--name", default="")
    p_admin.add_argument("--role", default="super_admin", choices=["super_admin", "operator"])
    p_admin.add_argument("--agent-id", dest="agent_id", default="")
    p_admin.add_argument("--level", default=None)
    p_admin.add_argument("--limit", type=int, default=50)

    # teacher / student
    p_teacher = subparsers.add_parser("teacher", help="教师工作台")
    p_teacher.add_argument("--id", type=int, help="教师用户ID")

    p_student = subparsers.add_parser("student", help="学生工作台")
    p_student.add_argument("--id", type=int, help="学生用户ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 如果指定了 --db，设置数据库路径
    if args.db:
        db._db_path = args.db

    commands = {
        "init": cmd_init,
        "user": cmd_user,
        "content": cmd_content,
        "question": cmd_question,
        "review": cmd_review,
        "handwriting": cmd_handwriting,
        "task": cmd_task,
        "thought": cmd_thought,
        "ai_session": cmd_ai_session,
        "concept": cmd_concept,
        "stats": cmd_stats,
        "teacher": cmd_teacher,
        "student": cmd_student,
        "export": cmd_export,
        "train": cmd_train,
        "admin": cmd_admin,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


# ============================================================
# 子命令：学生思考记录
# ============================================================
def cmd_thought(args):
    """学生思考记录管理"""
    if args.action == "add":
        result = db.record_thought(
            user_id=args.user_id or 1,
            thought_type=args.type or "question",
            question=args.question or "",
            idea=args.idea or "",
            conclusion=args.conclusion or "",
            session_id=args.session_id or "",
            task_id=args.task_id or 0,
            related_knowledge=args.knowledge or "",
            effort_level=args.effort or "normal",
            correctness_hint=args.correct or "neutral",
        )
        print(f"[OK] 思考记录 #{result['id']} [{result['type']}]")

    elif args.action == "reply":
        ok = db.update_thought_ai_feedback(args.id, args.feedback or "", args.followup or "")
        print(f"[OK] AI反馈已更新: {ok}")

    elif args.action == "list":
        thoughts = db.get_thoughts(
            user_id=args.user_id,
            thought_type=args.type,
            limit=args.limit,
        )
        if not thoughts:
            print("暂无思考记录")
            return
        print(f"\n共 {len(thoughts)} 条思考记录:")
        for t in thoughts:
            content_map = {"question": t.get("question",""), "idea": t.get("idea",""),
                          "conclusion": t.get("conclusion",""), "hint": t.get("ai_feedback","") or t.get("question","")}
            content = content_map.get(t["thought_type"], t.get("question",""))
            icon = {"question": "❓", "idea": "💡", "conclusion": "✅", "hint": "💬"}[t["thought_type"]]
            print(f"  {icon} #{t['id']} [{t['thought_type']}] {content[:40]}...")
            print(f"      关联: knowledge={t.get('related_knowledge','')} question={t.get('related_question','')}")
            if t.get("ai_feedback"):
                print(f"      AI: {t['ai_feedback'][:50]}...")

    elif args.action == "stats":
        summary = db.get_thought_summary(args.user_id or 1)
        print(f"\n思考统计 (用户{summary['total']}条):")
        for r in summary["by_type"]:
            print(f"  {r['thought_type']}: {r['n']}条 (正确{r['correct_cnt']}, 错误{r['wrong_cnt']}, 部分{r['partial_cnt']})")


# ============================================================
# 子命令：AI学习会话
# ============================================================
def cmd_ai_session(args):
    """AI学习会话管理"""
    if args.action == "start":
        result = db.create_ai_session(
            user_id=args.user_id or 1,
            topic=args.topic or "",
            session_type=args.type or "exploration",
            task_id=args.task_id or 0,
        )
        print(f"[OK] AI会话 #{result['id']} 已创建: topic={args.topic or '未指定'}")

    elif args.action == "turn":
        result = db.record_ai_session_event(
            session_id=args.session_id,
            user_input=args.input_text or "",
            agent_response=args.response or "",
            agent_model=args.model or "qwen2.5:7b",
        )
        print(f"[OK] 对话轮次已记录: {result}")

    elif args.action == "complete":
        ok = db.complete_ai_session(args.id, time_spent=args.duration or 0)
        print(f"[OK] 会话 #{args.id} 已标记完成: {ok}")

    elif args.action == "list":
        sessions = db.get_ai_sessions(user_id=args.user_id, status=args.status, limit=args.limit)
        if not sessions:
            print("暂无AI学习会话")
            return
        print(f"\n共 {len(sessions)} 条AI会话:")
        for s in sessions:
            status_icon = {"active": "🔄", "completed": "✅", "paused": "⏸", "failed": "❌"}[s["status"]]
            print(f"  {status_icon} #{s['id']} | {s['topic'] or '无主题'} | {s['session_type']} | "
                  f"思考{s['total_thoughts']}次 | 用时{s['time_spent']:.0f}秒")
            print(f"      模型: {s['agent_model']} | 状态: {s['agent_status']}")

    elif args.action == "detail":
        sess = db.get_ai_session_detail(args.id)
        if sess:
            print(f"\n会话 #{sess['id']}:")
            print(f"  用户ID: {sess['user_id']} | 主题: {sess['topic']} | 类型: {sess['session_type']}")
            print(f"  状态: {sess['status']} | 思考: {sess['total_thoughts']}次 | "
                  f"正确: {sess['correct_count']} | 错误: {sess['wrong_count']}")
            print(f"  用时: {sess['time_spent']:.0f}秒")
            thoughts = db.get_ai_session_thoughts(args.id)
            print(f"  思考记录 ({len(thoughts)}条):")
            for t in thoughts:
                print(f"    {t['thought_type']}: {t.get('question','') or t.get('idea','') or t.get('conclusion','')[:40]}...")
        else:
            print(f"[错误] 会话 #{args.id} 不存在")


# ============================================================
# 子命令：概念理解
# ============================================================
def cmd_concept(args):
    """概念理解状态管理"""
    if args.action == "update":
        result = db.update_concept_understanding(
            user_id=args.user_id or 1,
            node_id=args.node_id or "",
            understanding=args.understanding or 0.0,
            state=args.state or "learning",
            misconception=args.misconception or "",
            ai_assessment=args.assessment or "",
            recommended_action=args.action or "",
        )
        print(f"[OK] 概念理解已更新: {result['node_id']} -> 理解度{result['understanding']:.2f} [{result['state']}]")

    elif args.action == "attempt":
        result = db.increment_concept_attempts(
            user_id=args.user_id or 1,
            node_id=args.node_id or "",
            is_correct=args.correct,
            time_spent=args.time_spent or 0,
        )
        icon = "✓" if args.correct else "✗"
        print(f"[OK] {icon} 尝试结果: {result['node_id']} -> 理解度{result['understanding']:.2f} [{result['state']}]")

    elif args.action == "progress":
        prog = db.get_concept_progress(user_id=args.user_id or 1)
        print(f"\n概念学习进度 (用户{prog['user_id']}):")
        print(f"  总节点: {prog['total_nodes']} | 已学: {prog['studied']} | "
              f"掌握: {prog['mastered']} | 学习中: {prog['learning']} | 困难: {prog['difficult']}")
        print(f"  整体进度: {prog['overall_progress']}%")
        for n in prog['nodes']:
            icon = "✅" if n['state'] == 'mastered' else ("⚠️" if n['state'] == 'difficult' else "📖")
            print(f"  {icon} {n['name']} | 理解度{n['understanding']:.2f} | 状态:{n['state']}")

    elif args.action == "difficult":
        diffs = db.get_difficult_concepts(user_id=args.user_id or 1)
        if not diffs:
            print("暂无困难知识点")
            return
        print(f"\n困难知识点 ({len(diffs)}个):")
        for d in diffs:
            print(f"  ⚠️ {d['node_id']} | 理解度{d['understanding']:.2f} | 尝试{d['attempts']}次")
            if d['misconception']:
                print(f"     误解: {d['misconception'][:60]}")

    elif args.action == "insights":
        insights = db.get_learning_insights(user_id=args.user_id or 1)
        print(f"\n学习洞察报告:")
        print(f"  总思考数: {insights['total_thoughts']}")
        print(f"  错误比例: {insights['wrong_ratio']:.0%}")
        print(f"  提示依赖: {insights['hint_dependency']:.0%}")
        print(f"  AI会话完成: {insights['ai_sessions_completed']}次")
        if insights['recommendations']:
            print(f"  推荐:")
            for r in insights['recommendations']:
                print(f"    → {r}")
        else:
            print(f"  暂无推荐（学习表现良好）")


# ============================================================
# 子命令：学生工作台
# ============================================================
def cmd_student(args):
    """学生工作台"""
    user_id = args.id or 1
    print(f"\n{'='*50}")
    print(f"  学生工作台 (user_id={user_id})")
    print(f"{'='*50}")

    # 任务列表
    tasks = db.get_user_tasks(user_id)
    if tasks:
        print(f"\n我的任务 ({len(tasks)}个):")
        for t in tasks:
            icon = "📋" if t['assignment_status'] == 'assigned' else ("✅" if t['assignment_status'] == 'completed' else "⏳")
            print(f"  {icon} #{t['id']} {t['title']} | {t['assignment_status']} | 得分:{t['score']}")
    else:
        print("暂无任务")

    # 学习进度
    stats = db.get_stats(user_id=user_id)
    print(f"\n学习统计:")
    print(f"  答题: {stats['total_answers']}题 (正确{stats['correct']}, 错误{stats['wrong']}, 正确率{stats['accuracy']}%)")
    print(f"  学习时长: {stats['total_time_minutes']}分钟")
    print(f"  会话数: {stats['total_sessions']}次")

    # 概念进度
    prog = db.get_concept_progress(user_id=user_id)
    print(f"\n知识掌握:")
    print(f"  进度: {prog['studied']}/{prog['total_nodes']} | 掌握: {prog['mastered']} | "
          f"学习中: {prog['learning']} | 困难: {prog['difficult']}")

    # 每日统计
    daily = db.get_daily_stats(user_id=user_id, days=7)
    if daily:
        total_time = sum(d['total_time'] for d in daily) / 60
        print(f"\n近7天: 日均学习{total_time/len(daily):.1f}分钟, 共{len(daily)}天")


# ============================================================
# 子命令：教师工作台
# ============================================================
def cmd_teacher(args):
    """教师工作台"""
    user_id = args.id or 1
    print(f"\n{'='*50}")
    print(f"  教师工作台 (user_id={user_id})")
    print(f"{'='*50}")

    # 待审核区
    pending = db.get_submissions(status="pending")
    print(f"\n待审核: {len(pending)}条")
    for s in pending:
        print(f"  #{s['id']} [{s['type']}] {s['title'] or s['question'][:20]} | 提交者:{s['submitted_by_name']}")

    # 任务列表
    tasks = db.get_tasks(limit=20)
    print(f"\n我的任务: {len(tasks)}个")
    for t in tasks:
        icon = "📝" if t['status'] == 'draft' else ("✅" if t['status'] == 'active' else "📦")
        print(f"  {icon} #{t['id']} {t['title']} | {t['status']} | 学科:{t['subject']}")

    # 学生列表
    students = db.get_users(role="student")
    print(f"\n学生: {len(students)}个")
    for s in students:
        task_stats = db.get_task_stats(s['id'])
        learning_stats = db.get_stats(user_id=s['id'])
        print(f"  {s['name']}: 完成{task_stats['completed_tasks']}任务, 正确率{learning_stats['accuracy']}%")

    # 提交统计
    sub_stats = db.get_submission_stats()
    print(f"提交统计: 待审{sub_stats.get('pending',0)}, 通过{sub_stats.get('approved',0)}, "
          f"拒绝{sub_stats.get('rejected',0)}, 已发布{sub_stats.get('published',0)}")


if __name__ == "__main__":
    main()
