from typing import List, Dict, Any, Optional
import numpy as np
import httpx
from app.config import settings
from app.utils.logger import logger


class EmbeddingService:
    """Generate embeddings for text chunks using a local Ollama model (free, no API key)."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_EMBEDDING_MODEL
        self.dimension = 768  # nomic-embed-text output size

        # Cache for embeddings to avoid duplicate computation
        self.cache: Dict[str, List[float]] = {}

    async def _call_ollama_embedding(self, text: str) -> List[float]:
        """Call Ollama's local embeddings endpoint for a single text."""
        url = f"{self.base_url}/api/embeddings"
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json={"model": self.model, "prompt": text})
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            embeddings = []

            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                # Check cache
                cached_embeddings = []
                uncached_texts = []
                uncached_indices = []

                for idx, text in enumerate(batch):
                    if text in self.cache:
                        cached_embeddings.append((idx, self.cache[text]))
                    else:
                        uncached_texts.append(text)
                        uncached_indices.append(idx)

                # Generate embeddings for uncached texts (Ollama has no native
                # batch endpoint, so we call it once per text)
                for j, text in enumerate(uncached_texts):
                    embedding = await self._call_ollama_embedding(text)
                    self.cache[text] = embedding

                    original_idx = uncached_indices[j]
                    cached_embeddings.append((original_idx, embedding))

                # Sort by original index
                cached_embeddings.sort(key=lambda x: x[0])
                batch_embeddings = [emb for _, emb in cached_embeddings]
                embeddings.extend(batch_embeddings)

            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            if text in self.cache:
                return self.cache[text]

            embedding = await self._call_ollama_embedding(text)
            self.cache[text] = embedding
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    async def batch_embed_documents(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 50
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for document chunks and update them"""
        try:
            texts = [chunk['content'] for chunk in chunks]
            embeddings = await self.generate_embeddings(texts, batch_size)

            # Update chunks with embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk['embedding'] = embedding

            logger.info(f"Generated embeddings for {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error batch embedding documents: {str(e)}")
            raise

    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0

    def calculate_similarity_matrix(
        self,
        embeddings1: List[List[float]],
        embeddings2: List[List[float]]
    ) -> np.ndarray:
        """Calculate similarity matrix between two sets of embeddings"""
        try:
            matrix = np.zeros((len(embeddings1), len(embeddings2)))

            for i, emb1 in enumerate(embeddings1):
                for j, emb2 in enumerate(embeddings2):
                    matrix[i][j] = self.cosine_similarity(emb1, emb2)

            return matrix

        except Exception as e:
            logger.error(f"Error calculating similarity matrix: {str(e)}")
            raise
