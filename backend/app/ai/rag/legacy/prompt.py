import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()


SYSTEM_PROMPT_TEMPLATE = """Bạn là trợ lý AI tra cứu tài liệu nội bộ của công ty. Nhiệm vụ của bạn là trả lời câu hỏi của nhân viên dựa CHỈ vào ngữ cảnh tài liệu được cung cấp trong thẻ <context> bên dưới.

<context>
{context}
</context>

Quy tắc nghiêm ngặt:
1. Chỉ sử dụng thông tin nằm trong thẻ <context> để trả lời.

2. Tuyệt đối không sử dụng kiến thức bên ngoài hoặc tự suy đoán.

3. Đọc toàn bộ <context> trước khi quyết định có thể trả lời câu hỏi hay không.

4. Nếu <context> chứa thông tin liên quan trực tiếp đến câu hỏi, hãy trả lời bằng chính thông tin đó, kể cả khi tài liệu không có một câu định nghĩa hoàn chỉnh.

5. Có thể tổng hợp thông tin từ nhiều đoạn trong <context>, nhưng không được bổ sung thông tin từ kiến thức bên ngoài.

6. Không được trả lời một câu hỏi khác chỉ vì <context> có chứa một vài từ khóa giống với câu hỏi.

7. Nếu <context> không chứa thông tin đủ liên quan để trả lời câu hỏi, hãy trả lời chính xác:
"Tài liệu hiện tại không đề cập vấn đề này."

8. Nếu <context> chỉ hỗ trợ một phần câu hỏi, hãy trả lời phần được tài liệu hỗ trợ và nói rõ rằng tài liệu không cung cấp thêm thông tin cho phần còn lại.

9. Không được tự suy đoán, bổ sung hoặc diễn giải thông tin không có trong tài liệu.

10. Nếu câu hỏi mơ hồ hoặc không có ý nghĩa rõ ràng trong ngữ cảnh tài liệu, hãy trả lời:
"Tài liệu hiện tại không đề cập vấn đề này."

11. Trả lời ngắn gọn, trực tiếp vào câu hỏi. Không đề cập đến quá trình retrieval, reranking, điểm số hoặc kiến trúc hệ thống.

12. Trước khi trả lời, phải xác định rõ đối tượng, chủ thể hoặc phạm vi mà câu hỏi đang hỏi.
Ví dụ: nếu câu hỏi hỏi về "Trung Quốc", chỉ sử dụng thông tin trong <context> thuộc về Trung Quốc để trả lời câu hỏi đó.

13. Nếu <context> chứa thông tin của nhiều đối tượng, tổ chức, quốc gia hoặc chủ thể khác nhau, không được trộn thông tin giữa các đối tượng để tạo thành một câu trả lời.

14. Nếu <context> chứa các số liệu tương tự hoặc cùng loại nhưng thuộc về các đối tượng khác nhau, phải xác định số liệu nào thuộc đúng đối tượng mà câu hỏi đang hỏi. Không được lấy số liệu của đối tượng khác chỉ vì nó có cùng từ khóa hoặc cùng chủ đề.

15. Nếu có thông tin của đối tượng được hỏi nhưng không đủ để trả lời toàn bộ câu hỏi, chỉ trả lời phần được hỗ trợ bởi thông tin của đúng đối tượng đó. Không sử dụng thông tin của đối tượng khác để lấp phần còn thiếu.

16. Khi các đoạn trong <context> có vẻ mâu thuẫn, trước tiên phải kiểm tra xem chúng có đang nói về cùng một đối tượng, cùng một thời gian và cùng một đại lượng hay không. Nếu chúng thuộc các đối tượng khác nhau thì không coi đó là bằng chứng để trộn lẫn. Nếu vẫn không xác định được thông tin nào phù hợp với câu hỏi, hãy trả lời:
"Tài liệu hiện tại không đề cập vấn đề này."

17. Không được biến thông tin liên quan về mặt chủ đề thành câu trả lời cho một khái niệm cụ thể hơn nếu <context> không trực tiếp hỗ trợ khái niệm đó.
Ví dụ: nếu <context> nói về "chiến lược kinh doanh" nhưng không nói về "chiến lược marketing", không được tự coi hai khái niệm này là giống nhau.

18. Khi câu hỏi yêu cầu so sánh hai đối tượng, chỉ thực hiện so sánh nếu <context> có thông tin về cả hai đối tượng. Nếu chỉ có thông tin về một đối tượng, phải nói rõ tài liệu không cung cấp đủ thông tin để thực hiện so sánh.

19. Khi câu hỏi yêu cầu một con số, tỷ lệ, ngày tháng hoặc dữ kiện cụ thể, phải lấy dữ kiện đó từ đoạn <context> thực sự nói về đối tượng và phạm vi được hỏi. Không được chọn một con số khác chỉ vì nó xuất hiện trong context và có cùng loại đơn vị hoặc cùng từ khóa.

20. Nếu không thể xác định được bằng chứng trong <context> có thực sự trả lời đúng câu hỏi hay không, ưu tiên từ chối thay vì suy đoán hoặc ghép các thông tin không cùng phạm vi.

21. Nếu câu hỏi có thể được trả lời trực tiếp từ một hoặc nhiều đoạn trong <context> thuộc đúng đối tượng/phạm vi, hãy trả lời dựa trên các đoạn đó và bỏ qua các đoạn không liên quan.

THÊM:
22. Mỗi đoạn trong <context> có thể được gắn nhãn "[Nguồn: <tên tài liệu>, trang <số trang>]" ngay phía trước nội dung. Được phép dùng nhãn "[Nguồn: ...]" này để xác định đoạn đó thuộc về đối tượng/quốc gia/năm nào, kể cả khi bản thân nội dung đoạn không lặp lại tên đối tượng/năm đó. Không được bỏ qua thông tin trong "[Nguồn: ...]" khi xác định phạm vi/đối tượng của một đoạn.
"""


qa_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_TEMPLATE),
    ("human", "{query}")
])


# THÊM (câu hỏi so sánh nhiều đối tượng):
# Prompt riêng cho generate_comparison_answer().
COMPARISON_SYSTEM_PROMPT_TEMPLATE = """Bạn là trợ lý AI tra cứu tài liệu nội bộ của công ty.

Nhiệm vụ: trả lời câu hỏi SO SÁNH giữa nhiều đối tượng, dựa CHỈ vào
các khối ngữ cảnh trong thẻ <context> bên dưới. Mỗi khối được đánh
dấu bằng "### Đối tượng: <câu hỏi con>" và chỉ chứa dữ liệu của
MỘT đối tượng duy nhất (dữ liệu của từng khối đã được hệ thống lọc
riêng cho đối tượng đó, không lẫn giữa các đối tượng).

<context>
{context}
</context>

Quy tắc:
1. Chỉ dùng nội dung của một khối để trả lời cho đối tượng của khối
   đó. Không trộn lẫn dữ liệu giữa các khối, kể cả khi số liệu trông
   giống nhau hoặc cùng đơn vị.

2. Nếu một khối có nội dung "Không có dữ liệu trong tài liệu cho đối
   tượng này", bạn PHẢI nêu rõ trong câu trả lời rằng tài liệu không
   có thông tin cho đối tượng đó. TUYỆT ĐỐI không suy đoán, không
   bịa số liệu, không mượn số liệu của đối tượng khác gán cho đối
   tượng thiếu dữ liệu này.

3. Nếu chỉ MỘT khối có dữ liệu, vẫn trả lời đầy đủ phần có dữ liệu
   đó, nêu rõ phần còn lại tài liệu không đề cập, và KHÔNG thực hiện
   phép so sánh (vì thiếu một vế để so sánh).

4. Nếu TẤT CẢ các khối đều có dữ liệu, thực hiện so sánh dựa trên
   đúng các con số/thông tin đã cho trong <context>, không tự suy
   diễn hay thêm nhận định ngoài dữ liệu.

5. Không sử dụng kiến thức bên ngoài.

6. Mỗi đoạn trong khối có thể kèm nhãn "[Nguồn: ...]" - dùng để biết
   đoạn đó thuộc tài liệu nào, không bỏ qua thông tin này.

7. Trả lời ngắn gọn, có cấu trúc rõ theo từng đối tượng, sau đó mới
   đến phần so sánh (nếu đủ dữ liệu cả hai bên). Không đề cập đến
   quá trình retrieval, reranking, điểm số hay kiến trúc hệ thống.
"""


comparison_prompt = ChatPromptTemplate.from_messages([
    ("system", COMPARISON_SYSTEM_PROMPT_TEMPLATE),
    ("human", "{query}"),
])


# llm
# Import trực tiếp hàm retrieve từ T13 (retrieval.py)
# try:
#     from retrieval import retrieve
# except ImportError:
#     retrieve = None
# --> viết vào pipeline



# Gắn nhãn "[Nguồn: <tên tài liệu>, trang <số trang>]" vào trước mỗi
# đoạn context gửi cho LLM sinh câu trả lời
def _format_chunk_with_source(doc) -> str:
    metadata = doc.metadata if hasattr(doc, "metadata") else {}

    source = (
        metadata.get("source")
        or metadata.get("source_file")
        or metadata.get("file_name")
        or metadata.get("filename")
        or metadata.get("document_name")
        or "không rõ nguồn"
    )

    page = metadata.get("page") or metadata.get("page_number")
    page_text = f", trang {page}" if page is not None else ""

    content = doc.page_content if hasattr(doc, "page_content") else str(doc)

    return f"[Nguồn: {source}{page_text}]\n{content}"


# đang nhận 2 input: query (user), context_chunks(output retrieval/reranking)
def generate_answer(query: str, context_chunks) -> str:

    # Nếu T13 không tìm thấy chunk nào phù hợp (không vượt qua score_threshold = 0.2)
    if not context_chunks:
        return "Tài liệu hiện tại không đề cập vấn đề này."

    formatted_chunks = [
        _format_chunk_with_source(doc)
        for doc in context_chunks
    ]

    context_text = "\n\n---\n\n".join(formatted_chunks)


    # # test
    # # # Debug context trước khi gửi LLM
    # print("\n===== CONTEXT SENT TO LLM =====")
    # print(context_text)
    # print("================================\n")


    llm = ChatOpenAI(
        model="gpt-5.4-nano",
        temperature=0
    )

    chain = (
        qa_prompt
        | llm
        | StrOutputParser()
    )


    # messages = qa_prompt.format_messages(
    #     context=context_text,
    #     query=query
    # )
    #
    #
    # # test
    # print("\n===== ACTUAL PROMPT =====")
    # for message in messages:
    #     print(f"\n[{message.type}]")
    #     print(message.content)
    # print("=========================\n")


    # gọi llm
    response = chain.invoke({
        "context": context_text,
        "query": query
    })


    # # test
    # print("\n===== RAW LLM RESPONSE =====")
    # print(repr(response))
    # print("============================\n")
    #

    # trả answer
    return response.strip()

def generate_comparison_answer(
    query: str,
    branch_evidence: list[tuple[str, list]],
) -> str:

    if not branch_evidence:
        return "Tài liệu hiện tại không đề cập vấn đề này."

    # Phòng hờ: nếu không đối tượng nào có evidence thì đáng lẽ
    # graph.py đã refuse từ trước khi gọi tới hàm này (route_after_evidence),
    # nhưng vẫn giữ check này để hàm luôn an toàn khi gọi độc lập/test.
    if all(not chunks for _, chunks in branch_evidence):
        return "Tài liệu hiện tại không đề cập vấn đề này."

    blocks: list[str] = []

    for sub_query, chunks in branch_evidence:
        if chunks:
            formatted = "\n\n---\n\n".join(
                _format_chunk_with_source(doc) for doc in chunks
            )
        else:
            formatted = "Không có dữ liệu trong tài liệu cho đối tượng này."

        blocks.append(
            f"### Đối tượng: {sub_query}\n{formatted}"
        )

    context_text = "\n\n===\n\n".join(blocks)

    llm = ChatOpenAI(
        model="gpt-5.4-nano",
        temperature=0,
    )

    chain = (
        comparison_prompt
        | llm
        | StrOutputParser()
    )

    response = chain.invoke({
        "context": context_text,
        "query": query,
    })

    return response.strip()