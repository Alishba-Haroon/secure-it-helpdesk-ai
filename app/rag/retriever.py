from typing import List, Dict, Any, Optional
import chromadb
import requests
from app.config import settings
from app.rag.embeddings import EmbeddingService
from app.utils.logger import logger


class OllamaEmbeddingFunction:
    """ChromaDB-compatible embedding function backed by a local Ollama model.

    ChromaDB calls embedding functions synchronously, so this uses `requests`
    (not the async EmbeddingService) directly against Ollama's REST API.
    """

    def __init__(self, base_url: str = None, model_name: str = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OLLAMA_EMBEDDING_MODEL

    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings = []
        for text in input:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=120
            )
            response.raise_for_status()
            embeddings.append(response.json()["embedding"])
        return embeddings

    def name(self) -> str:
        return f"ollama-{self.model_name}"


class DocumentRetriever:
    """Retrieve relevant documents from vector database"""
    
    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.persist_dir = settings.CHROMA_PERSIST_DIR
        self.embedding_service = EmbeddingService()
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_dir
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=OllamaEmbeddingFunction()
        )
    
    async def add_documents(
        self,
        chunks: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents to vector database"""
        try:
            documents = [chunk['content'] for chunk in chunks]
            metadatas = [chunk.get('metadata', {}) for chunk in chunks]
            
            # Generate IDs if not provided
            if ids is None:
                import uuid
                ids = [str(uuid.uuid4()) for _ in chunks]
            
            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(chunks)} documents to collection {self.collection_name}")
        
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_criteria: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query"""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_criteria
            )
            
            # Format results
            retrieved_docs = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    doc = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'id': results['ids'][0][i] if results['ids'] else None,
                        'distance': results['distances'][0][i] if results['distances'] else None
                    }
                    retrieved_docs.append(doc)
            
            logger.info(f"Retrieved {len(retrieved_docs)} documents for query: {query[:50]}...")
            return retrieved_docs
        
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise
    
    async def retrieve_by_embedding(
        self,
        embedding: List[float],
        top_k: int = 5,
        filter_criteria: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve documents using an embedding directly"""
        try:
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=filter_criteria
            )
            
            retrieved_docs = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    doc = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'id': results['ids'][0][i] if results['ids'] else None,
                        'distance': results['distances'][0][i] if results['distances'] else None
                    }
                    retrieved_docs.append(doc)
            
            return retrieved_docs
        
        except Exception as e:
            logger.error(f"Error retrieving by embedding: {str(e)}")
            raise
    
    async def delete_documents(self, ids: List[str]) -> None:
        """Delete documents from vector database"""
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from collection")
        
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            raise
    
    async def update_documents(
        self,
        ids: List[str],
        chunks: List[Dict[str, Any]]
    ) -> None:
        """Update existing documents"""
        try:
            documents = [chunk['content'] for chunk in chunks]
            metadatas = [chunk.get('metadata', {}) for chunk in chunks]
            
            self.collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Updated {len(ids)} documents in collection")
        
        except Exception as e:
            logger.error(f"Error updating documents: {str(e)}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            return {
                'collection_name': self.collection_name,
                'document_count': count,
                'persist_directory': self.persist_dir
            }
        
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            raise