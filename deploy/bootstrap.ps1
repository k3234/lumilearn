# ============================================================
# LumiLearn 一键部署引导（Windows PowerShell）
# 从任意目录运行，自动完成：克隆/更新仓库 → 配置 → 启动服务
#
# 完整流程：
#   1. 检测 git / python
#   2. 克隆仓库（已存在则 git pull 更新）
#   3. 运行 deploy/setup.py（依赖安装 / 端口 / 模型配置）
#   4. 运行 deploy/start.py 启动全部启用服务
#
# 用法：
#   bootstrap.bat                # 完整一键部署（克隆→配置→启动）
#   bootstrap.bat --quick        # 全默认值，无人值守
#   bootstrap.bat --skip-deps    # 跳过依赖安装
#   bootstrap.bat --no-start     # 只克隆+配置，不启动服务
#   bootstrap.bat --dir D:\proj  # 克隆到指定目录
#   bootstrap.bat --branch dev   # 指定分支（默认 master）
#
# 环境变量可覆盖（方便 fork 用户）：
#   LUMILEARN_REPO_URL   仓库地址（默认 https://github.com/k3234/lumilearn.git）
#   LUMILEARN_BRANCH     分支（默认 master）
#
# 隐私说明：本脚本仅使用公开仓库地址，不含任何真实 IP / 密码 / API Key。
# ============================================================
param(
    [switch]$Quick,
    [switch]$SkipDeps,
    [switch]$NoStart,
    [string]$Dir = "",
    [string]$Branch = ""
)

# 外部命令（git/python）错误不中断，统一用 $LASTEXITCODE 判断
$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoUrl = if ($env:LUMILEARN_REPO_URL) { $env:LUMILEARN_REPO_URL } else { "https://github.com/k3234/lumilearn.git" }
$BranchName = if ($Branch) { $Branch } elseif ($env:LUMILEARN_BRANCH) { $env:LUMILEARN_BRANCH } else { "master" }

Write-Host "============================================================"
Write-Host "  LumiLearn 一键部署引导 (Windows)"
Write-Host "  仓库: $RepoUrl (分支: $BranchName)"
Write-Host "============================================================"

# [1/5] 检测 git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] 未检测到 git，请先安装 Git: https://git-scm.com"
    exit 1
}

# [2/5] 确定目标目录（已在仓库内则复用，否则克隆到当前目录）
$Dest = ""
if ($Dir) {
    $Dest = $Dir
} else {
    if ((Test-Path "deploy\setup.py") -and (Test-Path ".git")) {
        $Dest = (Get-Location).Path                 # 已在仓库内
    } elseif ((Test-Path "$PSScriptRoot\..\deploy\setup.py") -and (Test-Path "$PSScriptRoot\..\.git")) {
        $Dest = (Resolve-Path "$PSScriptRoot\..").Path
    } else {
        $Dest = Join-Path (Get-Location).Path "lumilearn"   # 克隆到当前目录
    }
}
New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
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
        exit 1
    }
    Write-Host "  ✓ 仓库克隆完成"
}
Write-Host ""

# [3/5] 检测 python
$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) {
    Write-Host "[错误] 未检测到 python，请先安装 Python 3.9+: https://www.python.org"
    Write-Host "  安装时请勾选 Add Python to PATH"
    exit 1
}
Write-Host "  ✓ $(& python --version)"

# [4/5] 部署配置（依赖安装 / 端口 / 模型）
Push-Location $Dest
Write-Host ""
Write-Host "[4/5] 运行部署配置引导（依赖 / 端口 / 模型）..."
$setupArgs = @("deploy\setup.py")
if ($SkipDeps) { $setupArgs += "--skip-deps" }
if ($Quick) { $setupArgs += "--quick" }
& python @setupArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 部署配置失败（退出码 $LASTEXITCODE）"
    Pop-Location
    exit 1
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
Pop-Location

Write-Host ""
Write-Host "============================================================"
Write-Host "  ✅ LumiLearn 部署完成"
Write-Host "  终端页面:   http://localhost:18080"
Write-Host "  管理面板:   http://localhost:18080/admin"
Write-Host "  REST API:   http://localhost:18081"
Write-Host "  模型管理:   http://localhost:18082"
Write-Host "============================================================"
