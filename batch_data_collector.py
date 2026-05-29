#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 大规模数据收集器
目标：从零训练需要10000+条高质量教育数据
"""
import sys, os, time, random, json, csv, re
from datetime import datetime
from collections import Counter
from difflib import SequenceMatcher

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from lumilearn_shared import read_existing_master, write_master_csv, generate_id, clean_text

TIANHONG = "http://192.168.2.63:11434"
MODEL = "qwen2.5:7b"

# ================================================================
# 全学科知识点库 - 9大核心学科
# ================================================================
KNOWLEDGE_BASE = {
    "数学": {
        "target": 600, "topics": [
            # 代数
            "一元二次方程", "二元一次方程组", "分式方程", "无理方程",
            "一次函数", "二次函数", "反比例函数", "指数函数", "对数函数",
            "幂函数", "三角函数基础", "任意角的三角函数", "三角恒等变换",
            # 几何
            "三角形全等", "三角形相似", "勾股定理", "锐角三角函数",
            "平行四边形", "矩形", "菱形", "正方形", "梯形",
            "圆的方程", "直线与圆的位置关系", "圆与圆的位置关系",
            "椭圆", "双曲线", "抛物线",
            "立体几何直线与平面", "线面垂直判定", "面面垂直判定",
            # 分析
            "函数的概念", "函数的单调性", "函数的奇偶性", "函数的周期性",
            "指数运算与对数运算", "数列的概念", "等差数列", "等比数列",
            "数列求和", "函数的极限", "导数的概念", "导数的计算",
            "导数的应用", "定积分", "不定积分",
            # 概率统计
            "排列", "组合", "二项式定理", "随机事件", "古典概型",
            "几何概型", "条件概率", "事件的独立性", "离散型随机变量",
            "二项分布", "正态分布", "统计估计", "回归分析",
        ]
    },
    "英语": {
        "target": 600, "topics": [
            # 语法
            "一般现在时", "现在进行时", "现在完成时", "现在完成进行时",
            "一般过去时", "过去进行时", "过去完成时",
            "一般将来时", "将来进行时", "将来完成时",
            "主动语态", "被动语态", "各种时态的被动语态",
            "情态动词can", "情态动词could", "情态动词may", "情态动词might",
            "情态动词must", "情态动词should", "情态动词would",
            "虚拟语气if从句", "虚拟语气倒装", "wish后的虚拟",
            "名词性从句", "定语从句", "状语从句", "同位语从句",
            "非谓语to do", "非谓语doing", "非谓语done",
            "独立主格", "with复合结构", "倒装句", "强调句",
            "主谓一致", "it用法", "省略与替代",
            # 词汇
            "词根词缀记忆法", "同义词辨析", "形近词辨析",
            "介词搭配in", "介词搭配on", "介词搭配at", "介词搭配for",
            "动词短语run", "动词短语take", "动词短语make", "动词短语get",
            # 阅读写作
            "阅读理解主旨题", "阅读理解细节题", "阅读理解推理题", "阅读理解词义题",
            "完形填空解题技巧", "七选五解题技巧",
            "应用文写作模板", "议论文写作框架", "读后续写技巧",
        ]
    },
    "语文": {
        "target": 600, "topics": [
            # 文言文
            "文言实词一词多义", "文言虚词之", "文言虚词乎", "文言虚词也",
            "文言虚词矣", "文言虚词哉", "文言虚词焉", "文言虚词于",
            "名词作动词", "名词作状语", "形容词作动词", "使动用法",
            "意动用法", "为动用法", "宾语前置", "状语后置",
            "定语后置", "判断句", "被动句", "省略句",
            # 古诗词
            "诗歌意象月亮", "诗歌意象柳树", "诗歌意象梅花", "诗歌意象菊花",
            "诗歌意象大雁", "诗歌意象杜鹃", "诗歌意象梧桐", "诗歌意象杨柳",
            "借景抒情", "托物言志", "用典手法", "对比手法",
            "比喻论证", "举例论证", "引用论证", "比喻修辞",
            # 现代文
            "散文线索分析", "散文主旨概括", "小说环境描写", "小说情节结构",
            "小说人物塑造", "戏剧冲突", "议论文论点", "议论文论据",
            "说明方法", "说明顺序",
            # 语言运用
            "病句类型", "病句辨析方法", "成语误用", "语言表达得体",
            "图文转换", "压缩语段", "仿写句子", "句式变换",
            # 写作
            "审题立意", "议论文结构", "记叙文技巧", "说明文写法",
        ]
    },
    "物理": {
        "target": 600, "topics": [
            # 力学
            "质点参考系", "位移速度加速度", "匀变速直线运动",
            "自由落体运动", "竖直上抛运动", "运动图像分析",
            "重力弹力摩擦力", "力的合成与分解", "共点力平衡",
            "牛顿第一定律", "牛顿第二定律", "牛顿第三定律",
            "受力分析", "动力学两类问题", "超重与失重",
            "曲线运动基础", "平抛运动", "匀速圆周运动",
            "向心力", "向心加速度", "万有引力定律",
            "天体运动", "人造卫星", "功和功率", "动能定理",
            "机械能守恒", "能量守恒定律", "动量冲量", "动量守恒",
            # 电学
            "电场强度", "电场线", "电势能", "电势",
            "电容器", "带电粒子在电场中运动", "电阻定律",
            "欧姆定律", "串并联电路", "电动势", "闭合电路欧姆定律",
            "电功率", "焦耳定律", "磁场", "磁感应强度",
            "安培力", "洛伦兹力", "带电粒子在磁场中运动",
            "电磁感应", "法拉第定律", "楞次定律", "自感",
            # 其他
            "机械振动", "简谐运动", "单摆", "受迫振动共振",
            "机械波", "横波纵波", "波的干涉", "波的衍射",
            "光的折射", "光的全反射", "光的干涉", "光的衍射",
            "热学基础", "分子动理论", "热力学第一定律", "热力学第二定律",
        ]
    },
    "化学": {
        "target": 600, "topics": [
            # 基础
            "物质的量", "气体摩尔体积", "阿伏加德罗定律",
            "物质的分类", "分散系", "电解质", "非电解质",
            "离子反应", "离子方程式", "离子共存",
            # 元素
            "钠及其化合物", "镁及其化合物", "铝及其化合物",
            "铁及其化合物", "铜及其化合物",
            "氯及其化合物", "硫及其化合物", "氮及其化合物",
            "碳及其化合物", "硅及其化合物",
            # 理论
            "原子结构", "核外电子排布", "元素周期律",
            "元素周期表", "化学键", "离子键", "共价键",
            "金属键", "分子间作用力", "氢键",
            "氧化还原反应", "氧化剂还原剂", "电子转移",
            "化学反应速率", "有效碰撞", "活化能",
            "化学平衡", "勒夏特列原理", "平衡常数",
            "电离平衡", "水的电离", "pH计算", "盐类水解",
            "难溶电解质溶解平衡",
            # 有机
            "甲烷结构", "烷烃性质", "乙烯结构", "烯烃性质",
            "乙炔结构", "炔烃性质", "苯结构", "苯的性质",
            "乙醇性质", "乙酸性质", "酯化反应",
            "糖类", "蛋白质", "油脂水解",
            # 实验
            "常见气体制备", "物质的分离", "物质的检验", "离子检验",
        ]
    },
    "生物": {
        "target": 600, "topics": [
            # 细胞
            "细胞学说", "细胞膜结构", "细胞膜功能", "细胞器",
            "线粒体", "叶绿体", "内质网", "高尔基体",
            "核糖体", "中心体", "液泡", "细胞核",
            "物质跨膜运输", "渗透作用", "质壁分离", "主动运输",
            "酶的作用", "酶的特性", "ATP结构", "ATP合成",
            "细胞呼吸", "有氧呼吸", "无氧呼吸", "呼吸作用应用",
            "光合作用", "光反应", "暗反应", "光合作用影响因素",
            # 遗传
            "减数分裂", "受精作用", "配子形成", "受精过程",
            "基因分离定律", "基因自由组合定律", "伴性遗传",
            "DNA结构", "DNA复制", "DNA功能", "DNA与RNA对比",
            "基因表达", "转录", "翻译", "中心法则",
            "基因突变", "染色体变异", "基因重组", "遗传病",
            # 调节
            "神经调节结构", "反射与反射弧", "兴奋传导", "兴奋传递",
            "体液调节", "激素调节", "反馈调节", "血糖调节",
            "体温调节", "水盐调节",
            "免疫系统", "非特异性免疫", "特异性免疫", "体液免疫",
            "细胞免疫", "免疫失调", "免疫应用",
            # 生态
            "种群特征", "种群数量增长", "群落特征", "群落演替",
            "生态系统结构", "生态系统功能", "能量流动", "物质循环",
            "信息传递", "生态平衡", "生物多样性", "环境保护",
        ]
    },
    "历史": {
        "target": 600, "topics": [
            # 中国古代
            "先秦政治", "商周制度", "春秋战国百家争鸣", "商鞅变法",
            "秦朝统一", "秦朝制度", "秦末农民战争",
            "汉朝休养生息", "汉武帝大一统", "丝绸之路",
            "三国两晋南北朝", "北魏孝文帝改革", "隋朝统一", "科举制度",
            "唐朝繁荣", "贞观之治", "开元盛世", "安史之乱",
            "宋元经济", "宋代中央集权", "元朝行省制度",
            "明朝专制", "明朝经济", "清朝专制", "康乾盛世",
            # 中国近现代
            "鸦片战争", "第二次鸦片战争", "太平天国运动",
            "洋务运动", "甲午战争", "戊戌变法", "义和团运动",
            "辛亥革命", "中华民国", "新文化运动", "五四运动",
            "中国共产党成立", "国民革命", "土地革命", "抗日战争",
            "解放战争", "新中国成立", "社会主义改造",
            "改革开放", "中国特色社会主义",
            # 世界古代
            "古希腊民主", "古罗马法律", "雅典民主政治",
            # 世界近代
            "文艺复兴", "宗教改革", "启蒙运动",
            "英国资产阶级革命", "美国独立", "法国大革命",
            "工业革命", "第二次工业革命", "工业革命影响",
            "马克思主义诞生", "巴黎公社",
            "十月革命", "一战", "二战",
            "冷战", "战后资本主义", "战后社会主义",
        ]
    },
    "地理": {
        "target": 600, "topics": [
            # 自然地理
            "地球形状", "地球经纬网", "地球运动", "时区计算",
            "大气组成", "大气分层", "大气受热过程", "热力环流",
            "风的形成", "气压带风带", "季风环流",
            "冷锋", "暖锋", "准静止锋", "气旋反气旋",
            "水循环", "海陆间循环", "洋流分类", "洋流分布",
            "内力作用", "外力作用", "岩石圈物质循环",
            "板块构造", "褶皱", "断层", "地质构造",
            "山岳地貌", "河流地貌", "海岸地貌", "冰川地貌",
            # 人文地理
            "人口增长", "人口分布", "人口迁移",
            "城市区位", "城市化", "城市问题",
            "农业区位", "农业分类", "农业地域类型",
            "工业区位", "工业分类", "工业地域形成",
            "交通运输", "交通布局",
            # 区域地理
            "中国地形", "中国气候", "中国河流", "中国资源",
            "北方地区", "南方地区", "西北地区", "青藏地区",
            "世界气候", "世界地形", "世界大洋",
            # 选修
            "自然灾害", "环境保护", "地理信息技术",
            "资源跨区域调配", "产业转移", "流域开发",
        ]
    },
    "政治": {
        "target": 600, "topics": [
            # 经济
            "商品", "货币", "价值规律", "价格",
            "消费", "消费心理", "消费原则",
            "生产与消费", "基本经济制度", "分配制度",
            "个人收入分配", "财政", "税收",
            "社会主义市场经济", "市场经济", "宏观调控",
            "小康经济", "新发展理念", "高质量发展",
            "经济全球化", "对外开放",
            # 政治
            "公民身份", "公民权利", "公民义务",
            "公民参与", "公民监督", "公民维权",
            "政府职能", "政府权力", "政府责任",
            "政府权威", "依法行政", "政府决策",
            "人民代表大会", "人大制度", "人大代表",
            "政党制度", "政协制度", "民族区域自治", "宗教信仰",
            "主权国家", "国际组织", "和平与发展",
            "中国外交", "人类命运共同体",
            # 文化
            "文化与社会", "文化影响", "文化多样性",
            "文化传承", "文化创新", "继承发展",
            "中华文化", "民族精神", "文化自信",
            "社会主义核心价值观", "精神文明建设",
            # 哲学
            "哲学基本问题", "唯物主义", "唯心主义",
            "物质", "意识", "物质与意识",
            "实践", "认识", "实践与认识",
            "真理", "真理标准", "认识发展",
            "联系", "发展", "矛盾", "否定之否定",
            "唯物辩证法", "认识论", "历史唯物主义",
        ]
    },
}

TARGET_TOTAL = 10000


def call_tianhong(prompt: str) -> str:
    try:
        r = requests.post(f"{TIANHONG}/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.4, "top_p": 0.9}},
            timeout=90)
        if r.status_code == 200:
            return r.json().get("response", "")
    except:
        pass
    return ""


class MassiveDataCollector:
    def __init__(self, target: int = 10000):
        self.target = target
        self.existing = read_existing_master()
        self.existing_ids = {r["id"] for r in self.existing}
        self.existing_texts = [r.get("content", "") for r in self.existing]
        self.counts = Counter(r.get("subject", "?") for r in self.existing)

    def _is_dup(self, text: str) -> bool:
        if not text or len(text) < 80:
            return True
        sample = random.sample(self.existing_texts, min(200, len(self.existing_texts)))
        for old in sample:
            if SequenceMatcher(None, text[:250], old[:250]).ratio() > 0.75:
                return True
        return False

    def _gen_one(self, subject: str, topic: str) -> str:
        prompt = f"""你是{subject}教育专家。请为"{topic}"生成高质量教学内容用于AI模型从零训练。

格式要求：
1. 核心概念定义（60-120字）
2. 3-5个关键知识点，每个50-100字
3. 2个具体示例
4. 1个常见误区
5. 学习建议

纯文本，总字数300-600字。"""

        content = call_tianhong(prompt)
        if not content or len(content) < 80:
            time.sleep(1)
            content = call_tianhong(prompt)
        if content:
            content = clean_text(content)
        return content

    def collect(self):
        print(f"\n{'='*70}")
        print(f"🚀 LumiLearn 大规模数据收集 (目标: {self.target}条)")
        print(f"{'='*70}")
        print(f"当前已有: {len(self.existing)} 条")

        total_added = 0

        # 按学科循环，直到达到目标
        while total_added < self.target - len(self.existing):
            for subject, info in KNOWLEDGE_BASE.items():
                current = self.counts.get(subject, 0)
                target = info["target"]
                topics = info["topics"]

                # 循环使用topics，直到达标
                cycle = 0
                while self.counts.get(subject, 0) < target:
                    topic = topics[cycle % len(topics)]
                    cycle += 1

                    content = self._gen_one(subject, topic)
                    if not content:
                        print(f"  ❌ {subject}/{topic} 生成失败")
                        time.sleep(2)
                        continue

                    if self._is_dup(content):
                        print(f"  ⏭️  {subject}/{topic} 重复")
                        continue

                    # 入库
                    rid = generate_id(self.existing_ids)
                    self.existing_ids.add(rid)
                    self.existing_texts.append(content)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    record = {
                        "id": rid, "subject": subject, "grade": "高中",
                        "version": "通用版", "chapter": topic, "section": topic,
                        "title": topic, "content": content, "content_format": "text",
                        "type": "知识点",
                        "difficulty": random.choice(["基础", "中等", "困难"]),
                        "source": f"大规模收集({MODEL}@天虹)",
                        "source_type": "massive_collect",
                        "tags": f"{subject},{topic}",
                        "deepseek_r1_15b": "AUTO", "qwen2_5_7b_p2": "AUTO",
                        "qwen2_5_7b_p3": "AUTO",
                        "check_time": now, "errors": "", "create_time": now,
                        "update_time": now,
                    }
                    self.existing.append(record)
                    self.counts[subject] = self.counts.get(subject, 0) + 1
                    total_added += 1

                    print(f"  ✅ {subject}/{topic} ({len(content)}字) "
                          f"[{self.counts[subject]}/{target}] "
                          f"[总计{len(self.existing)}条]")

                    time.sleep(0.3)

                    # 每20条保存一次
                    if total_added % 20 == 0:
                        write_master_csv(self.existing)
                        print(f"  💾 已保存 ({total_added}条)")

            # 检查是否达标
            if len(self.existing) >= self.target:
                break

        # 最终保存
        write_master_csv(self.existing)

        print(f"\n{'='*70}")
        print(f"🎉 收集完成! 新增{total_added}条, 总计{len(self.existing)}条")
        print(f"{'='*70}")
        print("\n最终分布:")
        for s, c in sorted(self.counts.items(), key=lambda x: x[1], reverse=True)[:12]:
            pct = c / len(self.existing) * 100
            print(f"  {s:10s}: {c:4d} ({pct:.1f}%)")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=10000,
                        help="目标数据量")
    args = parser.parse_args()

    collector = MassiveDataCollector(target=args.target)
    collector.collect()


if __name__ == "__main__":
    main()
