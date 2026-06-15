"""
AI Coding Tools - 配置辅助脚本

帮助你快速检查和配置 AI 编程工具环境
包括: Ollama, Cursor, Continue, Aider, GitHub Copilot

使用方法:
    python ai_coding_tools.py              # 环境检查
    python ai_coding_tools.py --check      # 检查已安装的工具
    python ai_coding_tools.py --setup      # 安装推荐工具
    python ai_coding_tools.py --install-cursorrules  # 安装 Cursor 规则
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


# ============================================================
# 项目配置
# ============================================================

LUMILEARN_ROOT = Path(__file__).parent.parent  # lumilearn 根目录
SKILLS_DIR = LUMILEARN_ROOT / "skills" / "ai-coding-tools"


# ============================================================
# 工具检测
# ============================================================

def check_ollama():
    """检查 Ollama 是否已安装"""
    print("\n🔍 检查 Ollama...")
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        version = result.stdout.strip()
        print(f"  ✅ 已安装: {version}")

        # 检查有哪些模型
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            models = [l for l in result.stdout.strip().split("\n") if l]
            if len(models) > 1:  # 第一行是表头
                print(f"  📦 已下载模型:")
                for m in models[1:]:  # 跳过表头
                    parts = m.split()
                    if parts:
                        print(f"     - {parts[0]}")
            else:
                print("  ⚠️  还没有下载任何模型")
                print("     推荐: ollama pull qwen2.5-coder:7b")
        except Exception as e:
            print(f"  ⚠️  无法获取模型列表: {e}")

        return True
    except FileNotFoundError:
        print("  ❌ 未安装")
        print("     安装: 访问 https://ollama.com 下载安装包")
        return False
    except Exception as e:
        print(f"  ❌ 检测失败: {e}")
        return False


def check_vscode():
    """检查 VSCode 是否已安装"""
    print("\n🔍 检查 VSCode...")
    try:
        result = subprocess.run(
            ["code", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        version = result.stdout.strip().split("\n")[0]
        print(f"  ✅ 已安装: VSCode {version}")
        return True
    except FileNotFoundError:
        print("  ❌ 未安装")
        print("     安装: 访问 https://code.visualstudio.com")
        return False
    except Exception as e:
        print(f"  ⚠️  检测失败: {e}")
        return False


def check_cursor():
    """检查 Cursor 是否已安装（Windows 上通过检查可执行文件）"""
    print("\n🔍 检查 Cursor IDE...")

    # Windows 常见安装路径
    possible_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\cursor\Cursor.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Cursor\Cursor.exe"),
        os.path.expandvars(r"%PROGRAMFILES(x86)%\Cursor\Cursor.exe"),
    ]

    found = False
    for path in possible_paths:
        if os.path.exists(path):
            print(f"  ✅ 已安装: {path}")
            found = True
            break

    if not found:
        print("  ❌ 未安装（或未在标准路径）")
        print("     安装: 访问 https://cursor.com 下载")

    return found


def check_aider():
    """检查 Aider 是否已安装"""
    print("\n🔍 检查 Aider...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "aider", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✅ 已安装: {version or 'Aider (版本信息未显示)'}")
            return True
        else:
            # 尝试直接调用 aider
            result2 = subprocess.run(
                ["aider", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result2.returncode == 0:
                print(f"  ✅ 已安装: Aider")
                return True

    except (FileNotFoundError, subprocess.CalledProcessError):
        print("  ❌ 未安装")
        print("     安装: pip install aider-chat")
        return False
    except Exception as e:
        print(f"  ⚠️  检测失败: {e}")
        return False

    print("  ❌ 未安装")
    print("     安装: pip install aider-chat")
    return False


def check_cursorrules():
    """检查 .cursorrules 是否已安装到项目根目录"""
    print("\n🔍 检查 Cursor 规则集...")
    rules_path = LUMILEARN_ROOT / ".cursorrules"

    if rules_path.exists():
        print(f"  ✅ 已安装: {rules_path}")
        return True
    else:
        print(f"  ⚠️  未安装: {rules_path}")
        print(f"     安装: python ai_coding_tools.py --install-cursorrules")
        return False


# ============================================================
# 安装/配置操作
# ============================================================

def install_cursorrules():
    """将 .cursorrules 复制到项目根目录"""
    print("\n📦 安装 Cursor 规则集到 LumiLearn 项目...")

    source = SKILLS_DIR / ".cursorrules"
    target = LUMILEARN_ROOT / ".cursorrules"

    if not source.exists():
        print(f"  ❌ 找不到源文件: {source}")
        return False

    try:
        shutil.copy2(source, target)
        print(f"  ✅ 已安装: {target}")
        print("     现在在 Cursor IDE 中打开 LumiLearn 项目，")
        print("     AI 会自动读取这个规则文件！")
        return True
    except Exception as e:
        print(f"  ❌ 安装失败: {e}")
        return False


def install_aider():
    """安装 Aider"""
    print("\n📦 安装 Aider (终端 AI 编程助手)...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "aider-chat", "--upgrade"],
            check=True
        )
        print("  ✅ 安装成功！")
        print("     使用: cd lumilearn ; aider --model ollama/qwen2.5-coder:7b")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ 安装失败: {e}")
        return False


def install_ollama_coder_models():
    """推荐下载的代码模型"""
    print("\n📦 推荐的 Ollama 代码模型:")
    print("     1. qwen2.5-coder:7b    - 阿里云千问代码模型（推荐）")
    print("     2. deepseek-coder:6.7b - 深度求索代码模型")
    print("     3. codegecko:7b         - 轻量级代码模型")
    print()
    print("     下载命令:")
    print("     ollama pull qwen2.5-coder:7b")
    print("     ollama pull deepseek-coder:6.7b")
    print()
    choice = input("     要下载 qwen2.5-coder:7b 吗？(y/n): ").strip().lower()
    if choice == "y":
        try:
            print("     正在下载，这可能需要几分钟...")
            subprocess.run(["ollama", "pull", "qwen2.5-coder:7b"], check=True)
            print("  ✅ 下载完成！")
            return True
        except subprocess.CalledProcessError:
            print("  ❌ 下载失败")
            return False
    return False


# ============================================================
# 主程序
# ============================================================

def main():
    args = sys.argv[1:]

    print("=" * 60)
    print("  AI Coding Tools - 环境配置工具")
    print("  LumiLearn 项目专属")
    print("=" * 60)

    # 默认执行完整检查
    if not args or "--check" in args:
        check_ollama()
        check_vscode()
        check_cursor()
        check_aider()
        check_cursorrules()

        print("\n" + "=" * 60)
        print("  下一步:")
        print("  1. 如果 Ollama 已安装，运行: ollama pull qwen2.5-coder:7b")
        print("  2. 安装 Cursor 或 VSCode + Continue")
        print("  3. 安装 .cursorrules: python ai_coding_tools.py --install-cursorrules")
        print("  4. 详细使用指南: skills/ai-coding-tools/README.md")
        print("=" * 60)
        return

    # 安装推荐工具
    if "--setup" in args:
        print("\n🚀 开始配置 AI 编程环境...\n")

        if check_ollama():
            install_ollama_coder_models()
        else:
            print("\n⚠️  请先安装 Ollama，然后重新运行此脚本")
            return

        check_vscode()
        check_cursor()

        if not check_aider():
            choice = input("\n要安装 Aider 吗？(y/n): ").strip().lower()
            if choice == "y":
                install_aider()

        if not check_cursorrules():
            choice = input("\n要安装 .cursorrules 规则集吗？(y/n): ").strip().lower()
            if choice == "y":
                install_cursorrules()

        print("\n✅ 配置完成！")
        print("详细使用指南: skills/ai-coding-tools/README.md")
        return

    # 安装 Cursor 规则集
    if "--install-cursorrules" in args:
        install_cursorrules()
        return

    # 安装 Aider
    if "--install-aider" in args:
        install_aider()
        return

    # 帮助信息
    if "--help" in args or "-h" in args:
        print(__doc__)
        return

    # 未知参数
    print(f"\n❌ 未知参数: {args}")
    print("使用 --help 查看帮助")


if __name__ == "__main__":
    main()
