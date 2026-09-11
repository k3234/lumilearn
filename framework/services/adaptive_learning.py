# -*- coding: utf-8 -*-
"""
自适应学习引擎
知识图谱 + 进度追踪 + 智能推荐 + 动态学习路径

核心功能：
- 知识图谱：知识点之间的依赖关系
- 进度追踪：用户学习记录和掌握程度
- 薄弱点分析：识别需要加强的知识点
- 智能推荐：基于当前水平的个性化推荐
- 学习路径：动态生成最优学习顺序

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-06
"""

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class KnowledgeNode:
    """知识图谱节点"""
    id: str
    name: str
    category: str  # geometry, algebra, physics, calculus, statistics
    difficulty: int  # 1-5
    prerequisites: List[str] = field(default_factory=list)
    animation_type: str = "auto"  # 对应的动画类型
    description: str = ""
    common_mistakes: List[str] = field(default_factory=list)


# ============================================================
# 知识图谱定义
# ============================================================

KNOWLEDGE_GRAPH: Dict[str, KnowledgeNode] = {
    # === 几何 ===
    "triangle_basics": KnowledgeNode(
        id="triangle_basics", name="三角形基础", category="geometry",
        difficulty=1, animation_type="geometry",
        description="三角形的定义、分类、内角和"
    ),
    "pythagorean": KnowledgeNode(
        id="pythagorean", name="勾股定理", category="geometry",
        difficulty=2, prerequisites=["triangle_basics"], animation_type="geometry",
        description="直角三角形的边长关系"
    ),
    "circle_area": KnowledgeNode(
        id="circle_area", name="圆面积", category="geometry",
        difficulty=2, prerequisites=["triangle_basics"], animation_type="geometry",
        description="圆的面积公式推导"
    ),
    "cosine_rule": KnowledgeNode(
        id="cosine_rule", name="余弦定理", category="geometry",
        difficulty=3, prerequisites=["pythagorean"], animation_type="geometry",
        description="任意三角形的边长与角度关系"
    ),

    # === 代数 ===
    "quadratic_formula": KnowledgeNode(
        id="quadratic_formula", name="求根公式", category="algebra",
        difficulty=2, animation_type="formula",
        description="一元二次方程的求根公式推导"
    ),
    "completing_square": KnowledgeNode(
        id="completing_square", name="配方法", category="algebra",
        difficulty=2, prerequisites=["quadratic_formula"], animation_type="formula",
        description="通过配方解二次方程"
    ),
    "polynomial": KnowledgeNode(
        id="polynomial", name="多项式运算", category="algebra",
        difficulty=3, prerequisites=["quadratic_formula"], animation_type="formula",
        description="多项式的加减乘除和因式分解"
    ),

    # === 函数 ===
    "linear_function": KnowledgeNode(
        id="linear_function", name="一次函数", category="functions",
        difficulty=1, animation_type="functions",
        description="y=kx+b 的图像与性质"
    ),
    "quadratic_function": KnowledgeNode(
        id="quadratic_function", name="二次函数", category="functions",
        difficulty=2, prerequisites=["linear_function", "quadratic_formula"],
        animation_type="functions",
        description="y=ax²+bx+c 的图像与性质"
    ),

    # === 物理 ===
    "free_fall": KnowledgeNode(
        id="free_fall", name="自由落体", category="physics",
        difficulty=2, prerequisites=["quadratic_function"], animation_type="physics",
        description="匀加速直线运动"
    ),
    "light_refraction": KnowledgeNode(
        id="light_refraction", name="光的折射", category="physics",
        difficulty=3, prerequisites=["triangle_basics"], animation_type="physics",
        description="斯涅尔定律与折射现象"
    ),

    # === 统计 ===
    "mean_median": KnowledgeNode(
        id="mean_median", name="均值与中位数", category="statistics",
        difficulty=1, animation_type="statistics",
        description="描述性统计基础"
    ),
    "normal_distribution": KnowledgeNode(
        id="normal_distribution", name="正态分布", category="statistics",
        difficulty=3, prerequisites=["mean_median"], animation_type="statistics",
        description="正态分布的性质与应用",
        common_mistakes=["混淆标准差与方差的概念", "误用正态分布表格查找概率"]
    ),

    # === 集合与逻辑 ===
    "set_concepts": KnowledgeNode(
        id="set_concepts", name="集合概念", category="algebra",
        difficulty=1, animation_type="formula",
        description="集合的定义、表示方法与基本性质",
        common_mistakes=["遗漏空集是任何集合的子集", "混淆元素与集合的关系符号∈和⊆"]
    ),
    "set_intersection_union": KnowledgeNode(
        id="set_intersection_union", name="交集与并集", category="algebra",
        difficulty=1, prerequisites=["set_concepts"], animation_type="formula",
        description="集合的交集、并集运算及Venn图表示",
        common_mistakes=["将交集与并集的定义混淆", "韦恩图中区域划分错误"]
    ),
    "set_complement": KnowledgeNode(
        id="set_complement", name="补集运算", category="algebra",
        difficulty=2, prerequisites=["set_intersection_union"], animation_type="formula",
        description="全集与补集的定义及德摩根定律",
        common_mistakes=["忽略全集的限定范围", "德摩根定律符号遗漏负号"]
    ),
    "sufficient_necessary": KnowledgeNode(
        id="sufficient_necessary", name="充分必要条件", category="algebra",
        difficulty=2, prerequisites=["set_concepts"], animation_type="formula",
        description="充分条件、必要条件与充要条件的判定",
        common_mistakes=["将充分条件与必要条件颠倒", "混淆推论方向p→q与q→p"]
    ),
    "proposition_quantifier": KnowledgeNode(
        id="proposition_quantifier", name="命题与量词", category="algebra",
        difficulty=2, prerequisites=["set_concepts"], animation_type="formula",
        description="全称量词与存在量词及其否定",
        common_mistakes=["否定全称命题时遗漏存在量词", "命题否定与否命题概念混淆"]
    ),
    "inequality_solving": KnowledgeNode(
        id="inequality_solving", name="不等式求解", category="algebra",
        difficulty=2, prerequisites=["quadratic_formula"], animation_type="formula",
        description="一元二次不等式与分式不等式的解法",
        common_mistakes=["不等式两边同乘负数未变号", "分式不等式未考虑分母为零的情况"]
    ),

    # === 函数与导数 ===
    "function_concept": KnowledgeNode(
        id="function_concept", name="函数概念", category="functions",
        difficulty=1, animation_type="functions",
        description="函数的定义、三要素与对应关系",
        common_mistakes=["忽略函数的定义域限制", "将多值对应误认为函数"]
    ),
    "domain_range": KnowledgeNode(
        id="domain_range", name="定义域与值域", category="functions",
        difficulty=2, prerequisites=["function_concept"], animation_type="functions",
        description="求函数定义域和值域的方法",
        common_mistakes=["开根号下未要求≥0", "对数真数未要求>0"]
    ),
    "function_monotonicity": KnowledgeNode(
        id="function_monotonicity", name="函数单调性", category="functions",
        difficulty=2, prerequisites=["linear_function", "quadratic_function"], animation_type="functions",
        description="单调递增与单调递减的定义与判定",
        common_mistakes=["将单调区间写成并集形式", "复合函数单调性判断规则记错"]
    ),
    "function_parity": KnowledgeNode(
        id="function_parity", name="函数奇偶性", category="functions",
        difficulty=2, prerequisites=["function_concept"], animation_type="functions",
        description="奇函数与偶函数的定义与图像性质",
        common_mistakes=["忽略定义域关于原点对称的前提", "奇偶性与周期性混淆"]
    ),
    "exponential_function": KnowledgeNode(
        id="exponential_function", name="指数函数", category="functions",
        difficulty=2, prerequisites=["function_concept"], animation_type="functions",
        description="指数函数的图像、性质与应用",
        common_mistakes=["底数范围a>0且a≠1的条件遗漏", "指数运算法则与幂运算混淆"]
    ),
    "logarithm_function": KnowledgeNode(
        id="logarithm_function", name="对数函数", category="functions",
        difficulty=2, prerequisites=["exponential_function"], animation_type="functions",
        description="对数的运算性质与对数函数图像",
        common_mistakes=["log(a+b)≠log a + log b", "换底公式符号方向错误"]
    ),
    "inverse_function": KnowledgeNode(
        id="inverse_function", name="反函数", category="functions",
        difficulty=3, prerequisites=["exponential_function", "logarithm_function"], animation_type="functions",
        description="反函数的概念与求法，指数与对数互为反函数",
        common_mistakes=["忽略原函数单调性要求", "图像关于y=x对称的对应关系搞错"]
    ),
    "derivative_concept": KnowledgeNode(
        id="derivative_concept", name="导数定义", category="functions",
        difficulty=3, prerequisites=["function_monotonicity"], animation_type="functions",
        description="导数的极限定义与几何意义",
        common_mistakes=["混淆平均变化率与瞬时变化率", "求导公式记忆错误，如(x^n)'=x^(n-1)"]
    ),
    "derivative_application": KnowledgeNode(
        id="derivative_application", name="导数应用", category="functions",
        difficulty=3, prerequisites=["derivative_concept"], animation_type="functions",
        description="利用导数研究函数的单调性与极值",
        common_mistakes=["未检查导数为零的点两侧符号变化", "导数不存在点遗漏"]
    ),
    "extreme_values": KnowledgeNode(
        id="extreme_values", name="极值与最值", category="functions",
        difficulty=3, prerequisites=["derivative_application"], animation_type="functions",
        description="函数极值、最值的求法与判定",
        common_mistakes=["极值点与最值点概念混淆", "闭区间最值未比较端点与极值"]
    ),
    "tangent_line": KnowledgeNode(
        id="tangent_line", name="切线方程", category="functions",
        difficulty=2, prerequisites=["derivative_concept"], animation_type="functions",
        description="曲线在某点的切线方程求法",
        common_mistakes=["将切点与定点混淆", "斜率计算错误"]
    ),

    # === 三角函数 ===
    "arbitrary_angle": KnowledgeNode(
        id="arbitrary_angle", name="任意角", category="geometry",
        difficulty=1, animation_type="geometry",
        description="正角、负角、零角与象限角的定义",
        common_mistakes=["象限角范围写错", "混淆终边相同角与相等角"]
    ),
    "radian_system": KnowledgeNode(
        id="radian_system", name="弧度制", category="geometry",
        difficulty=1, prerequisites=["arbitrary_angle"], animation_type="geometry",
        description="弧度与角度的换算及弧长扇形面积公式",
        common_mistakes=["弧度与角度换算时遗漏π", "弧长公式l=αr中α未用弧度"]
    ),
    "trig_definitions": KnowledgeNode(
        id="trig_definitions", name="三角函数定义", category="geometry",
        difficulty=2, prerequisites=["radian_system"], animation_type="geometry",
        description="任意角的正弦、余弦、正切定义",
        common_mistakes=["三角函数值符号判断错误", "单位圆上坐标对应关系搞错"]
    ),
    "trig_induction": KnowledgeNode(
        id="trig_induction", name="诱导公式", category="geometry",
        difficulty=2, prerequisites=["trig_definitions"], animation_type="geometry",
        description="奇变偶不变，符号看象限的诱导公式",
        common_mistakes=["诱导公式符号判断错误", "函数名是否改变记错"]
    ),
    "trig_graph_property": KnowledgeNode(
        id="trig_graph_property", name="三角函数图像性质", category="geometry",
        difficulty=2, prerequisites=["trig_definitions"], animation_type="functions",
        description="y=sin x, y=cos x, y=tan x 的图像与性质",
        common_mistakes=["周期公式T=2π/ω中ω遗漏", "相位平移方向判断反"]
    ),
    "trig_transform": KnowledgeNode(
        id="trig_transform", name="三角恒等变换", category="geometry",
        difficulty=3, prerequisites=["trig_induction"], animation_type="formula",
        description="和差角公式、二倍角公式与辅助角公式",
        common_mistakes=["二倍角公式记忆错误", "辅助角公式asin x+bcos x变换遗漏"]
    ),
    "solve_triangle": KnowledgeNode(
        id="solve_triangle", name="解三角形", category="geometry",
        difficulty=3, prerequisites=["sine_rule", "cosine_rule"], animation_type="geometry",
        description="利用正弦定理和余弦定理解三角形",
        common_mistakes=["正弦定理多解情况遗漏", "余弦定理求角时角度范围判断错误"]
    ),
    "sine_rule": KnowledgeNode(
        id="sine_rule", name="正弦定理", category="geometry",
        difficulty=2, prerequisites=["trig_definitions"], animation_type="geometry",
        description="a/sinA=b/sinB=c/sinC=2R及其应用",
        common_mistakes=["外接圆半径R与直径2R混淆", "已知两边一角求角时多解情况遗漏"]
    ),

    # === 数列 ===
    "arithmetic_sequence": KnowledgeNode(
        id="arithmetic_sequence", name="等差数列", category="algebra",
        difficulty=2, animation_type="formula",
        description="等差数列的通项公式与性质",
        common_mistakes=["通项公式an=a1+(n-1)d中(n-1)写成n", "前n项和公式Sn=n(a1+an)/2与n/2[a1+an]混淆"]
    ),
    "geometric_sequence": KnowledgeNode(
        id="geometric_sequence", name="等比数列", category="algebra",
        difficulty=2, prerequisites=["arithmetic_sequence"], animation_type="formula",
        description="等比数列的通项公式与性质",
        common_mistakes=["公比q=1的情况遗漏", "等比数列求和公式中q≠1的前提忽略"]
    ),
    "sequence_sum": KnowledgeNode(
        id="sequence_sum", name="数列求和", category="algebra",
        difficulty=3, prerequisites=["arithmetic_sequence", "geometric_sequence"], animation_type="formula",
        description="错位相减法、裂项相消法、分组求和法",
        common_mistakes=["错位相减时末项符号处理错误", "裂项相消后剩余项判断错误"]
    ),
    "sequence_recursion": KnowledgeNode(
        id="sequence_recursion", name="递推公式", category="algebra",
        difficulty=3, prerequisites=["arithmetic_sequence"], animation_type="formula",
        description="由递推关系求数列通项的方法",
        common_mistakes=["累加法与累乘法适用条件混淆", "构造等比数列时常数项遗漏"]
    ),
    "math_induction": KnowledgeNode(
        id="math_induction", name="数学归纳法", category="algebra",
        difficulty=3, prerequisites=["sequence_recursion"], animation_type="formula",
        description="数学归纳法的两个步骤及其应用",
        common_mistakes=["归纳递推时n=k+1的变形遗漏", "第一步验证n的起始值错误"]
    ),
    "sequence_limit": KnowledgeNode(
        id="sequence_limit", name="数列极限", category="algebra",
        difficulty=3, prerequisites=["geometric_sequence"], animation_type="formula",
        description="数列极限的概念与常见极限",
        common_mistakes=["|q|<1时等比数列极限为0的条件遗漏", "极限四则运算使用条件忽视"]
    ),

    # === 向量 ===
    "vector_concept": KnowledgeNode(
        id="vector_concept", name="向量概念", category="geometry",
        difficulty=1, animation_type="geometry",
        description="向量的定义、表示方法与零向量、单位向量",
        common_mistakes=["混淆向量与数量的区别", "向量方向判断错误"]
    ),
    "vector_linear_op": KnowledgeNode(
        id="vector_linear_op", name="向量线性运算", category="geometry",
        difficulty=2, prerequisites=["vector_concept"], animation_type="geometry",
        description="向量加法、减法与数乘运算",
        common_mistakes=["三角形法则首尾相连方向错误", "平行四边形法则对角线对应向量搞错"]
    ),
    "vector_dot_product": KnowledgeNode(
        id="vector_dot_product", name="向量数量积", category="geometry",
        difficulty=2, prerequisites=["vector_linear_op"], animation_type="geometry",
        description="向量数量积的定义、性质与投影",
        common_mistakes=["数量积结果误认为是向量", "a·b=0时忽略a=0或b=0或垂直三种情况"]
    ),
    "vector_coordinate": KnowledgeNode(
        id="vector_coordinate", name="向量坐标运算", category="geometry",
        difficulty=2, prerequisites=["vector_linear_op"], animation_type="geometry",
        description="平面向量的坐标表示与运算",
        common_mistakes=["坐标运算时符号遗漏", "向量模长公式√(x²+y²)计算错误"]
    ),
    "vector_fundamental": KnowledgeNode(
        id="vector_fundamental", name="平面向量基本定理", category="geometry",
        difficulty=3, prerequisites=["vector_coordinate"], animation_type="geometry",
        description="平面向量基本定理与基底表示",
        common_mistakes=["基底不共线的条件遗漏", "坐标表示不唯一时混淆"]
    ),

    # === 概率统计 ===
    "counting_principle": KnowledgeNode(
        id="counting_principle", name="计数原理", category="statistics",
        difficulty=1, animation_type="statistics",
        description="分类加法计数与分步乘法计数原理",
        common_mistakes=["分类与分步混淆", "重复计数或遗漏情况"]
    ),
    "permutation_combination": KnowledgeNode(
        id="permutation_combination", name="排列组合", category="statistics",
        difficulty=2, prerequisites=["counting_principle"], animation_type="statistics",
        description="排列数与组合数公式及经典模型",
        common_mistakes=["A(n,m)与C(n,m)公式混淆", "捆绑法与插空法适用场景判断错误"]
    ),
    "probability_definition": KnowledgeNode(
        id="probability_definition", name="概率定义", category="statistics",
        difficulty=2, prerequisites=["counting_principle"], animation_type="statistics",
        description="古典概型与几何概型的概率计算",
        common_mistakes=["古典概型基本事件数计算错误", "几何概型测度选取错误"]
    ),
    "conditional_probability": KnowledgeNode(
        id="conditional_probability", name="条件概率", category="statistics",
        difficulty=3, prerequisites=["probability_definition"], animation_type="statistics",
        description="条件概率公式P(B|A)=P(AB)/P(A)与独立性",
        common_mistakes=["混淆条件概率与积事件概率", "独立事件与互斥事件概念混淆"]
    ),
    "random_variable": KnowledgeNode(
        id="random_variable", name="离散型随机变量", category="statistics",
        difficulty=3, prerequisites=["conditional_probability"], animation_type="statistics",
        description="离散型随机变量的分布列与期望方差",
        common_mistakes=["分布列概率之和不等于1", "期望与方差的计算公式混淆"]
    ),
    "binomial_distribution": KnowledgeNode(
        id="binomial_distribution", name="二项分布", category="statistics",
        difficulty=3, prerequisites=["random_variable"], animation_type="statistics",
        description="二项分布B(n,p)的分布列、期望与方差",
        common_mistakes=["C(n,k)p^k(1-p)^(n-k)中指数计算错误", "期望公式E(X)=np与方差D(X)=np(1-p)记错"]
    ),
    "normal_distribution_node": KnowledgeNode(
        id="normal_distribution_node", name="正态分布", category="statistics",
        difficulty=3, prerequisites=["random_variable"], animation_type="statistics",
        description="正态分布N(μ,σ²)的性质与3σ原则",
        common_mistakes=["σ与σ²混淆", "3σ原则概率值记忆错误"]
    ),
    "statistics_charts": KnowledgeNode(
        id="statistics_charts", name="统计图表", category="statistics",
        difficulty=1, animation_type="statistics",
        description="频率分布直方图、茎叶图与散点图",
        common_mistakes=["直方图纵轴是频率/组距而非频率", "茎叶图茎叶顺序颠倒"]
    ),
    "regression_analysis": KnowledgeNode(
        id="regression_analysis", name="回归分析", category="statistics",
        difficulty=3, prerequisites=["mean_median"], animation_type="statistics",
        description="线性回归方程的求法与相关性检验",
        common_mistakes=["回归直线必过样本中心点( x̄, ȳ )", "相关系数r的正负与相关性判断错误"]
    ),

    # === 解析几何 ===
    "line_equation": KnowledgeNode(
        id="line_equation", name="直线方程", category="geometry",
        difficulty=2, animation_type="geometry",
        description="直线的点斜式、斜截式、一般式及距离公式",
        common_mistakes=["斜率不存在的情况遗漏", "点到直线距离公式分母漏√(A²+B²)"]
    ),
    "circle_equation": KnowledgeNode(
        id="circle_equation", name="圆的方程", category="geometry",
        difficulty=2, prerequisites=["line_equation"], animation_type="geometry",
        description="圆的标准方程与一般方程及直线与圆的位置关系",
        common_mistakes=["圆的标准方程中(a,b)符号搞错", "直线与圆相交弦长公式遗漏"]
    ),
    "ellipse": KnowledgeNode(
        id="ellipse", name="椭圆", category="geometry",
        difficulty=3, prerequisites=["circle_equation"], animation_type="geometry",
        description="椭圆的定义、标准方程与几何性质",
        common_mistakes=["a²=b²+c²与c²=a²-b²混淆", "焦点位置判断错误导致方程写错"]
    ),
    "hyperbola": KnowledgeNode(
        id="hyperbola", name="双曲线", category="geometry",
        difficulty=3, prerequisites=["ellipse"], animation_type="geometry",
        description="双曲线的定义、标准方程与渐近线",
        common_mistakes=["a²+b²=c²的关系与椭圆混淆", "渐近线方程y=±(b/a)x符号写错"]
    ),
    "parabola": KnowledgeNode(
        id="parabola", name="抛物线", category="geometry",
        difficulty=3, prerequisites=["hyperbola"], animation_type="geometry",
        description="抛物线的定义、标准方程与几何性质",
        common_mistakes=["四种标准方程形式混淆", "焦点到准线的距离p与方程系数关系搞错"]
    ),
    "coordinate_transform": KnowledgeNode(
        id="coordinate_transform", name="坐标变换", category="geometry",
        difficulty=3, prerequisites=["line_equation"], animation_type="geometry",
        description="坐标平移与旋转变换",
        common_mistakes=["平移方向与坐标变化符号相反", "旋转变换公式记忆错误"]
    ),
    "conic_section_summary": KnowledgeNode(
        id="conic_section_summary", name="圆锥曲线综合", category="geometry",
        difficulty=4, prerequisites=["ellipse", "hyperbola", "parabola"], animation_type="geometry",
        description="椭圆、双曲线、抛物线的综合应用与统一定义",
        common_mistakes=["离心率e的范围搞错", "统一定义中焦点与准线对应关系混淆"]
    ),
}


class AdaptiveLearningEngine:
    """自适应学习引擎"""

    def __init__(self, data_dir: str = "data/learning"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.graph = KNOWLEDGE_GRAPH.copy()
        self._progress: Dict[str, Dict] = {}
        self._profiles: Dict[str, Dict] = {}
        self._load_progress()

    # ============================================================
    # 进度管理
    # ============================================================

    def _progress_file(self) -> Path:
        return self.data_dir / "learning_progress.json"

    def _load_progress(self):
        """加载学习进度"""
        pf = self._progress_file()
        if pf.exists():
            try:
                self._progress = json.loads(pf.read_text("utf-8"))
            except (json.JSONDecodeError, IOError):
                self._progress = {}

    def _save_progress(self):
        """保存学习进度"""
        self._progress_file().write_text(
            json.dumps(self._progress, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def record_learning(self, user_id: str, node_id: str,
                        score: float = 1.0, time_spent: float = 0):
        """
        记录学习活动

        Args:
            user_id: 用户标识
            node_id: 知识点ID
            score: 学习得分 (0-1)
            time_spent: 学习时长（秒）
        """
        uid = user_id or "default"
        if uid not in self._progress:
            self._progress[uid] = {"nodes": {}, "history": []}

        node = self.graph.get(node_id)
        if not node:
            return

        # 更新节点掌握度
        if node_id not in self._progress[uid]["nodes"]:
            self._progress[uid]["nodes"][node_id] = {
                "mastery": 0.0,
                "attempts": 0,
                "total_time": 0,
                "last_study": None
            }

        entry = self._progress[uid]["nodes"][node_id]
        # 指数移动平均更新掌握度
        alpha = 0.3
        entry["mastery"] = entry["mastery"] * (1 - alpha) + score * alpha
        entry["attempts"] += 1
        entry["total_time"] += time_spent
        entry["last_study"] = time.time()

        # 记录历史
        self._progress[uid]["history"].append({
            "node_id": node_id,
            "score": score,
            "time_spent": time_spent,
            "timestamp": time.time()
        })

        self._save_progress()

    def get_progress(self, user_id: str = "default") -> Dict:
        """获取用户学习进度"""
        uid = user_id or "default"
        progress = self._progress.get(uid, {"nodes": {}, "history": []})

        # 计算总体统计
        nodes = progress.get("nodes", {})
        total_nodes = len(self.graph)
        mastered = sum(1 for n in nodes.values() if n.get("mastery", 0) >= 0.8)
        learning = sum(1 for n in nodes.values() if 0.3 <= n.get("mastery", 0) < 0.8)

        return {
            "user_id": uid,
            "total_knowledge_nodes": total_nodes,
            "studied_nodes": len(nodes),
            "mastered_nodes": mastered,
            "learning_nodes": learning,
            "not_started": total_nodes - len(nodes),
            "overall_progress": round(mastered / max(total_nodes, 1) * 100, 1),
            "nodes": {
                nid: {
                    "name": self.graph[nid].name if nid in self.graph else nid,
                    "category": self.graph[nid].category if nid in self.graph else "unknown",
                    "difficulty": self.graph[nid].difficulty if nid in self.graph else 0,
                    **info
                }
                for nid, info in nodes.items()
            },
            "recent_history": progress.get("history", [])[-20:]
        }

    # ============================================================
    # 薄弱点分析
    # ============================================================

    def analyze_weaknesses(self, user_id: str = "default") -> List[Dict]:
        """分析薄弱知识点"""
        uid = user_id or "default"
        nodes = self._progress.get(uid, {}).get("nodes", {})

        weaknesses = []
        for node_id, info in nodes.items():
            mastery = info.get("mastery", 0)
            if mastery < 0.6:
                node = self.graph.get(node_id)
                if node:
                    weaknesses.append({
                        "node_id": node_id,
                        "name": node.name,
                        "category": node.category,
                        "difficulty": node.difficulty,
                        "mastery": round(mastery, 2),
                        "attempts": info.get("attempts", 0),
                        "severity": "high" if mastery < 0.3 else "medium"
                    })

        # 按掌握度排序（最低优先）
        weaknesses.sort(key=lambda x: x["mastery"])
        return weaknesses

    # ============================================================
    # 智能推荐
    # ============================================================

    def recommend_next(self, user_id: str = "default", count: int = 5) -> List[Dict]:
        """
        推荐下一个学习知识点

        策略：
        1. 优先推荐可学习（前置条件满足）的知识点
        2. 按难度和用户水平匹配
        3. 薄弱点优先
        """
        uid = user_id or "default"
        nodes = self._progress.get(uid, {}).get("nodes", {})

        # 计算用户平均水平
        if nodes:
            avg_mastery = sum(n["mastery"] for n in nodes.values()) / len(nodes)
        else:
            avg_mastery = 0

        candidates = []
        for node_id, node in self.graph.items():
            # 已掌握的跳过
            if nodes.get(node_id, {}).get("mastery", 0) >= 0.85:
                continue

            # 检查前置条件
            prereqs_met = True
            for prereq_id in node.prerequisites:
                if nodes.get(prereq_id, {}).get("mastery", 0) < 0.7:
                    prereqs_met = False
                    break

            if not prereqs_met:
                continue

            current_mastery = nodes.get(node_id, {}).get("mastery", 0)

            # 计算推荐分数
            score = 0.0
            # 难度匹配：推荐略高于当前水平的
            difficulty_match = 1.0 - abs(node.difficulty - (avg_mastery * 5 + 1)) / 5
            score += difficulty_match * 0.3
            # 薄弱点加分
            if current_mastery < 0.5:
                score += (0.5 - current_mastery) * 0.4
            # 未学习的新知识点加分
            if current_mastery == 0:
                score += 0.3

            candidates.append({
                "node_id": node_id,
                "name": node.name,
                "category": node.category,
                "difficulty": node.difficulty,
                "current_mastery": round(current_mastery, 2),
                "animation_type": node.animation_type,
                "description": node.description,
                "recommendation_score": round(score, 3)
            })

        # 按推荐分数排序
        candidates.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return candidates[:count]

    # ============================================================
    # 学习路径生成
    # ============================================================

    def generate_learning_path(self, user_id: str = "default",
                               target_category: str = None) -> List[Dict]:
        """
        生成最优学习路径

        使用拓扑排序 + 薄弱点优先策略
        """
        uid = user_id or "default"
        nodes = self._progress.get(uid, {}).get("nodes", {})

        # 过滤类别
        if target_category:
            available = {
                nid: node for nid, node in self.graph.items()
                if node.category == target_category
            }
        else:
            available = self.graph.copy()

        # 拓扑排序
        in_degree = {nid: len(node.prerequisites) for nid, node in available.items()}
        adj = defaultdict(list)
        for nid, node in available.items():
            for prereq in node.prerequisites:
                if prereq in available:
                    adj[prereq].append(nid)

        # 优先队列：薄弱点优先
        path = []
        visited = set()

        while len(path) < len(available):
            # 找入度为0的节点
            candidates = [nid for nid, deg in in_degree.items()
                          if deg == 0 and nid not in visited]

            if not candidates:
                # 有环或无法继续，加入剩余节点
                remaining = [nid for nid in available if nid not in visited]
                for nid in remaining:
                    node = available[nid]
                    path.append({
                        "node_id": nid,
                        "name": node.name,
                        "category": node.category,
                        "difficulty": node.difficulty,
                        "mastery": round(nodes.get(nid, {}).get("mastery", 0), 2),
                        "animation_type": node.animation_type,
                        "description": node.description,
                        "step": len(path) + 1
                    })
                    visited.add(nid)
                break

            # 按薄弱程度排序（掌握度低的优先）
            candidates.sort(key=lambda nid: nodes.get(nid, {}).get("mastery", 0))

            # 取第一个（最薄弱的）
            next_node = candidates[0]
            node = available[next_node]

            path.append({
                "node_id": next_node,
                "name": node.name,
                "category": node.category,
                "difficulty": node.difficulty,
                "mastery": round(nodes.get(next_node, {}).get("mastery", 0), 2),
                "animation_type": node.animation_type,
                "description": node.description,
                "step": len(path) + 1
            })

            visited.add(next_node)

            # 更新入度
            for neighbor in adj[next_node]:
                in_degree[neighbor] -= 1

            # 标记已处理
            in_degree[next_node] = -1

        return path

    # ============================================================
    # 知识图谱查询
    # ============================================================

    def get_knowledge_graph(self) -> Dict:
        """获取完整知识图谱"""
        nodes = []
        edges = []
        for nid, node in self.graph.items():
            nodes.append({
                "id": nid,
                "name": node.name,
                "category": node.category,
                "difficulty": node.difficulty,
                "animation_type": node.animation_type,
                "description": node.description
            })
            for prereq in node.prerequisites:
                edges.append({"from": prereq, "to": nid})

        return {
            "nodes": nodes,
            "edges": edges,
            "categories": list(set(n["category"] for n in nodes))
        }

    def get_node_detail(self, node_id: str) -> Optional[Dict]:
        """获取知识点详情"""
        node = self.graph.get(node_id)
        if not node:
            return None

        # 获取依赖关系
        dependents = [
            nid for nid, n in self.graph.items()
            if node_id in n.prerequisites
        ]

        return {
            "id": node.id,
            "name": node.name,
            "category": node.category,
            "difficulty": node.difficulty,
            "animation_type": node.animation_type,
            "description": node.description,
            "common_mistakes": node.common_mistakes,
            "prerequisites": [
                {"id": pid, "name": self.graph[pid].name}
                for pid in node.prerequisites if pid in self.graph
            ],
            "dependents": [
                {"id": did, "name": self.graph[did].name}
                for did in dependents
            ]
        }

    def get_statistics(self, user_id: str = "default") -> Dict:
        """获取学习统计"""
        uid = user_id or "default"
        nodes = self._progress.get(uid, {}).get("nodes", {})
        history = self._progress.get(uid, {}).get("history", [])

        # 类别统计
        category_stats = defaultdict(lambda: {"total": 0, "mastered": 0, "avg_mastery": 0})
        for nid, node in self.graph.items():
            cat = node.category
            category_stats[cat]["total"] += 1
            mastery = nodes.get(nid, {}).get("mastery", 0)
            if mastery >= 0.8:
                category_stats[cat]["mastered"] += 1
            category_stats[cat]["avg_mastery"] += mastery

        for cat in category_stats:
            total = category_stats[cat]["total"]
            if total > 0:
                category_stats[cat]["avg_mastery"] = round(
                    category_stats[cat]["avg_mastery"] / total, 2
                )

        # 时间统计
        total_time = sum(n.get("total_time", 0) for n in nodes.values())
        total_attempts = sum(n.get("attempts", 0) for n in nodes.values())

        # 最近学习
        recent = history[-10:] if history else []

        return {
            "user_id": uid,
            "total_study_time_seconds": round(total_time, 1),
            "total_attempts": total_attempts,
            "category_stats": dict(category_stats),
            "weaknesses_count": len(self.analyze_weaknesses(uid)),
            "recent_activity": recent
        }

    # ============================================================
    # 学习者画像系统
    # ============================================================

    def get_student_profile(self, user_id: str) -> Dict:
        """
        获取学生画像

        返回画像字典，包含掌握度、薄弱点、学习风格和错题历史。
        画像数据缓存在 self._profiles 中，避免重复计算。
        """
        uid = user_id or "default"
        if uid in self._profiles:
            return self._profiles[uid]

        nodes = self._progress.get(uid, {}).get("nodes", {})
        history = self._progress.get(uid, {}).get("history", [])

        mastery_scores = {
            nid: info.get("mastery", 0.0)
            for nid, info in nodes.items()
        }

        weak_points = [
            nid for nid, score in mastery_scores.items()
            if score < 0.4
        ]

        learning_style = self.infer_learning_style(history)

        error_history = [
            entry for entry in history
            if entry.get("score", 1.0) < 0.5
        ]

        profile = {
            "user_id": uid,
            "mastery_scores": mastery_scores,
            "weak_points": weak_points,
            "learning_style": learning_style,
            "error_history": error_history,
        }

        self._profiles[uid] = profile
        return profile

    def update_profile_after_learning(
        self, user_id: str, node_id: str, score: float, time_spent: float
    ):
        """
        学习活动后更新画像

        先调用现有的 record_learning 方法更新进度，
        然后清除该用户的画像缓存，使其在下次获取时重新计算。
        """
        self.record_learning(user_id, node_id, score, time_spent)
        self._profiles.pop(user_id or "default", None)

    def infer_learning_style(self, history: List[Dict]) -> str:
        """
        根据学习历史记录推断学习风格

        推断规则：
        - 答题速度快（time_spent<30s）且正确率高（score>=0.7） → "logical"
        - 答题慢但持续练习（time_spent>=30s 且 score<0.7 多次出现） → "practice"
        - 涉及几何/图形类知识点多（category="geometry"）       → "visual"
        - 默认返回 "visual"
        """
        if not history:
            return "visual"

        fast_correct = 0
        geometry_count = 0
        slow_attempts = 0
        total = len(history)

        for entry in history:
            node_id = entry.get("node_id", "")
            score = entry.get("score", 0.0)
            time_spent = entry.get("time_spent", 0.0)

            if time_spent > 0 and time_spent < 30 and score >= 0.7:
                fast_correct += 1

            node = self.graph.get(node_id)
            if node and node.category == "geometry":
                geometry_count += 1

            if time_spent >= 30 and score < 0.7:
                slow_attempts += 1

        if total > 0 and fast_correct / total >= 0.6:
            return "logical"

        if slow_attempts >= 2:
            return "practice"

        if total > 0 and geometry_count / total >= 0.4:
            return "visual"

        return "visual"


# 全局单例
_engine: Optional[AdaptiveLearningEngine] = None


def get_adaptive_engine() -> AdaptiveLearningEngine:
    """获取自适应学习引擎单例"""
    global _engine
    if _engine is None:
        _engine = AdaptiveLearningEngine()
    return _engine
