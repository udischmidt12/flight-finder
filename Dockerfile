# Flight-finder — production image for Fly.io
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Writable state (expenses, caches) goes on the mounted volume.
ENV DATA_DIR=/data
RUN mkdir -p /data

EXPOSE 8080

# One worker, many threads: the workload is all I/O (SerpApi, Anthropic),
# and this keeps memory low enough for a 256 MB machine. Long timeout: a
# pre-arrival lookup can spend ~30-60s in Claude + web search.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", \
     "--workers", "1", "--threads", "8", "--timeout", "120", \
     "--access-logfile", "-", "app:app"]
