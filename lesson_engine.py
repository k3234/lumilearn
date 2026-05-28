"""
LumiLearn 智能讲解引擎 - 直播讲课专用
自动生成结构化教案，每个知识点拆分为6-8张幻灯片
内置TTS旁白脚本，直接可用于OBS直播叠加
"""

import json, time, threading, random
from dataclasses import dataclass, field
from typing import Optional, Callable

# ============================================================
# 数据结构
# ============================================================
@dataclass
class Slide:
    title: str
    content: str = ""     # 正文（讲解内容）
    formula: str = ""     # 公式/重点（大字显示）
    example: str = ""     # 例题
    tip: str = ""         # 小贴士
    tts_script: str = ""  # TTS 朗读脚本
    duration_sec: int = 8

@dataclass
class Lesson:
    id: str
    subject: str          # 数学 / 英语 / 语文 / 学习方法
    grade: str            # 小学 / 初中 / 通用
    title: str            # 课程标题
    intro: str            # 课程简介
    slides: list = field(default_factory=list)
    total_duration: int = 0


# ============================================================
# 完整课程库
# ============================================================

LESSONS = {
    # ========== 数学 ==========
    "triangle_area": Lesson(
        id="triangle_area", subject="数学", grade="小学三四年级",
        title="三角形的面积",
        intro="从长方形面积出发，推导三角形面积公式，配合例题练习",
        slides=[
            Slide(
                title="📐 三角形的面积",
                content="同学们好！今天我们来学习三角形的面积。\n\n先回忆一下：长方形的面积 = 长 × 宽，这个大家都记住了吧？",
                tts_script="同学们好！今天我们来学习三角形的面积。先回忆一下，长方形的面积等于长乘以宽，大家都记住了吧？",
                duration_sec=10
            ),
            Slide(
                title="🔍 观察：三角形和长方形的关系",
                content="把一个长方形沿对角线剪开，就得到了两个一模一样的三角形！\n\n这说明：每个三角形的面积 = 长方形面积的一半",
                formula="长方形面积 ÷ 2 = 三角形面积",
                tts_script="把一个长方形沿对角线剪开，你会得到两个完全一样的三角形。这说明每个三角形的面积，正好是长方形面积的一半。",
                duration_sec=12
            ),
            Slide(
                title="📝 三角形面积公式",
                content="三角形的底就相当于长方形的长，三角形的高就相当于长方形的宽。\n\n所以三角形的面积公式是：",
                formula="S = 底 × 高 ÷ 2",
                tip="💡 记忆口诀：底乘高，除以二",
                tts_script="三角形的底就相当于长方形的长，高就相当于宽。所以三角形面积就等于底乘高，再除以二。口诀就是：底乘高，除以二！",
                duration_sec=12
            ),
            Slide(
                title="📐 例题一",
                content="一个三角形，底是 6 厘米，高是 4 厘米，求面积。",
                formula="S = 6 × 4 ÷ 2",
                example="= 24 ÷ 2\n= 12 平方厘米",
                tip="注意单位：平方厘米",
                tts_script="来看例题：底是六厘米，高是四厘米。面积等于六乘四除以二，六乘四得二十四，二十四除以二得十二。答案是十二平方厘米。",
                duration_sec=14
            ),
            Slide(
                title="📐 例题二",
                content="一个三角形，底是 8 米，高是 5 米，求面积。",
                formula="S = 8 × 5 ÷ 2",
                example="= 40 ÷ 2\n= 20 平方米",
                tip="自己试试：底10cm，高3cm，面积是多少？",
                tts_script="再看一题：底八米，高五米。八乘五等于四十，四十除以二等于二十。答案是二十平方米。大家试试：底十厘米，高三厘米，面积是多少？",
                duration_sec=15
            ),
            Slide(
                title="🎯 解题技巧",
                content="三角形面积题的三个关键步骤：\n\n1️⃣ 找到底和高（必须是垂直的！）\n2️⃣ 底 × 高\n3️⃣ 结果 ÷ 2",
                tip="⚠️ 底和高要对应，不是任意两条边！",
                tts_script="做三角形面积题，记住三步：第一步，找到底和高，注意底和高必须是垂直的；第二步，底乘高；第三步，除以二。记住，底和高必须对应，不是任意两条边都能算！",
                duration_sec=12
            ),
            Slide(
                title="📝 课堂小结",
                content="今天我们学了：\n\n✅ 三角形面积 = 底 × 高 ÷ 2\n✅ 本质是把三角形看成半个长方形\n✅ 解题关键：找到正确的底和高",
                tts_script="今天我们学了三角形的面积公式，底乘高除以二。本质是把三角形看成半个长方形。解题关键是找到正确的底和高。下节课我们继续！",
                duration_sec=10
            ),
        ]
    ),

    "linear_equation": Lesson(
        id="linear_equation", subject="数学", grade="初中一年级",
        title="一元一次方程",
        intro="从天平平衡理解方程，掌握移项、合并同类项、求解的完整步骤",
        slides=[
            Slide(
                title="⚖️ 一元一次方程",
                content="同学们，今天我们学习一元一次方程。\n\n先看一个例子：x + 5 = 12，x 是多少？",
                formula="x + 5 = 12",
                tts_script="同学们，今天我们来学习一元一次方程。先看一个简单的例子：x加五等于十二，x是多少呢？",
                duration_sec=8
            ),
            Slide(
                title="⚖️ 理解方程：天平思维",
                content="方程就像一架天平，等号两边必须保持平衡。\n\n左边放了 x 和 5，右边放了 12。\n\n要让天平平衡，两边重量必须相等！",
                formula="x + 5 = 12\n两边同时减 5\nx = 7",
                tip="💡 核心思想：等式两边做同样的运算",
                tts_script="方程就像一架天平，等号两边必须保持平衡。左边有x加五，右边有十二。要让天平平衡，两边同时减去五，x就等于七。核心思想就是：等式两边做同样的运算！",
                duration_sec=14
            ),
            Slide(
                title="📝 解方程四步法",
                content="1️⃣ 去分母（如果有分数）\n2️⃣ 去括号（如果有括号）\n3️⃣ 移项（把含 x 的移到左边，常数移到右边）\n4️⃣ 合并同类项，求出 x",
                formula="例：2x + 3 = 11\n移项：2x = 11 - 3\n合并：2x = 8\n求解：x = 4",
                tts_script="解方程有四步：第一步去分母，第二步去括号，第三步移项，把含x的移到左边，常数移到右边，第四步合并同类项，求出x。注意：移项要变号！",
                duration_sec=15
            ),
            Slide(
                title="📐 例题一",
                content="解方程：3x - 7 = 14",
                formula="3x - 7 = 14\n3x = 14 + 7\n3x = 21\nx = 7",
                tip="⚠️ 移项时 -7 变 +7",
                tts_script="解方程：3x减7等于14。把负7移到右边变成正7，3x等于14加7，等于21。x等于21除以3，等于7。注意移项要变号！",
                duration_sec=14
            ),
            Slide(
                title="📐 例题二",
                content="解方程：5x + 9 = 2x + 24",
                formula="5x - 2x = 24 - 9\n3x = 15\nx = 5",
                tip="💡 含x的移到左边，常数移到右边",
                tts_script="解这个方程：5x加9等于2x加24。把2x移到左边变负2x，9移到右边变负9。5x减2x等于24减9，3x等于15，x等于5。",
                duration_sec=14
            ),
            Slide(
                title="🎯 常见错误提醒",
                content="❌ 移项忘记变号\n❌ 合并同类项算错\n❌ 最后一步除错\n\n✅ 养成检验习惯：把答案代回原方程",
                formula="检验：x=7 代入 3×7-7=14\n21-7=14 ✓ 正确！",
                tts_script="解方程最容易出错的地方：移项忘记变号，合并同类项算错，最后一步除错。养成好习惯：求出答案后，代回原方程检验一下！",
                duration_sec=12
            ),
            Slide(
                title="📝 课堂小结",
                content="✅ 方程 = 天平，两边做同样运算\n✅ 解方程四步：去分母→去括号→移项→合并\n✅ 移项必变号！\n✅ 算完要检验",
                tts_script="今天学了一元一次方程。记住：方程就是天平，两边做同样运算。解方程四步走，移项必须变号，算完要检验。多练习就熟了！",
                duration_sec=10
            ),
        ]
    ),

    "fraction_ops": Lesson(
        id="fraction_ops", subject="数学", grade="小学四五年级",
        title="分数的加减运算",
        intro="理解通分的意义，掌握分数加减法",
        slides=[
            Slide(
                title="🍕 分数的加减运算",
                content="同学们好！今天学分数加减法。\n\n分数就像分披萨🍕，把一块披萨分成几份，取其中几份就是分数。",
                formula="1/4 + 1/4 = 2/4 = 1/2",
                tts_script="同学们好！今天我们来学分数加减法。分数就像分披萨，把一块披萨分成四份，取一份就是四分之一。",
                duration_sec=8
            ),
            Slide(
                title="🔑 关键：分母相同才能加减",
                content="为什么分母要相同？\n\n因为分母代表「把整体分成几份」，份数不一样就不能直接比较！",
                formula="✅ 1/4 + 2/4 = 3/4\n❌ 1/4 + 1/3 ≠ 2/7",
                tip="💡 分母不同 → 先通分",
                tts_script="分数加减法最关键的一点：分母必须相同才能加减。分母代表把整体分成了几份，份数不一样就没法直接加。比如四分之一加四分之二等于四分之三，但四分之一加三分之一不能直接加，要先通分！",
                duration_sec=14
            ),
            Slide(
                title="📝 通分的方法",
                content="通分 = 把分母变成相同的数\n\n方法：找到两个分母的最小公倍数\n\n1/4 + 1/6 → 分母4和6的最小公倍数是12",
                formula="1/4 = 3/12\n1/6 = 2/12\n3/12 + 2/12 = 5/12",
                tts_script="通分就是把分母变成相同的数。方法是找到两个分母的最小公倍数。比如四分之一加六分之一，四和六的最小公倍数是十二，四分之一变成十二分之三，六分之一变成十二分之二，加起来等于十二分之五。",
                duration_sec=15
            ),
            Slide(
                title="📐 例题",
                content="计算：2/3 + 1/4",
                formula="分母 3 和 4，最小公倍数 = 12\n2/3 = 8/12\n1/4 = 3/12\n8/12 + 3/12 = 11/12",
                tip="试试：3/5 - 1/3 = ?",
                tts_script="计算：三分之二加四分之一。三和四的最小公倍数是十二。三分之二变成十二分之八，四分之一变成十二分之三，加起来等于十二分之十一。",
                duration_sec=14
            ),
            Slide(
                title="⚠️ 约分：结果要化简",
                content="分数加减完后，要看能不能约分。\n\n方法：分子分母同时除以它们的最大公约数",
                formula="4/8 = 1/2\n6/9 = 2/3\n10/15 = 2/3",
                tts_script="分数加减完后，一定要检查能不能约分。约分的方法：分子分母同时除以它们的最大公约数。比如八分之四，分子分母同时除以四，就等于二分之一。",
                duration_sec=12
            ),
            Slide(
                title="📝 课堂小结",
                content="✅ 分母相同才能加减\n✅ 分母不同 → 找最小公倍数 → 通分\n✅ 加减完 → 约分化简\n✅ 多练习，自然熟！",
                tts_script="今天学了分数加减法。记住：分母相同才能加减，分母不同要先通分，算完要检查能不能约分。多练习就熟了！",
                duration_sec=10
            ),
        ]
    ),

    "prime_numbers": Lesson(
        id="prime_numbers", subject="数学", grade="小学五年级",
        title="质数与合数",
        intro="理解质数概念，学会判断质数，掌握100以内的质数表",
        slides=[
            Slide(
                title="🔢 质数与合数",
                content="同学们，今天学习质数和合数。\n\n先看几个数：2、3、5、7、11——它们有什么共同点？",
                tts_script="同学们，今天我们来学习质数和合数。先看几个数：二、三、五、七、十一，它们有什么共同点呢？",
                duration_sec=8
            ),
            Slide(
                title="📖 什么是质数？",
                content="质数：只能被 1 和它本身整除的数\n\n注意：1 既不是质数也不是合数！",
                formula="质数：2, 3, 5, 7, 11, 13, 17, 19, 23, 29...\n合数：4, 6, 8, 9, 10, 12, 14, 15...",
                tip="💡 2是最小的质数，也是唯一的偶质数",
                tts_script="质数就是只能被1和它本身整除的数。比如7只能被1和7整除，所以7是质数。注意：1既不是质数也不是合数。2是最小的质数，也是唯一的偶质数！",
                duration_sec=14
            ),
            Slide(
                title="🔍 怎么判断一个数是质数？",
                content="方法：用 2、3、5、7... 依次试除\n\n如果都不能整除 → 就是质数\n只要有一个能整除 → 就是合数",
                formula="判断 17：\n17÷2=8.5 ✗  17÷3≈5.67 ✗\n17÷5=3.4 ✗  17÷7≈2.43 ✗\n→ 17 是质数 ✅",
                tts_script="判断一个数是不是质数，用2、3、5、7依次试除。如果都不能整除，就是质数。比如17，除以2、3、5、7都不能整除，所以17是质数。",
                duration_sec=14
            ),
            Slide(
                title="📝 100以内质数表",
                content="2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97",
                tip="💡 共25个，建议背熟前15个",
                tts_script="一百以内的质数一共有25个，建议大家背熟前15个：2、3、5、7、11、13、17、19、23、29、31、37、41、43、47。",
                duration_sec=12
            ),
            Slide(
                title="📝 课堂小结",
                content="✅ 质数：只能被1和自身整除\n✅ 合数：除了1和自身，还有别的因数\n✅ 1 既不是质数也不是合数\n✅ 2 是唯一的偶质数",
                tts_script="总结一下：质数只能被1和自身整除，合数还有别的因数。1既不是质数也不是合数。2是唯一的偶质数。记住这些就掌握了！",
                duration_sec=10
            ),
        ]
    ),

    # ========== 英语 ==========
    "english_tenses": Lesson(
        id="english_tenses", subject="英语", grade="初中",
        title="英语三大时态",
        intro="现在时、过去时、将来时的用法和标志词",
        slides=[
            Slide(
                title="⏰ 英语三大时态",
                content="英语中，动作发生的时间不同，动词形式也不同。\n\n今天学三个最常用的时态：\n一般现在时 · 一般过去时 · 一般将来时",
                tts_script="Hello everyone！今天我们来学习英语的三大时态：一般现在时、一般过去时和一般将来时。",
                duration_sec=8
            ),
            Slide(
                title="📖 一般现在时",
                content="表示经常发生的动作或状态。\n\n结构：主语 + 动词原形（第三人称单数 + s/es）",
                formula="I go to school every day.\nShe goes to school every day.\n（她→goes，加es）",
                tip="🔑 标志词：every day, often, usually, always",
                tts_script="一般现在时表示经常发生的动作。结构是主语加动词原形。注意第三人称单数，也就是he、she、it，动词要加s或es。比如I go to school和She goes to school。标志词有every day、often、usually、always。",
                duration_sec=15
            ),
            Slide(
                title="📖 一般过去时",
                content="表示过去发生的动作。\n\n结构：主语 + 动词过去式",
                formula="I went to school yesterday.\nShe played basketball last week.\n（play→played，加ed）",
                tip="🔑 标志词：yesterday, last week, ago, in 2020",
                tts_script="一般过去时表示过去发生的动作。结构是主语加动词过去式。规则动词加ed，比如play变成played。不规则动词要单独记，比如go变成went。标志词有yesterday、last week、ago。",
                duration_sec=15
            ),
            Slide(
                title="📖 一般将来时",
                content="表示将来要发生的动作。\n\n结构：主语 + will + 动词原形",
                formula="I will go to school tomorrow.\nShe will study English next week.",
                tip="🔑 标志词：tomorrow, next week, in the future, soon",
                tts_script="一般将来时表示将来要发生的动作。结构是主语加will加动词原形。比如I will go to school tomorrow。标志词有tomorrow、next week、in the future、soon。",
                duration_sec=12
            ),
            Slide(
                title="📝 三时态对比",
                formula="现在：I play  →  He plays\n过去：I played  →  He played\n将来：I will play  →  He will play",
                tip="💡 过去式关注动词变化，将来时关注 will",
                tts_script="对比三个时态：现在时I play，He plays；过去时统一用played；将来时用will play。过去式关注动词变化，将来时关注will。多练习造句就记住了！",
                duration_sec=12
            ),
            Slide(
                title="📝 课堂小结",
                content="✅ 现在时：动词原形（三单+s）\n✅ 过去时：动词过去式（+ed / 不规则）\n✅ 将来时：will + 动词原形\n✅ 看标志词判断时态！",
                tts_script="总结：现在时用动词原形，三单加s；过去时用过去式；将来时用will加原形。做题时先找标志词，判断时态再变形！",
                duration_sec=10
            ),
        ]
    ),

    "english_phrases": Lesson(
        id="english_phrases", subject="英语", grade="小学",
        title="常用英语口语",
        intro="10个最常用的日常英语表达，即学即用",
        slides=[
            Slide(title="🗣️ 常用英语口语", content="今天学10个最常用的日常英语表达！\n\n跟着我一起读，记住发音和用法～", tts_script="Hello！今天我们来学十个最常用的日常英语表达，跟着我一起读！", duration_sec=6),
            Slide(title="1-3", formula="Hello!  →  你好！\nThank you!  →  谢谢！\nYou're welcome.  →  不客气。", tts_script="第一个：Hello，你好。第二个：Thank you，谢谢。第三个：You're welcome，不客气。", duration_sec=10),
            Slide(title="4-6", formula="Excuse me.  →  打扰一下。\nI'm sorry.  →  对不起。\nHow are you?  →  你好吗？", tts_script="第四个：Excuse me，打扰一下。第五个：I'm sorry，对不起。第六个：How are you，你好吗？", duration_sec=10),
            Slide(title="7-10", formula="Nice to meet you.  →  很高兴认识你。\nGood job!  →  做得好！\nI don't know.  →  我不知道。\nSee you later!  →  待会见！", tts_script="第七个：Nice to meet you，很高兴认识你。第八个：Good job，做得好。第九个：I don't know，我不知道。第十个：See you later，待会见。", duration_sec=14),
            Slide(title="📝 课堂小结", content="✅ 每天记2-3个新短语\n✅ 试着在生活中用英语表达\n✅ 反复练习，形成肌肉记忆！\n\nGood job, everyone!", tts_script="每天记两三个新短语，试着在生活中用英语表达，反复练习形成肌肉记忆。Good job everyone！", duration_sec=10),
        ]
    ),

    # ========== 语文 ==========
    "essay_writing": Lesson(
        id="essay_writing", subject="语文", grade="小学高年级 / 初中",
        title="作文写作三步法",
        intro="开头点题 → 中间展开 → 结尾升华，配具体例子",
        slides=[
            Slide(title="✍️ 作文写作三步法", content="很多同学觉得作文难写，其实掌握了方法，写作文也可以很简单！\n\n今天教你「三步法」", tts_script="很多同学觉得作文难写，其实掌握了方法，写作文也可以很简单！今天教你三步法。", duration_sec=7),
            Slide(title="1️⃣ 开头：点题吸引人", content="开头要简短有力，可以用：\n\n• 一句名言\n• 一个有趣的问题\n• 一个生动的场景", formula="例：《我的妈妈》\n开头：\"妈妈的手上有许多茧，那是她每天为我做饭留下的痕迹。\"", tip="💡 开头1-2句话就够了，不要啰嗦", tts_script="第一步，开头要简短有力。可以用名言、问题或场景开头。比如写我的妈妈，可以这样开头：妈妈的手上有许多茧，那是她每天为我做饭留下的痕迹。开头一两句话就够了。", duration_sec=14),
            Slide(title="2️⃣ 中间：展开举例", content="中间是文章的主体，至少写2-3个具体事例。\n\n每个事例按「起因→经过→结果」来写", formula="例：《我的妈妈》中间：\n① 妈妈每天早起做早餐\n② 妈妈在我生病时整夜照顾我\n③ 妈妈陪我写作业到很晚", tip="💡 用具体的故事代替空洞的形容词", tts_script="第二步，中间是文章主体，至少写两到三个具体事例。每个事例按起因、经过、结果来写。比如写妈妈，可以写妈妈每天早起做早餐，生病时照顾我，陪我写作业。用具体故事代替空洞形容词。", duration_sec=15),
            Slide(title="3️⃣ 结尾：总结升华", content="结尾要回到主题，表达自己的感悟。\n\n可以写：\n• 我学到了什么\n• 我想对ta说什么\n• 我的感受", formula="例：《我的妈妈》\n结尾：\"妈妈的爱就像春雨，润物细无声。我长大了，也要像妈妈一样，成为一个温暖的人。\"", tts_script="第三步，结尾要回到主题，表达感悟。可以写我学到了什么，我想对ta说什么，或者我的感受。好的结尾能让文章升华，给读者留下深刻印象。", duration_sec=14),
            Slide(title="📝 课堂小结", content="✅ 开头：点题吸引人（1-2句）\n✅ 中间：2-3个具体事例\n✅ 结尾：总结升华，回到主题\n\n多读多写，自然越写越好！✍️", tts_script="总结：开头点题，中间具体事例，结尾总结升华。多读多写，自然越写越好！", duration_sec=10),
        ]
    ),

    # ========== 学习方法 ==========
    "study_methods": Lesson(
        id="study_methods", subject="学习方法", grade="通用",
        title="高效学习法",
        intro="番茄钟 + 费曼学习法 + 间隔复习，三大方法提升学习效率",
        slides=[
            Slide(title="📚 高效学习法", content="为什么有的同学学得又快又好？\n\n不是因为他们更聪明，而是因为他们有方法！\n\n今天分享三个最实用的学习方法", tts_script="为什么有的同学学得又快又好？不是因为他们更聪明，而是因为他们有方法！今天分享三个最实用的学习方法。", duration_sec=8),
            Slide(title="🍅 番茄钟学习法", content="25分钟专注学习 + 5分钟休息 = 一个番茄钟\n\n每4个番茄钟后，休息15-30分钟", formula="📱 推荐App：Forest、番茄ToDo、专注清单", tip="💡 关键：25分钟内只做一件事，绝不碰手机", tts_script="番茄钟学习法：25分钟专注学习，5分钟休息，这就是一个番茄钟。每四个番茄钟后，休息15到30分钟。关键是在25分钟内只做一件事，绝不碰手机。", duration_sec=12),
            Slide(title="👨‍🏫 费曼学习法", content="学完一个知识点后，假装给一个8岁小孩讲解。\n\n讲不清楚的地方 = 你没真懂的地方\n回去再学，直到能讲清楚为止！", formula="四步：\n1. 选一个概念\n2. 教给别人\n3. 发现卡壳 → 回去学\n4. 简化语言重讲", tip="💡 最好的学习方法就是教别人", tts_script="费曼学习法：学完一个知识点后，假装给一个8岁小孩讲解。讲不清楚的地方，就是你没真懂的地方，回去再学。最好的学习方法就是教别人！", duration_sec=14),
            Slide(title="🔄 间隔复习法", content="人的遗忘曲线：刚学完记得100%，1天后只剩33%\n\n对抗遗忘的方法：间隔复习", formula="当天 → 第二天 → 一周后 → 一月后\n每次复习只需要5-10分钟", tip="💡 复习比学新知识更重要！", tts_script="间隔复习法：刚学完记得100%，但一天后就只剩33%。对抗遗忘的方法就是间隔复习：当天学完，第二天复习，一周后再复习，一月后还复习。每次只需要5-10分钟。", duration_sec=14),
            Slide(title="📝 三个方法结合使用", formula="🍅 番茄钟 → 保证专注\n👨‍🏫 费曼法 → 保证理解\n🔄 间隔复习 → 保证不忘\n\n三管齐下，学习效率翻倍！", tts_script="三个方法结合使用：番茄钟保证专注，费曼法保证理解，间隔复习保证不忘。三管齐下，学习效率翻倍！", duration_sec=10),
        ]
    ),
}


# ============================================================
# 课程控制器
# ============================================================
class LessonController:
    """课程控制器：管理幻灯片播放、自动推进、TTS旁白"""

    def __init__(self, lesson_id: str):
        self.lesson = LESSONS.get(lesson_id)
        if not self.lesson:
            raise ValueError(f"课程不存在: {lesson_id}")

        self.current_slide = 0
        self.total_slides = len(self.lesson.slides)
        self.is_playing = False
        self.on_slide_change: Optional[Callable] = None
        self._timer: Optional[threading.Timer] = None

    def get_current_slide(self) -> Optional[Slide]:
        if 0 <= self.current_slide < self.total_slides:
            return self.lesson.slides[self.current_slide]
        return None

    def next_slide(self) -> Optional[Slide]:
        self.current_slide += 1
        slide = self.get_current_slide()
        if self.on_slide_change:
            self.on_slide_change(slide)
        return slide

    def prev_slide(self) -> Optional[Slide]:
        self.current_slide = max(0, self.current_slide - 1)
        slide = self.get_current_slide()
        if self.on_slide_change:
            self.on_slide_change(slide)
        return slide

    def go_to(self, index: int) -> Optional[Slide]:
        self.current_slide = max(0, min(index, self.total_slides - 1))
        slide = self.get_current_slide()
        if self.on_slide_change:
            self.on_slide_change(slide)
        return slide

    def auto_play(self, on_slide_change: Callable = None):
        """自动播放模式"""
        self.on_slide_change = on_slide_change
        self.is_playing = True
        self._play_next()

    def _play_next(self):
        if not self.is_playing:
            return
        slide = self.get_current_slide()
        if slide and self.on_slide_change:
            self.on_slide_change(slide)

        duration = slide.duration_sec if slide else 8
        self._timer = threading.Timer(duration, self._advance_and_play)
        self._timer.start()

    def _advance_and_play(self):
        self.current_slide += 1
        if self.current_slide < self.total_slides:
            self._play_next()
        else:
            self.is_playing = False
            if self.on_slide_change:
                self.on_slide_change(None)  # 课程结束

    def stop(self):
        self.is_playing = False
        if self._timer:
            self._timer.cancel()

    def to_dict(self):
        slide = self.get_current_slide()
        return {
            "lesson": {
                "id": self.lesson.id,
                "subject": self.lesson.subject,
                "grade": self.lesson.grade,
                "title": self.lesson.title,
                "intro": self.lesson.intro,
            },
            "current": self.current_slide,
            "total": self.total_slides,
            "slide": {
                "title": slide.title if slide else "",
                "content": slide.content if slide else "",
                "formula": slide.formula if slide else "",
                "example": slide.example if slide else "",
                "tip": slide.tip if slide else "",
                "tts_script": slide.tts_script if slide else "",
                "duration": slide.duration_sec if slide else 0,
            } if slide else None,
            "is_playing": self.is_playing,
            "is_finished": self.current_slide >= self.total_slides,
        }


# ============================================================
# HTTP API 服务器（供 OBS 浏览器源调用）
# ============================================================
def start_api_server(port: int = 8766):
    """启动 HTTP API 服务器"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json as _json

    controllers = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?")[0]

            if path == "/api/lessons":
                data = []
                for lid, lesson in LESSONS.items():
                    data.append({
                        "id": lid, "subject": lesson.subject,
                        "grade": lesson.grade, "title": lesson.title,
                        "intro": lesson.intro, "slides": len(lesson.slides),
                    })
                self._json(data)

            elif path == "/api/lesson":
                params = {}
                if "?" in self.path:
                    for p in self.path.split("?")[1].split("&"):
                        if "=" in p:
                            k, v = p.split("=", 1)
                            params[k] = v
                lid = params.get("id")
                if lid and lid in controllers:
                    self._json(controllers[lid].to_dict())
                else:
                    self._json({"error": "not found"}, 404)

            elif path == "/api/lesson/next":
                params = {}
                if "?" in self.path:
                    for p in self.path.split("?")[1].split("&"):
                        if "=" in p:
                            k, v = p.split("=", 1)
                            params[k] = v
                lid = params.get("id")
                if lid and lid in controllers:
                    controllers[lid].next_slide()
                    self._json(controllers[lid].to_dict())
                else:
                    self._json({"error": "not found"}, 404)

            elif path == "/api/lesson/prev":
                params = {}
                if "?" in self.path:
                    for p in self.path.split("?")[1].split("&"):
                        if "=" in p:
                            k, v = p.split("=", 1)
                            params[k] = v
                lid = params.get("id")
                if lid and lid in controllers:
                    controllers[lid].prev_slide()
                    self._json(controllers[lid].to_dict())
                else:
                    self._json({"error": "not found"}, 404)

            elif path == "/api/lesson/start":
                params = {}
                if "?" in self.path:
                    for p in self.path.split("?")[1].split("&"):
                        if "=" in p:
                            k, v = p.split("=", 1)
                            params[k] = v
                lid = params.get("id")
                if lid and lid in LESSONS:
                    controllers[lid] = LessonController(lid)
                    self._json(controllers[lid].to_dict())
                else:
                    self._json({"error": "not found"}, 404)

            elif path == "/":
                self._serve_html()

            else:
                self._json({"error": "not found"}, 404)

        def _json(self, data, code=200):
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(_json.dumps(data, ensure_ascii=False).encode("utf-8"))

        def _serve_html(self):
            html = generate_overlay_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"[Lesson API] 服务器启动: http://localhost:{port}")
    server.serve_forever()


def generate_overlay_html():
    return """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>小澍智能讲解</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:transparent;font-family:'Microsoft YaHei','PingFang SC',sans-serif;width:800px;height:600px;overflow:hidden}
.container{width:100%;height:100%;display:flex;flex-direction:column;padding:24px}

/* 顶部标题栏 */
.header{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.avatar{font-size:36px;animation:float 3s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
.header-info h2{color:#7ee787;font-size:20px;font-weight:bold}
.header-info span{color:#8b949e;font-size:12px}

/* 进度条 */
.progress-bar{height:3px;background:#21262d;border-radius:2px;margin-bottom:20px;overflow:hidden}
.progress-fill{height:100%;background:linear-gradient(90deg,#238636,#7ee787);transition:width 0.5s ease}

/* 幻灯片主体 */
.slide-area{flex:1;display:flex;flex-direction:column;gap:12px}
.slide-title{color:#7ee787;font-size:22px;font-weight:bold;padding-bottom:8px;border-bottom:2px solid #238636}
.slide-content{color:#c9d1d9;font-size:15px;line-height:1.8;white-space:pre-line}

/* 公式区 */
.formula-box{background:rgba(35,134,54,0.1);border:1px solid #238636;border-radius:8px;padding:16px 20px;font-size:18px;color:#7ee787;font-family:'Consolas','Microsoft YaHei',monospace;white-space:pre-line;line-height:1.8;text-align:center}

/* 例题区 */
.example-box{background:rgba(88,166,255,0.08);border:1px solid #58a6ff;border-radius:8px;padding:12px 16px;font-size:16px;color:#58a6ff;font-family:'Consolas','Microsoft YaHei',monospace;white-space:pre-line;line-height:1.8}

/* 小贴士 */
.tip-box{background:rgba(210,153,34,0.1);border:1px solid #d29922;border-radius:8px;padding:10px 14px;font-size:13px;color:#d29922;display:flex;align-items:center;gap:8px}

/* 底部控制 */
.footer{display:flex;justify-content:space-between;align-items:center;margin-top:16px;padding-top:12px;border-top:1px solid #21262d}
.slide-counter{color:#8b949e;font-size:12px}
.controls{display:flex;gap:8px}
.btn{background:#21262d;border:1px solid #30363d;color:#c9d1d9;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;transition:all 0.2s}
.btn:hover{background:#30363d;border-color:#58a6ff}
.btn.active{background:#238636;border-color:#238636;color:white}
.btn.auto{background:#1f6feb;border-color:#1f6feb;color:white}

/* 动画 */
.fade-in{animation:fadeIn 0.4s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

/* 课程选择 */
.lesson-select{display:none;flex-direction:column;gap:8px;padding:20px}
.lesson-select h3{color:#7ee787;margin-bottom:8px}
.lesson-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px;cursor:pointer;transition:all 0.2s}
.lesson-card:hover{border-color:#238636;background:rgba(35,134,54,0.06)}
.lesson-card .sub{color:#7ee787;font-size:14px;font-weight:bold}
.lesson-card .grade{color:#8b949e;font-size:11px;margin-left:8px}
.lesson-card .intro{color:#8b949e;font-size:12px;margin-top:4px}
</style>
</head>
<body>
<div class="container" id="app">
  <div class="lesson-select" id="lesson-select">
    <h3>🌿 选择讲解主题</h3>
    <div id="lesson-list"></div>
  </div>

  <div id="slide-view" style="display:none;flex:1;display:flex;flex-direction:column">
    <div class="header">
      <div class="avatar">🌿</div>
      <div class="header-info">
        <h2 id="lesson-title">--</h2>
        <span id="lesson-subject">--</span>
      </div>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="progress" style="width:0%"></div></div>
    <div class="slide-area fade-in" id="slide-area">
      <div class="slide-title" id="stitle">--</div>
      <div class="slide-content" id="scontent"></div>
      <div class="formula-box" id="sformula" style="display:none"></div>
      <div class="example-box" id="sexample" style="display:none"></div>
      <div class="tip-box" id="stip" style="display:none"></div>
    </div>
    <div class="footer">
      <span class="slide-counter" id="counter">--</span>
      <div class="controls">
        <button class="btn" onclick="prevSlide()">⬅ 上一页</button>
        <button class="btn auto" id="auto-btn" onclick="toggleAuto()">▶ 自动播放</button>
        <button class="btn" onclick="nextSlide()">下一页 ➡</button>
      </div>
    </div>
  </div>
</div>
<script>
const API = 'http://localhost:8766';
let currentLesson = null;
let autoTimer = null;
let isAutoPlaying = false;

async function loadLessons() {
  const r = await fetch(API + '/api/lessons');
  const lessons = await r.json();
  const list = document.getElementById('lesson-list');
  const sel = document.getElementById('lesson-select');
  sel.style.display = 'flex';
  document.getElementById('slide-view').style.display = 'none';

  lessons.forEach(l => {
    const card = document.createElement('div');
    card.className = 'lesson-card';
    card.innerHTML = `<div class="sub">${l.subject} · ${l.title}</div>
      <div class="grade">${l.grade} | ${l.slides}页幻灯片</div>
      <div class="intro">${l.intro}</div>`;
    card.onclick = () => startLesson(l.id);
    list.appendChild(card);
  });
}

async function startLesson(id) {
  await fetch(API + '/api/lesson/start?id=' + id);
  currentLesson = id;
  document.getElementById('lesson-select').style.display = 'none';
  document.getElementById('slide-view').style.display = 'flex';
  refreshSlide();
}

async function refreshSlide() {
  const r = await fetch(API + '/api/lesson?id=' + currentLesson);
  const d = await r.json();
  if (!d.slide) return;

  document.getElementById('lesson-title').textContent = d.lesson.title;
  document.getElementById('lesson-subject').textContent = d.lesson.subject + ' · ' + d.lesson.grade;
  document.getElementById('counter').textContent = (d.current+1) + ' / ' + d.total;
  document.getElementById('progress').style.width = ((d.current+1)/d.total*100) + '%';

  const s = d.slide;
  document.getElementById('stitle').textContent = s.title;
  document.getElementById('scontent').textContent = s.content;
  document.getElementById('sformula').style.display = s.formula ? 'block' : 'none';
  document.getElementById('sformula').textContent = s.formula;
  document.getElementById('sexample').style.display = s.example ? 'block' : 'none';
  document.getElementById('sexample').textContent = s.example;
  document.getElementById('stip').style.display = s.tip ? 'flex' : 'none';
  document.getElementById('stip').textContent = s.tip;

  // Re-trigger animation
  const area = document.getElementById('slide-area');
  area.classList.remove('fade-in');
  void area.offsetWidth;
  area.classList.add('fade-in');
}

async function nextSlide() {
  const r = await fetch(API + '/api/lesson/next?id=' + currentLesson);
  const d = await r.json();
  if (d.is_finished) {
    if (isAutoPlaying) toggleAuto();
    return;
  }
  refreshSlide();
}

async function prevSlide() {
  await fetch(API + '/api/lesson/prev?id=' + currentLesson);
  refreshSlide();
}

function toggleAuto() {
  if (isAutoPlaying) {
    clearInterval(autoTimer);
    isAutoPlaying = false;
    document.getElementById('auto-btn').textContent = '▶ 自动播放';
    document.getElementById('auto-btn').classList.remove('active');
  } else {
    isAutoPlaying = true;
    document.getElementById('auto-btn').textContent = '⏸ 停止';
    document.getElementById('auto-btn').classList.add('active');
    autoAdvance();
  }
}

async function autoAdvance() {
  if (!isAutoPlaying) return;
  const r = await fetch(API + '/api/lesson?id=' + currentLesson);
  const d = await r.json();
  const dur = (d.slide ? d.slide.duration : 8) * 1000;
  await nextSlide();
  if (isAutoPlaying) {
    autoTimer = setTimeout(autoAdvance, dur);
  }
}

loadLessons();
</script>
</body>
</html>"""


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()

    print("=" * 50)
    print("  🌿 LumiLearn 智能讲解系统")
    print(f"  API: http://localhost:{args.port}")
    print(f"  OBS: 添加浏览器源，URL=http://localhost:{args.port}")
    print("=" * 50)
    print(f"\n  可用课程 ({len(LESSONS)}门):")
    for lid, lesson in LESSONS.items():
        print(f"    {lesson.subject} · {lesson.title} ({lesson.grade}) [{len(lesson.slides)}页]")

    start_api_server(args.port)