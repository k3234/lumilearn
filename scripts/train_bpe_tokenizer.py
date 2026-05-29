#!/usr/bin/env python3
"""
BPE Tokenizer Training Script
Extracts training corpus from CSV + JSON, then trains a BPE tokenizer
"""
import csv
import json
import os

from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders, processors

LUMILEARN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSV_FILES = [
    os.path.join(LUMILEARN_DIR, "lumilearn_training_merged.csv"),
    os.path.join(LUMILEARN_DIR, "lumilearn_master.csv"),
]

JSON_FILE = os.path.join(os.path.dirname(LUMILEARN_DIR), "training_data_batch001.json")

CORPUS_PATH = os.path.join(LUMILEARN_DIR, "data", "bpe_corpus.txt")
TOKENIZER_PATH = os.path.join(LUMILEARN_DIR, "framework", "bpe_tokenizer.json")

VOCAB_SIZE = 8000
MIN_FREQUENCY = 2
SPECIAL_TOKENS = ["[PAD]", "[EOS]", "[BOS]", "[UNK]"]


def extract_texts():
    texts = []
    seen = set()

    for csv_path in CSV_FILES:
        print(f"Reading {os.path.basename(csv_path)}...")
        with open(csv_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                content = row.get("content", "").strip()
                if content and content not in seen:
                    seen.add(content)
                    texts.append(content)
        print(f"  -> {len(texts)} unique texts so far")

    if os.path.exists(JSON_FILE):
        print(f"Reading {os.path.basename(JSON_FILE)}...")
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            for msg in item.get("messages", []):
                content = msg.get("content", "").strip()
                if content and content not in seen:
                    seen.add(content)
                    texts.append(content)
        print(f"  -> {len(texts)} unique texts total")

    return texts


def train_tokenizer(texts):
    tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))

    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)

    tokenizer.decoder = decoders.ByteLevel()

    trainer = trainers.BpeTrainer(
        vocab_size=VOCAB_SIZE,
        min_frequency=MIN_FREQUENCY,
        special_tokens=SPECIAL_TOKENS,
        show_progress=True,
    )

    print(f"Training BPE tokenizer on {len(texts)} texts...")
    tokenizer.train_from_iterator(texts, trainer)

    tokenizer.post_processor = processors.TemplateProcessing(
        single="[BOS] $A [EOS]",
        special_tokens=[
            ("[BOS]", tokenizer.token_to_id("[BOS]")),
            ("[EOS]", tokenizer.token_to_id("[EOS]")),
        ],
    )

    os.makedirs(os.path.dirname(TOKENIZER_PATH), exist_ok=True)
    tokenizer.save(TOKENIZER_PATH)
    print(f"Tokenizer saved to {TOKENIZER_PATH}")

    print(f"Vocab size: {tokenizer.get_vocab_size()}")
    return tokenizer


def verify_tokenizer(tokenizer):
    tokenizer.no_padding()
    tokenizer.no_truncation()

    print("\n=== Verification ===")

    assert tokenizer.token_to_id("[PAD]") == 0, "PAD != 0"
    assert tokenizer.token_to_id("[EOS]") == 1, "EOS != 1"
    assert tokenizer.token_to_id("[BOS]") == 2, "BOS != 2"
    assert tokenizer.token_to_id("[UNK]") == 3, "UNK != 3"
    print("Special tokens OK")

    enc = tokenizer.encode("三角形的面积公式")
    print(f"'三角形的面积公式': {len(enc.ids)} tokens -> {enc.tokens}")
    assert len(enc.ids) < 14, f"BPE should use fewer tokens than char-level (14), got {len(enc.ids)}"

    enc = tokenizer.encode("x²+y²=z²")
    decoded = tokenizer.decode(enc.ids)
    print(f"'x²+y²=z²': {len(enc.ids)} tokens -> '{decoded}'")
    assert decoded == "x²+y²=z²", f"roundtrip failed: '{decoded}'"

    enc = tokenizer.encode("sin(x)函数图像")
    decoded = tokenizer.decode(enc.ids)
    print(f"'sin(x)函数图像': {decoded}")
    assert decoded == "sin(x)函数图像", f"roundtrip failed: '{decoded}'"

    assert tokenizer.get_vocab_size() <= VOCAB_SIZE, f"vocab too large: {tokenizer.get_vocab_size()}"
    print("Vocab size OK")

    print("\nAll verifications passed!")


def main():
    os.makedirs(os.path.dirname(CORPUS_PATH), exist_ok=True)

    if os.path.exists(CORPUS_PATH):
        print(f"Corpus already exists at {CORPUS_PATH}, loading...")
        with open(CORPUS_PATH, "r", encoding="utf-8") as f:
            texts = [line.rstrip("\n") for line in f]
        print(f"Loaded {len(texts)} texts")
    else:
        texts = extract_texts()
        with open(CORPUS_PATH, "w", encoding="utf-8") as f:
            for t in texts:
                f.write(t + "\n")
        print(f"Saved {len(texts)} texts to {CORPUS_PATH}")

    tokenizer = train_tokenizer(texts)
    verify_tokenizer(tokenizer)


if __name__ == "__main__":
    main()