"""
Error handling utilities for the Podcast Creator Studio.

Provides consistent error handling and user-friendly error messages.
"""

import traceback
from typing import Optional, Dict, Any, List
import streamlit as st
from enum import Enum


class ErrorType(Enum):
    """Types of errors that can occur in the application."""
    NETWORK_ERROR = "network_error"
    FILE_ERROR = "file_error"
    CONTENT_ERROR = "content_error"
    PROFILE_ERROR = "profile_error"
    GENERATION_ERROR = "generation_error"
    VALIDATION_ERROR = "validation_error"
    IMPORT_ERROR = "import_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorHandler:
    """Handles errors and provides user-friendly messages."""
    
    @staticmethod
    def handle_generation_error(error: Exception) -> str:
        """
        Handle podcast generation errors.
        
        Args:
            error: The exception that occurred
            
        Returns:
            User-friendly error message
        """
        error_str = str(error).lower()
        
        # API-related errors
        if "api" in error_str or "timeout" in error_str or "rate limit" in error_str:
            return ErrorHandler._format_api_error(error)
        
        # Content-related errors
        if "content" in error_str or "empty" in error_str:
            return ErrorHandler._format_content_error(error)
        
        # Configuration errors
        if "config" in error_str or "profile" in error_str:
            return ErrorHandler._format_config_error(error)
        
        # Generic error
        return ErrorHandler._format_generic_error(error)
    
    @staticmethod
    def _format_api_error(error: Exception) -> str:
        """Format API-related errors."""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return (
                "⏱️ **Request Timeout**\n\n"
                "The AI service took too long to respond. This can happen when:\n"
                "• The service is experiencing high load\n"
                "• Your internet connection is slow\n"
                "• The content is very long\n\n"
                "**What to try:**\n"
                "• Click 'Retry' to try again\n"
                "• Check your internet connection\n"
                "• Try with shorter content\n"
                "• Wait a few minutes and try again"
            )
        
        elif "rate limit" in error_str:
            return (
                "🚫 **Rate Limit Exceeded**\n\n"
                "You've exceeded the API rate limit. This happens when:\n"
                "• Too many requests in a short time\n"
                "• Your API quota is exhausted\n\n"
                "**What to try:**\n"
                "• Wait a few minutes and try again\n"
                "• Check your API usage and limits\n"
                "• Consider upgrading your API plan"
            )
        
        elif "authentication" in error_str or "unauthorized" in error_str:
            return (
                "🔑 **Authentication Error**\n\n"
                "There's an issue with your API credentials:\n"
                "• API key may be invalid or expired\n"
                "• API key may not have required permissions\n\n"
                "**What to try:**\n"
                "• Check your API key configuration\n"
                "• Verify your API key is still valid\n"
                "• Check if your API key has required permissions"
            )
        
        else:
            return (
                "🌐 **API Error**\n\n"
                f"An error occurred while communicating with the AI service:\n"
                f"`{str(error)}`\n\n"
                "**What to try:**\n"
                "• Click 'Retry' to try again\n"
                "• Check your internet connection\n"
                "• Verify your API configuration"
            )
    
    @staticmethod
    def _format_content_error(error: Exception) -> str:
        """Format content-related errors."""
        return (
            "📄 **Content Error**\n\n"
            f"There's an issue with the content you provided:\n"
            f"`{str(error)}`\n\n"
            "**What to try:**\n"
            "• Make sure your content is not empty\n"
            "• Check that the content is readable text\n"
            "• Try with different content\n"
            "• If using a file, make sure it's not corrupted"
        )
    
    @staticmethod
    def _format_config_error(error: Exception) -> str:
        """Format configuration-related errors."""
        return (
            "⚙️ **Configuration Error**\n\n"
            f"There's an issue with your configuration:\n"
            f"`{str(error)}`\n\n"
            "**What to try:**\n"
            "• Check your speaker and episode profiles\n"
            "• Verify all required fields are filled\n"
            "• Try with a different profile\n"
            "• Check your model settings"
        )
    
    @staticmethod
    def _format_generic_error(error: Exception) -> str:
        """Format generic errors."""
        return (
            "❌ **Unexpected Error**\n\n"
            f"An unexpected error occurred:\n"
            f"`{str(error)}`\n\n"
            "**What to try:**\n"
            "• Click 'Retry' to try again\n"
            "• Try with different settings\n"
            "• Check your configuration\n"
            "• If the problem persists, try restarting the application"
        )
    
    @staticmethod
    def display_error_message(error_msg: str, error_type: ErrorType = ErrorType.UNKNOWN_ERROR) -> None:
        """
        Display a formatted error message in Streamlit.
        
        Args:
            error_msg: The error message to display
            error_type: Type of error for appropriate styling
        """
        if error_type == ErrorType.NETWORK_ERROR:
            st.error(error_msg)
        elif error_type == ErrorType.VALIDATION_ERROR:
            st.warning(error_msg)
        else:
            st.error(error_msg)
    
    @staticmethod
    def get_retry_options(error_type: ErrorType) -> List[str]:
        """
        Get appropriate retry options based on error type.
        
        Args:
            error_type: Type of error that occurred
            
        Returns:
            List of retry option descriptions
        """
        if error_type == ErrorType.NETWORK_ERROR:
            return [
                "Retry with same settings",
                "Check network connection",
                "Try with different API endpoint"
            ]
        elif error_type == ErrorType.CONTENT_ERROR:
            return [
                "Try with different content",
                "Check content format",
                "Use shorter content"
            ]
        elif error_type == ErrorType.PROFILE_ERROR:
            return [
                "Try with different profile",
                "Check profile configuration",
                "Create new profile"
            ]
        elif error_type == ErrorType.GENERATION_ERROR:
            return [
                "Retry generation",
                "Try with different settings",
                "Use different AI model"
            ]
        else:
            return [
                "Retry operation",
                "Check configuration",
                "Try different settings"
            ]
    
    @staticmethod
    def classify_error(error: Exception) -> ErrorType:
        """
        Classify an error into an appropriate error type.
        
        Args:
            error: The exception to classify
            
        Returns:
            Appropriate ErrorType
        """
        error_str = str(error).lower()
        
        # Network/API errors
        if any(keyword in error_str for keyword in ["timeout", "connection", "network", "api", "http"]):
            return ErrorType.NETWORK_ERROR
        
        # File errors
        if any(keyword in error_str for keyword in ["file", "path", "directory", "permission"]):
            return ErrorType.FILE_ERROR
        
        # Content errors
        if any(keyword in error_str for keyword in ["content", "empty", "invalid", "format"]):
            return ErrorType.CONTENT_ERROR
        
        # Profile errors
        if any(keyword in error_str for keyword in ["profile", "config", "speaker", "episode"]):
            return ErrorType.PROFILE_ERROR
        
        # Generation errors
        if any(keyword in error_str for keyword in ["generation", "create", "podcast", "outline", "transcript"]):
            return ErrorType.GENERATION_ERROR
        
        # Validation errors
        if any(keyword in error_str for keyword in ["validation", "validate", "required", "missing"]):
            return ErrorType.VALIDATION_ERROR
        
        # Import errors
        if any(keyword in error_str for keyword in ["import", "module", "dependency"]):
            return ErrorType.IMPORT_ERROR
        
        return ErrorType.UNKNOWN_ERROR
    
    @staticmethod
    def create_error_report(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a detailed error report for debugging.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            
        Returns:
            Dictionary containing error details
        """
        error_report = {
            "error_type": str(type(error).__name__),
            "error_message": str(error),
            "error_classification": ErrorHandler.classify_error(error).value,
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        return error_report
    
    @staticmethod
    def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error for debugging purposes.
        
        Args:
            error: The exception that occurred
            context: Additional context information
        """
        error_report = ErrorHandler.create_error_report(error, context)
        
        # In a real application, you might want to log to a file or external service
        # For now, we'll just print to console
        print(f"Error logged: {error_report}")
    
    @staticmethod
    def handle_streamlit_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Handle an error in Streamlit with appropriate UI feedback.
        
        Args:
            error: The exception that occurred
            context: Additional context information
        """
        # Classify the error
        error_type = ErrorHandler.classify_error(error)
        
        # Generate user-friendly message
        if error_type == ErrorType.GENERATION_ERROR:
            user_message = ErrorHandler.handle_generation_error(error)
        else:
            user_message = ErrorHandler._format_generic_error(error)
        
        # Display the error
        ErrorHandler.display_error_message(user_message, error_type)
        
        # Log the error for debugging
        ErrorHandler.log_error(error, context)
        
        # Show retry options
        retry_options = ErrorHandler.get_retry_options(error_type)
        if retry_options:
            st.markdown("### Suggested Actions:")
            for option in retry_options:
                st.markdown(f"• {option}")
    
    @staticmethod
    def create_error_expander(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Create an expandable error details section.
        
        Args:
            error: The exception that occurred
            context: Additional context information
        """
        with st.expander("🔍 Error Details (for debugging)"):
            error_report = ErrorHandler.create_error_report(error, context)
            
            st.markdown("**Error Type:** " + error_report["error_type"])
            st.markdown("**Error Message:** " + error_report["error_message"])
            st.markdown("**Classification:** " + error_report["error_classification"])
            
            if error_report["context"]:
                st.markdown("**Context:**")
                st.json(error_report["context"])
            
            st.markdown("**Traceback:**")
            st.code(error_report["traceback"], language="python")