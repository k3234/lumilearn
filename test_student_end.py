#!/usr/bin/env python3
"""学生端全流程测试：思考记录 + AI学习会话 + 概念理解"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util
spec = importlib.util.spec_from_file_location("lumilearn_db", "<project-root>/framework/database.py")
lumilearn_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lumilearn_db)
db = lumilearn_db.db

if os.path.exists("lumilearn.db"):
    os.remove("lumilearn.db")
db.init()
print("[OK] 数据库已初始化\n")

# 准备数据
teacher = db.add_user('张老师', role='teacher')
xiaoming = db.add_user('小明', role='student')
xiaohong = db.add_user('小红', role='student')

db.add_training_data(subject='数学', chapter='勾股定理', title='勾股定理',
                     content='直角三角形 a²+b²=c²', difficulty='基础', status='published')
db.add_question(subject='数学', topic='勾股定理', question='a=3,b=4,求c', correct_answer='5', difficulty=2)

task = db.create_task(title='勾股定理练习', subject='数学',
                      knowledge_ids=['pythagorean'], question_ids=[1],
                      task_type='exercise', difficulty='基础', created_by=teacher['id'])
db.assign_task(task['id'], xiaoming['id'])
db.assign_task(task['id'], xiaohong['id'])
print(f"[OK] 任务创建: #{task['id']}")

# ============================================================
print('\n=== 1. 学生思考记录 ===')
sid = db.start_session(user_id=xiaoming['id'], subject='数学')

th1 = db.record_thought(
    user_id=xiaoming['id'], session_id=sid, task_id=task['id'],
    thought_type='question',
    question='为什么是a²+b²=c²？能不能用面积理解？',
    related_knowledge='pythagorean', effort_level='high',
)
print(f"[OK] 小明提问: #{th1['id']}")

db.update_thought_ai_feedback(th1['id'],
    ai_feedback='想象一个边长为a的正方形面积是a²，边长为b的正方形面积是b²，拼在一起刚好填满斜边为c的大正方形',
    ai_follow_up='你能用面积法验证一下吗？')
print(f"[OK] AI回复已记录")

th2 = db.record_thought(
    user_id=xiaoming['id'], session_id=sid, task_id=task['id'],
    thought_type='idea', idea='a²=9, b²=16, 加起来25, 所以c²=25, c=5',
    related_question='1', correctness_hint='correct', effort_level='high',
)
print(f"[OK] 小明想法: #{th2['id']}")

th3 = db.record_thought(
    user_id=xiaoming['id'], session_id=sid, task_id=task['id'],
    thought_type='conclusion', conclusion='c=5', correctness_hint='correct',
)
print(f"[OK] 小明结论: #{th3['id']}")

summary = db.get_thought_summary(user_id=xiaoming['id'])
print(f"[OK] 思考摘要: 共{summary['total']}条")
for r in summary['by_type']:
    print(f"   {r['thought_type']}: {r['n']}条")

# ============================================================
print('\n=== 2. AI学习会话 ===')
ai_sess = db.create_ai_session(user_id=xiaoming['id'], topic='勾股定理', session_type='exploration')
print(f"[OK] AI会话创建: #{ai_sess['id']}")

db.record_ai_session_event(ai_sess['id'], '勾股定理是什么？',
    '直角三角形中a²+b²=c²，两条直角边的平方和等于斜边的平方', 'qwen2.5:7b')
print(f"[OK] AI对话轮次1")

db.record_ai_session_event(ai_sess['id'], '能举个例子吗？',
    '当然！a=3,b=4时c²=9+16=25，所以c=5', 'qwen2.5:7b')
print(f"[OK] AI对话轮次2")

db.record_ai_session_event(ai_sess['id'], '原来是这样！',
    '掌握了！这是勾股定理的基本应用', 'qwen2.5:7b')
db.complete_ai_session(ai_sess['id'], time_spent=180.0)
print(f"[OK] AI会话完成: 180秒")

sessions = db.get_ai_sessions(user_id=xiaoming['id'])
print(f"[OK] 小明的AI会话: {len(sessions)}条")
for s in sessions:
    print(f"  #{s['id']} {s['topic']} | 思考{s['total_thoughts']}次 | 用时{s['time_spent']:.0f}秒")

# ============================================================
print('\n=== 3. 概念理解跟踪 ===')
r = db.increment_concept_attempts(xiaoming['id'], 'pythagorean', is_correct=False, time_spent=60)
print(f"[OK] 尝试1(错): 理解度{r['understanding']:.2f} [{r['state']}]")

r = db.increment_concept_attempts(xiaoming['id'], 'pythagorean', is_correct=True, time_spent=45)
print(f"[OK] 尝试2(对): 理解度{r['understanding']:.2f} [{r['state']}]")

r = db.increment_concept_attempts(xiaoming['id'], 'pythagorean', is_correct=True, time_spent=30)
print(f"[OK] 尝试3(对): 理解度{r['understanding']:.2f} [{r['state']}]")

db.update_concept_understanding(
    user_id=xiaoming['id'], node_id='pythagorean',
    ai_assessment='已掌握勾股定理基本应用',
    recommended_action='挑战更复杂题目',
)
print(f"[OK] AI评估已更新")

prog = db.get_concept_progress(user_id=xiaoming['id'])
print(f"[OK] 概念进度: 已学{prog['studied']}/{prog['total_nodes']}, 掌握{prog['mastered']}, 进度{prog['overall_progress']}%")

insights = db.get_learning_insights(user_id=xiaoming['id'])
print(f"[OK] 学习洞察:")
print(f"  总思考: {insights['total_thoughts']} | 错误率:{insights['wrong_ratio']:.0%} | 提示依赖:{insights['hint_dependency']:.0%}")
for rec in insights['recommendations']:
    print(f"    -> {rec}")

# ============================================================
print('\n=== 4. 数据库总览 ===')
overview = db.get_stats_overview()
for k, v in overview.items():
    print(f"  {k}: {v}")

db.close()
print('\n' + '=' * 50)
print('STUDENT END-TO-END TEST PASSED')
print('=' * 50)
