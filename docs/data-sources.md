# Nguồn dữ liệu

Nguồn được sao chép từ bộ đầy đủ `InternshipConnect_Data_v2` do người dùng cung cấp. Dữ liệu gốc của dự án mới nằm trong `data/seed/source`. Tài liệu Markdown RAG dùng để nhập nằm tại `data/knowledge`. Ba bộ dữ liệu tách riêng là các phần trích từ bộ đầy đủ.

| Nguồn | Sử dụng |
| --- | --- |
| access | Vai trò, quyền, tài khoản mẫu, thành viên doanh nghiệp |
| core | 20 doanh nghiệp, 40 hồ sơ sinh viên, 106 tin, kỹ năng |
| demo | 100 đơn, lịch sử đơn và lịch phỏng vấn mẫu |
| ai/chatbot | 8 tài liệu Markdown và danh mục để seed RAG, bộ câu hỏi đánh giá đi kèm |
| ai/matching | Dữ liệu tham chiếu và ca kiểm thử. Gợi ý chạy trên tin và hồ sơ SQL hiện hành |
| ai/virtual_interview | 30 câu hỏi và rubric theo vai trò, mẫu cấu hình và ca đánh giá |

Một phần tin đã đóng, hết hạn hoặc chưa duyệt dùng để kiểm tra điều kiện hiển thị. Hạn tin phụ thuộc ngày chạy. Seed bật bốn tài khoản thử. Tài khoản mẫu còn lại chờ admin đặt mật khẩu. Seed lặp giữ bản ghi đã có. Bản ghi mẫu dùng email `example.invalid`, dữ liệu không mô tả cá nhân hoặc doanh nghiệp thật.

Ứng dụng sinh cơ sở dữ liệu local (hoặc volume Docker), chỉ mục Qdrant, tệp CV người dùng tải lên, lịch sử hội thoại và phiên luyện khi chạy. File CSV và Markdown là nguồn đầu vào. Dữ liệu đánh giá có sẵn phục vụ kiểm thử ban đầu, chưa thay thế tập nhãn do người đánh giá độc lập.
