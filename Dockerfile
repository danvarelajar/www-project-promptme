# PromptMe in one container: the dashboard plus every challenge it starts.
# The model is NOT inside: point OLLAMA_HOST at an Ollama (or gateway).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Run as an unprivileged user; challenges write their state (stores,
# progress, logs) under /app.
RUN useradd --create-home --uid 10001 promptme \
    && mkdir -p /app/data /app/logs /app/run \
    && chown -R promptme:promptme /app
USER promptme

# 5000 dashboard, 5001-5010 challenges, 5012 the LLM04 collector
EXPOSE 5000-5010 5012
CMD ["python", "main.py"]
