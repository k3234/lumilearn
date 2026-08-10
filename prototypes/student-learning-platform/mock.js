/* ============================================================
 * mock.js — LumiLearn 学生端原型 · 单一数据源
 * 跨页共享的假数据：历史会话 / 费曼五步教学文案库 / Agent 定义
 * 数据为演示用教学样例；未来由真实后端（lumilearn API）替代。
 * ============================================================ */

const DB = (() => {

  const SUBJECTS = ["数学", "物理", "化学", "生物"];

  /* ---------- Agent 定义（与 learn.html 协作面板一致） ---------- */
  const agentDefs = [
    { id: "orchestrator", name: "编排调度", model: "orchestrator-core", role: "任务分发 · 流程编排 · 结果聚合", color: "amber" },
    { id: "feynman",      name: "费曼教学", model: "qwen2.5:7b",          role: "五步教学法生成教学内容",      color: "sky" },
    { id: "knowledge",    name: "知识检索", model: "retrieval-index",     role: "检索知识点 · 注入上下文",      color: "mint" },
    { id: "coach",        name: "评测与路径", model: "lumilearn-v2",      role: "输出评分 · 个性化学习路径",    color: "danger" },
  ];

  /* ---------- 费曼五步教学文案库（4 个快捷主题） ---------- */
  const STEP_NAMES = ["现象引入", "认知冲突", "思维模型", "自主推导", "费曼测试"];
  const STEP_PURPOSES = [
    "从生活场景切入，零术语切入，让学生觉得亲切",
    "制造认知冲突，激发求知欲，打破原有认知",
    "用比喻/画面让抽象概念可操作、可触摸",
    "苏格拉底式追问，引导学生自己得出结论",
    "检验学生是否真正理解——能否用简单话讲清楚",
  ];

  const stepLibrary = {
    "函数的单调性": {
      subject: "数学", difficulty: "高中",
      steps: [
        { step: 1, content: "想象你站在山顶看日落，太阳的位置随时间一点点往下沉。气温也是——早上八点的 18℃，到了下午两点变成 32℃，再入夜又回到 20℃。温度不是乱变的，它在某些时间段一直在升，在另一些时间段一直在降。这种\"朝着一个方向走\"的变化，就是今天要认识的主角。" },
        { step: 2, content: "那问题来了：是不是只要 x 增大，y 就一定跟着增大？给你一个反例——函数 y = x²。x 从 -2 变到 -1，x 在增大，但 y 从 4 掉到了 1，反而变小了。所以\"单调\"这件事，跟 x 取在哪一段有巨大关系。你能想到别的例子吗？" },
        { step: 3, content: "把函数图像想象成一座山坡的侧影。你沿着 x 轴的方向往前推一个滑块，函数图像就是这条山坡。如果滑块往前走，你的海拔一直在上升，这段就是\"单调递增\"；如果一直下降，就是\"单调递减\"。山坡有平有陡，但只要方向不变，它就是单调的。" },
        { step: 4, content: "现在我们一起把它写严谨。要判断函数 f(x) 在区间 I 上单调递增，需要验证什么？提示：随便取两个点，但要保证它们的位置关系。先取 x₁ < x₂，然后检查 f(x₁) 和 f(x₂) 谁大谁小——请你说出完整的判断条件。" },
        { step: 5, content: "现在请你用 30 秒，把\"什么是单调递增函数\"讲给一个完全没学过函数的人听。要求：不许用任何数学符号，只能靠日常语言和例子。" },
      ],
    },
    "牛顿第二定律": {
      subject: "物理", difficulty: "高中",
      steps: [
        { step: 1, content: "超市里推购物车：空车轻轻一推就跑得飞快，装满饮料的车要花大力气才能推起来，但一旦推起来又不容易停下。同样是\"改变运动状态\"这件事，为什么有的轻松有的费力？这里面藏着一个把力和运动连起来的定律。" },
        { step: 2, content: "先别急着背公式。问问自己：同样用力推空车和满车，哪个更快加速？如果你说\"空车\"，那说明你其实已经直觉到了——同一个力下，质量越大，加速度越小。可是反过来，如果你用两倍的力推同一个车，加速度会变成几倍呢？" },
        { step: 3, content: "把力想象成\"推一把\"的劲，把加速度想象成\"速度变得有多快\"。牛顿说的就是：加速度跟你的劲成正比，跟东西的分量成反比。就像掰手腕——你力气越大越容易赢，对手越壮越难赢。数学上就是 F = ma。" },
        { step: 4, content: "来，我们推一次：一辆 1000 kg 的车，引擎给它的合力是 2000 N，加速度是多少？先别算数，先告诉我：应该用哪个量除以哪个量？提示：回忆一下，加速度跟力成正比、跟质量成反比，那公式应该怎么摆？" },
        { step: 5, content: "请用 30 秒，把\"力、质量和加速度的关系\"讲给一个没学过物理的朋友。可以用购物车的例子，但不能用 F=ma 这个公式。" },
      ],
    },
    "化学平衡移动": {
      subject: "化学", difficulty: "高中",
      steps: [
        { step: 1, content: "你往一杯糖水里再加糖，发现糖不再溶解了——因为已经饱和。可如果把杯子加热，剩下的糖又继续溶解了。一个看起来\"到顶了\"的平衡状态，换个条件又会动起来。化学平衡就像这样一个随时会被打破的\"饱和\"。" },
        { step: 2, content: "问题来了：平衡被打破之后，反应是永远跑向一边，还是跑一跑又停下来？你可能会猜\"会一直生成到用完为止\"。但真实的平衡系统会自己找到一个新的平衡点停下来——它并不是非黑即白地反应完。" },
        { step: 3, content: "把平衡想象成一座天平的跷跷板：正反应和逆反应是跷跷板两头的两个人，反应条件一变，就相当于给其中一个人脚下垫了砖，跷跷板重新倾斜，但倾斜到某个角度又会稳定下来。勒夏特列告诉我们：你施加什么压力，系统就朝消解这个压力的方向躲。" },
        { step: 4, content: "一起推理：2NO₂(棕) ⇌ N₂O₄(无色) 这个反应，若突然加压，气体体积被压缩。提示：压缩会让哪边分子总数更少？平衡会朝分子数变多还是变少的方向移动？请你自己说出结论和理由。" },
        { step: 5, content: "请用 30 秒，把\"勒夏特列原理\"讲给一个只学过一点化学的同学：条件一变，平衡就往哪个方向躲？举例说明即可。" },
      ],
    },
    "光合作用": {
      subject: "生物", difficulty: "高中",
      steps: [
        { step: 1, content: "你阳台上的绿植放窗边长得茂盛，搬到昏暗角落就蔫了。植物的叶子像一个工厂，用光、水和空气里的二氧化碳，造出自己吃的糖，还顺手排出氧气。这个过程每天都在悄悄进行——它叫光合作用。" },
        { step: 2, content: "先抛个问题：光合作用到底是\"把太阳能存起来\"还是\"把能量放出来\"？很多人以为植物是\"吃光\"，其实它是把光的能量变成化学能，存在葡萄糖里。你平时吃饭得到的能量，追根溯源，都是植物当年存下来的太阳光。这个说法对吗？" },
        { step: 3, content: "把叶绿体想象成一个微型太阳能工厂：光反应是\"发电车间\"（用光把水拆开，产生氧气和能量通货 ATP），暗反应是\"组装车间\"（用 ATP 和二氧化碳组装出葡萄糖）。两个车间一明一暗，接力完成从光到糖的转换。" },
        { step: 4, content: "现在推理一个环境问题：如果某天光照突然变强但二氧化碳供应不变，组装车间的原料够吗？提示：光反应产出的 ATP 多了，但暗反应缺 CO₂ 会怎样？请你说出\"光反应增强、暗反应跟不上\"会带来什么结果。" },
        { step: 5, content: "请用 30 秒，把\"光合作用的两个阶段各做了什么\"讲给一个刚学生物的同学。可以借用工厂的比喻。" },
      ],
    },
  };

  /* 通用兜底文案生成器（非快捷主题时使用） */
  function fallbackSteps(topic, subject, difficulty) {
    const s = subject || "这门学科";
    const examples = {
      "数学": "把问题变成一段图像或数字的变化规律",
      "物理": "找一个身边能摸到的运动或力",
      "化学": "用一杯溶液或一个反应现象来切入",
      "生物": "从你身体或身边生物的一个现象切入",
      "综合": "从生活里最常见的例子切入",
    };
    return [
      { step: 1, content: `先别急着定义。用${s}里的一个生活场景引入「${topic}」——${examples[s] || examples["综合"]}，让学生先"看见"它。` },
      { step: 2, content: `现在制造一个矛盾：抛出一个看起来简单、但按直觉会答错的${s}问题，让学生发现自己原来的理解不完整，好奇心被勾起来。` },
      { step: 3, content: `用一个脑中能操作的画面比喻「${topic}」——就像"山谷和山峰""天平两端""工厂车间"一样，让抽象概念变得可以摸到。` },
      { step: 4, content: `给学生一个分析方向和一个关键提示，用追问让他自己推出第一步结论，而不是直接给答案。` },
      { step: 5, content: `进入费曼测试：请你用 30 秒，用最简单的话把「${topic}」讲给一个完全不懂的人听，不许堆术语。` },
    ];
  }

  /* ---------- 历史会话（与报告/历史页一致，掌握度 62–92） ---------- */
  const sessions = [
    {
      id: "s-1006", topic: "函数的单调性", subject: "数学", difficulty: "高中",
      date: "2026-08-10 21:42", status: "done", mastery: 88,
      model: "qwen2.5:7b", duration: "3分28秒", toolCalls: 14,
      weakPoints: [
        { text: "区间端点的开闭判断不够严谨", severity: "中" },
        { text: "偶函数在对称区间的单调性易混淆", severity: "低" },
      ],
      nextSteps: [
        "完成《单调性与最值》专题练习（高中难度）",
        "用 30 秒向同学讲解\"单调递增的定义\"",
        "复习周期：1 天后 → 3 天后 → 7 天后 → 14 天后",
      ],
      agents: [
        { id: "orchestrator", name: "编排调度", model: "orchestrator-core", status: "done", calls: 6 },
        { id: "feynman", name: "费曼教学", model: "qwen2.5:7b", status: "done", calls: 5 },
        { id: "knowledge", name: "知识检索", model: "retrieval-index", status: "done", calls: 2 },
        { id: "coach", name: "评测与路径", model: "lumilearn-v2", status: "done", calls: 1 },
      ],
    },
    {
      id: "s-1005", topic: "牛顿第二定律", subject: "物理", difficulty: "高中",
      date: "2026-08-10 20:15", status: "done", mastery: 92,
      model: "qwen2.5:7b", duration: "4分02秒", toolCalls: 16,
      weakPoints: [{ text: "瞬时加速度与平均加速度区分不足", severity: "低" }],
      nextSteps: [
        "练习 F=ma 的受力分析综合题",
        "用购物车例子向家人讲一遍牛顿第二定律",
        "复习周期：1 天后 → 3 天后 → 7 天后",
      ],
      agents: [
        { id: "orchestrator", name: "编排调度", model: "orchestrator-core", status: "done", calls: 6 },
        { id: "feynman", name: "费曼教学", model: "qwen2.5:7b", status: "done", calls: 5 },
        { id: "knowledge", name: "知识检索", model: "retrieval-index", status: "done", calls: 3 },
        { id: "coach", name: "评测与路径", model: "lumilearn-v2", status: "done", calls: 2 },
      ],
    },
    {
      id: "s-1004", topic: "化学平衡移动", subject: "化学", difficulty: "高中",
      date: "2026-08-09 22:08", status: "done", mastery: 71,
      model: "qwen2.5:7b", duration: "3分51秒", toolCalls: 15,
      weakPoints: [
        { text: "勒夏特列原理应用场景判断不准", severity: "高" },
        { text: "压强改变对平衡移动方向的推理不熟练", severity: "中" },
      ],
      nextSteps: [
        "重点复习\"压强对平衡的影响\"并做 5 道专项题",
        "画一张平衡移动判断流程图",
        "复习周期：1 天后 → 2 天后 → 5 天后",
      ],
      agents: [
        { id: "orchestrator", name: "编排调度", model: "orchestrator-core", status: "done", calls: 6 },
        { id: "feynman", name: "费曼教学", model: "qwen2.5:7b", status: "done", calls: 5 },
        { id: "knowledge", name: "知识检索", model: "retrieval-index", status: "done", calls: 2 },
        { id: "coach", name: "评测与路径", model: "lumilearn-v2", status: "done", calls: 2 },
      ],
    },
    {
      id: "s-1003", topic: "光合作用", subject: "生物", difficulty: "高中",
      date: "2026-08-09 19:33", status: "done", mastery: 84,
      model: "qwen2.5:7b", duration: "3分07秒", toolCalls: 13,
      weakPoints: [{ text: "光反应与暗反应的场所容易记混", severity: "中" }],
      nextSteps: [
        "用\"工厂两个车间\"比喻复述光合作用全过程",
        "完成叶绿体结构功能对照表",
        "复习周期：1 天后 → 3 天后 → 7 天后",
      ],
      agents: [
        { id: "orchestrator", name: "编排调度", model: "orchestrator-core", status: "done", calls: 6 },
        { id: "feynman", name: "费曼教学", model: "qwen2.5:7b", status: "done", calls: 5 },
        { id: "knowledge", name: "知识检索", model: "retrieval-index", status: "done", calls: 2 },
        { id: "coach", name: "评测与路径", model: "lumilearn-v2", status: "done", calls: 1 },
      ],
    },
    {
      id: "s-1002", topic: "数列求和·裂项相消", subject: "数学", difficulty: "高中",
      date: "2026-08-08 21:20", status: "done", mastery: 62,
      model: "qwen2.5:7b", duration: "4分26秒", toolCalls: 17,
      weakPoints: [
        { text: "裂项公式的记忆与变形不熟练", severity: "高" },
        { text: "含参数列求和易漏讨论", severity: "中" },
      ],
      nextSteps: [
        "整理 6 个常用裂项公式并每日默写",
        "做 5 道含参裂项求和专项题",
        "复习周期：1 天后 → 2 天后 → 4 天后",
      ],
      agents: [
        { id: "orchestrator", name: "编排调度", model: "orchestrator-core", status: "done", calls: 7 },
        { id: "feynman", name: "费曼教学", model: "qwen2.5:7b", status: "done", calls: 5 },
        { id: "knowledge", name: "知识检索", model: "retrieval-index", status: "done", calls: 3 },
        { id: "coach", name: "评测与路径", model: "lumilearn-v2", status: "done", calls: 2 },
      ],
    },
    {
      id: "s-1001", topic: "电场强度与电势", subject: "物理", difficulty: "高中",
      date: "2026-08-07 20:45", status: "done", mastery: 77,
      model: "qwen2.5:7b", duration: "3分40秒", toolCalls: 15,
      weakPoints: [
        { text: "电场强度与电势的正负号含义混淆", severity: "中" },
        { text: "等势面与电场线的关系不清晰", severity: "低" },
      ],
      nextSteps: [
        "对比整理 E-φ 关系表并自测",
        "用等高线类比理解等势面",
        "复习周期：1 天后 → 3 天后 → 7 天后",
      ],
      agents: [
        { id: "orchestrator", name: "编排调度", model: "orchestrator-core", status: "done", calls: 6 },
        { id: "feynman", name: "费曼教学", model: "qwen2.5:7b", status: "done", calls: 5 },
        { id: "knowledge", name: "知识检索", model: "retrieval-index", status: "done", calls: 2 },
        { id: "coach", name: "评测与路径", model: "lumilearn-v2", status: "done", calls: 2 },
      ],
    },
  ];

  const quickExamples = [
    "函数的单调性", "牛顿第二定律", "化学平衡移动", "光合作用",
  ];

  return { SUBJECTS, agentDefs, STEP_NAMES, STEP_PURPOSES, stepLibrary, fallbackSteps, sessions, quickExamples };
})();
