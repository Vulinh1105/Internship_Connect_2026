from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from app.core.deps import Actor, DB, OptionalActor
from . import service
from .schemas import CompanyInput
from .service import LOGO_MAX

router = APIRouter(prefix="/api/companies", tags=["companies"])

@router.get("")
def list_companies(db: DB):
    return service.list_public(db)

@router.get("/mine")
def mine(db: DB, actor: Actor):
    return service.mine(db, actor)

@router.get("/{ident}")
def detail(ident: int, db: DB, actor: OptionalActor):
    return service.profile(db, ident, actor)

@router.get("/{ident}/logo")
def logo(ident: int, db: DB):
    path, media_type = service.logo_file(db, ident)
    return FileResponse(path, media_type=media_type,
                        headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"})

@router.post("/{ident}/logo")
def upload_logo(ident: int, db: DB, actor: Actor, file: UploadFile = File()):
    return service.set_logo(db, actor, ident, file.file.read(LOGO_MAX + 1), file.filename or "")

@router.delete("/{ident}/logo")
def delete_logo(ident: int, db: DB, actor: Actor):
    return service.remove_logo(db, actor, ident)

@router.put("/{ident}")
def update(ident: int, data: CompanyInput, db: DB, actor: Actor):
    return service.save(db, actor, ident, data)

@router.put("/{ident}/follow")
def follow(ident: int, db: DB, actor: Actor, value: bool = True):
    return service.follow(db, actor, ident, value)
