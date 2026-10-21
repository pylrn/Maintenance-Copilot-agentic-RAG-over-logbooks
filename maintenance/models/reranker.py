import re


class Reranker:
    def __init__(self,revision,cache_dir='models',local_only=True):
        if not re.fullmatch(r'[0-9a-f]{40}',revision): raise ValueError('immutable model revision required')
        from sentence_transformers import CrossEncoder
        self.model=CrossEncoder('cross-encoder/ms-marco-MiniLM-L6-v2',revision=revision,cache_folder=str(cache_dir),local_files_only=local_only,device='cpu',trust_remote_code=False)

    def score(self,pairs):
        if len(pairs)>20: raise ValueError('rerank limit exceeded')
        return self.model.predict(pairs,batch_size=20,show_progress_bar=False).tolist() if pairs else []
