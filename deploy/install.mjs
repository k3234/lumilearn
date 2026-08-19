#!/usr/bin/env node
/**
 * LumiLearn Node.js 可选启动器（npx 风格）
 *
 * 仅在已克隆的仓库内使用（从仓库根目录或 deploy/ 下调用）：
 *   node deploy/install.mjs [--quick] [--skip-deps] [--no-start]
 *
 * 若不在仓库内运行，将提示改用零文件单行命令：
 *   Linux/macOS: curl -fsSL https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.sh | bash
 *   Windows:     irm https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.ps1 | iex
 *
 * 隐私说明：本脚本不访问除公开仓库地址外的任何网络资源，不含真实 IP / 密码 / API Key。
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");

// 解析参数
const args = process.argv.slice(2);
let quick = false;
let skipDeps = false;
let noStart = false;
for (const a of args) {
    switch (a) {
        case "--quick": quick = true; break;
        case "--skip-deps": skipDeps = true; break;
        case "--no-start": noStart = true; break;
    }
}

// 未在仓库内运行检查
if (!existsSync(join(ROOT, "deploy", "setup.py"))) {
    console.log("⚠ 未在仓库内运行，请使用零文件单行命令：");
    console.log("  Linux/macOS: curl -fsSL https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.sh | bash");
    console.log("  Windows:     irm https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.ps1 | iex");
    process.exit(0);
}

// 查找 Python（Node.js 仅为可选入口，Python 必需）
function findPython() {
    for (const cmd of ["python3", "python"]) {
        const r = spawnSync(cmd, ["--version"]);
        if (r.status === 0) return cmd;
    }
    return null;
}

const py = findPython();
if (!py) {
    console.error("[错误] 未检测到 Python（Node.js 仅为可选入口，Python 必需），请先安装 Python 3.9+。");
    console.error("  零文件回退命令：");
    console.error("    irm https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.ps1 | iex");
    process.exit(1);
}

console.log("============================================================");
console.log("  🚀 LumiLearn 一键部署（Node 启动器）");
console.log("============================================================");
console.log(`  ✓ ${py} --version 检查通过`);

// 委托 deploy/setup.py
const setupArgs = ["deploy/setup.py"];
if (skipDeps) setupArgs.push("--skip-deps");
if (quick) setupArgs.push("--quick");
console.log("");
console.log("[4/5] 运行部署配置引导（依赖 / 端口 / 模型）...");
let r = spawnSync(py, setupArgs, { cwd: ROOT, stdio: "inherit" });
if (r.status !== 0) {
    console.error(`[错误] 部署配置失败（退出码 ${r.status}）`);
    process.exit(r.status ?? 1);
}

// 委托 deploy/start.py
console.log("");
if (!noStart) {
    console.log("[5/5] 启动全部服务...");
    r = spawnSync(py, ["deploy/start.py"], { cwd: ROOT, stdio: "inherit" });
    if (r.status !== 0) {
        console.error(`[错误] 服务启动失败（退出码 ${r.status}）`);
        process.exit(r.status ?? 1);
    }
} else {
    console.log("[5/5] 已跳过服务启动（--no-start），手动启动命令：");
    console.log(`  ${py} deploy/start.py`);
}

console.log("");
console.log("============================================================");
console.log("  ✅ LumiLearn 部署完成");
console.log("  终端页面:   http://localhost:18080");
console.log("  管理面板:   http://localhost:18080/admin");
console.log("  REST API:   http://localhost:18081");
console.log("  模型管理:   http://localhost:18082");
console.log("============================================================");
