# Reciprocal Rank Fusion from chatbot_AI/backend/app/ai_agent/hybrid_retrieval.py.
RRF_K = 60


def fuse_ranks(semantic_results, keyword_results):
    scores = {}
    docs = {}
    for result_set in (
        semantic_results,
        keyword_results,
    ):
        for rank, document in enumerate(
            result_set,
            start=1,
        ):
            key = (document["document_id"], document["position"])
    
            scores[key] = (
                scores.get(key, 0.0)
                + 1
                / (
                    RRF_K
                    + rank
                )
            )
    
            docs[key] = document
    return scores, docs
