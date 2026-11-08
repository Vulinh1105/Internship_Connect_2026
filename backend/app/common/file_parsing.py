import re
from fastapi import HTTPException

def pdf_text(pdf,ocr_tessdata):
    pages=[]
    for page in pdf:
        text=page.get_text()
        if ocr_tessdata is not None and len(text.strip())<32 and page.get_image_info():
            if not (ocr_tessdata/"vie.traineddata").is_file():
                raise HTTPException(422,"PDF scan cần bộ OCR tiếng Việt. Hãy cài vie.traineddata hoặc tải bản PDF có lớp văn bản.")
            recognized=page.get_textpage_ocr(language="vie",dpi=180,full=True,tessdata=str(ocr_tessdata))
            text=page.get_text(textpage=recognized)
        pages.append(text)
    return "\n".join(pages)


def parse(path, *, max_pdf_pages=100, max_chars=160_000, allow_empty_pdf=False, ocr_tessdata=None):
    suffix = path.suffix.lower()
    try:
        match suffix:
            case ".pdf":
                import pymupdf
                # CV uploads are bounded and can be opened without locking the stored file.
                document = pymupdf.open(stream=path.read_bytes(), filetype="pdf") if allow_empty_pdf else pymupdf.open(path)
                with document as pdf:
                    if len(pdf) == 0 or pdf.needs_pass:
                        raise HTTPException(422, "PDF phải có ít nhất một trang và mở được không cần mật khẩu.")
                    if len(pdf) > max_pdf_pages:
                        raise HTTPException(422, f"Chỉ hỗ trợ tài liệu tối đa {max_pdf_pages} trang")
                    text = pdf_text(pdf,ocr_tessdata)
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
    if not text and not (allow_empty_pdf and suffix == ".pdf"):
        raise HTTPException(422, "Không có văn bản đọc được. Với PDF ảnh, hãy nhập hồ sơ bằng tay.")
    return text[:max_chars]

def redact(text, name=""):
    if name:
        text = re.sub(re.escape(name), "[đã ẩn]", text, flags=re.I)
    text = re.sub(r"(?im)^\s*(?:họ và tên|họ tên|tên|name|địa chỉ|address|trường|university|ngày sinh|date of birth|tuổi|age|giới tính|gender)\s*[:：].*$", "[đã ẩn]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.\w+", "[email]", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d .()-]{7,}\d)(?!\w)", "[số liên lạc]", text)
    return text
