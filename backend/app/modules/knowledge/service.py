from hashlib import sha256
import re
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select, text
from app.common import storage,file_parsing
from app.ai.rag.legacy_text import _clean_text
from app.common.records import record,require
from app.ai.providers.embedding import words
from app.core.config import now,ROOT,RUNTIME
from .models import Document,Chunk
from . import repository as repo

MAX_UPLOAD_BYTES = 50_000_000
MAX_PDF_PAGES = 600
MAX_DOCUMENT_CHARS = 3_000_000

def admin(actor):
    if actor["role"] not in {"staff","admin"}:
        raise HTTPException(403,"Chỉ nhân sự được quản lý tài liệu")

def list_all(db,actor):
    admin(actor)
    return [record(d,"id","code","title","topic","source","version","status","vector_synced_at") for d in db.scalars(select(Document))]

def publish(db,actor,title,content,source="",topic="FAQ"):
    from app.ai.vector.sync import enqueue
    admin(actor)
    d=Document(title=title,content=content,source=source or "Web",topic=topic)
    db.add(d);db.flush()
    enqueue(db,"knowledge",d.id)
    db.commit()
    return record(d,"id","title","status")

def read_document(path):
    content = file_parsing.parse(path,max_pdf_pages=MAX_PDF_PAGES,max_chars=None,ocr_tessdata=RUNTIME/"tessdata")
    if len(content) > MAX_DOCUMENT_CHARS:
        raise HTTPException(422, "Tài liệu vượt 3 triệu ký tự. Hãy tách thành nhiều phần.")
    return _clean_text(content)


def upload(db,actor,name,data,title):
    admin(actor)
    if not title.strip() or len(title)>220:
        raise HTTPException(422,"Tiêu đề không hợp lệ")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Tệp vượt giới hạn 50 MB.")
    key=storage.save(data,name,folder="knowledge",allowed={".txt",".md",".pdf",".docx"},max_bytes=MAX_UPLOAD_BYTES)
    path=storage.resolve(key)
    try:
        content=read_document(path)
        dest=ROOT/"data/knowledge"/path.name
        dest.parent.mkdir(parents=True,exist_ok=True)
        path.replace(dest)
        try:
            return publish(db,actor,title,content,str(dest.relative_to(ROOT)))
        except Exception:
            dest.unlink(missing_ok=True)
            raise
    finally:
        path.unlink(missing_ok=True)

def reprocess(db,actor,ident):
    from app.ai.vector.sync import enqueue
    admin(actor)
    d=require(repo.get_document(db,ident))
    source=(ROOT/d.source).resolve()
    if (d.status!="published" or not source.is_relative_to((ROOT/"data/knowledge").resolve())
            or source.suffix.lower()!=".pdf" or not source.is_file()):
        raise HTTPException(422,"Chỉ xử lý lại được PDF đang công khai có tệp gốc.")
    content=read_document(source)
    if d.content!=content or not d.vector_synced_at:
        d.content=content
        d.vector_synced_at=None
        enqueue(db,"knowledge",d.id)
        db.commit()
    return record(d,"id","title","status","vector_synced_at")


def remove(db,actor,ident):
    from app.ai.vector.sync import enqueue
    admin(actor)
    d=require(repo.get_document(db,ident))
    d.status="archived"
    enqueue(db,"knowledge",ident)
    db.commit()
    return {"ok":True}

def split(text):
    sections=re.split(r"(?m)(?=^#{1,6} )",text)
    for section in sections:
        tokens=section.split()
        for i in range(0,len(tokens),440):
            chunk=" ".join(tokens[i:i+500])
            if chunk:
                yield chunk
            if i+500>=len(tokens):
                break

def vector_record(db,ident):
    d=repo.get_document(db,ident)
    if not d or d.status!="published" or d.visibility!="public":
        return None
    return {"title":d.title,"topic":d.topic,"source":d.source,"version":d.version,"content_hash":d.content_hash,"texts":list(split(d.content))}

def mark_synced(db,ident,digest,texts):
    d=repo.get_document(db,ident)
    if d:
        for c in db.scalars(select(Chunk).filter_by(document_id=ident)):
            db.delete(c)
        db.flush()
        for i,t in enumerate(texts):
            db.add(Chunk(document_id=ident,position=i,text=t,content_hash=sha256(t.encode()).hexdigest()))
        d.content_hash=digest
        d.vector_synced_at=now()

def public_ids(db):
    return set(db.scalars(select(Document.id).filter_by(status="published",visibility="public")))

def chunks_for(db,ids,*,positions=None):
    if not ids:
        return []
    stmt=select(Chunk,Document).join(Document,Chunk.document_id==Document.id).where(
        Document.id.in_(ids),Document.status=="published",Document.visibility=="public")
    if positions is not None:
        stmt=stmt.where(Chunk.position.in_(positions))
    return [{"document_id":d.id,"position":c.position,"text":c.text,"title":d.title,"source":d.source} for c,d in db.execute(stmt)]

def lexical(db,query,limit=20):
    if db.bind.dialect.name=="mysql" and query.strip():
        match=text("MATCH(knowledge_chunks.text) AGAINST (:term IN NATURAL LANGUAGE MODE)").bindparams(term=query)
        order=text("MATCH(knowledge_chunks.text) AGAINST (:term IN NATURAL LANGUAGE MODE) DESC").bindparams(term=query)
        stmt=select(Chunk,Document).join(Document,Chunk.document_id==Document.id).where(
            Document.status=="published",Document.visibility=="public",match).order_by(order).limit(limit)
        return [{"document_id":d.id,"position":c.position,"text":c.text,"title":d.title,"source":d.source} for c,d in db.execute(stmt)]
    qs=set(words(query))
    rows=chunks_for(db,public_ids(db))
    scores=[(len(qs.intersection(words(r["title"]+" "+r["text"]))),r) for r in rows]
    return [r for score,r in sorted(scores,key=lambda pair:pair[0],reverse=True)[:limit] if score>0]
