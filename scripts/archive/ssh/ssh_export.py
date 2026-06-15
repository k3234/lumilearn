import paramiko
import sys

HOST = '192.168.2.63'
USER = 'kai'
PASSWORD = 'WWw2021x'
TIMEOUT = 300


def run_step(ssh, cmd, step_name):
    print(f"\n{'='*60}")
    print(f"  {step_name}")
    print(f"{'='*60}")
    print(f"  CMD: {cmd}")
    print(f"{'-'*60}")

    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=TIMEOUT)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    exit_code = stdout.channel.recv_exit_status()

    if out:
        print(out.rstrip())
    if err:
        print("[STDERR]", err.rstrip())

    print(f"[EXIT_CODE] {exit_code}")
    return exit_code, out, err


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
        print("SSH 连接成功: {}@{}\n".format(USER, HOST))
    except Exception as e:
        print(f"SSH 连接失败: {e}")
        sys.exit(1)

    try:
        # ── 步骤 1: 安装 tokenizers ──
        ec1, out1, err1 = run_step(ssh, "pip3 install tokenizers -q", "步骤 1: 安装 Python 依赖 (tokenizers)")
        if ec1 != 0:
            print("\n[ERROR] 步骤 1 失败 (exit_code={}), 停止执行。".format(ec1))
            if err1:
                print("错误详情:", err1[:1000])
            ssh.close()
            sys.exit(1)
        print("步骤 1 完成。")

        # ── 步骤 2: 运行 export_gguf_v6.py ──
        ec2, out2, err2 = run_step(
            ssh,
            "cd /home/kai/lumilearn && python3 export_gguf_v6.py 2>&1",
            "步骤 2: 运行 export_gguf_v6.py 导出 GGUF"
        )
        if ec2 != 0:
            print("\n[ERROR] 步骤 2 失败 (exit_code={}), 停止执行。".format(ec2))
            if err2:
                print("错误详情:", err2[:1000])
            ssh.close()
            sys.exit(1)
        print("步骤 2 完成。")

        # ── 步骤 3: 检查导出的 GGUF 文件 ──
        ec3, out3, err3 = run_step(
            ssh,
            "ls -lh /home/kai/lumilearn/deploy_gguf/*.gguf 2>&1",
            "步骤 3: 检查导出的 GGUF 文件"
        )
        print("步骤 3 完成。")

        # ── 汇总 ──
        print(f"\n{'='*60}")
        print("  汇总结果")
        print(f"{'='*60}")

        gguf_success = ec2 == 0
        print(f"GGUF 导出成功: {'是' if gguf_success else '否'}")

        gguf_output = out3.strip()
        if gguf_output and "No such file" not in gguf_output:
            print(f"GGUF 文件列表:\n{gguf_output}")
        else:
            print("GGUF 文件列表: (无匹配文件或路径不存在)")

        print(f"\n--- export_gguf_v6.py 完整输出日志 ---")
        print(out2.strip() if out2.strip() else "(无输出)")

    finally:
        ssh.close()
        print("\nSSH 连接已关闭。")


if __name__ == '__main__':
    main()