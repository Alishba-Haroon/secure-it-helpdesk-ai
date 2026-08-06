from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.utils.logger import logger

class DocumentSplitter:
    """Split documents into chunks for RAG processing"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = ["\n\n", "\n", ".", " ", ""]
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
        )
    
    async def split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split documents into chunks"""
        try:
            chunks = []
            
            for doc in documents:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                
                # Split text into chunks
                text_chunks = self.text_splitter.split_text(content)
                
                # Create chunk documents
                for i, chunk_text in enumerate(text_chunks):
                    if chunk_text.strip():
                        chunk_metadata = metadata.copy()
                        chunk_metadata.update({
                            'chunk_id': i,
                            'total_chunks': len(text_chunks),
                            'chunk_size': len(chunk_text)
                        })
                        
                        chunks.append({
                            'content': chunk_text,
                            'metadata': chunk_metadata
                        })
            
            logger.info(f"Split {len(documents)} documents into {len(chunks)} chunks")
            return chunks
        
        except Exception as e:
            logger.error(f"Error splitting documents: {str(e)}")
            raise
    
    async def split_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Split a single text into chunks"""
        try:
            text_chunks = self.text_splitter.split_text(text)
            chunks = []
            
            for i, chunk_text in enumerate(text_chunks):
                if chunk_text.strip():
                    chunk_metadata = metadata.copy() if metadata else {}
                    chunk_metadata.update({
                        'chunk_id': i,
                        'total_chunks': len(text_chunks),
                        'chunk_size': len(chunk_text)
                    })
                    
                    chunks.append({
                        'content': chunk_text,
                        'metadata': chunk_metadata
                    })
            
            return chunks
        
        except Exception as e:
            logger.error(f"Error splitting text: {str(e)}")
            raise
    
    async def split_with_semantic(
        self,
        documents: List[Dict[str, Any]],
        min_chunk_size: int = 200,
        max_chunk_size: int = 1500
    ) -> List[Dict[str, Any]]:
        """Split documents with semantic boundaries (sentences/paragraphs)"""
        try:
            # Use different separators for semantic splitting
            semantic_splitter = RecursiveCharacterTextSplitter(
                chunk_size=max_chunk_size,
                chunk_overlap=min(200, max_chunk_size // 5),
                separators=[
                    "\n\n",  # Paragraphs
                    "\n",    # Lines
                    ". ",    # Sentences
                    "! ",    # Exclamations
                    "? ",    # Questions
                    "; ",    # Semicolons
                    ", ",    # Commas
                    " ",     # Words
                    "",      # Characters
                ],
                length_function=len,
            )
            
            chunks = []
            for doc in documents:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                
                text_chunks = semantic_splitter.split_text(content)
                
                for i, chunk_text in enumerate(text_chunks):
                    if chunk_text.strip() and len(chunk_text) >= min_chunk_size:
                        chunk_metadata = metadata.copy()
                        chunk_metadata.update({
                            'chunk_id': i,
                            'total_chunks': len(text_chunks),
                            'chunk_size': len(chunk_text)
                        })
                        
                        chunks.append({
                            'content': chunk_text,
                            'metadata': chunk_metadata                        })
            
            logger.info(f"Semantically split into {len(chunks)} chunks")
            return chunks
        
        except Exception as e:
            logger.error(f"Error in semantic splitting: {str(e)}")
            raise