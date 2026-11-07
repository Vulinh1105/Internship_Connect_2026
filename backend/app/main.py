import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.core import metadata
from app.core.config import AI_BACKEND, ROOT
from app.core.database import Session
from app.core.deps import Actor, DB
from app.modules.applications.router import router as applications
from app.modules.auth.router import router as auth
from app.modules.companies.router import router as companies
from app.modules.interviews.router import router as interviews
from app.modules.jobs.router import router as jobs
from app.modules.knowledge.router import router as knowledge
from app.modules.mock_interviews.router import router as mock
from app.modules.notifications.router import router as notifications
from app.modules.students.router import router as students
from app.ai.chatbot.router import router as chatbot
from app.ai.matching.service import recommend
from app.ai.vector import sync

log=logging.getLogger(__name__)

def tick(reconcile):
    with Session() as db:
        if reconcile:
            sync.reconcile(db)
        sync.drain(db)

async def worker():
    loop=asyncio.get_running_loop()
    next_reconcile=0
    while True:
        try:
            current=loop.time()
            await asyncio.to_thread(tick,current>=next_reconcile)
            if current>=next_reconcile:
                next_reconcile=current+86400
        except Exception:
            log.exception("Vector worker unavailable")
        await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(_):
    task=asyncio.create_task(worker())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

app=FastAPI(title="Internship Connect 2026",version="1.0.0",lifespan=lifespan)
for router in (auth,students,companies,jobs,applications,interviews,notifications,knowledge,mock,chatbot):
    app.include_router(router)

@app.middleware("http")
async def protect_origin(request:Request,call_next):
    origin=request.headers.get("origin")
    if request.method in {"POST","PUT","PATCH","DELETE"} and origin:
        if origin!=f"{request.url.scheme}://{request.url.netloc}":
            return JSONResponse({"detail":"Nguồn yêu cầu không hợp lệ"},status_code=403)
    return await call_next(request)

@app.get("/health")
def health(db:DB):
    db.execute(text("SELECT 1"))
    return {"status":"ok","database":db.bind.dialect.name,"ai":AI_BACKEND}

@app.get("/api/matching")
def matching(db:DB,actor:Actor):
    return recommend(db,actor)

@app.get("/")
def home():
    return RedirectResponse("/app/")

app.mount("/app",StaticFiles(directory=ROOT/"frontend",html=True),name="frontend")
