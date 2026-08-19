# ============================================================
# LumiLearn 零文件一键部署（Windows PowerShell，管道安全）
#
# 用法（不下载文件，直接执行远程脚本）：
#   irm https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.ps1 | iex
#
# 选项可用环境变量设置（值 "1" 表示开启）：
#   LUMILEARN_QUICK       全默认值，无人值守（"1" 开启）
#   LUMILEARN_SKIP_DEPS   跳过依赖安装（"1" 开启）
#   LUMILEARN_NO_START    只克隆+配置，不启动服务（"1" 开启）
#   LUMILEARN_DIR         克隆到指定目录（默认 当前目录\lumilearn）
#   LUMILEARN_BRANCH      指定分支（默认 master）
#   LUMILEARN_REPO_URL    仓库地址（默认 https://github.com/k3234/lumilearn.git）
#   例：$env:LUMILEARN_QUICK = "1"; irm ... | iex
#
# 也可保存为文件后使用参数：
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Quick -SkipDeps
#       -NoStart -Dir D:\lumilearn -Branch dev
#
# 隐私说明：本脚本仅访问公开仓库地址，不含任何真实 IP / 密码 / API Key。
# ============================================================

# 外部命令（git/python）错误不中断，统一用 $LASTEXITCODE 判断
$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 环境变量（值 "1" 表示开启；严禁用 [bool] 强转，[bool]"0" 为 True 的坑）
$Quick    = ($env:LUMILEARN_QUICK -eq "1")
$SkipDeps = ($env:LUMILEARN_SKIP_DEPS -eq "1")
$NoStart  = ($env:LUMILEARN_NO_START -eq "1")
$Dir      = $env:LUMILEARN_DIR
$Branch   = $env:LUMILEARN_BRANCH
$RepoUrl  = if ($env:LUMILEARN_REPO_URL) { $env:LUMILEARN_REPO_URL } else { "https://github.com/k3234/lumilearn.git" }
$BranchName = if ($Branch) { $Branch } else { "master" }

# 参数解析（不写 param(...) 块，避免与 iex 管道输入冲突）
for ($i = 0; $i -lt $args.Count; $i++) {
    switch -Regex ($args[$i]) {
        "^-Quick$"       { $Quick = $true; break }
        "^-SkipDeps$"    { $SkipDeps = $true; break }
        "^-NoStart$"     { $NoStart = $true; break }
        "^-Dir=(.+)$"    { $Dir = $matches[1]; break }
        "^-Dir$"         { if ($i + 1 -lt $args.Count) { $Dir = [string]$args[++$i] }; break }
        "^-Branch=(.+)$" { $Branch = $matches[1]; $BranchName = $Branch; break }
        "^-Branch$"      { if ($i + 1 -lt $args.Count) { $Branch = [string]$args[++$i] }; $BranchName = $Branch; break }
    }
}

# 管道执行（irm | iex）检测：stdin 被重定向且无法交互 → 强制 --quick。
# 双重保障：deploy/setup.py 检测到非 TTY 输入时也会自动切 --quick 且绝不 input()，
# 避免子进程抢读管道中的脚本残留字节（污染 .env / 丢失脚本尾部）。
if ([Console]::IsInputRedirected -and -not $Quick) {
    Write-Host "  [提示] 检测到管道执行（非交互），自动使用 --quick 全部默认值"
    $Quick = $true
}

Write-Host "============================================================"
Write-Host "  LumiLearn 零文件一键部署 (Windows)"
Write-Host "  仓库: $RepoUrl (分支: $BranchName)"
Write-Host "============================================================"

# [1/5] 检测 git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] 未检测到 git，请先安装 Git: https://git-scm.com"
    return
}

# [2/5] 定位 / 克隆仓库
# 管道安全：irm | iex 场景无 $PSScriptRoot / $PSCommandPath；
# 「已在仓库内」仅靠 cwd 特征（deploy\setup.py + .git）判断。
$Dest = ""
if ($Dir) {
    $Dest = $Dir
} else {
    if ((Test-Path "deploy\setup.py") -and (Test-Path ".git")) {
        $Dest = (Get-Location).Path                 # 已在仓库内：复用当前目录
    } else {
        $Dest = Join-Path (Get-Location).Path "lumilearn"   # 克隆到当前目录
    }
}
Write-Host "  目标目录: $Dest"

if (Test-Path "$Dest\.git") {
    Write-Host "[2/5] 检测到已有仓库，正在更新..."
    Push-Location $Dest
    git fetch origin 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        git pull --ff-only origin $BranchName 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ 仓库已更新"
        } else {
            Write-Host "  [提示] 快进更新失败（可能本地有未提交改动），继续使用现有代码"
        }
    } else {
        Write-Host "  [提示] 网络无法访问远程仓库，继续使用现有代码"
    }
    Pop-Location
} else {
    Write-Host "[2/5] 正在克隆仓库 $RepoUrl ..."
    git clone -b $BranchName --depth 1 $RepoUrl $Dest
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 克隆仓库失败，请检查网络与仓库地址"
        return
    }
    Write-Host "  ✓ 仓库克隆完成"
}
Write-Host ""

# [3/5] 检测 python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] 未检测到 python，请先安装 Python 3.9+: https://www.python.org"
    Write-Host "  安装时请勾选 Add Python to PATH"
    return
}
Write-Host "  ✓ $(& python --version)"

# [4/5] 部署配置（依赖安装 / 端口 / 模型）
Set-Location $Dest
Write-Host ""
Write-Host "[4/5] 运行部署配置引导（依赖 / 端口 / 模型）..."
$setupArgs = @("deploy\setup.py")
if ($SkipDeps) { $setupArgs += "--skip-deps" }
if ($Quick) { $setupArgs += "--quick" }
& python @setupArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 部署配置失败（退出码 $LASTEXITCODE）"
    return
}

# [5/5] 启动服务
Write-Host ""
if (-not $NoStart) {
    Write-Host "[5/5] 启动全部服务..."
    & python "deploy\start.py"
} else {
    Write-Host "[5/5] 已跳过服务启动（--no-start），手动启动命令："
    Write-Host "  python deploy\start.py"
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  ✅ LumiLearn 部署完成"
Write-Host "  终端页面:   http://localhost:18080"
Write-Host "  管理面板:   http://localhost:18080/admin"
Write-Host "  REST API:   http://localhost:18081"
Write-Host "  模型管理:   http://localhost:18082"
Write-Host "============================================================"
