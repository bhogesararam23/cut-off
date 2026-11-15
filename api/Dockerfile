# Build from the repository root:  docker build -f api/Dockerfile -t cutoff-api .
# python:3.11-slim, pinned by digest (multi-arch index)
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY api/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY api/*.py /app/
COPY web/public/data /app/data

# The build fails if the data is mock data: a mock must never be served as a real result.
RUN python -c "import json,sys,pathlib; bad=[str(p) for n in ('event.json','stats.json') for p in pathlib.Path('/app/data').rglob(n) if json.loads(p.read_text(encoding='utf-8')).get('mock') is True]; sys.exit('mock data in image: '+', '.join(bad)) if bad else print('data check ok')"

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && chown -R 10001:10001 /app
USER 10001:10001

ENV DATA_DIR=/app/data \
    PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"]

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
