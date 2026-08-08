#!/usr/bin/env python3
"""手写识别流程测试"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib.util
spec = importlib.util.spec_from_file_location("database", "framework/database.py")
db_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_module)
db = db_module.db

print("=" * 70)
print("  手写识别流程测试")
print("=" * 70)

db_path = "test_handwriting.db"
if os.path.exists(db_path):
    os.remove(db_path)
db.init(db_path)
print("\n[OK] 数据库初始化完成")

teacher = db.add_user("测试老师", role="teacher")
student = db.add_user("测试学生", role="student")
print(f"[OK] 用户创建: 老师#{teacher['id']}, 学生#{student['id']}")

print("\n【1】模拟手写输入")
handwriting_samples = [
    {"ocr_text": "a²+b²=c²", "ocr_confidence": 0.95},
    {"ocr_text": "F=ma", "ocr_confidence": 0.88},
    {"ocr_text": "H₂O", "ocr_confidence": 0.92},
]

for sample in handwriting_samples:
    record = db.add_handwriting(
        user_id=student['id'],
        ocr_text=sample['ocr_text'],
        ocr_confidence=sample['ocr_confidence'],
        edited_text=sample['ocr_text'],
    )
    print(f"   [OK] 识别 '{sample['ocr_text']}' → 置信度 {sample['ocr_confidence']}")

records = db.get_handwriting_list(user_id=student['id'])
print(f"\n[OK] 手写记录: {len(records)} 条")

print("\n【2】分析学习模式")
insights = db.get_learning_insights(user_id=student['id'])
print(f"   总思考: {insights['total_thoughts']}")
print(f"   错误率: {insights['wrong_ratio']:.0%}")
print(f"   提示依赖: {insights['hint_dependency']:.0%}")

db.close()
os.remove(db_path)
print("\n[OK] 测试数据库已清理")
print("\n🎉 手写识别流程测试通过")
