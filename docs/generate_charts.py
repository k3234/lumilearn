import json, os, math

DATA_DIR = r"E:\学习LLM\lumilearn\docs"

with open(os.path.join(DATA_DIR, "500-user-browser-test-results.json")) as f:
    test500 = json.load(f)
with open(os.path.join(DATA_DIR, "browser-automation-data.json")) as f:
    browser = json.load(f)

# Chart 1: API Success Rate
api_rates = test500["api_success_rates"]
api_names = {"login":"/api/login","learn":"/api/learn","chat":"/api/chat","history":"/api/history","status":"/api/status","health":"/health","models":"/api/models","ollama":"/api/tags"}
chart_width, chart_height = 720, 420
bar_w, gap, start_x, y_base, y_max = 60, 20, 80, 360, 105
colors = ["#2563eb","#3b82f6","#60a5fa","#93c5fd","#1d4ed8","#1e40af","#1e3a8a","#172554"]
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart_width}" height="{chart_height}" viewBox="0 0 {chart_width} {chart_height}">',
    f'<rect width="{chart_width}" height="{chart_height}" fill="#fafafa"/>',
    f'<text x="{chart_width//2}" y="24" text-anchor="middle" font-family="system-ui" font-size="15" font-weight="bold" fill="#111">图1: 500用户测试API成功率分布</text>',
    f'<text x="16" y="{y_base+30}" font-family="system-ui" font-size="11" fill="#555">成功率</text>']
for pct in [90,95,98,99,100]:
    y = y_base - (pct/100)*(y_base-y_max)
    svg.append(f'<line x1="{start_x}" y1="{y}" x2="{chart_width-20}" y2="{y}" stroke="#ddd" stroke-width="0.5"/>')
    svg.append(f'<text x="{start_x-6}" y="{y+4}" text-anchor="end" font-family="system-ui" font-size="10" fill="#888">{pct}%</text>')
for i, (key, data) in enumerate(api_rates.items()):
    x = start_x + i*(bar_w+gap)
    rate = float(data["rate"].replace("%",""))
    h = (rate/100)*(y_base-y_max)
    color = colors[i%len(colors)]
    svg.append(f'<rect x="{x}" y="{y_base-h}" width="{bar_w}" height="{h}" fill="{color}" rx="3"/>')
    svg.append(f'<text x="{x+bar_w//2}" y="{y_base-h-6}" text-anchor="middle" font-family="system-ui" font-size="11" font-weight="bold" fill="#111">{data["rate"]}</text>')
    svg.append(f'<text x="{x+bar_w//2}" y="{y_base+16}" text-anchor="middle" font-family="system-ui" font-size="9" fill="#555">{api_names.get(key,key)}</text>')
svg.append("</svg>")
with open(os.path.join(DATA_DIR,"chart1_api_rate.svg"),"w",encoding="utf-8") as f:
    f.write("\n".join(svg))
print("chart1 done")

# Chart 2: Latency
latency = test500["latency_stats"]
svgs = [f'<svg xmlns="http://www.w3.org/2000/svg" width="700" height="380" viewBox="0 0 700 380">',
    f'<rect width="700" height="380" fill="#fafafa"/>',
    f'<text x="350" y="24" text-anchor="middle" font-family="system-ui" font-size="15" font-weight="bold" fill="#111">图2: 关键API延迟分布对比 (ms)</text>']
iface_data = [("登录 /api/login", latency["login_ms"], "#2563eb"), ("学习 /api/learn", latency["learn_ms"], "#16a34a"), ("聊天 /api/chat", latency["chat_ms"], "#ca8a04")]
ix, iy = 90, 50
for idx, (label, stats, color) in enumerate(iface_data):
    by = iy + idx * 85
    vals = [stats["min"], stats["p50"], stats["avg"], stats["p90"], stats["p99"], stats["max"]]
    scale = 560 / max(vals) * 0.85
    cx = ix
    svgs.append(f'<text x="{ix-6}" y="{by+16}" text-anchor="end" font-family="system-ui" font-size="11" fill="#333">{label}</text>')
    svgs.append(f'<line x1="{cx + vals[0]*scale}" y1="{by+12}" x2="{cx + vals[5]*scale}" y2="{by+12}" stroke="#999" stroke-width="1.5"/>')
    svgs.append(f'<circle cx="{cx + vals[0]*scale}" cy="{by+12}" r="3" fill="#999"/>')
    svgs.append(f'<circle cx="{cx + vals[5]*scale}" cy="{by+12}" r="3" fill="#999"/>')
    box_left = cx + vals[1]*scale
    box_right = cx + vals[3]*scale
    svgs.append(f'<rect x="{box_left}" y="{by+4}" width="{box_right-box_left}" height="16" fill="{color}" opacity="0.7" rx="2"/>')
    svgs.append(f'<line x1="{cx + vals[1]*scale}" y1="{by+2}" x2="{cx + vals[1]*scale}" y2="{by+22}" stroke="#111" stroke-width="2"/>')
    svgs.append(f'<circle cx="{cx + vals[4]*scale}" cy="{by+12}" r="3" fill="{color}"/>')
    svgs.append(f'<text x="{cx + vals[0]*scale}" y="{by+30}" text-anchor="middle" font-family="system-ui" font-size="9" fill="#666">min:{vals[0]:.0f}</text>')
    svgs.append(f'<text x="{cx + vals[1]*scale}" y="{by+30}" text-anchor="middle" font-family="system-ui" font-size="9" font-weight="bold" fill="#111">P50:{vals[1]:.0f}</text>')
    svgs.append(f'<text x="{cx + vals[3]*scale}" y="{by+30}" text-anchor="middle" font-family="system-ui" font-size="9" fill="#666">P90:{vals[3]:.0f}</text>')
    svgs.append(f'<text x="{cx + vals[5]*scale}" y="{by+30}" text-anchor="middle" font-family="system-ui" font-size="9" fill="#666">max:{vals[5]:.0f}</text>')
svgs.append("</svg>")
with open(os.path.join(DATA_DIR,"chart2_latency.svg"),"w",encoding="utf-8") as f:
    f.write("\n".join(svgs))
print("chart2 done")

# Chart 3: Subject Pie
subjects = test500["subject_distribution"]
total = sum(subjects.values())
colors_pie = ["#2563eb","#16a34a","#ca8a04","#dc2626","#7c3aed","#db2777","#0891b2","#65a30d"]
svgs2 = [f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="400" viewBox="0 0 720 400">',
    f'<rect width="720" height="400" fill="#fafafa"/>',
    f'<text x="360" y="24" text-anchor="middle" font-family="system-ui" font-size="15" font-weight="bold" fill="#111">图3: 500用户学科分布 (N={total})</text>']
cx, cy, r = 200, 210, 140
start_angle = 0
for i, (subj, count) in enumerate(sorted(subjects.items(), key=lambda x:-x[1])):
    pct = count / total
    angle = pct * 360
    end_angle = start_angle + angle
    large_arc = 1 if angle > 180 else 0
    x1 = cx + r * math.cos(math.radians(start_angle))
    y1 = cy + r * math.sin(math.radians(start_angle))
    x2 = cx + r * math.cos(math.radians(end_angle))
    y2 = cy + r * math.sin(math.radians(end_angle))
    if angle >= 359.9:
        path_d = f"M {cx} {cy} A {r} {r} 0 1 1 {cx-0.01} {cy} Z"
    else:
        path_d = f"M {cx} {cy} L {x1} {y1} A {r} {r} 0 {large_arc} 1 {x2} {y2} Z"
    svgs2.append(f'<path d="{path_d}" fill="{colors_pie[i%len(colors_pie)]}" stroke="#fff" stroke-width="2"/>')
    mid_angle = start_angle + angle/2
    lx = cx + (r+25) * math.cos(math.radians(mid_angle))
    ly = cy + (r+25) * math.sin(math.radians(mid_angle))
    svgs2.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" font-family="system-ui" font-size="11" fill="#333">{subj} {count}</text>')
    start_angle = end_angle
lx, ly = 400, 80
for i, (subj, count) in enumerate(sorted(subjects.items(), key=lambda x:-x[1])):
    svgs2.append(f'<rect x="{lx}" y="{ly+i*24}" width="14" height="14" fill="{colors_pie[i]}" rx="2"/>')
    svgs2.append(f'<text x="{lx+20}" y="{ly+i*24+12}" text-anchor="start" font-family="system-ui" font-size="12" fill="#333">{subj}: {count} ({count/total*100:.1f}%)</text>')
svgs2.append("</svg>")
with open(os.path.join(DATA_DIR,"chart3_subject_pie.svg"),"w",encoding="utf-8") as f:
    f.write("\n".join(svgs2))
print("chart3 done")

# Chart 4: Test Comparison
metrics = [
    ("用户数", "30", "500", "#2563eb", "#3b82f6"),
    ("学习成功率", "100%", "99.8%", "#16a34a", "#22c55e"),
    ("平均延迟P50(ms)", "N/A", "47", "#ca8a04", "#eab308"),
    ("吞吐量(用户/秒)", "~1.6", "1.9", "#7c3aed", "#8b5cf6"),
    ("API接口数", "11", "8", "#dc2626", "#ef4444"),
]
svgs3 = [f'<svg xmlns="http://www.w3.org/2000/svg" width="700" height="320" viewBox="0 0 700 320">',
    f'<rect width="700" height="320" fill="#fafafa"/>',
    f'<text x="350" y="24" text-anchor="middle" font-family="system-ui" font-size="15" font-weight="bold" fill="#111">图4: 30用户 vs 500用户测试对比</text>']
bar_h = 36
for i, (name, v1, v2, c1, c2) in enumerate(metrics):
    y = 55 + i * 48
    svgs3.append(f'<text x="10" y="{y+18}" font-family="system-ui" font-size="12" fill="#333">{name}</text>')
    svgs3.append(f'<rect x="140" y="{y}" width="100" height="{bar_h}" fill="{c1}" rx="3"/>')
    svgs3.append(f'<text x="190" y="{y+22}" text-anchor="middle" font-family="system-ui" font-size="12" font-weight="bold" fill="#fff">{v1}</text>')
    svgs3.append(f'<rect x="260" y="{y}" width="100" height="{bar_h}" fill="{c2}" rx="3"/>')
    svgs3.append(f'<text x="310" y="{y+22}" text-anchor="middle" font-family="system-ui" font-size="12" font-weight="bold" fill="#fff">{v2}</text>')
    svgs3.append(f'<text x="140" y="{y-6}" font-family="system-ui" font-size="10" fill="#666">30用户</text>')
    svgs3.append(f'<text x="260" y="{y-6}" font-family="system-ui" font-size="10" fill="#666">500用户</text>')
svgs3.append("</svg>")
with open(os.path.join(DATA_DIR,"chart4_comparison.svg"),"w",encoding="utf-8") as f:
    f.write("\n".join(svgs3))
print("chart4 done")

# Chart 5: Browser vs Python table
comp_data = [
    ("维度", "浏览器自动化", "Python http.cookiejar"),
    ("登录方式", "已有session(学生02)", "每用户独立session"),
    ("学习流程", "2次完整流程", "500次批量流程"),
    ("UI可见性", "\u2705 完整DOM渲染", "\u274c 无UI"),
    ("网络请求", "25次(含导航)", "5000次(500用户x10接口)"),
    ("耗时", "~6分钟(详细交互)", "258秒(批量)"),
    ("数据深度", "学习报告完整内容", "仅状态码+延迟"),
]
svgs4 = [f'<svg xmlns="http://www.w3.org/2000/svg" width="700" height="300" viewBox="0 0 700 300">',
    f'<rect width="700" height="300" fill="#fafafa"/>',
    f'<text x="350" y="24" text-anchor="middle" font-family="system-ui" font-size="15" font-weight="bold" fill="#111">图5: 浏览器自动化 vs Python模拟测试对比</text>']
tw, th = 700, 240
tx, ty = 30, 45
cw = [200, 250, 250]
for ri, row in enumerate(comp_data):
    bg = "#f0f4ff" if ri == 0 else ("#fff" if ri%2==0 else "#f8fafc")
    for ci, val in enumerate(row):
        x = tx + sum(cw[:ci])
        fw = "bold" if ri == 0 else "normal"
        fs = "11"
        svgs4.append(f'<rect x="{x}" y="{ty+ri*30}" width="{cw[ci]}" height="30" fill="{bg}" stroke="#e2e8f0" stroke-width="0.5"/>')
        svgs4.append(f'<text x="{x+cw[ci]//2}" y="{ty+ri*30+19}" text-anchor="middle" font-family="system-ui" font-size="{fs}" font-weight="{fw}" fill="#111">{val}</text>')
svgs4.append("</svg>")
with open(os.path.join(DATA_DIR,"chart5_browser_vs_python.svg"),"w",encoding="utf-8") as f:
    f.write("\n".join(svgs4))
print("chart5 done")

# Chart 6: Error Analysis
errors = test500.get("error_summary", {})
svgs5 = [f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="220" viewBox="0 0 500 220">',
    f'<rect width="500" height="220" fill="#fafafa"/>',
    f'<text x="250" y="24" text-anchor="middle" font-family="system-ui" font-size="15" font-weight="bold" fill="#111">图6: 错误分析 (500用户测试)</text>']
if errors:
    total_users = 500
    ok_rate = (total_users - 1) / total_users * 100
    cx, cy, r = 120, 130, 80
    ok_angle = ok_rate / 100 * 360
    sx = cx + r * math.cos(math.radians(-90))
    sy = cy + r * math.sin(math.radians(-90))
    ex = cx + r * math.cos(math.radians(-90 + ok_angle))
    ey = cy + r * math.sin(math.radians(-90 + ok_angle))
    large = 1 if ok_angle > 180 else 0
    svgs5.append(f'<path d="M {cx} {cy} L {sx} {sy} A {r} {r} 0 {large} 1 {ex} {ey} Z" fill="#22c55e"/>')
    ex2 = cx + r * math.cos(math.radians(-90 + ok_angle))
    ey2 = cy + r * math.sin(math.radians(-90 + ok_angle))
    esx = cx + r * math.cos(math.radians(-90))
    esy = cy + r * math.sin(math.radians(-90))
    svgs5.append(f'<path d="M {cx} {cy} L {ex2} {ey2} A {r} {r} 0 0 1 {esx} {esy} Z" fill="#ef4444"/>')
    svgs5.append(f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-family="system-ui" font-size="18" font-weight="bold" fill="#111">{total_users-1}/{total_users}</text>')
    svgs5.append(f'<text x="{cx}" y="{cy+22}" text-anchor="middle" font-family="system-ui" font-size="11" fill="#666">成功用户</text>')
    svgs5.append(f'<rect x="240" y="90" width="14" height="14" fill="#22c55e" rx="2"/>')
    svgs5.append(f'<text x="260" y="102" font-family="system-ui" font-size="12" fill="#333">成功: {total_users-1} ({ok_rate:.1f}%)</text>')
    svgs5.append(f'<rect x="240" y="115" width="14" height="14" fill="#ef4444" rx="2"/>')
    svgs5.append(f'<text x="260" y="127" font-family="system-ui" font-size="12" fill="#333">失败: 1 (login:401)</text>')
else:
    svgs5.append(f'<text x="250" y="120" text-anchor="middle" font-family="system-ui" font-size="14" fill="#333">无错误</text>')
svgs5.append("</svg>")
with open(os.path.join(DATA_DIR,"chart6_error_analysis.svg"),"w",encoding="utf-8") as f:
    f.write("\n".join(svgs5))
print("chart6 done")

print("All charts generated successfully!")
