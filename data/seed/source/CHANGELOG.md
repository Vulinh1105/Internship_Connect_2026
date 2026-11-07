# Thay đổi từ gói gốc
- Giữ 20 công ty, 40 sinh viên và 100 tin gốc cùng mã. Thêm 6 ca trạng thái: nháp, chờ duyệt, bị từ chối, đóng, hết hạn, không hạn.
- Bỏ 24 dòng kỹ năng lặp; còn 96 cặp. Thêm danh mục kỹ năng và yêu cầu theo tin.
- Tách program_type, employment_schedule và work_mode. Giả định demo Part-time thuộc chương trình internship. Đổi 20 khoảng phụ cấp 0–0 sang negotiable, đồng bộ nội dung phụ cấp với khoảng tiền.
- Giữ 100 quan hệ ứng tuyển và 20 lịch. Sinh mốc thời gian, thư mẫu và lịch sử. Chuyển 5 đơn pending có lời mời sang reviewing. Chuyển 5 lịch của đơn rejected thành cancelled có lý do.
- Bổ sung vai trò, quyền và tài khoản mẫu. Chưa có mật khẩu, CV hoặc token.
- Thay snapshot qdrant_knowledge bằng văn bản công khai có hạn/phụ cấp và thêm tài liệu quy trình. Vector cần được tạo khi triển khai.
- Tạo mới câu hỏi theo 10 vị trí và rubric theo câu. Điểm mẫu dùng kiểm thử, chưa qua người chấm độc lập.
- Tin gốc vẫn có hạn đồng loạt và nhiều mô tả dùng chung mẫu. Bộ này kiểm thử logic và dựng demo, chưa đại diện cho hiệu quả AI trên dữ liệu thật.
