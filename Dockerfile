FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch==2.4.1 --index-url https://download.pytorch.org/whl/rocm6.0 \
    flask==3.0.0

WORKDIR /app

COPY framework/ ./framework/
COPY inference.py ./inference.py
COPY inference_server.py ./inference_server.py

ENV LUMILEARN_MODEL_DIR=/app/outputs
ENV LUMILEARN_VERSION=v5
ENV LUMILEARN_DEVICE=auto
ENV LUMILEARN_MAX_TOKENS=256
ENV LUMILEARN_TEMPERATURE=0.7
ENV LUMILEARN_TOP_P=0.9

EXPOSE 18080

CMD ["python", "-u", "inference_server.py", "--port", "18080"]