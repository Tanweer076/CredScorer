"""Entry point for the single-server deploy: the API under /api and the React app everywhere else.

Run with: uvicorn app.serve:app
(Local development still uses app.main:app, with Vite or nginx in front.)
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.main import app as api

DIST = Path(settings.frontend_dist).resolve()


@asynccontextmanager
async def lifespan(_):
    # A mounted app's own startup doesn't run by itself, so run the API's (it loads the model).
    async with api.router.lifespan_context(api):
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api)  # the browser calls /api/...; Swagger is at /api/docs


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    """Real files (JS, CSS, icons) as they are; any other path gets index.html so React Router can show the page."""
    file = (DIST / path).resolve()
    if path and file.is_file() and file.is_relative_to(DIST):
        return FileResponse(file)
    index = DIST / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Frontend not built")
    return FileResponse(index)