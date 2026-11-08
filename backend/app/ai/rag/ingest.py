from app.modules.knowledge import service

def ingest(db,actor,path,title=None):
    return service.publish(db,actor,title or path.stem,service.read_document(path),str(path))
