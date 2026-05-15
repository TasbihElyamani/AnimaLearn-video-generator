"""AnimaLearn — RAG Chain (sentence-transformers embeddings)"""
from __future__ import annotations
from typing import Any
from src.settings import QDRANT_COLLECTION, RAG_TOP_K, EMBEDDING_DIMENSION, MOCK_MODE

def embed_query(query):
    if MOCK_MODE:
        import numpy as np
        return np.random.randn(EMBEDDING_DIMENSION).tolist()
    from src.ingest_qdrant import get_embedder
    model = get_embedder()
    return model.encode(query, show_progress_bar=False).tolist()

def retrieve(query, top_k=RAG_TOP_K):
    if MOCK_MODE:
        return _mock_retrieve(query, top_k)
    from src.ingest_qdrant import get_qdrant_client
    client = get_qdrant_client()
    results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=embed_query(query),
        limit=top_k, with_payload=True)
    return [{"passage_id": h.payload.get("source_id", "?"),
             "source_file": h.payload.get("source_file", "?"),
             "text": h.payload.get("text", ""),
             "score": round(h.score, 4)} for h in results.points]

def retrieve_for_subtopics(subtopics, top_k=RAG_TOP_K):
    return {s: retrieve(s, top_k) for s in subtopics}

def format_passages_for_prompt(passages):
    if not passages:
        return "No reference passages available."
    return "\n".join(f"[{p['passage_id']}] (score:{p['score']}) {p['text']}" for p in passages)

def _mock_retrieve(query, top_k):
    nn_passages = [
        {"passage_id": "REF-neural_networks_overview", "source_file": "neural_networks_overview.txt",
         "text": "Artificial neural networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes: input, hidden, and output layers. Each connection has a weight adjusted during training via backpropagation. Deep learning uses networks with many hidden layers to learn hierarchical representations of data.",
         "score": 0.96},
        {"passage_id": "REF-nn_architectures", "source_file": "nn_architectures.txt",
         "text": "Key neural network architectures include CNNs for image processing, RNNs/LSTMs for sequential data, and Transformers for parallel sequence processing. The Transformer, introduced in 2017 by Vaswani et al., uses self-attention mechanisms and powers modern LLMs like GPT and BERT.",
         "score": 0.94},
        {"passage_id": "REF-nn_training", "source_file": "nn_training.txt",
         "text": "Neural networks learn through backpropagation and gradient descent. The loss function measures prediction error. The optimizer (SGD, Adam) updates weights to minimize loss. Training requires labeled datasets, epochs of forward and backward passes, and careful hyperparameter tuning to avoid overfitting.",
         "score": 0.91},
        {"passage_id": "REF-nn_applications", "source_file": "nn_applications.txt",
         "text": "Neural networks power image recognition (CNNs), natural language processing (Transformers), speech recognition (RNNs), autonomous vehicles, drug discovery, game playing (AlphaGo), recommendation systems, and generative AI including text, image, and video generation.",
         "score": 0.89},
        {"passage_id": "REF-nn_history", "source_file": "nn_history.txt",
         "text": "The perceptron was invented in 1958 by Frank Rosenblatt. The field experienced AI winters until the 2006 deep learning revival led by Geoffrey Hinton. The 2012 AlexNet breakthrough on ImageNet proved deep CNNs could achieve superhuman image classification. The 2017 Transformer paper revolutionized NLP.",
         "score": 0.86},
    ]
    return nn_passages[:top_k]
