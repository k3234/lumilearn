import sys, os, time, uuid, json, argparse
from flask import Flask, request, jsonify, Response, stream_with_context

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inference import LumiLearnInference

app = Flask(__name__)

MODEL_DIR = os.environ.get("LUMILEARN_MODEL_DIR", os.path.join(os.path.dirname(__file__), "outputs"))
MODEL_VERSION = os.environ.get("LUMILEARN_VERSION", "v5")
DEVICE = os.environ.get("LUMILEARN_DEVICE", "auto")
MAX_NEW_TOKENS = int(os.environ.get("LUMILEARN_MAX_TOKENS", "256"))
TEMPERATURE = float(os.environ.get("LUMILEARN_TEMPERATURE", "0.7"))
TOP_P = float(os.environ.get("LUMILEARN_TOP_P", "0.9"))

model: LumiLearnInference | None = None


def get_model():
    global model
    if model is None:
        dirs = sorted(
            [d for d in os.listdir(MODEL_DIR) if d.startswith("LumiLearn-") and os.path.isdir(os.path.join(MODEL_DIR, d))],
            reverse=True,
        )
        if not dirs:
            raise FileNotFoundError(f"No LumiLearn model found in {MODEL_DIR}")
        model_path = os.path.join(MODEL_DIR, dirs[0])
        print(f"[Server] Loading model from {model_path}")
        model = LumiLearnInference(model_path, device=DEVICE)
    return model


@app.route("/v1/models", methods=["GET"])
def list_models():
    return jsonify({
        "object": "list",
        "data": [{
            "id": f"LumiLearn-{MODEL_VERSION}",
            "object": "model",
            "owned_by": "lumilearn",
        }],
    })


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    data = request.get_json(force=True)
    messages = data.get("messages", [])
    stream = data.get("stream", False)
    temperature = data.get("temperature", TEMPERATURE)
    max_tokens = data.get("max_tokens", MAX_NEW_TOKENS)
    top_p = data.get("top_p", TOP_P)

    prompt_parts = []
    system_msg = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_msg = content
        elif role == "user":
            prompt_parts.append(f"问题：{content}")
        elif role == "assistant":
            prompt_parts.append(f"回答：{content}")

    full_prompt = "\n".join(prompt_parts)
    if system_msg:
        full_prompt = f"指令：{system_msg}\n\n{full_prompt}"
    full_prompt += "\n回答："

    if not full_prompt.strip():
        full_prompt = "请回答以下问题：\n"

    m = get_model()

    if stream:
        return Response(
            stream_with_context(_stream_response(m, full_prompt, temperature, max_tokens, top_p)),
            mimetype="text/event-stream",
        )

    result = m.generate(
        full_prompt,
        max_new_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )

    return jsonify({
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": f"LumiLearn-{MODEL_VERSION}",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": result["text"],
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": len(full_prompt),
            "completion_tokens": result["tokens"],
            "total_tokens": len(full_prompt) + result["tokens"],
        },
    })


def _stream_response(m, prompt, temperature, max_tokens, top_p):
    result = m.generate(prompt, max_new_tokens=max_tokens, temperature=temperature, top_p=top_p)
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    text = result["text"]
    chunk_size = 4
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        payload = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": f"LumiLearn-{MODEL_VERSION}",
            "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    final = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": f"LumiLearn-{MODEL_VERSION}",
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@app.route("/api/generate", methods=["POST"])
def ollama_generate():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    stream = data.get("stream", True)
    options = data.get("options", {})
    temperature = options.get("temperature", TEMPERATURE)
    max_tokens = options.get("num_predict", MAX_NEW_TOKENS)
    top_p = options.get("top_p", TOP_P)

    full_prompt = f"指令：你是LumiLearn，一个中文教育AI助手。请用中文回答。\n\n问题：{prompt}\n回答："

    m = get_model()

    if stream:
        def ollama_stream():
            result = m.generate(full_prompt, max_new_tokens=max_tokens, temperature=temperature, top_p=top_p)
            for ch in result["text"]:
                payload = {"model": f"LumiLearn-{MODEL_VERSION}", "response": ch, "done": False}
                yield json.dumps(payload, ensure_ascii=False) + "\n"
            final = {
                "model": f"LumiLearn-{MODEL_VERSION}",
                "response": "",
                "done": True,
                "total_duration": int(result["time"] * 1e9),
                "eval_count": result["tokens"],
            }
            yield json.dumps(final, ensure_ascii=False) + "\n"

        return Response(stream_with_context(ollama_stream()), mimetype="application/x-ndjson")

    result = m.generate(full_prompt, max_new_tokens=max_tokens, temperature=temperature, top_p=top_p)
    return jsonify({
        "model": f"LumiLearn-{MODEL_VERSION}",
        "response": result["text"],
        "done": True,
        "total_duration": int(result["time"] * 1e9),
        "eval_count": result["tokens"],
    })


@app.route("/api/tags", methods=["GET"])
def ollama_tags():
    return jsonify({
        "models": [{
            "name": f"LumiLearn-{MODEL_VERSION}",
            "modified_at": "2025-05-26T21:41:00Z",
            "size": 0,
        }],
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": f"LumiLearn-{MODEL_VERSION}", "device": DEVICE})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--model-dir", default=MODEL_DIR)
    parser.add_argument("--device", default=DEVICE)
    args = parser.parse_args()

    os.environ["LUMILEARN_MODEL_DIR"] = args.model_dir
    global DEVICE
    DEVICE = args.device

    print(f"[Server] LumiLearn Inference Server v1.0")
    print(f"[Server] Model dir: {args.model_dir}")
    print(f"[Server] Device: {args.device}")
    print(f"[Server] Listening on {args.host}:{args.port}")
    get_model()
    app.run(host=args.host, port=args.port, debug=False, threaded=True)