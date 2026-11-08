# Internship Connect 2026

Ứng dụng thực tập chạy trên máy cá nhân. FastAPI phục vụ API và giao diện HTML/JavaScript trên cùng địa chỉ. Dữ liệu mẫu lấy từ bộ InternshipConnect_Data_v2.

## Chạy nhanh trên Windows

Cài Python 3.11 trở lên. Mở Terminal PowerShell tại thư mục dự án rồi chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Mở [giao diện local](http://127.0.0.1:8010/app/) hoặc [tài liệu API](http://127.0.0.1:8010/docs). Lệnh tạo môi trường Python, chạy migration, seed và lập chỉ mục rồi khởi động máy chủ. Chế độ mặc định dùng SQLite và Qdrant lưu trên đĩa, trong `data/runtime/`. Lần chạy sau có thể thêm `-NoInstall` để bỏ qua cài gói. Dừng web bằng Ctrl+C.

## Chạy với MySQL và Qdrant

Mở Docker Desktop, chờ Docker Engine sẵn sàng, rồi chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1 -Database mysql
```

Compose tạo MySQL trên cổng 3307 và Qdrant trên cổng 6335. Alembic tạo bảng, script seed nhập dữ liệu mẫu. MySQL giữ dữ liệu nghiệp vụ. Qdrant giữ chỉ mục vector. Nếu chọn hai chế độ vào hai lần khác nhau, mỗi chế độ có dữ liệu nghiệp vụ riêng. Để dùng MySQL có sẵn, tạo database trống và cấu hình `DATABASE_URL` trong `.env`, dùng tùy chọn chạy mặc định với dịch vụ MySQL đã bật.

## Pipeline chatbot chuyển từ chatbot_AI

Mã graph, reranker và kiểm tra nguồn gốc nằm trong `backend/app/ai/rag/legacy/`.
Tiến trình `legacy_worker.py` chạy graph. `legacy_runtime.py` lấy các đoạn
tài liệu công khai từ MySQL và collection Tri thức của Internship Connect.

Để cài môi trường riêng trên Windows, chạy từ thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -m venv .\data\runtime\rag-venv
.\data\runtime\rag-venv\Scripts\python.exe -m pip install -r .\backend\requirements-rag.txt
```

Cần có model `BAAI/bge-reranker-v2-m3` trong cache Hugging Face. Sau khi
chuẩn bị model, đặt `RAG_LEGACY_PYTHON=data/runtime/rag-venv/Scripts/python.exe`
trong `.env`. Mặc định, bước chọn bằng chứng và sinh câu trả lời của graph
chạy local.

## OCR cho tài liệu chatbot

Để đọc PDF scan tiếng Việt, đặt [vie.traineddata](https://github.com/tesseract-ocr/tessdata_fast/blob/main/vie.traineddata) vào `data/runtime/tessdata/`. Mục Tri thức sẽ dùng OCR cho những trang scan gần như không có lớp văn bản. Với PDF đã tải lên trước đó, dùng nút **Đọc lại PDF** để cập nhật chỉ mục.

## Tài khoản thử

Dùng mật khẩu mặc định `LocalDemo2026!` cho bốn tài khoản mẫu. Có thể đặt `DEMO_PASSWORD` trong `.env` trước lần seed đầu.

| Vai trò | Email |
| --- | --- |
| Sinh viên | usr-demo-s001@example.invalid |
| Doanh nghiệp | usr-demo-c001@example.invalid |
| Kiểm duyệt | staff-demo@example.invalid |
| Quản trị | admin-demo@example.invalid |

Doanh nghiệp đăng tin → kiểm duyệt duyệt → sinh viên ứng tuyển → doanh nghiệp gửi lịch → sinh viên phản hồi qua mục Đơn ứng tuyển. Thông báo nằm trên web. Mục Phỏng vấn ảo là buổi luyện tập của riêng sinh viên.

## Bật OpenAI

Sao chép `.env.example` thành `.env`, đặt `AI_BACKEND=openai` và điền `OPENAI_API_KEY`. Mặc định cấu hình `gpt-4o-mini` cho tác vụ văn bản, `text-embedding-3-small` cho embedding. Khởi động lại để lập chỉ mục cho backend embedding mới. Các yêu cầu OpenAI được gửi từ backend. Chế độ `local` dùng embedding từ khóa và các quy tắc. Trình duyệt có thể cung cấp nhận diện giọng nói tùy hỗ trợ, hoặc dùng nhập chữ.

## Kiểm thử

```powershell
$env:PYTHONPATH = "$PWD/backend"
.\.venv\Scripts\python.exe -m pytest -q backend/tests
```

Xem `docs/architecture.md`, `docs/erd.md` và `docs/data-sources.md` để tra cấu trúc, luồng và nguồn dữ liệu.
