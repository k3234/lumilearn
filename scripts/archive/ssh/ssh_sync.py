import paramiko
import os
import sys

BASE = r"e:\学习LLM\lumilearn"
REMOTE = "/home/kai/lumilearn"

FILES_TO_SYNC = [
    ("tianhong/lumiterm_server.py", "tianhong/lumiterm_server.py"),
    ("tianhong/templates/lumiterm.html", "tianhong/templates/lumiterm.html"),
    ("tianhong/start_all.sh", "tianhong/start_all.sh"),
    ("tianhong/deploy_lumilearn_real.sh", "tianhong/deploy_lumilearn_real.sh"),
    ("export_gguf_v6.py", "export_gguf_v6.py"),
    ("train.py", "train.py"),
]

def sync():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)
    sftp = ssh.open_sftp()

    for local_rel, remote_rel in FILES_TO_SYNC:
        local_path = os.path.join(BASE, local_rel)
        remote_path = f"{REMOTE}/{remote_rel}"

        if not os.path.exists(local_path):
            print(f"  SKIP (not found): {local_rel}")
            continue

        try:
            # ensure remote dir exists
            remote_dir = os.path.dirname(remote_path)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                sftp.mkdir(remote_dir)

            sftp.put(local_path, remote_path)
            local_size = os.path.getsize(local_path)
            remote_stat = sftp.stat(remote_path)
            print(f"  OK  {local_rel} ({local_size} bytes) -> {remote_path}")
        except Exception as e:
            print(f"  FAIL {local_rel}: {e}")

    sftp.close()

    # sync framework directory
    print()
    print("Syncing framework/ directory...")
    local_framework = os.path.join(BASE, "framework")
    remote_framework = f"{REMOTE}/framework"

    if os.path.isdir(local_framework):
        # create tarball and transfer
        import tempfile, subprocess
        tar_path = os.path.join(tempfile.gettempdir(), "framework.tar.gz")
        
        # on windows, use python tarfile
        import tarfile
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(local_framework, arcname="framework")
        
        tar_size = os.path.getsize(tar_path)
        print(f"  Created tar: {tar_path} ({tar_size} bytes)")

        sftp = ssh.open_sftp()
        remote_tar = f"{REMOTE}/framework.tar.gz"
        sftp.put(tar_path, remote_tar)
        sftp.close()

        # extract on remote
        stdin, stdout, stderr = ssh.exec_command(
            f"cd {REMOTE} && tar xzf framework.tar.gz && rm framework.tar.gz && echo DONE"
        )
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        print(f"  Extract: {out}")
        if err:
            print(f"  STDERR: {err[:200]}")

        os.remove(tar_path)
    else:
        print(f"  SKIP: {local_framework} not found")

    # make scripts executable
    stdin, stdout, stderr = ssh.exec_command(
        f"chmod +x {REMOTE}/tianhong/start_all.sh {REMOTE}/tianhong/deploy_lumilearn_real.sh && echo OK"
    )
    print(f"  chmod: {stdout.read().decode().strip()}")

    ssh.close()
    print()
    print("Sync complete!")

if __name__ == "__main__":
    sync()