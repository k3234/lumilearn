import paramiko

def run(cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    ssh.close()
    return out, err

print("=== Check existing GGUF tokenizer ===")
cmd = 'python3 -c "from gguf import GGUFReader; r=GGUFReader(\'/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf\'); t=r.get_field(\'tokenizer.ggml.tokens\'); print(\'tokens field:\', type(t)); vals=t.parts[t.types[0]](0) if t and len(t.parts)>0 else None; print(\'count:\', len(vals) if vals else \'NULL\')"'
out, err = run(cmd)
print(out)
if err: print("ERR:", err[:300])

print()
print("=== Check architecture ===")
cmd = 'python3 -c "from gguf import GGUFReader; r=GGUFReader(\'/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf\'); arch=r.get_field(\'general.architecture\'); print(\'arch:\', arch.parts[arch.types[0]](0) if arch else \'NULL\'); hs=r.get_field(\'gpt2.embedding_length\'); print(\'hidden:\', hs.parts[hs.types[0]](0) if hs else \'NULL\'); nl=r.get_field(\'gpt2.block_count\'); print(\'layers:\', nl.parts[nl.types[0]](0) if nl else \'NULL\')"'
out, err = run(cmd)
print(out)
if err: print("ERR:", err[:300])

print()
print("=== Check if gguf lib installed ===")
out, err = run("pip3 list 2>/dev/null | grep -i gguf || echo NOT_INSTALLED")
print(out)

print()
print("=== Check model checkpoint architecture ===")
out, err = run("python3 -c \"import torch; ckpt=torch.load('/home/kai/lumilearn/outputs/LumiLearn-v5_20260527_075859/checkpoints/checkpoint_best.pt', map_location='cpu'); sd=ckpt.get('model_state_dict',ckpt); print('Keys:', len(sd)); [print(f'  {k}: {list(v.shape)}') for i,(k,v) in enumerate(sd.items()) if i<5]\"")
print(out[:800])
if err: print("ERR:", err[:300])