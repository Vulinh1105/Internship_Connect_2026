import re
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.common import storage
from app.common.records import first, require
from app.core.deps import Actor, DB, allow
from app.core.rate_limit import enforce
from app.core.security import hash_password, verify_password
from app.modules.auth.models import User
from app.modules.notifications.models import Notification
from .models import Company, CompanyRegistration, Member
from .service import LOGO_MAX, LOGO_TYPES, discard, logo_kind

router = APIRouter(prefix="/api/company-registrations", tags=["company registrations"])
DOC_MAX = 5 * 1024 * 1024
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
DOCUMENTS = {"certificate": "Giấy chứng nhận", "authorization": "Giấy ủy quyền",
             "identity": "Giấy tờ đại diện", "logo": "Logo"}


class RegistrationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=180)
    tax_code: str = Field(min_length=1, max_length=14)
    registration_number: str = Field(min_length=1, max_length=80)
    industry: str = Field(min_length=1, max_length=100)
    company_size: str = Field(min_length=1, max_length=40)
    address: str = Field(min_length=1, max_length=350)
    city: str = Field(min_length=1, max_length=100)
    website: str = Field(default="", max_length=250)
    company_email: str = Field(min_length=1, max_length=255)
    company_phone: str = Field(min_length=1, max_length=25)
    contact_name: str = Field(min_length=1, max_length=150)
    position: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=255, pattern=EMAIL)
    phone: str = Field(min_length=1, max_length=25)
    password: Annotated[str, StringConstraints(min_length=10, max_length=128, strip_whitespace=False)]
    representative: bool
    authorized: bool


class Decision(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    status: Literal["approved", "needs_changes", "rejected"]
    reason: str = Field(default="", max_length=2000)


def save_file(file, kind):
    max_bytes = LOGO_MAX if kind == "logo" else DOC_MAX
    content = file.file.read(max_bytes + 1)
    suffix = logo_kind(content)
    if kind != "logo" and content.startswith(b"%PDF-"):
        suffix = ".pdf"
    if suffix is None:
        raise HTTPException(415, f"{DOCUMENTS[kind]} có định dạng không hợp lệ")
    return storage.save(content, kind + suffix, folder="company-registrations",
                        allowed={*LOGO_TYPES, ".pdf"}, max_bytes=max_bytes)


@router.post("", status_code=201)
def submit(db: DB, request: Request, payload: Annotated[str, Form()],
           certificate: Annotated[UploadFile, File()],
           logo: Annotated[UploadFile | None, File()] = None,
           authorization: Annotated[UploadFile | None, File()] = None,
           identity: Annotated[UploadFile | None, File()] = None):
    enforce(("company-registration", request.client.host if request.client else "local"), 8, 3600)
    if len(payload) > 8000:
        raise HTTPException(422, "Thông tin đăng ký vượt giới hạn độ dài.")
    try:
        data = RegistrationInput.model_validate_json(payload)
    except ValidationError:
        raise HTTPException(422, "Hồ sơ chưa được gửi. Hãy điền các mục có dấu * và kiểm tra thông tin đăng nhập.")
    if not data.representative and not data.authorized:
        raise HTTPException(422, "Hãy xác nhận bạn có quyền tuyển dụng thay mặt doanh nghiệp.")
    if not data.representative and authorization is None:
        raise HTTPException(422, "Hãy tải giấy ủy quyền của doanh nghiệp.")
    email = data.email.lower()
    tax_code = re.sub(r"^([0-9]{10})-([0-9]{3})$", r"\1\2", data.tax_code)
    if len(tax_code) > 13:
        raise HTTPException(422, "Hồ sơ chưa được gửi. Vui lòng kiểm tra độ dài thông tin.")
    user = first(db, User, email=email)
    old = db.get(CompanyRegistration, user.id) if user else None
    if user and (not old or old.status != "needs_changes" or not verify_password(data.password, user.password)):
        raise HTTPException(409, "Email đã được sử dụng hoặc hồ sơ chưa được yêu cầu bổ sung.")
    claimed = first(db, CompanyRegistration, tax_code=tax_code)
    if claimed and (not old or claimed.user_id != old.user_id):
        raise HTTPException(409, "Mã số thuế đã có hồ sơ trong hệ thống.")

    info = data.model_dump(exclude={"password", "email", "tax_code"})
    files = {}
    previous_files = dict(old.files) if old else {}
    try:
        for kind, file in (("certificate", certificate), ("authorization", authorization),
                           ("identity", identity), ("logo", logo)):
            if file is not None:
                files[kind] = save_file(file, kind)
        if old:
            changed = db.execute(update(CompanyRegistration).where(
                CompanyRegistration.user_id == old.user_id, CompanyRegistration.status == "needs_changes"
            ).values(tax_code=tax_code, info=info, files=files, status="pending", reason=""))
            if not changed.rowcount:
                raise HTTPException(409, "Trạng thái hồ sơ đã thay đổi. Hãy tải lại.")
        else:
            user = User(email=email, password=hash_password(data.password), role="company_member", active=False)
            db.add(user)
            db.flush()
            db.add(CompanyRegistration(user_id=user.id, tax_code=tax_code, info=info, files=files, status="pending"))
        admins = db.scalars(select(User.id).where(User.role == "admin", User.active.is_(True), User.locked_at.is_(None)))
        message = f"Hồ sơ doanh nghiệp cần xác minh: {data.name}"
        db.add_all(Notification(user_id=admin_id, kind="company_registration", message=message, target_id=user.id)
                   for admin_id in admins)
        db.commit()
    except Exception as error:
        db.rollback()
        for key in files.values():
            discard(key)
        if isinstance(error, IntegrityError):
            raise HTTPException(409, "Email hoặc mã số thuế đã có hồ sơ trong hệ thống.") from error
        raise
    for key in previous_files.values():
        discard(key)
    return {"status": "pending"}


@router.get("")
def queue(db: DB, actor: Actor):
    allow(actor, "admin")
    statement = (select(CompanyRegistration, User.email).join(User)
                 .where(CompanyRegistration.status == "pending").order_by(CompanyRegistration.user_id.desc()))
    return [{"id": item.user_id, "tax_code": item.tax_code, "info": item.info,
             "email": email, "documents": list(item.files)} for item, email in db.execute(statement)]


@router.get("/{ident}/documents/{kind}")
def download(ident: int, kind: str, db: DB, actor: Actor):
    allow(actor, "admin")
    item = require(db.get(CompanyRegistration, ident))
    path = storage.resolve(require(item.files.get(kind), "Không tìm thấy giấy tờ"))
    return FileResponse(path, filename=kind + path.suffix,
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.patch("/{ident}")
def review(ident: int, decision: Decision, db: DB, actor: Actor):
    allow(actor, "admin")
    if decision.status != "approved" and not decision.reason:
        raise HTTPException(422, "Hãy nhập lý do xử lý hồ sơ.")
    item = require(db.get(CompanyRegistration, ident))
    changed = db.execute(update(CompanyRegistration).where(
        CompanyRegistration.user_id == ident, CompanyRegistration.status == "pending"
    ).values(status=decision.status, reason=decision.reason))
    if not changed.rowcount:
        raise HTTPException(409, "Hồ sơ đã được xử lý.")
    if decision.status == "approved":
        info = item.info
        details = {name: info[name] for name in ("address", "website", "company_size")}
        details["verification_status"] = "verified"
        if item.files.get("logo"):
            details["logo"] = item.files["logo"]
        company = Company(name=info["name"], industry=info["industry"], city=info["city"],
                          description="", details=details)
        db.add(company)
        db.flush()
        db.add(Member(company_id=company.id, user_id=ident, active=True, manager=True))
        db.get(User, ident).active = True
    db.commit()
    return {"status": decision.status}
