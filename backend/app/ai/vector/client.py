from functools import lru_cache
from pathlib import Path
from threading import RLock
from uuid import uuid5,NAMESPACE_URL
from qdrant_client import QdrantClient,models
from app.core.config import QDRANT_URL,QDRANT_PATH
from .collections import collection, dimensions

lock=RLock()

@lru_cache
def client():
    if QDRANT_URL:
        return QdrantClient(url=QDRANT_URL,timeout=5,check_compatibility=False)
    Path(QDRANT_PATH).mkdir(parents=True,exist_ok=True)
    return QdrantClient(path=QDRANT_PATH,force_disable_check_same_thread=True)

def point_id(kind, ident, part=0):
    return str(uuid5(NAMESPACE_URL,f"career:{kind}:{ident}:{part}"))

def ensure(kind):
    name=collection(kind)
    c=client()
    if not c.collection_exists(name):
        c.create_collection(name, vectors_config=models.VectorParams(size=dimensions(kind),distance=models.Distance.COSINE))
    return name

def filters(**pairs):
    return models.Filter(must=[models.FieldCondition(key=k,match=models.MatchValue(value=v))
                               for k,v in pairs.items() if v is not None])

def upsert(kind, points):
    with lock:
        client().upsert(ensure(kind),points=[models.PointStruct(id=ident,vector=vector,payload=payload)
                                           for ident,vector,payload in points],wait=True)

def delete_entity(kind,ident):
    with lock:
        if client().collection_exists(collection(kind)):
            client().delete(collection(kind),points_selector=models.FilterSelector(filter=filters(entity_id=ident)),wait=True)

def delete_points(kind,ids):
    if ids:
        with lock:
            client().delete(ensure(kind),points_selector=models.PointIdsList(points=ids),wait=True)

def entries(kind, condition=None):
    with lock:
        if not client().collection_exists(collection(kind)):
            return []
        page=None
        result=[]
        while True:
            data,page=client().scroll(collection(kind),scroll_filter=condition,offset=page,
                                     limit=100,with_payload=True,with_vectors=False)
            result.extend(data)
            if page is None:
                return result

def search(kind,vector,condition=None,limit=20):
    with lock:
        if not client().collection_exists(collection(kind)):
            return []
        return client().query_points(collection(kind),query=vector,query_filter=condition,limit=limit,with_payload=True).points

def get_vector(kind,ident):
    with lock:
        if not client().collection_exists(collection(kind)):
            return None
        items=client().retrieve(collection(kind),ids=[point_id(kind,ident)],with_vectors=True)
        return items[0].vector if items else None

def close():
    with lock:
        if client.cache_info().currsize:
            client().close()
            client.cache_clear()

def job_filters(location="",job_ids=None):
    condition=filters(status="active",location=location or None)
    if job_ids:
        condition.must.append(models.FieldCondition(key="entity_id",match=models.MatchAny(any=job_ids)))
    return condition
