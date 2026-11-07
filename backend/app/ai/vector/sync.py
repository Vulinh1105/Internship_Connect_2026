from datetime import timedelta
from hashlib import sha256
from threading import Lock
import json, logging
from sqlalchemy import select
from app.core.config import now
from app.modules.jobs import service as jobs
from app.modules.students import service as students
from app.modules.knowledge import service as knowledge
from app.ai.providers.embedding import embed
from . import client as vectors
from .models import SyncTask

lock=Lock()
log=logging.getLogger(__name__)

def enqueue(db,kind,ident):
    db.add(SyncTask(entity_type=kind,entity_id=ident))

def refresh(db,kind,ident):
    info={"jobs":jobs.vector_record,"cvs":students.vector_record,"knowledge":knowledge.vector_record}[kind](db,ident)
    if not info:
        vectors.delete_entity(kind,ident)
        return
    if kind=="jobs":
        texts=[" ".join([info["title"],info["description"],info["requirements"]," ".join(info["skills"])])]
        payload={k:info[k] for k in ("location","category","level","salary_min","salary_max","work_mode","deadline")}
        payload.update(status="active",skill_ids=info["skills"])
    elif kind=="cvs":
        texts=[info["text"]]
        payload={"user_id":info["user_id"]}
    else:
        texts=info["texts"]
        payload={k:info[k] for k in ("title","source","topic","version")}
    digest=sha256(json.dumps([texts,payload],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    old=vectors.entries(kind,vectors.filters(entity_id=ident))
    if len(old)==len(texts) and all(p.payload.get("hash")==digest for p in old):
        return
    if texts:
        values=embed(texts)
        vectors.upsert(kind,[(vectors.point_id(kind,ident,i),v,{**payload,"entity_id":ident,"position":i,"hash":digest})
                             for i,v in enumerate(values)])
    keep={vectors.point_id(kind,ident,i) for i in range(len(texts))}
    vectors.delete_points(kind,[p.id for p in old if p.id not in keep])
    if kind=="jobs":
        jobs.mark_synced(db,ident,digest)
    elif kind=="knowledge":
        knowledge.mark_synced(db,ident,digest,texts)

def drain(db,limit=40):
    with lock:
        ids=list(db.scalars(select(SyncTask.id).where(SyncTask.status=="pending",SyncTask.available_at<=now())
                            .order_by(SyncTask.id).limit(limit)))
        db.commit()
        result={"done":0,"failed":0}
        for ident in ids:
            task=db.get(SyncTask,ident)
            try:
                refresh(db,task.entity_type,task.entity_id)
                task.status="done"
                db.commit()
                result["done"]+=1
            except Exception as e:
                db.rollback()
                task=db.get(SyncTask,ident)
                task.attempts+=1
                task.last_error=type(e).__name__
                task.status="failed" if task.attempts>=5 else "pending"
                task.available_at=now()+timedelta(seconds=min(600,5*2**task.attempts))
                db.commit()
                log.warning("Vector task %s deferred (%s)",ident,type(e).__name__)
                result["failed"]+=1
        return result

def reconcile(db):
    for kind,ids in [("jobs",jobs.public_ids(db)),("knowledge",knowledge.public_ids(db)),("cvs",students.confirmed_cv_ids(db))]:
        existing={p.payload["entity_id"] for p in vectors.entries(kind)}
        for ident in existing|ids:
            enqueue(db,kind,ident)
    db.commit()
