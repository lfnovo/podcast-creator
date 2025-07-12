"""
Content extraction utilities for the Podcast Creator Studio.

Handles content extraction from various sources using content-core library.
"""

import asyncio
from typing import Optional, Union, Dict, Any, List
import streamlit as st
import requests
from pathlib import Path

try:
    from content_core import extract_content
    CONTENT_CORE_AVAILABLE = True
except ImportError:
    CONTENT_CORE_AVAILABLE = False


class ContentExtractor:
    """Content extraction utility using content-core library."""
    
    @staticmethod
    def is_content_core_available() -> bool:
        """Check if content-core library is available."""
        return CONTENT_CORE_AVAILABLE
    
    @staticmethod
    async def extract_from_url(url: str) -> str:
        """
        Extract content from a URL using content-core.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Extracted content as string
            
        Raises:
            ImportError: If content-core is not available
            Exception: If extraction fails
        """
        if not CONTENT_CORE_AVAILABLE:
            raise ImportError(
                "content-core library is required for URL extraction. "
                "Please install it using: pip install content-core"
            )
        
        try:
            result = await extract_content(dict(url=url))
            content = result.content if hasattr(result, 'content') else str(result)
            if not content or not content.strip():
                raise Exception("No content extracted from URL")
            return content
        except Exception as e:
            raise Exception(f"Failed to extract content from URL: {str(e)}")
    
    @staticmethod
    async def extract_from_file(file_path: str) -> str:
        """
        Extract content from a file using content-core.
        
        Args:
            file_path: Path to the file to extract content from
            
        Returns:
            Extracted content as string
            
        Raises:
            ImportError: If content-core is not available
            FileNotFoundError: If file doesn't exist
            Exception: If extraction fails
        """
        if not CONTENT_CORE_AVAILABLE:
            raise ImportError(
                "content-core library is required for file extraction. "
                "Please install it using: pip install content-core"
            )
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            result = await extract_content({"file_path": file_path})
            content = result.content if hasattr(result, 'content') else str(result)
            if not content or not content.strip():
                raise Exception("No content extracted from file")
            return content
        except Exception as e:
            raise Exception(f"Failed to extract content from file: {str(e)}")
    
    @staticmethod
    def extract_from_text(text: str) -> str:
        """
        Pass through text content directly.
        
        Args:
            text: Text content to pass through
            
        Returns:
            The same text content
        """
        return text
    
    @staticmethod
    def extract_from_uploaded_file(uploaded_file) -> str:
        """
        Extract content from a Streamlit uploaded file.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            
        Returns:
            Extracted content as string
        """
        try:
            # For text files, read directly
            if uploaded_file.type == "text/plain":
                return uploaded_file.read().decode("utf-8")
            
            # For other file types, we would need content-core
            # For now, save to temp file and use content-core
            if not CONTENT_CORE_AVAILABLE:
                raise ImportError(
                    "content-core library is required for file extraction. "
                    "Please install it using: pip install content-core"
                )
            
            # Save uploaded file to temporary location
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name
            
            try:
                # Extract content using content-core
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    extract_content({"file_path": tmp_file_path})
                )
                loop.close()
                content = result.content if hasattr(result, 'content') else str(result)
                if not content or not content.strip():
                    raise Exception("No content extracted from file")
                return content
            finally:
                # Clean up temporary file
                Path(tmp_file_path).unlink(missing_ok=True)
                
        except Exception as e:
            raise Exception(f"Failed to extract content from uploaded file: {str(e)}")
    
    @classmethod
    async def extract_content(cls, source: Union[str, Dict[str, Any]]) -> str:
        """
        Extract content from various sources.
        
        Args:
            source: Can be:
                - A string (treated as direct text)
                - A dict with 'url' key (for URL extraction)
                - A dict with 'file_path' key (for file extraction)
        
        Returns:
            Extracted content as string
            
        Raises:
            ValueError: If source format is invalid
            Exception: If extraction fails
        """
        if isinstance(source, str):
            return cls.extract_from_text(source)
        elif isinstance(source, dict):
            if 'url' in source:
                return await cls.extract_from_url(source['url'])
            elif 'file_path' in source:
                return await cls.extract_from_file(source['file_path'])
            else:
                raise ValueError("Dictionary source must contain 'url' or 'file_path' key")
        else:
            raise ValueError(
                "Source must be a string (direct text) or dict with 'url'/'file_path' key"
            )
    
    @staticmethod
    def validate_content(content: str) -> bool:
        """
        Validate that content is suitable for podcast generation.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is valid, False otherwise
        """
        if not content or not content.strip():
            return False
        
        # Check minimum length (at least 50 characters)
        if len(content.strip()) < 50:
            return False
        
        # Check that it's not just whitespace or special characters
        if not any(c.isalnum() for c in content):
            return False
        
        return True
    
    @staticmethod
    def get_content_stats(content: str) -> Dict[str, Any]:
        """
        Get statistics about the content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Dictionary with content statistics
        """
        if not content:
            return {
                'character_count': 0,
                'word_count': 0,
                'paragraph_count': 0,
                'estimated_reading_time': 0
            }
        
        # Basic stats
        character_count = len(content)
        word_count = len(content.split())
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        
        # Estimated reading time (average 200 words per minute)
        estimated_reading_time = max(1, word_count // 200)
        
        return {
            'character_count': character_count,
            'word_count': word_count,
            'paragraph_count': paragraph_count,
            'estimated_reading_time': estimated_reading_time
        }
    
    @staticmethod
    def truncate_content(content: str, max_length: int = 1000) -> str:
        """
        Truncate content to a maximum length for preview.
        
        Args:
            content: Content to truncate
            max_length: Maximum length in characters
            
        Returns:
            Truncated content
        """
        if len(content) <= max_length:
            return content
        
        # Try to truncate at word boundary
        truncated = content[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can find a good word boundary
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate that a URL is accessible.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is accessible, False otherwise
        """
        try:
            response = requests.head(url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    @staticmethod
    def get_supported_file_types() -> List[str]:
        """
        Get list of supported file types for extraction.
        
        Returns:
            List of supported file extensions
        """
        # These are common file types that content-core typically supports
        return [
            '.txt', '.md', '.pdf', '.docx', '.doc', '.rtf',
            '.html', '.htm', '.csv', '.json', '.xml'
        ]
    
    @staticmethod
    def is_file_type_supported(file_name: str) -> bool:
        """
        Check if a file type is supported for extraction.
        
        Args:
            file_name: Name of the file to check
            
        Returns:
            True if file type is supported, False otherwise
        """
        file_extension = Path(file_name).suffix.lower()
        return file_extension in ContentExtractor.get_supported_file_types()