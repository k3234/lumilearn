import sys, os, json, time, io
import torch
import torch.nn.functional as F

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from framework.model import LumiLearnModel
from framework.config import ModelConfig


class LumiLearnInference:
    def __init__(self, model_dir: str, device: str = "auto"):
        self.model_dir = model_dir
        config_path = os.path.join(model_dir, "model", "config.json")

        if not os.path.exists(config_path):
            dirs = sorted(
                [d for d in os.listdir(model_dir)
                 if (d.startswith("LumiLearn-") or d.startswith("outputs"))
                 and os.path.isdir(os.path.join(model_dir, d))],
                reverse=True,
            )
            if not dirs:
                dirs = sorted(
                    [d for d in os.listdir(model_dir)
                     if os.path.isdir(os.path.join(model_dir, d))],
                    reverse=True,
                )
            for sub in dirs:
                candidate = os.path.join(model_dir, sub, "model", "config.json")
                if os.path.exists(candidate):
                    config_path = candidate
                    model_dir = os.path.join(model_dir, sub)
                    break

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No model config found in {model_dir}")

        with open(config_path, "r") as f:
            config_dict = json.load(f)

        self.config = ModelConfig()
        for k, v in config_dict.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)

        if device == "auto":
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)

        self.model = LumiLearnModel(self.config)
        self.model.to(self.device)
        self.model.eval()

        model_path = os.path.join(model_dir, "model", "model.pt")
        if not os.path.exists(model_path):
            alt = os.path.join(model_dir, "model.pt")
            if os.path.exists(alt):
                model_path = alt
        state = torch.load(model_path, map_location=self.device, weights_only=True)

        if isinstance(state, dict):
            if "model_state_dict" in state:
                self.model.load_state_dict(state["model_state_dict"])
            else:
                keys = list(state.keys())
                if any(k.startswith("transformer.") or k.startswith("lm_head.") for k in keys):
                    self.model.load_state_dict(state)
                elif any(k.startswith("tok_embeddings.") for k in keys):
                    self.model.load_state_dict(state)
                else:
                    self.model.load_state_dict(state, strict=False)
        else:
            self.model.load_state_dict(state, strict=False)

        tokenizer_path = os.path.join(model_dir, "tokenizer.json")
        if not os.path.exists(tokenizer_path):
            for root, _, files in os.walk(model_dir):
                if "tokenizer.json" in files:
                    tokenizer_path = os.path.join(root, "tokenizer.json")
                    break
        self.vocab = self._load_tokenizer(tokenizer_path)

        self.vocab_size = self.config.vocab_size
        self.id_to_char = {v: k for k, v in self.vocab.items()}

        print(f"[LumiLearn] Loaded model: {sum(p.numel() for p in self.model.parameters()):,} params")
        print(f"[LumiLearn] Device: {self.device}, Vocab: {len(self.vocab)}")

    def _load_tokenizer(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            if "char_to_id" in data:
                return data["char_to_id"]
            if "vocab" in data:
                v = data["vocab"]
                if isinstance(v, dict):
                    return v
                if isinstance(v, list):
                    return {ch: i for i, ch in enumerate(v)}
            return {ch: i for i, ch in enumerate(data.keys())}
        if isinstance(data, list):
            return {ch: i for i, ch in enumerate(data)}
        return data

    def encode(self, text: str, max_len: int | None = None):
        if max_len is None:
            max_len = self.config.max_seq_len
        ids = []
        for ch in text:
            ids.append(self.vocab.get(ch, self.vocab.get("<unk>", 0)))
        if len(ids) > max_len - 1:
            ids = ids[-(max_len - 1):]
        return ids

    def decode(self, ids: list[int]) -> str:
        chars = []
        for i in ids:
            ch = self.id_to_char.get(i, "")
            if ch == "<eos>" or ch == "<pad>":
                break
            chars.append(ch)
        return "".join(chars)

    @torch.no_grad()
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 128,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        repetition_penalty: float = 1.1,
        stop_tokens: list[str] | None = None,
    ) -> dict:
        if stop_tokens is None:
            stop_tokens = ["<eos>", "<|end|>", "\n\n\n"]

        input_ids = self.encode(prompt)
        if not input_ids:
            return {"text": "", "tokens": 0, "time": 0.0}

        t_start = time.time()
        generated = list(input_ids)
        eos_id = self.vocab.get("<eos>", -1)

        full_ids = torch.tensor([input_ids], dtype=torch.long, device=self.device)

        for _ in range(max_new_tokens):
            if full_ids.size(1) > self.config.max_seq_len:
                full_ids = full_ids[:, -self.config.max_seq_len:]

            outputs = self.model(full_ids)
            logits = outputs["logits"][:, -1, :] / max(temperature, 0.01)
            logits = torch.nan_to_num(logits, nan=-1e9, posinf=-1e9, neginf=-1e9)

            for tid in set(generated[-20:]):
                logits[0, tid] /= repetition_penalty

            if top_k > 0:
                topk_vals, topk_idx = torch.topk(logits, min(top_k, logits.size(-1)), dim=-1)
                mask = logits < topk_vals[:, -1:]
                logits[mask] = float("-inf")

            if top_p < 1.0:
                valid_mask = logits > float("-inf")
                sorted_logits, sorted_idx = torch.sort(logits, descending=True, dim=-1)
                cum_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                sorted_logits[cum_probs > top_p] = float("-inf")
                logits = logits.scatter(-1, sorted_idx, sorted_logits)

            if torch.all(logits == float("-inf")):
                probs = torch.ones_like(logits) / logits.size(-1)
            else:
                probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1).item()
            generated.append(next_id)

            if next_id == eos_id:
                break

            full_ids = torch.cat([full_ids, torch.tensor([[next_id]], dtype=torch.long, device=self.device)], dim=-1)

        elapsed = time.time() - t_start
        output_text = self.decode(generated[len(input_ids):])

        for st in stop_tokens:
            idx = output_text.find(st)
            if idx >= 0:
                output_text = output_text[:idx]
                break

        return {
            "text": output_text,
            "tokens": len(generated) - len(input_ids),
            "time": round(elapsed, 2),
            "tokens_per_sec": round((len(generated) - len(input_ids)) / max(elapsed, 0.01), 1),
        }