# Text cleaning from chatbot_AI/backend/app/doc_processing/parsing.py.
import unicodedata


def _clean_text(text: str) -> str:
    """Chuẩn hoá text thô trước khi đưa sang chunking.py:
    - Chuẩn hoá Unicode NFC (tránh ký tự tiếng Việt tổ hợp bị tách thành
      nhiều code point, làm sai độ dài chunk ở bước sau).
    - Đưa CRLF/CR về LF, gộp nhiều dòng trống liên tiếp thành tối đa 1 dòng.
    - Trim khoảng trắng đầu/cuối.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.rstrip() for line in text.split("\n")]
    cleaned_lines: list[str] = []
    blank_streak = 0
    for line in lines:
        if line == "":
            blank_streak += 1
            if blank_streak > 1:
                continue
        else:
            blank_streak = 0
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()
