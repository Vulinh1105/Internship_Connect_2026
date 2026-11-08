from time import perf_counter

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder


# sd cross model
DEFAULT_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
DEFAULT_TOP_K = 5
DEFAULT_BATCH_SIZE = 8
DEFAULT_DEVICE = "cpu"

# đóng gói all chức năng của reranking
class Reranker:

    # khởi tạo model
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str = DEFAULT_DEVICE,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = CrossEncoder(
            model_name,
            device=device,
        )

    def rerank(
        self,
        query: str,
        documents: list[Document], # nhận output từ retrieval.py
        top_k: int = DEFAULT_TOP_K,
    ) -> tuple[list[Document], float]:

        # ktra query
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        # ktra top_k
        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        if not documents:
            return [], 0.0

        # tao cặp Query + Document
        pairs = [
            (query, document.page_content)
            for document in documents
        ]

        start_time = perf_counter()

        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )

        latency_ms = (perf_counter() - start_time) * 1000
        # tạo list chứa kqua
        ranked_documents = []

        # ghép Document với score
        for retrieval_rank, (document, score) in enumerate(
            zip(documents, scores),
            start=1,
        ):
            # copy metadata -> bổ sung ttin reranking/ k sửa trực tiếp vào metadata ban đầu
            metadata = dict(document.metadata)

            metadata["retrieval_rank"] = retrieval_rank
            metadata["rerank_score"] = float(score)

            # tạo Document mứi
            ranked_documents.append(
                Document(
                    page_content=document.page_content,
                    metadata=metadata,
                )
            )

        # sắp xếp lại theo score
        ranked_documents.sort(
            key=lambda document: document.metadata["rerank_score"],
            reverse=True,
        )
        # gán rerank_rank
        for rerank_rank, document in enumerate(
            ranked_documents,
            start=1,
        ):
            document.metadata["rerank_rank"] = rerank_rank

        return ranked_documents[:top_k], latency_ms