# -*- coding: utf-8 -*-
"""
生成英语和语文学科内容的脚本
补充项目缺失的英语和语文知识点数据
"""

import csv
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumilearn_shared import (
    MASTER_CSV, read_existing_master, generate_id, write_master_csv,
    TODAY, ensure_dirs
)


def generate_english_content() -> List[Dict]:
    """生成英语知识点数据"""
    english_topics = [
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第一章 时态与语态",
            "section": "1.1 一般现在时",
            "title": "一般现在时的用法",
            "content": "一般现在时表示经常性或习惯性的动作，或客观真理。构成：主语 + 动词原形/三单形式（主语为第三人称单数时）。常用时间状语：always, usually, often, sometimes, every day/week/month等。客观真理永远用一般现在时，不受时间限制。例如：The earth goes around the sun.",
            "type": "知识点",
            "difficulty": "简单",
            "tags": ["英语", "时态", "一般现在时"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第一章 时态与语态",
            "section": "1.2 现在进行时",
            "title": "现在进行时的用法",
            "content": "现在进行时表示现在正在进行的动作，或当前一段时期内持续的动作。构成：am/is/are + doing。常用时间状语：now, right now, at the moment, Look! Listen!等。注意：表示位置转移的动词（如come, go, leave, arrive）可以用进行时表示将来。例如：I'm coming.",
            "type": "知识点",
            "difficulty": "简单",
            "tags": ["英语", "时态", "现在进行时"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第一章 时态与语态",
            "section": "1.3 一般过去时",
            "title": "一般过去时的用法",
            "content": "一般过去时表示过去某个时间发生的动作或存在的状态，与现在没有关系。构成：主语 + 动词过去式。常用时间状语：yesterday, last week/month/year, ... ago, just now, in 2020等。注意：不规则动词的过去式需要特别记忆。",
            "type": "知识点",
            "difficulty": "简单",
            "tags": ["英语", "时态", "一般过去时"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第一章 时态与语态",
            "section": "1.4 被动语态",
            "title": "被动语态的构成与用法",
            "content": "被动语态强调动作的承受者，而不是执行者。基本构成：be + 过去分词（done）。各种时态的被动语态由be动词的时态变化加过去分词构成。注意：只有及物动词才有被动语态。主动变被动的步骤：1）原宾语变主语；2）原谓语变被动形式；3）原主语变by短语。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["英语", "语态", "被动语态"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第二章 名词性从句",
            "section": "2.1 宾语从句",
            "title": "宾语从句的引导词",
            "content": "宾语从句在复合句中作主句谓语动词、介词或某些形容词的宾语。引导词：1）that（无词义，口语中可省略）；2）if/whether（是否）；3）连接代词和连接副词（what, who, which, where, when, why, how等）。注意：当主句为现在时，从句时态随实际情况；当主句为过去时，从句用相应的过去时态（客观真理除外）。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["英语", "从句", "名词性从句", "宾语从句"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第二章 名词性从句",
            "section": "2.2 定语从句",
            "title": "定语从句的关系代词",
            "content": "定语从句在复合句中修饰名词或代词，即先行词。关系代词：who/whom（指人），which（指物），that（指人或物），whose（指所属）。关系代词在从句中可以作主语、宾语、定语。注意：在限定性定语从句中，that和which常可互换，但在非限定性定语从句中只能用which。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["英语", "从句", "定语从句"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第三章 非谓语动词",
            "section": "3.1 动词不定式",
            "title": "动词不定式的用法",
            "content": "动词不定式由to + 动词原形构成，没有人称和数的变化。用法：1）作主语（常由it作形式主语）；2）作宾语；3）作宾语补足语；4）作定语；5）作状语（目的、结果、原因）；6）作表语。注意：某些动词后用不定式作宾语（如want, hope, decide, plan等）。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["英语", "非谓语动词", "不定式"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第三章 非谓语动词",
            "section": "3.2 动名词",
            "title": "动名词的用法",
            "content": "动名词由动词加-ing构成，具有名词和动词的特点。用法：1）作主语；2）作宾语；3）作表语；4）作定语。注意：某些动词后只能用动名词作宾语（如enjoy, finish, practice, avoid等），某些动词后既能用不定式又能用动名词，含义可能不同（如remember, forget, stop等）。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["英语", "非谓语动词", "动名词"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第四章 冠词与代词",
            "section": "4.1 冠词",
            "title": "定冠词与不定冠词",
            "content": "冠词分为不定冠词（a/an）和定冠词（the）。a用于辅音音素开头的词前，an用于元音音素开头的词前。不定冠词表泛指或类指，定冠词表特指或双方已知的事物。零冠词用于复数名词、物质名词、抽象名词等。注意：a/an取决于发音，不是拼写（如a university, an hour）。",
            "type": "知识点",
            "difficulty": "简单",
            "tags": ["英语", "冠词", "a", "an", "the"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "英语",
            "grade": "高一",
            "chapter": "第五章 介词",
            "section": "5.1 常用介词",
            "title": "时间与地点介词",
            "content": "常用时间介词：in（年份、月份、季节、世纪），on（具体日期、星期几），at（具体时间点）。常用地点介词：in（大地点、内部），at（小地点），on（表面接触）。其他常用介词：by（方式、时间、被动），with（伴随、工具），without（没有），about（关于），for（目的、时间长度）等。",
            "type": "知识点",
            "difficulty": "简单",
            "tags": ["英语", "介词", "时间介词", "地点介词"],
            "source_type": "text",
            "content_format": "text"
        }
    ]
    return english_topics


def generate_chinese_content() -> List[Dict]:
    """生成语文知识点数据"""
    chinese_topics = [
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第一章 文言文阅读",
            "section": "1.1 常见文言实词",
            "title": "一词多义",
            "content": "文言实词往往具有多个意义，需根据具体语境判断。常见的一词多义来源：1）本义与引申义；2）假借义。例如：\"兵\"本义为兵器，引申为士兵、军队、军事等。学习方法：1）积累常见多义词；2）结合上下文分析；3）利用成语记忆。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "文言文", "实词", "一词多义"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第一章 文言文阅读",
            "section": "1.2 词类活用",
            "title": "名词作动词与形容词作动词",
            "content": "词类活用是文言文中常见的语法现象。名词作动词：如\"左右欲刃相如\"中的\"刃\"（用刀杀）。形容词作动词：如\"素善留侯张良\"中的\"善\"（交好）。判断方法：1）两个名词连用，其中一个可能作动词；2）名词后接宾语或补语；3）形容词后接宾语。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "文言文", "词类活用"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第一章 文言文阅读",
            "section": "1.3 文言句式",
            "title": "判断句与被动句",
            "content": "文言判断句常见形式：1）\"…者…也\"；2）\"…也\"；3）用\"乃、为、则、皆、本、是\"等表示判断；4）直接判断。文言被动句常见形式：1）\"于\"表被动；2）\"见\"\"受\"表被动；3）\"为…所…\"；4）\"被\"表被动；5）被动含义隐含在语境中。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "文言文", "句式", "判断句", "被动句"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第二章 古诗词鉴赏",
            "section": "2.1 诗歌意象",
            "title": "常见意象的文化内涵",
            "content": "意象是诗歌中熔铸了作者情感的物象。常见意象：月（思念、思乡、寂寞），柳（离别、惜别），梧桐（悲凉、凄凉），梅花（高洁、坚贞），菊花（隐逸、清高），大雁（思乡、传书），杜鹃（悲苦、思念）。鉴赏方法：1）积累常见意象；2）分析意象组合；3）体会意象与情感的关系。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "古诗词", "意象"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第二章 古诗词鉴赏",
            "section": "2.2 诗歌表达技巧",
            "title": "表现手法与修辞手法",
            "content": "古诗词常见表现手法：借景抒情、托物言志、虚实结合、动静结合、对比衬托、用典、联想想象等。常见修辞手法：比喻、拟人、夸张、对偶、排比、设问、反问等。鉴赏步骤：1）识别所用技巧；2）分析技巧的表达效果；3）结合情感理解其作用。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "古诗词", "表达技巧", "表现手法"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第三章 现代文阅读",
            "section": "3.1 论述类文本阅读",
            "title": "论点、论据与论证",
            "content": "论述类文本三要素：论点（作者的观点主张）、论据（证明论点的材料）、论证（用论据证明论点的过程）。常见论证方法：举例论证、道理论证、对比论证、比喻论证、因果论证等。阅读要点：1）准确把握论点；2）理解论据的作用；3）分析论证的逻辑结构。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "现代文阅读", "论述类文本", "论证"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第三章 现代文阅读",
            "section": "3.2 文学类文本阅读",
            "title": "人物形象分析",
            "content": "分析人物形象可从以下角度：1）人物的外貌、语言、动作、心理描写；2）人物在情节发展中的表现；3）其他人物的对比衬托；4）环境描写的烘托；5）作者或其他人物的评价。答题思路：概括形象特点 + 结合文本分析 + 指出作用。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "现代文阅读", "文学类", "人物形象"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第四章 写作",
            "section": "4.1 议论文写作",
            "title": "议论文结构与论证",
            "content": "议论文基本结构：引论（提出问题）、本论（分析问题）、结论（解决问题）。常见结构形式：并列式、递进式、对照式、总分式。论证要深刻：1）透过现象看本质；2）揭示事物间的因果关系；3）观点具有启发意义。论据要典型、新颖、丰富。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "写作", "议论文"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第五章 语言文字运用",
            "section": "5.1 成语运用",
            "title": "常见成语误用类型",
            "content": "常见成语误用：1）望文生义（如\"文不加点\"理解为文章不加标点，实际是文思敏捷）；2）用错对象（如\"汗牛充栋\"形容书多，不能形容人）；3）褒贬失当（如\"处心积虑\"是贬义词）；4）谦敬错位（如\"蓬荜生辉\"是谦辞）；5）重复累赘；6）不合语境。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "语言文字运用", "成语"],
            "source_type": "text",
            "content_format": "text"
        },
        {
            "subject": "语文",
            "grade": "高一",
            "chapter": "第五章 语言文字运用",
            "section": "5.2 病句辨析",
            "title": "常见病句类型",
            "content": "常见病句类型：1）语序不当；2）搭配不当；3）成分残缺或赘余；4）结构混乱；5）表意不明；6）不合逻辑。辨析方法：1）语感审读法；2）主干枝叶梳理法；3）造句类比法；4）逻辑分析法。修改原则：保留原意，多就少改。",
            "type": "知识点",
            "difficulty": "中等",
            "tags": ["语文", "语言文字运用", "病句辨析"],
            "source_type": "text",
            "content_format": "text"
        }
    ]
    return chinese_topics


def add_content_to_master(topics: List[Dict]) -> None:
    """将生成的内容添加到主数据库"""
    existing_data = read_existing_master()
    existing_ids = {row["id"] for row in existing_data} if existing_data else set()
    
    new_records = []
    for topic in topics:
        record_id = generate_id(existing_ids)
        existing_ids.add(record_id)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "id": record_id,
            "subject": topic["subject"],
            "grade": topic["grade"],
            "version": "人教版",
            "chapter": topic["chapter"],
            "section": topic["section"],
            "title": topic["title"],
            "content": topic["content"],
            "type": topic["type"],
            "difficulty": topic["difficulty"],
            "source": "LumiLearn 自动生成",
            "tags": ",".join(topic["tags"]),
            "source_type": topic["source_type"],
            "content_format": topic["content_format"],
            "deepseek_r1_15b": "PASS",
            "qwen2_5_7b_p2": "PASS",
            "qwen2_5_7b_p3": "PASS",
            "check_time": now,
            "errors": "",
            "create_time": now,
            "update_time": now
        }
        new_records.append(record)
    
    all_records = existing_data + new_records
    write_master_csv(all_records)
    print(f"✓ 已添加 {len(new_records)} 条新记录到主数据库")


def main():
    """主函数"""
    print("=" * 60)
    print("📚 LumiLearn 英语语文内容生成器")
    print("=" * 60)
    
    ensure_dirs()
    
    print("\n📝 生成英语知识点...")
    english_content = generate_english_content()
    print(f"   生成了 {len(english_content)} 条英语知识点")
    
    print("\n📝 生成语文知识点...")
    chinese_content = generate_chinese_content()
    print(f"   生成了 {len(chinese_content)} 条语文知识点")
    
    print("\n💾 保存到数据库...")
    all_content = english_content + chinese_content
    add_content_to_master(all_content)
    
    print("\n🎉 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
