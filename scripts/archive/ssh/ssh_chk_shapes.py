import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Check actual tensor names in checkpoint
remote_script = """import torch
ckpt = torch.load('/home/kai/lumilearn/outputs/LumiLearn-v5_20260527_075859/checkpoints/checkpoint_best.pt', map_location='cpu', weights_only=False)
state = ckpt['model_state_dict']
for k, v in sorted(state.items()):
    if 'attn' in k or 'qkv' in k or 'ln1' in k or 'ln2' in k:
        print(f'{k:50s} shape={list(v.shape)}')
"""
stdin, stdout, stderr = ssh.exec_command(
    "cat > /tmp/chk_shapes.py << 'PYEOF'\n" + remote_script + "\nPYEOF\npython3 /tmp/chk_shapes.py 2>&1",
    timeout=30
)
print(stdout.read().decode().strip())

ssh.close()