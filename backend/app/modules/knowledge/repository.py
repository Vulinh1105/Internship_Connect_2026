from sqlalchemy import select
from .models import Document, Chunk

def get_document(db, ident):
    return db.get(Document, ident)

def get_chunk(db, ident):
    return db.get(Chunk, ident)
