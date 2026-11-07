# Quan hệ dữ liệu

```mermaid
erDiagram
    ROLES ||--o{ USERS : assigns
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : defines
    USERS ||--o| STUDENTS : owns
    USERS ||--o{ COMPANY_MEMBERS : joins
    COMPANIES ||--o{ COMPANY_MEMBERS : has
    COMPANIES ||--o{ JOBS : posts
    JOBS ||--o{ JOB_REVIEWS : receives
    STUDENTS ||--o{ CVS : uploads
    STUDENTS ||--o{ APPLICATIONS : submits
    JOBS ||--o{ APPLICATIONS : receives
    APPLICATIONS ||--o{ APPLICATION_EVENTS : records
    APPLICATIONS ||--o{ INTERVIEWS : schedules
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ CHAT_SESSIONS : owns
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains
    CHAT_MESSAGES ||--o| CHAT_FEEDBACK : receives
    DOCUMENTS ||--o{ KNOWLEDGE_CHUNKS : divides
    USERS ||--o{ INTERVIEW_SESSIONS : practices
    INTERVIEW_SESSIONS ||--o{ INTERVIEW_ANSWERS : contains
    INTERVIEW_SESSIONS ||--o| INTERVIEW_REPORTS : generates
```

`vector_sync_queue` giữ tác vụ của jobs, cvs và knowledge. `ai_usage_logs` giữ mô hình, token, độ trễ và chi phí ước tính khi có cấu hình giá. `question_bank` giữ câu hỏi và rubric nguồn. Kỹ năng chuẩn nằm trong `skills`. Quyền sở hữu lấy từ quan hệ người dùng, hồ sơ sinh viên và thành viên doanh nghiệp.
