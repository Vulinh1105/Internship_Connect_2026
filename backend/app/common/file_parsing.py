import re
from fastapi import HTTPException

def parse(path):
    try:
        match path.suffix.lower():
            case ".pdf":
                import pymupdf
                with pymupdf.open(path) as pdf:
                    if len(pdf) > 100:
                        raise HTTPException(422, "Chỉ hỗ trợ tài liệu tối đa 100 trang")
                    text = "\n".join(page.get_text() for page in pdf)
            case ".docx":
                from docx import Document
                doc = Document(path)
                text = "\n".join([p.text for p in doc.paragraphs] +
                                 [" | ".join(c.text for c in r.cells) for t in doc.tables for r in t.rows])
            case _:
                text = path.read_text(encoding="utf-8-sig")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "Không đọc được tệp. Kiểm tra định dạng và mật khẩu.") from exc
    text = text.strip()
    if not text:
        raise HTTPException(422, "Không có văn bản đọc được. Với PDF ảnh, hãy nhập hồ sơ bằng tay.")
    return text[:160000]

def redact(text, name=""):
    if name:
        text = re.sub(re.escape(name), "[đã ẩn]", text, flags=re.I)
    text = re.sub(r"(?im)^\s*(?:họ và tên|họ tên|tên|name|địa chỉ|address|trường|university|ngày sinh|date of birth|tuổi|age|giới tính|gender)\s*[:：].*$", "[đã ẩn]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.\w+", "[email]", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d .()-]{7,}\d)(?!\w)", "[số liên lạc]", text)
    return text
