import os
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiofiles
from app.utils.logger import logger
from app.config import settings

class DocumentLoader:
    """Load and process documents from various sources"""
    
    def __init__(self):
        self.supported_extensions = {
            '.txt': self._load_text,
            '.pdf': self._load_pdf,
            '.docx': self._load_docx,
            '.csv': self._load_csv,
            '.xlsx': self._load_excel,
        }
    
    async def load_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load a single file"""
        try:
            file_extension = Path(file_path).suffix.lower()
            if file_extension not in self.supported_extensions:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            loader_func = self.supported_extensions[file_extension]
            documents = await loader_func(file_path)
            
            logger.info(f"Loaded {len(documents)} documents from {file_path}")
            return documents
        
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {str(e)}")
            raise
    
    async def load_bytes(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """Load a file from bytes"""
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = tmp_file.name
            
            # Load the file
            documents = await self.load_file(tmp_path)
            
            # Clean up
            os.unlink(tmp_path)
            
            return documents
        
        except Exception as e:
            logger.error(f"Error loading bytes for {filename}: {str(e)}")
            raise
    
    async def _load_text(self, file_path: str) -> List[Dict[str, Any]]:
        """Load text file"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        return [{
            'content': content,
            'metadata': {
                'source': file_path,
                'type': 'text',
                'filename': Path(file_path).name
            }
        }]
    
    async def _load_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Load PDF file"""
        try:
            import PyPDF2
            
            documents = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        documents.append({
                            'content': text,
                            'metadata': {
                                'source': file_path,
                                'page': page_num + 1,
                                'type': 'pdf',
                                'filename': Path(file_path).name
                            }
                        })
            
            return documents
        
        except ImportError:
            raise ImportError("PyPDF2 is not installed. Please install it: pip install PyPDF2")
        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {str(e)}")
            raise
    
    async def _load_docx(self, file_path: str) -> List[Dict[str, Any]]:
        """Load DOCX file"""
        try:
            from docx import Document
            
            doc = Document(file_path)
            content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            
            return [{
                'content': content,
                'metadata': {
                    'source': file_path,
                    'type': 'docx',
                    'filename': Path(file_path).name
                }
            }]
        
        except ImportError:
            raise ImportError("python-docx is not installed. Please install it: pip install python-docx")
        except Exception as e:
            logger.error(f"Error loading DOCX {file_path}: {str(e)}")
            raise
    
    async def _load_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Load CSV file"""
        try:
            import pandas as pd
            
            df = pd.read_csv(file_path)
            content = df.to_string()
            
            return [{
                'content': content,
                'metadata': {
                    'source': file_path,
                    'type': 'csv',
                    'filename': Path(file_path).name
                }
            }]
        
        except ImportError:
            raise ImportError("pandas is not installed. Please install it: pip install pandas")
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {str(e)}")
            raise
    
    async def _load_excel(self, file_path: str) -> List[Dict[str, Any]]:
        """Load Excel file"""
        try:
            import pandas as pd
            
            xls = pd.ExcelFile(file_path)
            documents = []
            
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                content = df.to_string()
                
                documents.append({
                    'content': content,
                    'metadata': {
                        'source': file_path,
                        'sheet': sheet_name,
                        'type': 'excel',
                        'filename': Path(file_path).name
                    }
                })
            
            return documents
        
        except ImportError:
            raise ImportError("pandas and openpyxl are not installed. Please install them")
        except Exception as e:
            logger.error(f"Error loading Excel {file_path}: {str(e)}")
            raise