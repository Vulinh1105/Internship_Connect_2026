# Internship Connect — Dữ liệu demo v2

Toàn bộ bản ghi là mô phỏng. Mốc tham chiếu của các ca kiểm thử là **07/11/2026**, múi giờ Asia/Bangkok.

| Thư mục | Nội dung |
|---|---|
| core/ | 20 công ty, 40 sinh viên, 100 tin gốc + 6 tin kiểm thử, danh mục và liên kết kỹ năng |
| access/ | 62 tài khoản chờ kích hoạt, 5 vai trò, ma trận quyền, 20 quan hệ thành viên |
| demo/ | 100 đơn, lịch sử trạng thái và 20 lịch phỏng vấn tuyển dụng giả lập |
| ai/matching/ | 40 hồ sơ gợi ý, 106 tin, 12 ca kỳ vọng xếp hạng và lọc |
| ai/chatbot/ | 8 tài liệu, metadata, bản xuất tin/công ty và 14 ca hỏi đáp |
| ai/virtual_interview/ | 30 câu cho 10 vị trí, 90 tiêu chí, 10 mẫu bài và 9 bài trả lời có điểm tham chiếu |

Đọc DATA_DICTIONARY.md để chốt schema. CHANGELOG.md ghi phần sửa và giả định. VALIDATION.json ghi số dòng và kiểm tra đã chạy.

Nạp theo thứ tự: roles/permissions/users → companies/students/skills → company_members/internships → student_skills/internship_skills → applications → events/interviews. Ánh xạ mã logic sang ID DB. Chỉ nạp demo/ khi muốn trình diễn lịch sử đã có sẵn. Email example.invalid là định danh giả lập. Nếu cần đăng nhập, kích hoạt tài khoản qua quy trình riêng của web.

Gói này là dữ liệu chuẩn bị cho hệ thống mới. Cần ánh xạ header và enum theo schema đã chốt. Script seed cũ không được kèm vì nó kỳ vọng job_type và tự gán approved/open. Không nạp đè vào DB đang chạy bằng script cũ.

Các gói AI riêng giúp đọc và thử từng tính năng. Dùng gói đầy đủ để có mọi bảng liên quan đến người dùng và đơn. Các ca kiểm thử là kết quả kỳ vọng theo quy tắc đề xuất, chưa phải kết quả chạy model.
