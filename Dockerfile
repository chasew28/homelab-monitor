FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

COPY . .

EXPOSE 5001
ENV HLM_CONFIG_DIR=/app

CMD ["hlm", "run"]
