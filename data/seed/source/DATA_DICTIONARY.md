# Từ điển dữ liệu

CSV UTF-8 BOM có header. Nội dung có thể xuống dòng trong một ô. Ô tùy chọn trống là NULL. Boolean True/False. Ngày YYYY-MM-DD. Thời điểm nghiệp vụ ISO 8601 có +07:00.

## Core
- companies: seed_code duy nhất. Hồ sơ doanh nghiệp, ngành, địa điểm, quy mô, năm thành lập. Website/logo tùy chọn. verification_status unverified/verified.
- students: seed_code, student_code duy nhất, user_code nối users. GPA giữ giá trị nguồn, gpa_scale chưa xác nhận. Tạm không dùng GPA để loại hồ sơ.
- skills: skill_id, skill_name duy nhất. student_skills khóa ghép student_seed_code + skill_id. internship_skills khóa ghép job_seed_code + skill_id. priority dùng preferred vì nguồn chưa xác định kỹ năng bắt buộc.
- internships: seed_code, company_seed_code, nội dung, địa điểm, số lượng, working_hours, deadline tùy chọn. program_type internship/trainee; employment_schedule part_time theo giả định demo; work_mode onsite/hybrid/remote. pay_type range/negotiable; min/max là số nguyên VND/tháng hoặc NULL cho negotiable.
- Tin công khai khi status=open, moderation_status=approved, deadline trống hoặc không trước ngày tra cứu. Duyệt tin và xác minh công ty độc lập trong bộ demo. fixture_case phân biệt tin gốc và tin kiểm thử.

## Access
- roles và permissions dùng role_code và permission_code. role_permissions nối hai bảng. guest đại diện khách, không gán tài khoản.
- users có user_code/email duy nhất, một role_code, trạng thái requires_activation. company_members nối user_code và company_seed_code. Quan hệ thành viên và kích hoạt tài khoản là hai điều kiện riêng.
- Quyền own cần đúng chủ sở hữu. Quyền company cần thành viên hoạt động thuộc đúng công ty sở hữu tin. CV cần gắn với đơn của công ty đó. Admin quản lý tài khoản, quyền và nhật ký; không mặc định đọc CV hay kết quả luyện. Backend kiểm quyền trước khi đưa dữ liệu cho AI.
- File CV, password hash, token, nhật ký quản trị và thông báo sẽ phát sinh theo chức năng khi chạy. Gói không có những dữ liệu thật này.

## Demo
- applications có seed_code, student_seed_code và job_seed_code; duy nhất theo cặp sinh viên–tin. cv_file_id tùy chọn, để trống. submitted_at/decision_at tạo giả lập; status pending/reviewing/accepted/rejected.
- application_events nối theo application_seed_code, actor_user_code; occurred_at xác định thứ tự. Sự kiện cuối khớp trạng thái của đơn.
- interviews nối đơn theo application_seed_code, người mời theo invited_by. invited_at/scheduled_at/cancelled_at có múi giờ. Lịch invited chỉ thuộc đơn reviewing/accepted. Các đơn rejected có lịch lịch sử cancelled.

## AI
- Matching profiles và jobs dùng mã core. skill_ids tách bằng |. Nguyện vọng demo sinh từ tin đầu tiên từng hồ sơ ứng tuyển. evaluation_cases có higher_job/lower_job và must_exclude, theo reference_rule.md.
- Chatbot document_catalog nối doc_id với relative_path từ ai/chatbot. visibility, version, status và effective_from mô tả quyền và công bố. Tài liệu là chính sách demo đề xuất. derived_public_text là snapshot, dùng source_key nối bản ghi gốc. Tin/hạn/phụ cấp hiện tại và đơn cá nhân được tra qua API có phân quyền. Các ca hỏi dữ liệu cá nhân giả định tài khoản đã xác thực khi có user_code.
- Phỏng vấn ảo questions nối rubrics bằng question_id và rubric_version. Trọng số mỗi câu cộng 100. Tổng điểm = tổng(weight × điểm tiêu chí / 2). practice_templates chọn câu theo question_ids tách bằng |. evaluation_cases chứa bài mẫu để kiểm tra. Khi luyện thật, lưu phiên theo user_id, phiên bản câu/rubric, câu trả lời, điểm và phản hồi.
