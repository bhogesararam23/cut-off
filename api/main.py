"""Read-only API that serves the pipeline's output files. Only the health check exists so far."""

from fastapi import FastAPI

VERSION = "0.1.0"

app = FastAPI(title="Cut Off API", version=VERSION)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}
