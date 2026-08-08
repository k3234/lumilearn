#!/usr/bin/env python3
"""
模拟手写录入 + 待审核流程的完整 Mock 数据脚本

流程：
  1. 创建用户（1 教师 + 3 学生）
  2. 学生手写录入（每人 2-3 条）→ 自动提交到待审核区
  3. 教师查看待审核列表
  4. 教师审核（通过部分，拒绝部分）
  5. 发布通过的内容到正式表
  6. 打印全流程状态变化

运行：
  python mock_handwriting_flow.py
"""
import sys, os, json, random, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework.database import db

# 删除旧数据库重建
db_path = os.path.join(os.path.dirname(__file__), "lumilearn.db")
if os.path.exists(db_path):
    os.remove(db_path)


def banner(msg):
    print(f'\n{"="*60}')
    print(f'  {msg}')
    print(f'{"="*60}')


def section(msg):
    print(f'\n--- {msg} ---')


# ============================================================
# Step 1: 初始化数据库 + 创建用户
# ============================================================
banner('Step 1: 初始化数据库 + 创建用户')
db.init()
print(f'[OK] 数据库已初始化: {db.db_path}')

# 创建教师
teacher = db.add_user('张老师', role='teacher')
print(f'[OK] 教师: {teacher["name"]} (id={teacher["id"]})')

# 创建学生
students = [
    db.add_user('小明', role='student'),
    db.add_user('小红', role='student'),
    db.add_user('小刚', role='student'),
]
for s in students:
    print(f'[OK] 学生: {s["name"]} (id={s["id"]})')

# ============================================================
# Step 2: 模拟手写录入数据
# ============================================================
banner('Step 2: 学生手写录入 → 自动提交到待审核区')

# Mock 手写录入数据集
MOCK_HANDWRITING = [
    # 学生1: 小明
    {
        'user': students[0],
        'image_path': 'data/handwriting/xiaoming_pythagorean.png',
        'strokes': [
            [{'x': 10, 'y': 20}, {'x': 15, 'y': 22}, {'x': 20, 'y': 25}],
            [{'x': 30, 'y': 20}, {'x': 35, 'y': 22}],
            [{'x': 50, 'y': 30}, {'x': 55, 'y': 32}, {'x': 60, 'y': 35}],
        ],
        'ocr_text': '勾股定理：直角三角形中 a2+b2=c2',
        'ocr_confidence': 0.94,
        'ocr_details': [
            {'text': '勾股定理', 'confidence': 0.96, 'box': [[10,20],[50,20],[50,40],[10,40]]},
            {'text': '直角三角形中', 'confidence': 0.93, 'box': [[10,45],[80,45],[80,65],[10,65]]},
            {'text': 'a2+b2=c2', 'confidence': 0.93, 'box': [[10,70],[70,70],[70,90],[10,90]]},
        ],
        'edited_text': '勾股定理：在直角三角形中，两条直角边的平方和等于斜边的平方，即 a²+b²=c²。',
        'device': 'iPad',
        'note': '课堂练习：勾股定理',
        'subject': '数学',
        'chapter': '勾股定理',
        'title': '勾股定理的内容',
        'content_type': '概念定义',
        'difficulty': '基础',
        'grade': '初二',
        'keywords': '勾股定理,直角三角形,毕达哥拉斯',
    },
    {
        'user': students[0],
        'image_path': 'data/handwriting/xiaoming_free_fall.png',
        'strokes': [
            [{'x': 5, 'y': 10}, {'x': 10, 'y': 12}, {'x': 15, 'y': 15}],
            [{'x': 25, 'y': 10}, {'x': 30, 'y': 12}],
        ],
        'ocr_text': '自由落体运动：物体只在重力作用下从静止开始下落的运动',
        'ocr_confidence': 0.91,
        'ocr_details': [
            {'text': '自由落体运动', 'confidence': 0.92, 'box': [[5,10],[60,10],[60,30],[5,30]]},
            {'text': '物体只在重力作用下从静止开始下落', 'confidence': 0.90, 'box': [[5,35],[120,35],[120,55],[5,55]]},
        ],
        'edited_text': '自由落体运动：物体只在重力作用下从静止开始下落的运动。是初速度为零的匀加速直线运动。',
        'device': 'iPad',
        'note': '物理课笔记',
        'subject': '物理',
        'chapter': '匀变速直线运动',
        'title': '自由落体运动',
        'content_type': '概念定义',
        'difficulty': '中等',
        'grade': '高一',
        'keywords': '自由落体,匀加速运动,重力',
    },
    # 学生2: 小红
    {
        'user': students[1],
        'image_path': 'data/handwriting/xiaohong_quadratic.png',
        'strokes': [
            [{'x': 8, 'y': 15}, {'x': 12, 'y': 18}, {'x': 16, 'y': 21}],
            [{'x': 28, 'y': 15}, {'x': 32, 'y': 18}],
        ],
        'ocr_text': '二次函数：y=ax2+bx+c (a≠0)',
        'ocr_confidence': 0.96,
        'ocr_details': [
            {'text': '二次函数', 'confidence': 0.97, 'box': [[8,15],[48,15],[48,35],[8,35]]},
            {'text': 'y=ax2+bx+c (a≠0)', 'confidence': 0.95, 'box': [[8,40],[80,40],[80,60],[8,60]]},
        ],
        'edited_text': '二次函数：形如 y=ax²+bx+c（a≠0）的函数。图像是抛物线，开口方向由 a 的正负决定。',
        'device': 'Android手写板',
        'note': '数学作业：二次函数',
        'subject': '数学',
        'chapter': '二次函数',
        'title': '二次函数的定义',
        'content_type': '概念定义',
        'difficulty': '中等',
        'grade': '初三',
        'keywords': '二次函数,抛物线,图像',
    },
    {
        'user': students[1],
        'image_path': 'data/handwriting/xiaohong_ohm.png',
        'strokes': [
            [{'x': 6, 'y': 12}, {'x': 10, 'y': 14}],
            [{'x': 20, 'y': 12}, {'x': 24, 'y': 14}, {'x': 28, 'y': 16}],
        ],
        'ocr_text': '欧姆定律：I=U/R 电流与电压成正比',
        'ocr_confidence': 0.89,
        'ocr_details': [
            {'text': '欧姆定律', 'confidence': 0.91, 'box': [[6,12],[46,12],[46,32],[6,32]]},
            {'text': 'I=U/R', 'confidence': 0.88, 'box': [[6,37],[40,37],[40,57],[6,57]]},
            {'text': '电流与电压成正比', 'confidence': 0.88, 'box': [[6,62],[80,62],[80,82],[6,82]]},
        ],
        'edited_text': '',
        'device': 'Android手写板',
        'note': '物理课：电学基础',
        'subject': '物理',
        'chapter': '恒定电流',
        'title': '欧姆定律',
        'content_type': '公式推导',
        'difficulty': '中等',
        'grade': '高二',
        'keywords': '欧姆定律,电流,电压,电阻',
    },
    # 学生3: 小刚
    {
        'user': students[2],
        'image_path': 'data/handwriting/xiaogang_mean.png',
        'strokes': [
            [{'x': 12, 'y': 25}, {'x': 16, 'y': 27}],
            [{'x': 35, 'y': 25}, {'x': 39, 'y': 27}, {'x': 43, 'y': 29}],
        ],
        'ocr_text': '平均数：一组数据的总和除以个数',
        'ocr_confidence': 0.97,
        'ocr_details': [
            {'text': '平均数', 'confidence': 0.98, 'box': [[12,25],[52,25],[52,45],[12,45]]},
            {'text': '一组数据的总和除以个数', 'confidence': 0.96, 'box': [[12,50],[100,50],[100,70],[12,70]]},
        ],
        'edited_text': '平均数：一组数据的总和除以数据的个数。公式：x̄ = (x₁+x₂+...+xₙ)/n',
        'device': 'Windows触屏',
        'note': '复习统计基础',
        'subject': '数学',
        'chapter': '统计初步',
        'title': '平均数的定义',
        'content_type': '概念定义',
        'difficulty': '基础',
        'grade': '初一',
        'keywords': '平均数,统计,数据',
    },
    {
        'user': students[2],
        'image_path': 'data/handwriting/xiaogang_buoyancy.png',
        'strokes': [
            [{'x': 7, 'y': 14}, {'x': 11, 'y': 16}],
            [{'x': 22, 'y': 14}, {'x': 26, 'y': 16}, {'x': 30, 'y': 18}],
        ],
        'ocr_text': '阿基米德原理：浮力等于排开液体的重力 F浮=ρ液gV排',
        'ocr_confidence': 0.87,
        'ocr_details': [
            {'text': '阿基米德原理', 'confidence': 0.89, 'box': [[7,14],[60,14],[60,34],[7,34]]},
            {'text': '浮力等于排开液体的重力', 'confidence': 0.86, 'box': [[7,39],[90,39],[90,59],[7,59]]},
            {'text': 'F浮=ρ液gV排', 'confidence': 0.86, 'box': [[7,64],[60,64],[60,84],[7,84]]},
        ],
        'edited_text': '阿基米德原理：浸在液体中的物体受到向上的浮力，浮力的大小等于它排开的液体所受的重力。公式：F浮=ρ液gV排',
        'device': 'Windows触屏',
        'note': '物理：浮力',
        'subject': '物理',
        'chapter': '浮力',
        'title': '阿基米德原理',
        'content_type': '公式推导',
        'difficulty': '困难',
        'grade': '初二',
        'keywords': '阿基米德原理,浮力,液体,排开',
    },
]


# 执行手写录入（每个学生提交）
submission_ids = []
for data in MOCK_HANDWRITING:
    result = db.submit_handwriting(
        user_id=data['user']['id'],
        image_path=data['image_path'],
        strokes=data['strokes'],
        ocr_text=data['ocr_text'],
        ocr_confidence=data['ocr_confidence'],
        ocr_details=data['ocr_details'],
        edited_text=data['edited_text'],
        device=data['device'],
        note=data['note'],
        subject=data['subject'],
        chapter=data['chapter'],
        title=data['title'],
        content_type=data['content_type'],
        difficulty=data['difficulty'],
        grade=data['grade'],
        keywords=data['keywords'],
        submitted_by_name=data['user']['name'],
    )
    submission_ids.append(result['submission_id'])
    print(f'  [录入] {data["user"]["name"]}: {data["title"]} '
          f'(OCR置信度:{data["ocr_confidence"]:.0%}, '
          f'提交#{result["submission_id"]})')


# ============================================================
# Step 3: 查看待审核列表
# ============================================================
banner('Step 3: 教师查看待审核列表')
stats = db.get_submission_stats()
section(f'审核区统计: 待审{stats.get("pending",0)}条, 通过{stats.get("approved",0)}条, 拒绝{stats.get("rejected",0)}条')

pending = db.get_submissions(status='pending')
for s in pending:
    print(f'  #{s["id"]} | {s["submitted_by_name"]} | '
          f'{s["subject"]}-{s["chapter"]} | {s["title"]} | '
          f'来源:{s["source"]}')


# ============================================================
# Step 4: 教师审核
# ============================================================
banner('Step 4: 教师审核')

# 审核决策（模拟教师判断）
REVIEW_DECISIONS = {
    1: (True, '内容准确，OCR 识别正确，通过'),
    2: (True, '自由落体定义清晰，通过'),
    3: (True, '二次函数定义完整，通过'),
    4: (False, '欧姆定律公式缺少上下文，建议补充导体电阻的定义后重新提交'),
    5: (True, '平均数定义简洁准确，通过'),
    6: (True, '阿基米德原理表述正确，公式完整，通过'),
}

for sub_id, (approved, comment) in REVIEW_DECISIONS.items():
    result = db.review_submission(
        submission_id=sub_id,
        approved=approved,
        reviewer_id=teacher['id'],
        review_comment=comment,
    )
    status_icon = '✓' if approved else '✗'
    print(f'  {status_icon} #{sub_id} {result["status"]}: {comment}')


# ============================================================
# Step 5: 查看审核后状态
# ============================================================
banner('Step 5: 审核后状态')
stats = db.get_submission_stats()
section(f'审核区统计: 待审{stats.get("pending",0)}条, 通过{stats.get("approved",0)}条, 拒绝{stats.get("rejected",0)}条')

section('已通过')
for s in db.get_submissions(status='approved'):
    print(f'  #{s["id"]} | {s["submitted_by_name"]} | {s["title"]}')

section('已拒绝')
for s in db.get_submissions(status='rejected'):
    print(f'  #{s["id"]} | {s["submitted_by_name"]} | {s["title"]}')
    print(f'         审核意见: {s["review_comment"]}')


# ============================================================
# Step 6: 发布通过的内容到正式表
# ============================================================
banner('Step 6: 发布通过的内容到正式教学内容表')

approved_ids = [s['id'] for s in db.get_submissions(status='approved')]
for sub_id in approved_ids:
    pub = db.publish_submission(sub_id)
    sub = db.get_submission(sub_id)
    if pub.get('published'):
        print(f'  ✓ #{sub_id} "{sub["title"]}" → {pub["target_table"]} #{pub["record_id"]}')
    else:
        print(f'  ✗ #{sub_id} 发布失败: {pub.get("error")}')


# ============================================================
# Step 7: 验证正式表数据
# ============================================================
banner('Step 7: 验证正式教学内容表')

published_subs = db.get_submissions(status='published')
print(f'\n已发布提交数: {len(published_subs)}')

training_data = db.get_training_data(status='published', limit=100)
print(f'\n正式教学内容数: {len(training_data)}')
for td in training_data:
    print(f'  #{td["id"]} | {td["subject"]} | {td["chapter"]} | {td["title"]}')
    print(f'         来源:{td["source"]} | 难度:{td["difficulty"]} | 年级:{td["grade"]}')
    print(f'         内容: {td["content"][:50]}...')


# ============================================================
# Step 8: 手写记录查询
# ============================================================
banner('Step 8: 手写记录查询')

hw_list = db.get_handwriting_list()
print(f'\n手写记录总数: {len(hw_list)}')
for hw in hw_list:
    print(f'  手写#{hw["id"]} | {hw["user_id"]} | {hw["image_path"]}')
    print(f'         OCR: {hw["ocr_text"][:30]}... '
          f'(置信度:{hw["ocr_confidence"]:.0%})')
    if hw['edited_text']:
        print(f'         校对: {hw["edited_text"][:30]}...')
    print(f'         笔画: {len(hw["strokes"])}笔 | 设备: {hw["device"]} | '
          f'提交: #{hw["submission_id"]}')


# ============================================================
# Step 9: 数据库总览
# ============================================================
banner('Step 9: 数据库总览')
overview = db.get_stats_overview()
for k, v in overview.items():
    print(f'  {k}: {v}')

db.close()
print(f'\n[完成] 数据库文件: {db_path}')
