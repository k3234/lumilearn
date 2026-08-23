# -*- coding: utf-8 -*-
"""仓库跟踪文件敏感信息扫描：检查 git 跟踪文件中的内网IP/API Key/硬编码口令"""
import re
import subprocess

r = subprocess.run(["git", "ls-files"], capture_output=True, text=True, encoding="utf-8")
files = [f for f in r.stdout.split("\n") if f]

SKIP_SUBSTR = ["/tests/", "/docs/", ".md", "static/vendor", "assets/", "package-lock"]

patterns = {
    "内网IP": re.compile(r"192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}"),
    "API Key": re.compile(r"sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,}"),
    "SSH/私钥头": re.compile(r"BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY"),
    "硬编码口令": re.compile(r"(?i)password\s*[:=]\s*[\"'][^\"']{6,}[\"']"),
}

hits = {}
for f in files:
    if not f:
        continue
    if any(s in f for s in SKIP_SUBSTR):
        continue
    try:
        content = open(f, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    for name, pat in patterns.items():
        for m in pat.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            snippet = content.split("\n")[line_no - 1].strip()[:100]
            hits.setdefault(name, []).append(f"  {f}:{line_no}  {snippet}")

for name, arr in hits.items():
    print(f"--- {name} ({len(arr)} 处) ---")
    for a in arr[:25]:
        print(a)

if not hits:
    print("检查通过：未在跟踪文件中发现内网IP/API Key/私钥/硬编码口令")
else:
    print(f"\n共发现 {sum(len(v) for v in hits.values())} 处需要人工确认")
