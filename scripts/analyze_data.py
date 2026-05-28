# -*- coding: utf-8 -*-
"""
数据分析和状态报告生成脚本
分析LumiLearn项目数据情况，生成详细报告
"""

import csv
import json
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumilearn_shared import (
    MASTER_CSV, read_existing_master, ANIMATION_OUTPUT_DIR,
    FLASHCARDS_CSV, LEARNING_SESSIONS_CSV
)


def analyze_master_data() -> dict:
    """分析主数据库数据"""
    data = read_existing_master()
    if not data:
        return {"error": "No data found"}
    
    subject_count = Counter(row["subject"] for row in data)
    grade_count = Counter(row["grade"] for row in data)
    difficulty_count = Counter(row["difficulty"] for row in data)
    type_count = Counter(row["type"] for row in data)
    
    # 按学科统计章节
    subjects_chapters = defaultdict(set)
    for row in data:
        if row["subject"] and row["chapter"]:
            subjects_chapters[row["subject"]].add(row["chapter"])
    
    return {
        "total_records": len(data),
        "subject_distribution": dict(subject_count),
        "grade_distribution": dict(grade_count),
        "difficulty_distribution": dict(difficulty_count),
        "type_distribution": dict(type_count),
        "subject_chapters": {k: list(v) for k, v in subjects_chapters.items()}
    }


def analyze_other_data() -> dict:
    """分析其他数据文件"""
    results = {}
    
    # 动画文件
    if os.path.exists(ANIMATION_OUTPUT_DIR):
        anim_files = [f for f in os.listdir(ANIMATION_OUTPUT_DIR) 
                     if f.endswith('.py')]
        results["animation_count"] = len(anim_files)
        results["animation_files"] = anim_files[:10]  # 前10个
    
    # 记忆卡片
    if os.path.exists(FLASHCARDS_CSV):
        try:
            with open(FLASHCARDS_CSV, 'r', encoding='utf-8') as f:
                cards = list(csv.DictReader(f))
                results["flashcard_count"] = len(cards)
        except:
            results["flashcard_count"] = 0
    
    # 学习会话
    if os.path.exists(LEARNING_SESSIONS_CSV):
        try:
            with open(LEARNING_SESSIONS_CSV, 'r', encoding='utf-8') as f:
                sessions = list(csv.DictReader(f))
                results["session_count"] = len(sessions)
        except:
            results["session_count"] = 0
    
    return results


def generate_html_report(analysis: dict, other_data: dict) -> str:
    """生成HTML格式的报告"""
    
    subject_html = ""
    for subject, count in analysis.get("subject_distribution", {}).items():
        subject_html += f"<tr><td>{subject}</td><td>{count}</td></tr>"
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>LumiLearn 项目状态报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .summary-box {{ background-color: #e8f4fc; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .good {{ color: #27ae60; font-weight: bold; }}
        .warning {{ color: #f39c12; font-weight: bold; }}
        .danger {{ color: #e74c3c; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 LumiLearn 项目状态报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary-box">
            <h2>📈 总体情况</h2>
            <p><strong>知识点总数:</strong> {analysis.get('total_records', 0)}</p>
            <p><strong>动画数量:</strong> {other_data.get('animation_count', 0)}</p>
            <p><strong>记忆卡片:</strong> {other_data.get('flashcard_count', 0)}</p>
            <p><strong>学习会话:</strong> {other_data.get('session_count', 0)}</p>
        </div>
        
        <h2>📚 学科分布</h2>
        <table>
            <tr><th>学科</th><th>记录数</th></tr>
            {subject_html}
        </table>
        
        <h2>📊 难度分布</h2>
        <table>
            <tr><th>难度</th><th>数量</th></tr>
            {''.join([f'<tr><td>{d}</td><td>{c}</td></tr>' for d, c in analysis.get('difficulty_distribution', {}).items()])}
        </table>
        
        <h2>📋 类型分布</h2>
        <table>
            <tr><th>类型</th><th>数量</th></tr>
            {''.join([f'<tr><td>{t}</td><td>{c}</td></tr>' for t, c in analysis.get('type_distribution', {}).items()])}
        </table>
        
        <h2>💡 建议</h2>
        <ul>
            <li>继续补充英语、语文学科内容</li>
            <li>增加化学、物理学科的覆盖面</li>
            <li>完善测试用例和文档</li>
            <li>优化模型训练过程，避免过拟合</li>
        </ul>
    </div>
</body>
</html>
    """
    return html


def main():
    """主函数"""
    print("=" * 60)
    print("📊 LumiLearn 数据分析")
    print("=" * 60)
    
    print("\n📝 分析主数据库...")
    analysis = analyze_master_data()
    
    print(f"   总记录数: {analysis.get('total_records', 0)}")
    print(f"   学科分布: {analysis.get('subject_distribution', {})}")
    
    print("\n📝 分析其他数据...")
    other_data = analyze_other_data()
    
    # 生成HTML报告
    print("\n📄 生成HTML报告...")
    html_report = generate_html_report(analysis, other_data)
    
    report_file = "project_status_report.html"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html_report)
    
    print(f"   ✓ 报告已保存到: {report_file}")
    
    # 保存JSON数据
    json_data = {
        "generated_at": datetime.now().isoformat(),
        "master_data": analysis,
        "other_data": other_data
    }
    with open("project_status.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print("\n🎉 分析完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
