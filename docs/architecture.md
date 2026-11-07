# Kiến trúc

```text
Trình duyệt /app/
  -> API cùng origin /api/
  -> router xác thực và kiểm tra kiểu dữ liệu
  -> service thực hiện quy tắc nghiệp vụ và kiểm tra quyền
  -> repository / SQLAlchemy
  -> MySQL hoặc SQLite

Service thay đổi tin, CV, tài liệu -> outbox SQL -> worker -> embedding -> Qdrant
Chatbot -> phân loại -> service nghiệp vụ hoặc RAG -> kiểm tra nguồn -> SSE
Phỏng vấn ảo -> lập đề -> từng lượt -> chấm theo rubric -> báo cáo
```

- `backend/app/main.py` ghép các router, chạy worker định kỳ và phục vụ frontend.
- `backend/app/core` tập trung cấu hình, kết nối SQL, JWT, xác thực và hạn mức HTTP.
- `backend/app/modules` chứa nghiệp vụ. JWT xác định tài khoản, service xác nhận vai trò và quyền sở hữu đối với dữ liệu riêng.
- `backend/app/ai` chứa cổng provider, nhật ký mức sử dụng, matching, RAG, chatbot và chấm phỏng vấn.
- `backend/alembic` tạo schema và chỉ mục FULLTEXT của MySQL. `backend/scripts` nạp dữ liệu và đối soát.
- `frontend/src/pages` nhóm màn hình. `api/client.js` xử lý HTTP và SSE, `components/ui.js` chứa thành phần dùng chung.

## Đường đi của dữ liệu

1. Tin mới được ghi trạng thái chờ duyệt. Tin công khai phải đang mở, đã duyệt, chưa bị xóa và còn hạn. Cùng giao dịch cập nhật tin, service ghi một tác vụ vector. Worker đọc trạng thái hiện hành và đồng bộ hoặc xóa vector. API kiểm tra lại SQL khi trả kết quả Qdrant.
2. CV nằm trong thư mục upload. Backend đọc chữ và lọc thông tin liên hệ trước khi phân tích. Sinh viên chỉnh và xác nhận dữ liệu trước khi backend ghi chỉ mục CV. Matching trả điểm, kỹ năng khớp và kỹ năng cần bổ sung.
3. Khi ứng tuyển, hệ thống lưu điểm và lịch sử trạng thái. Doanh nghiệp chỉ xem đơn của tin thuộc doanh nghiệp mình. Lời mời được lưu vào bảng lịch và tạo thông báo cho sinh viên.
4. Chatbot xác định ý định rồi gọi tool đọc dữ liệu hoặc truy xuất tài liệu. Tên tin, công ty, lương lấy từ SQL. Câu trả lời RAG hiển thị đoạn trích đã đối chiếu và nguồn.
5. Phiên luyện phỏng vấn lưu câu hiện tại, lượt hỏi phụ, câu trả lời xác nhận và báo cáo. Có thể mở lại để tiếp tục. Âm thanh gửi lên để STT chỉ được xử lý trong yêu cầu đó.

## Phạm vi bản local

SSE phát kết quả đã xác thực theo từng đoạn sau bước sinh nội dung. Hạn mức AI hiện dùng tổng số lời gọi mỗi người mỗi ngày, kèm hạn mức phiên luyện riêng. Chế độ local sử dụng gợi ý và điểm luyện tập theo quy tắc. Báo cáo hiện được tổng hợp từ điểm từng lượt. Hiệu chỉnh chất lượng theo nhãn người chấm, cache nhận xét LLM/FAQ và các bước chấm theo model nâng cao cần thêm dữ liệu và kiểm chứng.
