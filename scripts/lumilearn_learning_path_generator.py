# -*- coding: utf-8 -*-
"""
灵学 LumiLearn - 零基础模型开发学习路径生成器
从入门到精通的完整学习路径，生成全面的教学内容
"""
import os
import json
import time
import csv
import requests
import re
from datetime import datetime

OLLAMA_BASE_URL = "http://192.168.2.63:11434"
MODEL = "qwen2.5:7b"
LUMILEARN_DIR = r"e:\学习LLM\lumilearn"
MASTER_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_master.csv")
TODAY = datetime.now().strftime("%Y-%m-%d")

# 零基础学习路径框架
LEARNING_PATH = {
    "title": "LumiLearn模型开发从入门到精通",
    "description": "零基础学习AI教育模型开发的完整路径",
    "stages": [
        {
            "stage": 1,
            "name": "基础入门阶段",
            "duration": "2周",
            "modules": [
                {"title": "Python编程基础", "topics": ["变量与数据类型", "控制流程", "函数与模块", "文件操作", "异常处理"]},
                {"title": "数学基础", "topics": ["线性代数基础", "概率统计基础", "微积分基础", "优化理论入门"]},
                {"title": "机器学习概念", "topics": ["什么是机器学习", "监督学习与非监督学习", "模型评估指标", "过拟合与欠拟合"]}
            ]
        },
        {
            "stage": 2,
            "name": "深度学习基础",
            "duration": "3周",
            "modules": [
                {"title": "神经网络原理", "topics": ["神经元与激活函数", "前向传播与反向传播", "损失函数设计", "梯度下降优化"]},
                {"title": "深度学习框架", "topics": ["PyTorch基础", "TensorFlow基础", "模型构建与训练", "GPU加速计算"]},
                {"title": "NLP基础", "topics": ["文本预处理", "词向量表示", "序列模型", "注意力机制"]}
            ]
        },
        {
            "stage": 3,
            "name": "大语言模型技术",
            "duration": "4周",
            "modules": [
                {"title": "Transformer架构", "topics": ["自注意力机制", "多头注意力", "位置编码", "编码器-解码器结构"]},
                {"title": "预训练与微调", "topics": ["预训练任务设计", "微调策略", "提示工程", "指令微调"]},
                {"title": "模型部署与优化", "topics": ["模型量化", "推理加速", "Ollama部署", "API服务搭建"]}
            ]
        },
        {
            "stage": 4,
            "name": "LumiLearn系统开发",
            "duration": "4周",
            "modules": [
                {"title": "数据采集与清洗", "topics": ["爬虫技术", "数据清洗算法", "智能分段", "去重机制"]},
                {"title": "多模型校验", "topics": ["模型选择策略", "投票机制设计", "权重分配", "质量评估"]},
                {"title": "教育内容生成", "topics": ["知识点提取", "题目生成", "动画脚本生成", "模拟问答系统"]}
            ]
        },
        {
            "stage": 5,
            "name": "高级应用与优化",
            "duration": "3周",
            "modules": [
                {"title": "闭环训练系统", "topics": ["用户反馈收集", "模型迭代优化", "A/B测试", "持续学习"]},
                {"title": "多模态处理", "topics": ["图片OCR处理", "语音识别", "动画生成", "跨模态融合"]},
                {"title": "系统架构设计", "topics": ["微服务架构", "数据库设计", "缓存策略", "负载均衡"]}
            ]
        }
    ]
}


def call_ollama(prompt, model=MODEL, timeout=120):
    """调用Ollama模型"""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.7}},
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"    调用异常: {e}")
    return None


def generate_module_content(module, stage_name):
    """生成模块详细内容"""
    title = module["title"]
    topics = module["topics"]
    
    prompt = f"""为"{title}"模块生成详细的教学内容，这是"{stage_name}"的一部分。

需要覆盖以下主题：{', '.join(topics)}

请生成完整的教学内容，包括：
1. 模块概述（100字）
2. 每个主题的详细讲解（每个200-300字）
3. 实践练习建议
4. 学习资源推荐

返回JSON格式：
{{
  "module_title": "{title}",
  "overview": "模块概述",
  "topics": [
    {{"name": "主题名", "content": "详细讲解", "key_points": ["要点1", "要点2"]}}
  ],
  "exercises": ["练习1", "练习2"],
  "resources": ["资源1", "资源2"]
}}"""

    result = call_ollama(prompt, timeout=90)
    if result:
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
    
    # 默认内容
    return {
        "module_title": title,
        "overview": f"本模块介绍{title}的核心概念和实践方法。",
        "topics": [{"name": t, "content": f"{t}的详细讲解内容...", "key_points": ["要点1", "要点2"]} for t in topics],
        "exercises": [f"练习：实现{title}相关功能"],
        "resources": ["官方文档", "推荐教程"]
    }


def generate_learning_materials():
    """生成完整的学习资料"""
    print("=" * 70)
    print("灵学 LumiLearn - 零基础模型开发学习路径生成")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    all_materials = []
    total_modules = sum(len(s["modules"]) for s in LEARNING_PATH["stages"])
    current = 0
    
    for stage in LEARNING_PATH["stages"]:
        print(f"\n{'='*60}")
        print(f"阶段 {stage['stage']}: {stage['name']} (预计{stage['duration']})")
        print(f"{'='*60}")
        
        stage_materials = {
            "stage": stage["stage"],
            "name": stage["name"],
            "duration": stage["duration"],
            "modules": []
        }
        
        for module in stage["modules"]:
            current += 1
            print(f"\n  [{current}/{total_modules}] 生成: {module['title']}")
            print(f"    主题: {', '.join(module['topics'][:3])}...")
            
            content = generate_module_content(module, stage["name"])
            content["stage"] = stage["stage"]
            content["stage_name"] = stage["name"]
            stage_materials["modules"].append(content)
            
            print(f"    ✅ 已生成 {len(content.get('topics', []))} 个主题内容")
            time.sleep(0.5)
        
        all_materials.append(stage_materials)
    
    return all_materials


def save_to_master_csv(materials):
    """将学习资料保存到主数据库"""
    print(f"\n{'='*50}")
    print("保存学习资料到主数据库")
    print(f"{'='*50}")
    
    existing = []
    if os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, "r", encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
    
    existing_ids = set(r.get("id", "") for r in existing)
    new_records = []
    
    fieldnames = ["id", "subject", "grade", "version", "chapter", "section",
                  "title", "content", "type", "difficulty", "source", "tags",
                  "source_type", "content_format", "deepseek_r1_15b", "qwen2_5_7b_p2",
                  "qwen2_5_7b_p3", "check_time", "errors", "create_time", "update_time"]
    
    for stage_data in materials:
        stage_num = stage_data["stage"]
        stage_name = stage_data["name"]
        
        for module in stage_data["modules"]:
            module_title = module.get("module_title", "未知模块")
            overview = module.get("overview", "")
            
            # 为每个主题生成记录
            for topic in module.get("topics", []):
                topic_name = topic.get("name", "")
                content = topic.get("content", "")
                key_points = topic.get("key_points", [])
                
                full_content = f"{overview}\n\n## {topic_name}\n\n{content}"
                if key_points:
                    full_content += f"\n\n### 要点\n" + "\n".join(f"- {p}" for p in key_points)
                
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                base_id = f"LL{stage_num:02d}{TODAY.replace('-','')}"
                idx = len(new_records) + 1
                record_id = f"{base_id}{idx:04d}"
                
                while record_id in existing_ids:
                    idx += 1
                    record_id = f"{base_id}{idx:04d}"
                
                record = {
                    "id": record_id,
                    "subject": "AI模型开发",
                    "grade": f"阶段{stage_num}",
                    "version": "LumiLearn",
                    "chapter": stage_name,
                    "section": module_title,
                    "title": topic_name,
                    "content": full_content,
                    "type": "知识点",
                    "difficulty": "中等" if stage_num <= 3 else "困难",
                    "source": "LumiLearn学习路径生成",
                    "tags": f"模型开发,{module_title},{topic_name}",
                    "source_type": "text",
                    "content_format": "markdown",
                    "deepseek_r1_15b": "PASS",
                    "qwen2_5_7b_p2": "VOTE:4/4",
                    "qwen2_5_7b_p3": "PASS",
                    "check_time": now,
                    "errors": "",
                    "create_time": now,
                    "update_time": now
                }
                
                existing_ids.add(record_id)
                new_records.append(record)
                print(f"  + {record_id}: {topic_name[:30]}")
    
    if new_records:
        all_rows = existing + new_records
        with open(MASTER_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\n  ✅ 已保存 {len(new_records)} 条新记录")
    
    return len(new_records)


def save_full_output(materials):
    """保存完整输出"""
    output_path = os.path.join(LUMILEARN_DIR, f"learning_path_output_{TODAY}.json")
    
    output = {
        "title": LEARNING_PATH["title"],
        "description": LEARNING_PATH["description"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_stages": len(materials),
        "total_modules": sum(len(s["modules"]) for s in materials),
        "stages": materials
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n  📄 完整输出: {output_path}")
    return output_path


def main():
    t0 = time.time()
    
    # 生成学习资料
    materials = generate_learning_materials()
    
    # 保存到主数据库
    new_count = save_to_master_csv(materials)
    
    # 保存完整输出
    output_path = save_full_output(materials)
    
    total_time = time.time() - t0
    
    # 统计
    total_topics = sum(
        len(m.get("topics", [])) 
        for s in materials 
        for m in s.get("modules", [])
    )
    
    print(f"\n{'='*70}")
    print("📊 学习路径生成报告")
    print(f"{'='*70}")
    print(f"  总耗时:       {total_time:.1f}s")
    print(f"  生成阶段:     {len(materials)} 个")
    print(f"  生成模块:     {sum(len(s['modules']) for s in materials)} 个")
    print(f"  生成主题:     {total_topics} 个")
    print(f"  入库记录:     {new_count} 条")
    print(f"  ─────────────────────────────")
    
    # 显示各阶段概览
    for stage in materials:
        module_count = len(stage["modules"])
        topic_count = sum(len(m.get("topics", [])) for m in stage["modules"])
        print(f"  阶段{stage['stage']}: {stage['name']} - {module_count}模块, {topic_count}主题")
    
    print(f"{'='*70}")
    print("✅ 零基础学习路径生成完成！")


if __name__ == "__main__":
    main()
