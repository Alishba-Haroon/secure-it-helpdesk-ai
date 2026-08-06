import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.rag.retriever import DocumentRetriever
from app.rag.embeddings import EmbeddingService
from app.rag.loader import DocumentLoader
from app.rag.splitter import DocumentSplitter
from app.rag.chain import RAGChain

@pytest.mark.asyncio
async def test_document_loader_text():
    loader = DocumentLoader()
    
    # Test text loading
    with patch('aiofiles.open', new_callable=MagicMock) as mock_open:
        mock_open.return_value.__aenter__.return_value.read = AsyncMock(return_value="Test content")
        docs = await loader.load_file("test.txt")
        
        assert len(docs) > 0
        assert "content" in docs[0]
        assert docs[0]["content"] == "Test content"

@pytest.mark.asyncio
async def test_document_splitter():
    splitter = DocumentSplitter(chunk_size=100, chunk_overlap=20)
    
    docs = [{
        "content": "This is a test document. " * 10,
        "metadata": {"source": "test"}
    }]
    
    chunks = await splitter.split_documents(docs)
    
    assert len(chunks) > 0
    assert all("content" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)

@pytest.mark.asyncio
async def test_embedding_service():
    service = EmbeddingService()
    
    with patch.object(service.client, 'embeddings') as mock_embeddings:
        mock_embeddings.create = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
        ))
        
        embeddings = await service.generate_embeddings(["test text"])
        
        assert len(embeddings) > 0
        assert len(embeddings[0]) == 3

@pytest.mark.asyncio
async def test_document_retriever():
    retriever = DocumentRetriever()
    
    with patch.object(retriever.collection, 'query') as mock_query:
        mock_query.return_value = {
            'documents': [['relevant doc']],
            'metadatas': [[{'source': 'test'}]],
            'ids': [['id1']],
            'distances': [[0.5]]
        }
        
        docs = await retriever.retrieve("test query")
        
        assert len(docs) > 0
        assert "content" in docs[0]
        assert "metadata" in docs[0]

@pytest.mark.asyncio
async def test_rag_chain():
    chain = RAGChain()
    
    with patch.object(chain.retriever, 'retrieve') as mock_retrieve:
        mock_retrieve.return_value = [
            {
                'content': 'Test content',
                'metadata': {'source': 'test'},
                'distance': 0.5
            }
        ]
        
        with patch.object(chain, 'generate_response') as mock_generate:
            mock_generate.return_value = "Test response"
            
            result = await chain.process_query("test query")
            
            assert "response" in result
            assert "sources" in result
            assert "confidence_score" in result
            assert result["response"] == "Test response"