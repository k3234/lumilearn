"""
LumiLearn 智能混合回复引擎
- LumiLearn 模型作为第一层尝试
- 教育知识库精确匹配
- 规则引擎兜底
- 乱码检测自动切换
"""

import re
import random
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

DEFAULT_API_BASE = "http://192.168.2.63:18080"

def try_lumilearn(prompt: str, question: str = "", api_base: str = DEFAULT_API_BASE, timeout: int = 15) -> Tuple[Optional[str], bool]:
    """尝试调用 LumiLearn 模型，返回 (文本, 是否可用)"""
    try:
        resp = requests.post(
            f"{api_base}/api/generate",
            json={
                "model": "lumilearn-v5",
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 60, "temperature": 0.8}
            },
            timeout=timeout
        )

        if resp.status_code == 200:
            data = resp.json()
            text = data.get("response", "").strip()

            if not text:
                return None, False

            if is_gibberish(text):
                return None, False

            # 清理输出
            cleaned = clean_output(text)
            if len(cleaned) < 3:
                return None, False

            if question and not is_semantically_valid(cleaned, question):
                return None, False

            return cleaned, True

        return None, False

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
    """直播讲解专用引擎"""

    def __init__(self, api_base: str = DEFAULT_API_BASE):
        self.api_base = api_base
        self.conversation_history = []
        self.max_history = 10

    def respond(self, question: str, user_name: str = "") -> str:
        """主回复入口"""
        if not question.strip():
            return "有什么问题随时问我哦～"

        # 0. 记录对话
        self.conversation_history.append(f"观众: {question}")
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        # 1. 尝试知识库
        kb = search_knowledge_base(question)
        if kb:
            self.conversation_history.append(f"小澍(知识库): {kb[:30]}")
            return kb

        # 2. 分类并给针对性建议
        qtype = classify_question(question)

        if qtype == "greeting":
            return random.choice(GREETING_REPLIES)
        elif qtype == "thanks":
            return random.choice(THANKS_REPLIES)

        # 3. 尝试 LumiLearn 模型
        system_prompt = ("你是「小澍」，专业亲切的中文AI学习规划师。"
                         "回答简洁有趣，适合中小学生。用比喻和例子解释概念。"
                         "回答在50字以内。")
        full_prompt = f"指令：{system_prompt}\n\n问题：{question}\n回答："

        llm_text, success = try_lumilearn(full_prompt, question, self.api_base)
        if success and llm_text:
            self.conversation_history.append(f"小澍(模型): {llm_text[:30]}")
            return f"AI小澍：{llm_text}"

        # 4. 知识库兜底
        return get_intelligent_reply(question)

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