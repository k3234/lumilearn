import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

print("=== Check gguf version and API ===")
cmd = """python3 << 'PYEOF'
import gguf
print(f"gguf version: {gguf.__version__}")

from gguf import GGUFWriter
writer = GGUFWriter("/tmp/test.gguf", "gpt2")

# List available methods for tokenizer
methods = [m for m in dir(writer) if 'token' in m.lower() or 'add_' in m.lower()]
print(f"Tokenizer-related methods: {methods}")

# Check add_token_list
if hasattr(writer, 'add_token_list'):
    print("add_token_list: AVAILABLE")
else:
    print("add_token_list: NOT AVAILABLE")

# Check GGUFWriter constructor
import inspect
sig = inspect.signature(GGUFWriter.__init__)
print(f"GGUFWriter init: {sig}")

# Check add_array signature
sig = inspect.signature(writer.add_array)
print(f"add_array sig: {sig}")
PYEOF"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip())

print()
print("=== Try add_token_list ===")
cmd = """python3 << 'PYEOF'
from gguf import GGUFWriter, GGUFReader
import os

tokens = ["<pad>", "<eos>", "<bos>", "<unk>", "hello", "world", "test"]
path = "/tmp/test_tokenlist.gguf"

writer = GGUFWriter(path, "gpt2")
writer.add_string("tokenizer.ggml.model", "gpt2")

# Try add_token_list
if hasattr(writer, 'add_token_list'):
    writer.add_token_list(tokens)
    writer.add_uint32("tokenizer.ggml.eos_token_id", 1)
    writer.add_uint32("tokenizer.ggml.bos_token_id", 2)
    writer.add_uint32("tokenizer.ggml.padding_token_id", 0)
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()

    r = GGUFReader(path)
    t = r.fields.get("tokenizer.ggml.tokens")
    if t:
        vals = t.parts[t.types[0]]
        print(f"Type: {type(vals)}")
        print(f"Count: {len(vals)}")
        print(f"  [0]: {repr(vals[0])}")
        print(f"  [1]: {repr(vals[1])}")
        print(f"  [6]: {repr(vals[6])}")
    else:
        print("NULL!")
else:
    print("add_token_list not available")

os.unlink(path)
PYEOF"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip())

ssh.close()