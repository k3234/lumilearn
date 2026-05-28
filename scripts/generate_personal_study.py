#!/usr/bin/env python3
"""
LumiLearn - 个人学习内容生成器
专为语文和英语提分设计
"""

import os
import sys
import csv
import random
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumilearn_config import CFG

def call_ollama(model, prompt, timeout=60):
    """调用 Ollama 本地模型"""
    try:
        import requests
        response = requests.post(
            f"{CFG['ollama_host']}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "top_p": 0.9}
            },
            timeout=timeout
        )
        if response.status_code == 200:
            return response.json()["response"]
    except Exception as e:
        print(f"  Ollama 调用失败: {e}")
    return None

def generate_english_reading_comprehension():
    """生成英语阅读理解练习（针对英语 42 分的提升）"""
    print("\n" + "="*60)
    print("📚 生成英语阅读理解练习")
    print("="*60)
    
    topics = [
        "学校生活", "环境保护", "科技发展", "家庭故事",
        "历史事件", "名人介绍", "健康生活", "旅行经历"
    ]
    
    topic = random.choice(topics)
    
    prompt = f"""请为高中英语水平设计一篇阅读理解练习，包含以下内容：

主题：{topic}

格式要求：
1. 一篇约 200-300 词的英语短文
2. 5 道阅读理解选择题（每题 4 个选项）
3. 答案解析（为什么某个选项正确，其他错误）
4. 重点词汇表（文中出现的 10 个重点词汇，带中文解释）

请用英语短文 + 中文解析的形式返回。"""

    content = call_ollama("qwen2.5:7b", prompt, timeout=90)
    
    if content:
        print("\n" + content)
        
        # 保存到文件
        filename = f"english_reading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✅ 已保存到: {filename}")
        
        return content
    else:
        print("❌ 生成失败")
        return None

def generate_chinese_classical_text():
    """生成语文文言文阅读理解"""
    print("\n" + "="*60)
    print("📖 生成语文文言文阅读理解")
    print("="*60)
    
    texts = [
        "论语选段", "孟子选段", "史记选段", "战国策选段",
        "唐宋八大家散文", "明代小品文", "清代笔记"
    ]
    
    text_type = random.choice(texts)
    
    prompt = f"""请为高中语文设计一篇文言文阅读理解练习，包含以下内容：

文本类型：{text_type}

格式要求：
1. 一篇约 100-200 字的文言文（难度适中）
2. 3 道题目：
   - 1 题：解释文中 2-3 个重点字词
   - 1 题：翻译文中 1-2 句话
   - 1 题：阅读理解选择题或简答题
3. 全文翻译
4. 答案解析

请用文言文 + 中文解析的形式返回。"""

    content = call_ollama("qwen2.5:7b", prompt, timeout=90)
    
    if content:
        print("\n" + content)
        
        # 保存到文件
        filename = f"chinese_classical_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✅ 已保存到: {filename}")
        
        return content
    else:
        print("❌ 生成失败")
        return None

def generate_english_vocabulary_list():
    """生成英语词汇表（针对高频词汇）"""
    print("\n" + "="*60)
    print("📝 生成英语高频词汇表")
    print("="*60)
    
    categories = [
        "高频动词（50个）", "高频名词（50个）", "高频形容词（30个）",
        "高频副词（20个）", "高频介词（20个）", "高频短语（30个）"
    ]
    
    category = random.choice(categories)
    
    prompt = f"""请生成高中英语{category}，要求：

1. 每个词汇包含：
   - 单词拼写
   - 音标
   - 中文释义（1-3个常用义）
   - 一个例句（英语 + 中文翻译）
2. 按字母顺序排列
3. 共生成 30 个词汇

请用清晰的表格或列表格式返回。"""

    content = call_ollama("qwen2.5:7b", prompt, timeout=120)
    
    if content:
        print("\n" + content)
        
        # 保存到文件
        filename = f"english_vocabulary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✅ 已保存到: {filename}")
        
        return content
    else:
        print("❌ 生成失败")
        return None

def show_menu():
    """显示菜单"""
    print("\n" + "="*60)
    print("   🎓 LumiLearn - 个人学习内容生成器")
    print("="*60)
    print("请选择要生成的内容：")
    print("  1. 英语阅读理解练习")
    print("  2. 语文文言文阅读理解")
    print("  3. 英语高频词汇表")
    print("  0. 退出")
    print("="*60)

def main():
    while True:
        show_menu()
        
        try:
            choice = input("\n请输入选项 (0-3): ").strip()
            
            if choice == "0":
                print("\n👋 再见！加油学习！")
                break
            elif choice == "1":
                generate_english_reading_comprehension()
            elif choice == "2":
                generate_chinese_classical_text()
            elif choice == "3":
                generate_english_vocabulary_list()
            else:
                print("❌ 无效选项，请重新输入")
            
            # 询问是否继续
            input("\n按 Enter 继续...")
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()
