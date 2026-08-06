from typing import List, Dict, Any, Optional, AsyncGenerator
import json
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.rag.retriever import DocumentRetriever
from app.rag.prompt import PromptTemplates
from app.rag.embeddings import EmbeddingService
from app.utils.logger import logger

class RAGChain:
    """RAG chain for processing queries with retrieval and generation"""
    
    def __init__(self):
        self.client = ChatOllama(
        model="llama3.2",
        temperature=0.7)
        self.retriever = DocumentRetriever()
        self.prompts = PromptTemplates()
        self.embedding_service = EmbeddingService()
        
        # Configuration
        self.temperature = 0.7
        self.max_tokens = 2000
        self.top_p = 0.9
        self.frequency_penalty = 0.1
        self.presence_penalty = 0.1
    
    async def process_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Process a query through the RAG chain"""
        try:
            # Step 1: Retrieve relevant documents
            retrieved_docs = await self.retriever.retrieve(query, top_k=top_k)
            
            # Step 2: Format context
            context = self.prompts.format_retrieved_context(retrieved_docs)
            
            # Step 3: Format conversation history
            history_str = ""
            if conversation_history:
                history_str = self.prompts.format_conversation_history(conversation_history)
            
            # Step 4: Create prompt
            prompt = self.prompts.get_chat_prompt(query, context, history_str)
            
            # Step 5: Generate response
            response = await self.generate_response(prompt)
            
            # Step 6: Extract sources
            sources = self.extract_sources(retrieved_docs)
            
            # Step 7: Calculate confidence
            confidence = self.calculate_confidence(retrieved_docs, response)
            
            return {
                'response': response,
                'sources': sources,
                'confidence_score': confidence,
                'retrieved_count': len(retrieved_docs)
            }
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise
    
    async def process_stream_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5
    ) -> AsyncGenerator[str, None]:
        """Process a query with streaming response"""
        try:
            # Retrieve documents
            retrieved_docs = await self.retriever.retrieve(query, top_k=top_k)
            
            # Format context
            context = self.prompts.format_retrieved_context(retrieved_docs)
            
            # Format history
            history_str = ""
            if conversation_history:
                history_str = self.prompts.format_conversation_history(conversation_history)
            
            # Create prompt
            prompt = self.prompts.get_chat_prompt(query, context, history_str)
            
            # Extract sources once
            sources = self.extract_sources(retrieved_docs)
            
            # Send sources first
            yield json.dumps({
                'type': 'sources',
                'data': sources
            })
            
            # Stream the response using ChatOllama
            messages = [
                SystemMessage(content=self.prompts.SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            async for chunk in self.client.astream(messages):
                if chunk.content:
                    yield json.dumps({
                        'type': 'content',
                        'data': chunk.content
                    })
            
            # Send completion signal
            yield json.dumps({
                'type': 'complete',
                'data': {
                    'confidence': self.calculate_confidence(retrieved_docs, ""),
                    'total_documents': len(retrieved_docs)
                }
            })
        
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}")
            yield json.dumps({
                'type': 'error',
                'data': str(e)
            })
    
    async def generate_response(self, prompt: str) -> str:
        try:
            response = await self.client.ainvoke([
               SystemMessage(content=self.prompts.SYSTEM_PROMPT),
               HumanMessage(content=prompt),
            ])
            return response.content

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    async def process_with_metadata(
        self,
        query: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process query with additional metadata for filtering"""
        try:
            # Use metadata for filtering
            filter_criteria = metadata.get('filter', {})
            
            # Retrieve with filter
            retrieved_docs = await self.retriever.retrieve(
                query,
                top_k=metadata.get('top_k', 5),
                filter_criteria=filter_criteria
            )
            
            # Continue with regular processing
            context = self.prompts.format_retrieved_context(retrieved_docs)
            
            # Add metadata context
            context += f"\n\nAdditional Context: {json.dumps(metadata.get('context', {}))}"
            
            prompt = self.prompts.get_chat_prompt(query, context, "")
            response = await self.generate_response(prompt)
            
            return {
                'response': response,
                'sources': self.extract_sources(retrieved_docs),
                'metadata': metadata
            }
        
        except Exception as e:
            logger.error(f"Error processing with metadata: {str(e)}")
            raise
    
    def extract_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract source information from retrieved documents"""
        sources = []
        for doc in documents:
            metadata = doc.get('metadata', {})
            source = {
                'content': doc.get('content', '')[:200] + '...',
                'source': metadata.get('source', 'Unknown'),
                'filename': metadata.get('filename', 'Unknown'),
                'relevance_score': doc.get('distance', 0)
            }
            sources.append(source)
        
        return sources
    
    def calculate_confidence(
        self,
        documents: List[Dict[str, Any]],
        response: str
    ) -> float:
        """Calculate confidence score based on retrieved documents and response"""
        if not documents:
            return 0.0
        
        # Calculate average distance (lower is better for cosine distance)
        avg_distance = sum([doc.get('distance', 1) for doc in documents]) / len(documents)
        
        # Convert distance to similarity (assuming cosine distance 0-2)
        avg_similarity = 1 - (avg_distance / 2)
        
        # Check if response contains relevant content
        response_length = len(response.split())
        response_quality = min(response_length / 200, 1.0)  # 200 words = full quality
        
        # Confidence is a combination of similarity and response quality
        confidence = (avg_similarity * 0.6) + (response_quality * 0.4)
        
        return round(min(confidence, 1.0), 2)