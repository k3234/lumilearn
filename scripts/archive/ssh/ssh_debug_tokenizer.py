import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

print("=== Debug: Check tokenizer building ===")
cmd = """python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/kai/lumilearn')
from framework.tokenizer import LumiLearnTokenizer

tokenizer = LumiLearnTokenizer(vocab_size=8000)
bpe_vocab = tokenizer._tokenizer.get_vocab()
print(f"BPE vocab size: {len(bpe_vocab)}")

# Sample entries
items = list(bpe_vocab.items())[:5]
print(f"Sample entries: {items}")

# Build the same way as export_gguf_v6.py
vocab = {}
for token_str, tid in bpe_vocab.items():
    if 0 <= tid < 8000:
        vocab[tid] = token_str

for i in range(8000):
    if i not in vocab:
        vocab[i] = f"<unk_{i}>"

vocab[0] = "<pad>"
vocab[1] = "<eos>"
vocab[2] = "<bos>"
vocab[3] = "<unk>"

result_tokens = [vocab[i] for i in range(8000)]
print(f"result_tokens count: {len(result_tokens)}")
print(f"  [0]: {repr(result_tokens[0])}")
print(f"  [1]: {repr(result_tokens[1])}")
print(f"  [2]: {repr(result_tokens[2])}")
print(f"  [3]: {repr(result_tokens[3])}")
print(f"  [4]: {repr(result_tokens[4])}")
print(f"  [7999]: {repr(result_tokens[7999])}")
PYEOF"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip())

print()
print("=== Debug: Test gguf add_array ===")
cmd = """python3 << 'PYEOF'
from gguf import GGUFWriter
import tempfile, os

# Test with minimal data
tokens = ["<pad>", "<eos>", "<bos>", "<unk>", "hello", "world"]
scores = [0.0] * 6
toktypes = [1] * 6

path = "/tmp/test_gguf.gguf"
writer = GGUFWriter(path, "gpt2")
writer.add_string("tokenizer.ggml.model", "gpt2")
writer.add_array("tokenizer.ggml.tokens", tokens)
writer.add_array("tokenizer.ggml.scores", scores)
writer.add_array("tokenizer.ggml.token_type", toktypes)
writer.add_uint32("tokenizer.ggml.eos_token_id", 1)
writer.add_uint32("tokenizer.ggml.bos_token_id", 2)
writer.add_uint32("tokenizer.ggml.padding_token_id", 0)
writer.write_header_to_file()
writer.write_kv_data_to_file()
writer.write_tensors_to_file()
writer.close()

# Read back
from gguf import GGUFReader
r = GGUFReader(path)
t = r.fields.get("tokenizer.ggml.tokens")
if t:
    vals = t.parts[t.types[0]]
    print(f"Tokens array type: {type(vals)}")
    print(f"Tokens count: {len(vals)}")
    print(f"  [0]: {repr(vals[0])}")
    print(f"  [1]: {repr(vals[1])}")
    print(f"  [5]: {repr(vals[5])}")
else:
    print("NULL!")
os.unlink(path)
PYEOF"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip())

ssh.close()