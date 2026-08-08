"""
LumiLearn 智能混合回复引擎
- LumiLearn 模型作为第一层尝试
- 教育知识库精确匹配
- 规则引擎兜底
- 乱码检测自动切换
- 费曼教学模式：不直接给答案，引导式教学
"""

import os as _os
import re
import random
import json
import requests
from typing import Optional, Tuple

# ============================================================
# 乱码检测（基于常用字频率）
# ============================================================

# 中文最常用的 500 个字符（按频率排列）
TOP500_COMMON_CHARS = set(
    "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十"
    "三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全"
    "表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料"
    "象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则"
    "任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花"
    "带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越"
    "织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往历酸克市何除消构府称太准精值号率族"
    "维划选标写存候毛亲快效斯院查江型眼王按格养置层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严首底液官德随病苏失讲配"
    "黄推显谈罪神艺呢席含企望密批营项防举球英氧势告李台落木帮轮破亚师围注远字材排供河态封另施减树溶怎止案言士均武固叶鱼波视仅费紧爱"
    "左章早朝害续轻服试食充兵源判护司足练差致板田降黑犯负击范继兴似余坚曲输修故城夫够送笔船占右财吃富春职觉汉画功巴跟虽杂飞检吸助"
    "升阳互初创抗考投坏策古径换未跑留钢曾端责站简述钱副尽帝射草冲承独令限阿宣环双请超微让控州良轴找否纪益依优顶础载倒房突坐粉敌略"
    "客袁冷胜绝析块剂测丝协诉念陈仍罗盐友洋错苦夜刑移频逐靠混母短皮终聚汽村云哪既距卫停烈央察烧迅境若印洲刻括激孔搞甚室待核校散侵"
    "吧甲游久菜味旧模湖货损预阻毫普稳乙妈植息扩银语挥酒守拿序纸医缺雨吗针刘啊急唱误训愿审附获茶鲜粮斤孩脱硫肥善龙演父渐血欢械掌歌"
    "沙刚攻谓盾讨晚粒乱燃矛乎杀药宁鲁贵钟煤读班伯香介迫句丰培握兰担弦蛋沉假穿执答乐准顺")

def is_gibberish(text: str) -> bool:
    """检测文本是否为乱码（基于常用字频率）"""
    if not text or len(text) < 2:
        return True

    # 提取汉字
    chinese_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']

    if len(chinese_chars) < 3:
        return False

    # 计算常用字比例
    common_count = sum(1 for c in chinese_chars if c in TOP500_COMMON_CHARS)
    common_ratio = common_count / len(chinese_chars)

    # 检查是否包含常见中文词
    common_words = ["的", "是", "在", "有", "我", "你", "他", "不", "了", "人",
                    "一", "这", "中", "大", "来", "上", "学", "习", "好", "会",
                    "可", "以", "要", "就", "能", "对", "知", "道", "什", "么",
                    "怎", "样", "为", "因", "和", "与", "但", "问", "答", "说",
                    "看", "做", "去", "还", "把", "被", "从", "到", "给", "让",
                    "很", "都", "也", "只", "太", "最", "更", "非", "常", "多",
                    "几", "百", "千", "万", "两", "个", "种", "些", "次", "回",
                    "今", "明", "昨", "年", "月", "日", "时", "分", "秒", "天",
                    "小", "加", "减", "乘", "除", "等", "于", "数", "字", "语",
                    "英", "数", "算", "计", "公", "式", "定", "理", "高", "体",
                    "长", "宽", "面", "积", "周", "边", "角", "点", "线", "圆",
                    "方", "三", "四", "五", "六", "七", "八", "九", "十", "百",
                    "应", "用", "问", "题", "解", "答", "法", "步", "思", "想"]
    found_words = sum(1 for w in common_words if w in text)

    # 判定规则
    if common_ratio < 0.25:
        return True
    if common_ratio < 0.4 and found_words < 2:
        return True
    if len(chinese_chars) >= 6 and found_words == 0 and common_ratio < 0.6:
        return True
    if found_words == 0 and common_ratio < 0.5:
        return True

    return False


# ============================================================
# 教育知识库
# ============================================================

EDUCATION_KB = {
    # === 数学 ===
    "加法": {
        "keywords": ["加法", "相加", "加", "1+1", "2+2", "3+3", "几加几"],
        "reply": "加法就是合并数字～比如 28+15，先个位 8+5=13 进1，再十位 2+1+1=4，结果 43！加法是数学最基础的运算哦 📐"
    },
    "减法": {
        "keywords": ["减法", "相减", "减", "5-3", "10-几"],
        "reply": "减法就是拿走的概念～比如 52-28，个位2不够减，向十位借1，12-8=4；十位4-2=2，答案24！借位法多练习就熟了 🧮"
    },
    "乘法": {
        "keywords": ["乘法", "相乘", "乘", "乘以", "×", "九九"],
        "reply": "乘法是重复加法～比如 7×8，可以背九九乘法表：七八五十六！也可以用 7×4=28 再加 7×4=28，得 56。日常多背就熟了 ✨"
    },
    "除法": {
        "keywords": ["除法", "除以", "除", "÷", "平均"],
        "reply": "除法是平均分配～比如 126÷3，12÷3=4，6÷3=2，答案42！被除数÷除数=商，要注意余数哦 🔢"
    },
    "三角形面积": {
        "keywords": ["三角形面积", "三角形", "面积"],
        "reply": "三角形面积 = 底 × 高 ÷ 2！比如底4cm、高3cm的三角形，面积 = 4×3÷2 = 6平方厘米。本质是把三角形看成半个长方形～ 📐"
    },
    "长方形面积": {
        "keywords": ["长方形面积", "长方形", "面积"],
        "reply": "长方形面积 = 长 × 宽！比如长5米、宽3米的长方形，面积 = 5×3 = 15平方米。最简单最好记的面积公式 ✨"
    },
    "圆的面积": {
        "keywords": ["圆的面积", "圆形", "圆面积"],
        "reply": "圆的面积 = π × 半径²！比如半径2cm的圆，面积 ≈ 3.14×4 = 12.56平方厘米。记π约等于3.14就好～ ⭕"
    },
    "分数运算": {
        "keywords": ["分数", "几分", "分之"],
        "reply": "分数就是部分除以整体～比如 3/4 + 1/2，先通分，1/2变成2/4，然后 3/4+2/4=5/4=1又1/4。记住：加减先通分，乘法分子乘分子分母乘分母！"
    },
    "方程": {
        "keywords": ["方程", "解方程", "未知数", "x="],
        "reply": "方程就是含有未知数的等式～比如 x+5=12，两边同时减5，x=7。核心思想：等式两边做同样的运算，保持平衡！⚖️"
    },
    "质数": {
        "keywords": ["质数", "素数", "因数"],
        "reply": "质数是只能被1和它本身整除的数，比如2、3、5、7、11、13、17、19...记住：2是最小的质数，也是唯一的偶质数！🔢"
    },
    "概念解释": {
        "keywords": ["是什么", "什么意思", "定义", "概念"],
        "reply": "理解概念最好的方法是用自己的话解释它，再举个生活中的例子～比如「力」：就是推或拉的作用，像推门就是施加力。把抽象变具体就懂了！💡"
    },

    # === 英语 ===
    "英语翻译": {
        "keywords": ["英语怎么说", "翻译", "英文", "英语"],
        "reply": "学英语小技巧：1️⃣ 先理解中文意思 2️⃣ 找对应的英文句式 3️⃣ 常用短语多背诵。比如「谢谢」= Thank you，「不客气」= You're welcome。每天记5个新词就很好！🇬🇧"
    },
    "英语语法": {
        "keywords": ["语法", "时态", "过去式", "现在式", "将来"],
        "reply": "英语语法记住三个核心：1️⃣ 时态（过去/现在/将来）2️⃣ 主谓一致（主语和动词搭配）3️⃣ 词序（主+谓+宾）。比如 I go (现在) → I went (过去) → I will go (将来)！"
    },

    # === 语文 ===
    "作文写作": {
        "keywords": ["作文", "写作", "怎么写", "写文章", "句子"],
        "reply": "写作文三步法：1️⃣ 开头点题吸引人（用一个好故事或问题开头）2️⃣ 中间展开举例（至少2-3个具体例子）3️⃣ 结尾总结升华（回到主题，表达感悟）。多读多练自然写得好！✍️"
    },
    "阅读理解": {
        "keywords": ["阅读", "理解", "读不懂", "课文"],
        "reply": "阅读理解四步走：1️⃣ 先看题目知道问什么 2️⃣ 通读全文抓大意 3️⃣ 精读关键段落找答案 4️⃣ 用自己的话复述一遍。坚持用这个方法，理解力提升很快！📖"
    },

    # === 学习方法 ===
    "学习计划": {
        "keywords": ["学习计划", "计划", "安排", "时间"],
        "reply": "制定学习计划的黄金法则：📅 每天固定时间（如早7点30分钟复习）📝 分科目轮换（数学→英语→语文轮换）⏰ 用番茄钟25分钟专注+5分钟休息 📊 每周总结错题整理。坚持21天形成习惯！"
    },
    "记不住": {
        "keywords": ["记不住", "忘记", "记忆力", "背不"],
        "reply": "提高记忆力四大法宝：1️⃣ 间隔复习（当天→第二天→一周后→一月后）2️⃣ 联想记忆（把新知识和已知的东西联系）3️⃣ 画思维导图（用图帮助记忆）4️⃣ 讲给别人听（最好的学习方法就是教别人！）🧠"
    },
    "考试技巧": {
        "keywords": ["考试", "怎么考", "做题", "复习"],
        "reply": "考试技巧分享：📝 先做会做的题，难题标记后做 🕐 合理分配时间，不要在一题上卡太久 ✅ 做完要检查，尤其是计算题 💪 考前一天早睡，保持好状态！"
    },
    "学习动力": {
        "keywords": ["不想学", "没动力", "累", "懒", "懈怠"],
        "reply": "学习没动力时试试这些：1️⃣ 设定小目标（今天搞定3道题就奖励自己）2️⃣ 换个学习方式（看视频比看书有趣）3️⃣ 找学习伙伴互相督促 4️⃣ 想象学成后的成就感！你已经很棒了，坚持就是胜利 💪✨"
    },

    # === 科学 ===
    "科学常识": {
        "keywords": ["为什么天是蓝色", "为什么水", "科学", "实验"],
        "reply": "科学就在身边！天空蓝色是因为阳光穿过大气时蓝色光被散射得最多。科学学习的关键是：观察 → 提问 → 假设 → 验证 → 结论。多动手做实验，知识记得最牢！🔬"
    },

    # === 学习资源 ===
    "资源推荐": {
        "keywords": ["推荐", "资源", "什么书", "资料", "App"],
        "reply": "推荐学习资源：📱 数学用作业帮、猿题库 📖 英语用百词斩、每日英语听力 📚 语文多看名著、用喜马拉雅听书 🎬 B站有很多免费的教学视频。选择适合自己的最重要！"
    },
}

# 通用回复模板
GENERAL_REPLIES = [
    "这个问题问得好！可以具体说说哪里不太明白吗？我来帮你分析～",
    "让我想想怎么用最简单的方式解释给你听...先从基础说起",
    "学习上遇到问题是好事！说明你在思考，我来帮你梳理一下",
    "这个问题不简单哦！我们一步一步来分析",
    "好的！这个知识点其实很重要，我来用生活中的例子解释",
]

GREETING_REPLIES = [
    "你好呀！我是小澍，AI学习规划师！有什么问题随时问～",
    "欢迎来到直播间！🌿 我是小澍，今天陪你学习～",
    "大家好！有任何学习问题都可以打在公屏上，我来解答！",
]

THANKS_REPLIES = [
    "不客气！有问题随时问哦～🌿",
    "很高兴能帮到你！继续加油学习！",
    "谢谢支持！你认真学习的样子最棒了～",
]

# ============================================================
# "反着教"引导式回复（不给答案，只给思路）
# ============================================================

GUIDED_QUESTION_STARTERS = {
    "math": [
        "🤔 好问题！在解题之前，先想想：题目给了什么条件？你要找的是什么？",
        "💡 这个问题不急着给答案。你先说说看，你觉得第一步应该做什么？",
        "📐 先别算！先告诉我，这道题可以用哪个公式？为什么选这个？",
        "🔍 看到这道题，你最先想到的方法是什么？先说说你的思路",
    ],
    "english": [
        "🇬🇧 试着先翻译一下这句话的意思？你认识哪些单词？",
        "📖 先不查答案。你试着读一遍，能理解大概意思吗？",
        "✍️ 先自己试着写一下，写了再来对答案",
    ],
    "chinese": [
        "✍️ 写作文之前，先列出你要写的几个要点。你先列一下？",
        "📚 你读这段文字，试着用自己的话概括一下讲了什么？",
    ],
    "science": [
        "🔬 先别查答案。你观察到了什么现象？先描述一下",
        "🧪 你觉得可能是什么原因？先猜一下，再验证",
    ],
    "general": [
        "🤔 这个问题问得好。你先说说你已经知道的部分？",
        "💡 我不直接告诉你答案。但可以给你提示：从哪里开始想？",
        "先自己试着分析一下，然后我帮你检查思路对不对",
    ],
}

FOLLOWUP_HINTS = {
    "面积": [
        "提示：面积公式里的底和高，必须是垂直的！",
        "再想想：这个图形可以看成什么基本图形的组合？",
        "检查一下单位：厘米还是米？平方厘米还是平方米？",
    ],
    "方程": [
        "提示：移项的时候注意变号！",
        "左边有什么，右边有什么？试试把含未知数的移到同一边",
    ],
    "分数": [
        "提示：分母不同怎么办？对，先通分！",
        "分子分母约分了吗？结果要最简形式",
    ],
    "乘法": [
        "提示：可以用九九乘法表，也可以拆开算",
        "试试：把大数拆成两个熟悉的小数来乘",
    ],
    "计算": [
        "提示：先看运算顺序！有括号先算括号里的",
        "再检查一遍：进位/借位有没有漏掉？",
    ],
}

ANSWER_CHECK_TEMPLATES = {
    "correct": [
        "🎉 完全正确！你是怎么想到这个方法的？说说你的思路！",
        "✅ 答对了！能给我讲讲你的解题过程吗？",
        "💪 厉害！这道题你用了什么方法？分享给大家听听",
    ],
    "close": [
        "🤏 很接近了！再检查一下最后一步的计算",
        "思路对了，但答案差一点点。看看有没有算错的地方？",
        "方向正确！但中间好像有个小失误，再算一遍？",
    ],
    "wrong": [
        "🤔 这个答案不对。不过没关系，我们一起分析下哪里出了问题",
        "❌ 不对哦。不过失败是学习的一部分！先想想公式用对了吗？",
        "💡 答案是错的，但没关系。你先说说你是怎么想的，我帮你找问题",
    ],
}


def get_guided_question(question: str, subject: str = "general") -> str:
    """根据问题生成引导式提问（不直接给答案）"""
    import random

    starters = GUIDED_QUESTION_STARTERS.get(subject, GUIDED_QUESTION_STARTERS["general"])
    starter = random.choice(starters)

    hints = []
    for keyword, hint_list in FOLLOWUP_HINTS.items():
        if keyword in question:
            hints.append(random.choice(hint_list))

    if hints:
        return f"{starter}\n\n{random.choice(hints)}"
    return starter


def check_user_answer(user_answer: str, correct_answer: str,
                      question: str = "") -> dict:
    """
    验证用户答案，返回引导反馈
    不给直接的"对/错"，而是引导思考
    """
    import random

    user = user_answer.strip().lower().replace(" ", "")
    correct = correct_answer.strip().lower().replace(" ", "")

    if user == correct:
        return {
            "status": "correct",
            "message": random.choice(ANSWER_CHECK_TEMPLATES["correct"]),
            "next": "next_challenge",
        }

    if "×" in question or "*" in question or "x" in user.lower():
        user_num = "".join(c for c in user if c.isdigit() or c == "-")
        correct_num = "".join(c for c in correct if c.isdigit() or c == "-")
        try:
            if abs(int(user_num) - int(correct_num)) <= max(1, int(correct_num) * 0.1):
                return {
                    "status": "close",
                    "message": random.choice(ANSWER_CHECK_TEMPLATES["close"]),
                    "next": "hint",
                }
        except (ValueError, ZeroDivisionError):
            pass

    return {
        "status": "wrong",
        "message": random.choice(ANSWER_CHECK_TEMPLATES["wrong"]),
        "next": "hint",
    }


def search_knowledge_base(question: str) -> Optional[str]:
    """在知识库中搜索匹配"""
    q_lower = question.lower()
    best_match = None
    best_score = 0

    for topic, entry in EDUCATION_KB.items():
        score = 0
        for kw in entry["keywords"]:
            if kw.lower() in q_lower:
                score += len(kw)
        if score > best_score:
            best_score = score
            best_match = topic

    if best_match and best_score >= 2:
        return EDUCATION_KB[best_match]["reply"]
    return None


def classify_question(question: str) -> str:
    """分类问题类型"""
    q = question.lower()

    if any(k in q for k in ["你好", "在吗", "hello", "hi", "老师好", "来了"]):
        return "greeting"
    if any(k in q for k in ["谢谢", "好棒", "厉害", "加油", "支持", "👍", "赞"]):
        return "thanks"

    # 先检查具体科目（优先级高于通用词）
    if any(k in q for k in ["物理", "化学", "科学", "实验", "元素", "分子"]):
        return "science"
    if any(k in q for k in ["英语", "英文", "语法", "翻译", "单词"]):
        return "english"
    if any(k in q for k in ["语文", "作文", "阅读", "写作", "文章"]):
        return "chinese"
    if any(k in q for k in ["数学", "计算", "面积", "公式", "方程", "质数", "几何",
                             "代数", "+", "×", "几分"]):
        return "math"
    if any(k in q for k in ["计划", "记忆", "学习", "复习", "怎么学", "记不住", "考试"]):
        return "study_method"
    if any(k in q for k in ["题", "算", "解", "-", "÷"]):
        return "math"
    return "general"


def get_intelligent_reply(question: str) -> str:
    """智能回复核心函数"""

    # 1. 知识库精确匹配
    kb_result = search_knowledge_base(question)
    if kb_result:
        return kb_result

    # 2. 分类后给针对性回复
    qtype = classify_question(question)

    if qtype == "greeting":
        return random.choice(GREETING_REPLIES)
    elif qtype == "thanks":
        return random.choice(THANKS_REPLIES)
    elif qtype == "math":
        return ("数学问题我来帮你！记住：理解概念比死记公式更重要。"
                "先审题找已知条件，再想用什么方法。需要我讲解哪类题型？📐")
    elif qtype == "english":
        return ("英语学习的关键是多听多读多练习！每天背5个新单词，"
                "读一段英文文章，坚持下去进步很快。具体哪里不会？🇬🇧")
    elif qtype == "chinese":
        return ("语文重在积累！多读好书、勤写日记。作文要真情实感，"
                "用具体事例支撑观点。需要什么写作技巧？✍️")
    elif qtype == "study_method":
        return random.choice([
            "学习要讲究方法！用番茄钟25分钟专注+5分钟休息，效率最高。每天整理错题本，温故知新很重要！📝",
            "试试费曼学习法：学完后假装给一个8岁小孩讲解，讲不清楚的地方就是没真懂的，回头再学！🧠",
            "建立知识框架很重要！用思维导图把知识点串起来，比孤立记忆效果好十倍 🌳",
        ])
    elif qtype == "science":
        return ("科学讲究观察和实验！很多原理都可以用生活中的现象来解释。"
                "具体的科学问题可以告诉我，我用简单方式讲给你听 🔬")

    # 3. 通用兜底
    return random.choice(GENERAL_REPLIES)


# ============================================================
# LumiLearn 模型调用（尝试 + 乱码检测）
# ============================================================

# 注意：localhost:18080 是 Flask 前端，不提供 /api/generate。
# 实际的本地 LLM 推理由 Ollama 提供（OLLAMA_URL 环境变量，默认 localhost:11434）。
# 这里保留 18080 作为默认 API_BASE，以便兼容 chat_service.py 中的流式 /api/chat 路由；
# 真正直接调用 Ollama 的场景（如 generate_slides）请显式传入 ollama_base。
DEFAULT_API_BASE = _os.environ.get("API_BASE_URL", "http://localhost:18080")
DEFAULT_OLLAMA_BASE = _os.environ.get("OLLAMA_URL", "http://localhost:11434")


def try_lumilearn(prompt: str, question: str = "", api_base: str = DEFAULT_OLLAMA_BASE, timeout: int = 15) -> Tuple[Optional[str], bool]:
    """尝试调用 Ollama 本地模型，返回 (文本, 是否可用)

    默认调用 Ollama /api/chat 接口；兼容：
      - Ollama 直接返回：{"message": {"content": "..."}}
      - 或 /api/generate 返回：{"response": "..."}
    """
    try:
        # 优先用 /api/chat 接口（更通用，支持 system prompt）
        resp = requests.post(
            f"{api_base}/api/chat",
            json={
                "model": "qwen2.5:7b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"num_predict": 200, "temperature": 0.8}
            },
            timeout=timeout
        )

        text = ""
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                msg = data.get("message")
                if isinstance(msg, dict):
                    text = msg.get("content", "").strip()
                if not text:
                    text = data.get("response", "").strip()

        if not text:
            return None, False

        if is_gibberish(text):
            return None, False

        cleaned = clean_output(text)
        if len(cleaned) < 3:
            return None, False

        if question and not is_semantically_valid(cleaned, question):
            return None, False

        return cleaned, True

    except Exception:
        return None, False


def clean_output(text: str) -> str:
    """清理模型输出"""
    text = text.strip()
    text = re.sub(r'[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffefa-zA-Z0-9\s\.\,\!\?\;\:\-\+\=\(\)\[\]\{\}""''《》、。，！？；：""''（）]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text[:200]
    return text


def is_semantically_valid(text: str, question: str) -> bool:
    """检查模型回复是否有语义意义（不只是常见字随机排列）"""
    if len(text) < 4:
        return False

    # 提取问题中的关键词
    q_chars = set(c for c in question if '\u4e00' <= c <= '\u9fff')

    # 预定义的语义模式（常见中文词组）
    semantic_patterns = [
        "方法", "可以", "需要", "应该", "注意", "建议", "首先", "然后",
        "比如", "例如", "因为", "所以", "如果", "那么", "但是", "虽然",
        "学习", "练习", "掌握", "理解", "记住", "知道", "了解", "认识",
        "重要", "关键", "基础", "基本", "简单", "复杂", "容易", "困难",
        "问题", "答案", "结果", "过程", "步骤", "阶段", "开始", "结束",
        "提高", "增加", "减少", "改变", "变化", "发展", "进步", "改善",
        "小学数学", "初中数学", "语文", "英语", "物理", "化学", "生物",
        "历史", "地理", "政治", "科学", "技术", "工程", "数学",
        "么", "吗", "呢", "吧", "啊", "哦", "嗯", "呀",
        "今天", "昨天", "明天", "现在", "以前", "以后", "每天", "每周",
        "一下", "一些", "一定", "一样", "一直", "一起", "一点",
        "不是", "不会", "不行", "不同", "不错", "不够",
        "大家", "同学", "老师", "朋友", "家人", "自己",
        "这个", "那个", "哪个", "这里", "那里", "怎么", "什么",
    ]

    found_patterns = sum(1 for p in semantic_patterns if p in text)

    # 检查是否有问句中的关键词出现在回复中（基本的相关性）
    relevant_keywords = sum(1 for c in q_chars if c in text)

    # 必须满足：有足够的语义词组 + 与问题有一定相关性
    if found_patterns >= 2 and relevant_keywords >= 1:
        return True
    if found_patterns >= 3:
        return True

    return False


# ============================================================
# 教学讲解内容生成器（直播专用）
# ============================================================

class LiveTutor:
    """直播讲解专用引擎

    四种模式：
    - direct:  直接给出答案/解释（你的直播讲解模式）
    - guided:  "不给答案"引导模式（Koji 风格，让用户自己思考）
    - react:   OpenManus 风格 ReAct 推理模式（Think→Act→Observe 循环）
    - feynman: 费曼教学法模式（现象→冲突→模型→推导→测试五步引导）
    """

    def __init__(self, api_base: str = DEFAULT_API_BASE, mode: str = "direct"):
        self.api_base = api_base
        self.conversation_history = []
        self.max_history = 10
        self.mode = mode  # "direct" / "guided" / "react" / "feynman"
        self._manus_agent = None
        self._last_thinking_trace = []
        self._feynman_engine = None
        self._feynman_topic = ""  # 当前费曼教学的话题

    def set_mode(self, mode: str):
        """设置回复模式：direct 直接给答案 / guided 引导式提问 / react ReAct推理 / feynman 费曼教学"""
        assert mode in ("direct", "guided", "react", "feynman"), \
            f"mode must be 'direct', 'guided', 'react', or 'feynman', got {mode}"
        self.mode = mode
        # 切换到费曼模式时初始化引擎
        if mode == "feynman" and self._feynman_engine is None:
            self._init_feynman()

    def _init_feynman(self):
        """延迟初始化费曼引擎"""
        try:
            from framework.engines.feynman_engine import FeynmanEngine
            self._feynman_engine = FeynmanEngine(model_name="qwen2.5:7b")
        except ImportError:
            self._feynman_engine = None

    def toggle_mode(self) -> str:
        """切换模式，返回切换后的说明"""
        modes = ["direct", "guided", "react", "feynman"]
        current_idx = modes.index(self.mode) if self.mode in modes else 0
        next_idx = (current_idx + 1) % len(modes)
        self.mode = modes[next_idx]

        if self.mode == "feynman" and self._feynman_engine is None:
            self._init_feynman()

        descriptions = {
            "direct": "🔄 已切换到「直接解答」模式：我直接告诉你答案和方法 ✅",
            "guided": "🔄 已切换到「引导式思考」模式：我不直接给答案，帮你一步步思考 ✅",
            "react": "🔄 已切换到「ReAct推理」模式：AI会先思考分析，再选择工具，最后给出答案 🧠",
            "feynman": "🔄 已切换到「费曼教学」模式：用费曼学习法五步引导，让你真正理解每一个概念 💡🎓",
        }
        return descriptions.get(self.mode, f"模式已切换为: {self.mode}")

    def _get_manus_agent(self):
        """延迟初始化 ManusAgent"""
        if self._manus_agent is None:
            from openmanus.manus_agent import ManusAgent
            ollama_base = self.api_base.replace(":18080", ":11434")
            self._manus_agent = ManusAgent(
                api_base=self.api_base,
                ollama_base=ollama_base,
                mode="auto"
            )
        return self._manus_agent

    def get_thinking_trace(self) -> list:
        """获取最后一次 ReAct 推理的思考链路"""
        return self._last_thinking_trace

    def respond(self, question: str, user_name: str = "", correct_answer: str = "") -> str:
        """主回复入口
        guided 模式：如果是学习问题，先引导思考而不是直接给答案
        react 模式：使用 OpenManus 风格 ReAct 循环推理
        feynman 模式：费曼教学法五步引导式教学
        """
        if not question.strip():
            return "有什么问题随时问我哦～"

        # 0. 记录对话
        self.conversation_history.append(f"观众: {question}")
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        # 1. 分类
        qtype = classify_question(question)

        if qtype == "greeting":
            return random.choice(GREETING_REPLIES)
        elif qtype == "thanks":
            return random.choice(THANKS_REPLIES)

        # 2. ReAct 模式：使用 OpenManus 风格多步推理
        if self.mode == "react":
            return self._respond_react(question, qtype)

        # 3. 引导模式：如果是学习问题，先不给答案
        if self.mode == "guided" and qtype != "general":
            return get_guided_question(question, qtype)

        # 4. 费曼模式：使用费曼教学引擎引导
        if self.mode == "feynman":
            return self._respond_feynman(question, qtype)

        # 5. 尝试知识库
        kb = search_knowledge_base(question)
        if kb:
            self.conversation_history.append(f"小澍(知识库): {kb[:30]}")
            return kb

        # 6. 尝试 LumiLearn 模型
        system_prompt = ("你是「小澍」，专业亲切的中文AI学习规划师。"
                         "回答简洁有趣，适合中小学生。用比喻和例子解释概念。"
                         "回答在50字以内。")
        full_prompt = f"指令：{system_prompt}\n\n问题：{question}\n回答："

        llm_text, success = try_lumilearn(full_prompt, question, self.api_base)
        if success and llm_text:
            self.conversation_history.append(f"小澍(模型): {llm_text[:30]}")
            return f"AI小澍：{llm_text}"

        # 7. 知识库兜底
        return get_intelligent_reply(question)

    def _respond_react(self, question: str, qtype: str) -> str:
        """ReAct 模式：使用 ManusAgent 多步推理"""
        agent = self._get_manus_agent()

        if qtype in ("math", "science", "english", "chinese"):
            result = agent.run(question)
        else:
            result = agent.run(question)

        self._last_thinking_trace = agent.get_thinking_trace()
        final_answer = result.get("final_answer", "")

        if final_answer:
            self.conversation_history.append(f"小澍(ReAct): {final_answer[:30]}")
            return f"🧠 {final_answer}"

        return get_intelligent_reply(question)

    def _respond_feynman(self, question: str, qtype: str) -> str:
        """费曼教学模式：利用 FeynmanEngine 进行引导式教学"""
        # 如果费曼引擎不可用，降级到引导模式
        if self._feynman_engine is None:
            self._init_feynman()
        if self._feynman_engine is None:
            # 降级为普通引导模式
            if qtype != "general":
                return get_guided_question(question, qtype)
            return "🤔 费曼引擎正在准备中...先让我想想怎么引导你。"

        # 将学生问题作为费曼教学的话题
        self._feynman_topic = question[:50]  # 截取前50字作为话题

        # 根据问题类型差异化处理
        if qtype in ("greeting", "thanks"):
            if qtype == "greeting":
                return random.choice(GREETING_REPLIES)
            return random.choice(THANKS_REPLIES)

        # 学习方法类问题给直接建议
        if qtype == "study_method":
            return self._feynman_engine.ask_guiding_question(
                "学习方法", question
            )

        # 学科问题使用费曼引导
        if qtype in ("math", "science", "english", "chinese"):
            # 提取核心话题
            topic = self._extract_feynman_topic(question, qtype)
            self._feynman_topic = topic
            return f"🎓 费曼课堂：让我们真正理解「{topic}」\n\n" + \
                   self._feynman_engine.ask_guiding_question(topic, question)

        # 通用问题
        return self._feynman_engine.ask_guiding_question("这个问题", question)

    def _extract_feynman_topic(self, question: str, qtype: str) -> str:
        """从问题中提取费曼教学的核心话题"""
        # 移除常见问句结构
        topic = re.sub(r'^(什么是|什么叫做|如何|怎么|怎样|为什么|帮我|请|请问|告诉我|讲解|解释)', '', question)
        topic = re.sub(r'[？?！!。.]$', '', topic)
        topic = topic.strip()
        if len(topic) > 15:
            # 如果太长，尝试提取核心概念
            for kw in ["公式", "定理", "定律", "方法", "概念", "原理", "运算", "语法", "时态"]:
                if kw in topic:
                    idx = topic.index(kw)
                    start = max(0, idx - 5)
                    end = min(len(topic), idx + 8)
                    topic = topic[start:end]
                    break
        return topic if topic else question[:15]

    def feynman_explain(self, topic: str, level: str = "junior") -> str:
        """
        费曼教学完整讲解 - 五步教学法
        
        参数：
            topic: 教学主题
            level: 学生水平 (junior/senior/college)
        
        返回：
            格式化后的五步讲解内容
        """
        if self._feynman_engine is None:
            self._init_feynman()
        if self._feynman_engine is None:
            return f"抱歉，费曼引擎暂时不可用。关于「{topic}」的讲解..."

        self._feynman_topic = topic
        result = self._feynman_engine.explain(topic, level)
        return result.get("full_content", f"费曼讲解「{topic}」准备中...")

    def feynman_test(self, concept: str, 
                      student_explanation: str) -> dict:
        """
        费曼30秒测试评分
        
        参数：
            concept: 概念名
            student_explanation: 学生解释
        
        返回：
            评分结果Dict
        """
        if self._feynman_engine is None:
            self._init_feynman()
        if self._feynman_engine is None:
            return {"score": 0, "feedback": "费曼引擎不可用", "is_feynman_worthy": False}
        return self._feynman_engine.thirty_second_test(concept, student_explanation)

    def feynman_correct(self, concept: str, 
                         wrong_explanation: str) -> str:
        """
        费曼式纠错引导
        
        参数：
            concept: 概念名
            wrong_explanation: 学生的错误解释
        
        返回：
            引导式纠正文本
        """
        if self._feynman_engine is None:
            self._init_feynman()
        if self._feynman_engine is None:
            return f"关于{concept}，让我们重新想一想..."
        return self._feynman_engine.suggest_correction(concept, wrong_explanation)

    def feynman_next_step(self) -> str:
        """
        费曼教学下一步引导
        在上一段讲解后，继续引导下一步
        """
        if self._feynman_engine is None or not self._feynman_topic:
            return "我们先确定要学什么话题吧！你最近对什么知识点感兴趣？"

        # 根据历史步数决定下一步
        topic = self._feynman_topic
        history_count = sum(1 for h in self.conversation_history if "费曼" in h)

        steps = [
            f"让我们用一个生活中的例子来理解「{topic}」。你见过...",
            f"现在有个问题想问：你觉得为什么「{topic}」会是这样的？",
            f"我来给你一个简单的模型来理解「{topic}」。把它想象成...",
            f"根据刚才的模型，你能推出了吗？试试看...",
            f"好了，现在给你30秒，用最简单的话讲清楚什么是「{topic}」。开始！",
        ]

        idx = history_count % len(steps)
        return steps[idx]

    def check_answer(self, user_answer: str, correct_answer: str,
                     question: str = "", topic: str = "") -> dict:
        """
        验证用户答案，不给直接的"对/错"，而是引导思考
        返回 {"status": "correct"|"close"|"wrong", "message": ..., "next": ...}
        """
        return check_user_answer(user_answer, correct_answer, question)

    def teach_topic(self, topic: str) -> str:
        """主动讲解某个知识主题"""
        topic_lower = topic.lower()

        # 数学题
        if any(k in topic_lower for k in ["加法", "减法", "乘法", "除法"]):
            return get_intelligent_reply(f"{topic}计算方法")
        if any(k in topic_lower for k in ["面积", "周长", "体积"]):
            return get_intelligent_reply(f"{topic}公式")
        if "分数" in topic_lower:
            return EDUCATION_KB["分数运算"]["reply"]
        if "方程" in topic_lower:
            return EDUCATION_KB["方程"]["reply"]

        # 英语
        if any(k in topic_lower for k in ["英语", "英文", "单词", "语法"]):
            return EDUCATION_KB["英语翻译"]["reply"]

        # 学习方法
        if any(k in topic_lower for k in ["学习", "计划", "复习", "记忆"]):
            return EDUCATION_KB["学习计划"]["reply"]

        return f"关于{topic}，让我来讲解！可以告诉我你不太明白的具体部分，我针对性地解答～"


# ============================================================
# 幻灯片生成
# ============================================================

def _build_slide_prompt(topic: str, slide_count: int, style: str) -> str:
    """构建幻灯片生成的提示词"""
    style_descriptions = {
        "detailed": "详细讲解，每张幻灯片包含丰富的解释和例子",
        "concise": "简洁明了，每张幻灯片只包含核心要点",
        "outline": "大纲式，每张幻灯片列出关键知识点",
    }
    style_desc = style_descriptions.get(style, style_descriptions["detailed"])

    prompt = f"""你是一位专业的AI教育内容创作助手。请为主题「{topic}」生成 {slide_count} 张教学幻灯片。

幻灯片风格要求：{style_desc}

每张幻灯片必须包含以下字段：
- title: 幻灯片标题（简洁有吸引力）
- subtitle: 副标题（补充说明）
- content: HTML格式的正文内容，使用 <p>、<h3>、<ul>、<li> 等标签组织
- katex: 数学公式（KaTeX格式，如 a^2 + b^2 = c^2，没有公式则留空字符串 ""）

输出要求：
- 严格输出JSON数组格式，不要包含任何其他文字或代码块标记
- 按照教学逻辑从浅入深排列幻灯片

输出格式示例：
[{{"title": "勾股定理简介", "subtitle": "直角三角形的基本性质", "content": "<p>勾股定理是几何学中最重要的定理之一...</p>", "katex": "a^2 + b^2 = c^2"}}]

请直接输出JSON数组："""
    return prompt


def _parse_slides_json(text: str) -> list:
    """从LLM输出中解析幻灯片JSON数组"""
    text = text.strip()

    # 尝试直接解析
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 数组（处理可能包裹在代码块或其他文本中的情况）
    array_match = re.search(r'\[[\s\S]*\]', text)
    if array_match:
        try:
            result = json.loads(array_match.group(0))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # 尝试按行解析（每行一个JSON对象）
    lines = text.strip().split('\n')
    slides = []
    for line in lines:
        line = line.strip().rstrip(',')
        if line.startswith('{') and line.endswith('}'):
            try:
                slide = json.loads(line)
                if isinstance(slide, dict):
                    slides.append(slide)
            except json.JSONDecodeError:
                continue

    return slides if slides else []


def _normalize_slide(slide: dict) -> dict:
    """标准化幻灯片数据结构"""
    return {
        "title": str(slide.get("title", "")).strip(),
        "subtitle": str(slide.get("subtitle", "")).strip(),
        "content": str(slide.get("content", "")).strip(),
        "katex": str(slide.get("katex", "")).strip(),
    }


def _generate_template_slides(topic: str, slide_count: int, style: str) -> list:
    """基于模板生成幻灯片（LLM不可用时的回退方案）"""
    slides = []

    # 幻灯片模板
    template_structures = [
        {
            "title_suffix": "概述",
            "subtitle": f"什么是{topic}？",
            "content": f"<h3>欢迎学习</h3><p>本课程将带你深入了解「{topic}」的核心概念与应用。让我们一起开始这段学习之旅！</p>",
        },
        {
            "title_suffix": "背景与由来",
            "subtitle": f"{topic}的历史与发展",
            "content": f"<h3>知识背景</h3><p>了解「{topic}」的起源和发展历程，有助于我们更好地理解它的意义和价值。</p>",
        },
        {
            "title_suffix": "核心概念",
            "subtitle": f"理解{topic}的关键要素",
            "content": f"<h3>核心要点</h3><ul><li>关键概念的定义与解释</li><li>核心要素的拆解分析</li><li>与其他知识的关联</li></ul>",
        },
        {
            "title_suffix": "公式与推导",
            "subtitle": f"{topic}的数学表达",
            "content": f"<h3>公式推导</h3><p>让我们一步步推导「{topic}」的数学表达，理解每个符号的含义。</p>",
        },
        {
            "title_suffix": "应用举例",
            "subtitle": f"{topic}在实际中的应用",
            "content": f"<h3>实际应用</h3><p>通过实际例子来理解「{topic}」如何解决真实世界的问题。</p>",
        },
        {
            "title_suffix": "常见误区",
            "subtitle": f"学习{topic}时的注意事项",
            "content": f"<h3>避坑指南</h3><ul><li>容易混淆的概念辨析</li><li>常见错误及纠正</li><li>记忆技巧分享</li></ul>",
        },
        {
            "title_suffix": "进阶拓展",
            "subtitle": f"{topic}的深入探索",
            "content": f"<h3>进阶思考</h3><p>掌握了基础知识后，来看看「{topic}」在更高级场景中的应用和延伸。</p>",
        },
        {
            "title_suffix": "总结回顾",
            "subtitle": f"{topic}知识要点总结",
            "content": f"<h3>课程总结</h3><p>回顾本课程的核心知识点，巩固所学内容。你已经掌握了「{topic}」的要点！</p>",
        },
    ]

    # 根据 slide_count 均匀采样模板
    total_templates = len(template_structures)
    if slide_count <= total_templates:
        step = total_templates / slide_count
        indices = [int(i * step) for i in range(slide_count)]
    else:
        indices = list(range(total_templates))
        # 如果 slide_count 超过模板数，循环补充
        extra = slide_count - total_templates
        for i in range(extra):
            indices.append(i % total_templates)

    for idx in indices[:slide_count]:
        template = template_structures[idx]
        slide = {
            "title": f"{topic} - {template['title_suffix']}",
            "subtitle": template["subtitle"],
            "content": template["content"],
            "katex": "",
        }
        slides.append(slide)

    return slides


def generate_slides(topic: str, slide_count: int = 5, style: str = "detailed") -> list:
    """
    生成教学幻灯片内容

    参数：
        topic: 教学主题
        slide_count: 幻灯片数量（1-20）
        style: 风格（detailed/concise/outline）

    返回：
        幻灯片列表，每张包含 title, subtitle, content, katex
    """
    # 优先从环境变量读取 Ollama 地址，否则使用共享默认值
    ollama_base = _os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE)
    model_name = _os.environ.get("LUMILEARN_SLIDE_MODEL", "qwen2.5:7b")

    # 1. 尝试调用 Ollama 本地模型生成（使用 /api/chat 接口，更通用）
    try:
        user_prompt = _build_slide_prompt(topic, slide_count, style)

        resp = requests.post(
            f"{ollama_base}/api/chat",
            json={
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一名专业的教育内容创作助手，擅长为各类主题生成结构化的教学幻灯片。"
                                   "严格按 JSON 数组格式输出，不要包含任何其他文字。"
                    },
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {"num_predict": 4096, "temperature": 0.7}
            },
            timeout=120
        )

        if resp.status_code == 200:
            data = resp.json()
            text = ""
            # 兼容多种可能的响应格式
            if isinstance(data, dict):
                if "message" in data and isinstance(data["message"], dict):
                    text = data["message"].get("content", "").strip()
                elif "response" in data:
                    text = data.get("response", "").strip()
                elif "choices" in data and isinstance(data["choices"], list):
                    first = data["choices"][0]
                    if isinstance(first, dict) and "message" in first:
                        text = first["message"].get("content", "").strip()

            if text and not is_gibberish(text):
                raw_slides = _parse_slides_json(text)
                if raw_slides and len(raw_slides) > 0:
                    slides = [_normalize_slide(s) for s in raw_slides[:slide_count]]
                    if any(s["title"] or s["content"] for s in slides):
                        return slides
    except Exception as exc:
        logger_msg = f"[slides] ollama call failed: {exc}"
        # 简单打印，不引入新依赖
        try:
            import logging
            logging.getLogger("lumilearn.slides").warning(logger_msg)
        except Exception:
            pass

    # 2. 回退：模板生成（比空白好）
    return _generate_template_slides(topic, slide_count, style)


# ============================================================
# 交互式模拟代码生成
# ============================================================

SIMULATION_TEMPLATES = {
    "default": {
        "html": '<h2 style="text-align:center;color:#333;margin-top:40px;">交互式模拟</h2><p style="text-align:center;color:#666;">点击画布区域开始交互</p>',
        "css": 'body{margin:0;font-family:sans-serif;background:#f5f5f5;display:flex;align-items:center;justify-content:center;min-height:100vh;cursor:pointer;}',
        "js": 'document.body.addEventListener("click",function(){var c=document.createElement("div");c.style.cssText="position:absolute;width:20px;height:20px;border-radius:50%;background:hsl("+Math.random()*360+",70%,60%);animation:pop 0.6s ease-out forwards;";c.style.left=event.clientX-10+"px";c.style.top=event.clientY-10+"px";document.body.appendChild(c);setTimeout(function(){c.remove();},600);});var s=document.createElement("style");s.textContent="@keyframes pop{to{transform:scale(3);opacity:0;}}";document.head.appendChild(s);',
    },
    "geometry": {
        "html": '<canvas id="canvas" width="400" height="400"></canvas><div id="info" style="text-align:center;margin-top:10px;color:#555;">拖动三角形顶点查看变化</div>',
        "css": 'body{margin:20px;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;background:#f9f9f9;}#canvas{border:1px solid #ddd;border-radius:8px;background:#fff;cursor:pointer;}',
        "js": 'var c=document.getElementById("canvas"),ctx=c.getContext("2d");var A={x:200,y:300},B={x:100,y:100},C={x:300,y:100};var drag=null;function draw(){ctx.clearRect(0,0,400,400);ctx.beginPath();ctx.moveTo(A.x,A.y);ctx.lineTo(B.x,B.y);ctx.lineTo(C.x,C.y);ctx.closePath();ctx.fillStyle="rgba(59,130,246,0.2)";ctx.fill();ctx.strokeStyle="#3b82f6";ctx.lineWidth=2;ctx.stroke();[A,B,C].forEach(function(p){ctx.beginPath();ctx.arc(p.x,p.y,8,0,Math.PI*2);ctx.fillStyle="#3b82f6";ctx.fill();ctx.strokeStyle="#fff";ctx.lineWidth=2;ctx.stroke();});var ab=Math.sqrt(Math.pow(B.x-A.x,2)+Math.pow(B.y-A.y,2));var bc=Math.sqrt(Math.pow(C.x-B.x,2)+Math.pow(C.y-B.y,2));var ca=Math.sqrt(Math.pow(A.x-C.x,2)+Math.pow(A.y-C.y,2));ctx.fillStyle="#333";ctx.font="13px monospace";ctx.fillText("AB: "+ab.toFixed(0),10,20);ctx.fillText("BC: "+bc.toFixed(0),10,38);ctx.fillText("CA: "+ca.toFixed(0),10,56);}c.addEventListener("mousedown",function(e){var r=c.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;[A,B,C].forEach(function(p){if(Math.hypot(mx-p.x,my-p.y)<12)drag=p;});});c.addEventListener("mousemove",function(e){if(drag){var r=c.getBoundingClientRect();drag.x=e.clientX-r.left;drag.y=e.clientY-r.top;draw();}});c.addEventListener("mouseup",function(){drag=null;});draw();',
    },
    "physics": {
        "html": '<canvas id="canvas" width="500" height="400"></canvas><div style="text-align:center;margin-top:8px;color:#555;">小球自由落体模拟 | 点击添加新球</div>',
        "css": 'body{margin:20px;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;background:#f9f9f9;}#canvas{border:1px solid #ddd;border-radius:8px;background:#fff;cursor:pointer;}',
        "js": 'var c=document.getElementById("canvas"),ctx=c.getContext("2d");var balls=[],gravity=0.5,bounce=0.7;function addBall(x,y){balls.push({x:x,y:y,vx:(Math.random()-0.5)*4,vy:0,r:8+Math.random()*12,color:"hsl("+Math.random()*360+",70%,55%)"});}c.addEventListener("click",function(e){var r=c.getBoundingClientRect();addBall(e.clientX-r.left,e.clientY-r.top);});function update(){balls.forEach(function(b){b.vy+=gravity;b.x+=b.vx;b.y+=b.vy;if(b.y+b.r>400){b.y=400-b.r;b.vy*=-bounce;}if(b.x-b.r<0){b.x=b.r;b.vx*=-bounce;}if(b.x+b.r>500){b.x=500-b.r;b.vx*=-bounce;}});}function draw(){ctx.clearRect(0,0,500,400);ctx.fillStyle="#f0f0f0";ctx.fillRect(0,380,500,20);balls.forEach(function(b){ctx.beginPath();ctx.arc(b.x,b.y,b.r,0,Math.PI*2);ctx.fillStyle=b.color;ctx.fill();ctx.strokeStyle="rgba(0,0,0,0.2)";ctx.stroke();});}function loop(){update();draw();requestAnimationFrame(loop);}addBall(100,50);addBall(250,30);addBall(400,20);loop();',
    },
    "math": {
        "html": '<canvas id="canvas" width="450" height="450"></canvas><div style="text-align:center;margin-top:8px;color:#555;">函数图像绘制 | y = sin(x) · cos(x/2)</div>',
        "css": 'body{margin:20px;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;background:#f9f9f9;}#canvas{border:1px solid #ddd;border-radius:8px;background:#fff;}',
        "js": 'var c=document.getElementById("canvas"),ctx=c.getContext("2d"),W=450,H=450;ctx.beginPath();ctx.strokeStyle="#ddd";ctx.lineWidth=1;for(var i=0;i<=10;i++){var x=i*W/10;ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.moveTo(0,i*H/10);ctx.lineTo(W,i*H/10);}ctx.stroke();ctx.beginPath();ctx.strokeStyle="#3b82f6";ctx.lineWidth=2;for(var t=0;t<=W;t+=0.5){var angle=(t/W)*Math.PI*4-Math.PI*2;var y=H/2-Math.sin(angle)*Math.cos(angle/2)*(H/3);t===0?ctx.moveTo(t,y):ctx.lineTo(t,y);}ctx.stroke();ctx.fillStyle="#333";ctx.font="12px monospace";ctx.fillText("y=sin(x)·cos(x/2)",10,H-10);',
    },
}


def generate_simulation(topic: str, concept: str = "", scene_type: str = "default") -> dict:
    """
    生成交互式模拟 HTML/CSS/JS 代码

    参数：
        topic: 教学主题（如"勾股定理"）
        concept: 具体概念（如"直角三角形边的平方关系"）
        scene_type: 场景类型（default/geometry/physics/math）

    返回：
        {"html": "...", "css": "...", "js": "..."}
    """
    # 检测场景类型
    if not scene_type or scene_type == "default":
        topic_lower = (topic + concept).lower()
        if any(k in topic_lower for k in ["几何", "三角形", "勾股", "图形", "面积"]):
            scene_type = "geometry"
        elif any(k in topic_lower for k in ["物理", "力", "运动", "速度", "重力", "加速度"]):
            scene_type = "physics"
        elif any(k in topic_lower for k in ["函数", "方程", "曲线", "坐标", "图像"]):
            scene_type = "math"
        else:
            scene_type = "default"

    # 1. 尝试调用 LLM 生成
    try:
        prompt = f"""你是一位前端开发专家。请为主题「{topic}」生成一个交互式教学模拟的 HTML/CSS/JS 代码。

概念：{concept if concept else topic}
场景类型：{scene_type}

要求：
- 纯 HTML/CSS/JavaScript，无需任何外部库
- 使用 Canvas 或 DOM 操作实现交互
- 代码简洁，适合教学演示
- 大小为 500x400 左右
- 带有颜色和动画效果

请严格输出 JSON 格式（不要包含任何其他文字）：
{{"html": "HTML内容", "css": "CSS样式", "js": "JavaScript代码"}}

直接输出 JSON："""

        resp = requests.post(
            f"{DEFAULT_API_BASE}/api/generate",
            json={
                "model": "lumilearn-v5",
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 2048, "temperature": 0.6}
            },
            timeout=60
        )

        if resp.status_code == 200:
            data = resp.json()
            text = data.get("response", "").strip()
            if text and not is_gibberish(text):
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    result = json.loads(json_match.group(0))
                    if "html" in result and "js" in result:
                        return {
                            "html": result.get("html", ""),
                            "css": result.get("css", ""),
                            "js": result.get("js", ""),
                        }
    except Exception:
        pass

    # 2. 回退：使用预设模板
    template = SIMULATION_TEMPLATES.get(scene_type, SIMULATION_TEMPLATES["default"])
    return {
        "html": template["html"],
        "css": template["css"],
        "js": template["js"],
    }
if __name__ == "__main__":
    print("=" * 50)
    print("LumiLearn 智能混合回复引擎测试")
    print("=" * 50)

    tutor = LiveTutor()

    tests = [
        "你好",
        "1+1等于几",
        "三角形面积公式",
        "英语谢谢怎么说",
        "作文怎么写",
        "怎么制定学习计划",
        "记不住单词怎么办",
        "物理题怎么做",
        "什么是质数",
        "不想学了",
    ]

    for t in tests:
        reply = tutor.respond(t)
        print(f"\n❓ {t}")
        print(f"🌿 {reply}")

    print("\n" + "=" * 50)
    print("乱码检测测试")
    print("=" * 50)

    gibberish_tests = [
        ("彴剴儜梖孱坚傄与尊尊安", True),
        ("你好世界", False),
        ("1加1等于2", False),
        ("勰止嘅亚技劷坚乐尊", True),
        ("学习方法很重要", False),
    ]
    for text, expected in gibberish_tests:
        result = is_gibberish(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text[:20]}' → 乱码={result} (预期={expected})")