from app.modules.knowledge import service
from app.common.file_parsing import parse

def ingest(db,actor,path,title=None):
    return service.publish(db,actor,title or path.stem,parse(path),str(path))
