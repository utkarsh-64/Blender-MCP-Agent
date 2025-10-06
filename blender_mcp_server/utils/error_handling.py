"""
Error handling utilities
"""

import logging
import traceback
from enum import Enum
from typing import Optional, Dict, Any
from ..data_models import ResponseMessage


class ErrorCategory(Enum):
    """Error categories for better classification"""
    CONNECTION = "CONNECTION"
    VALIDATION = "VALIDATION"
    BLENDER_API = "BLENDER_API"
    COMMAND = "COMMAND"
    SYSTEM = "SYSTEM"
    TIMEOUT = "TIMEOUT"
    SECURITY = "SECURITY"


class MCPError(Exception):
    """Custom exception for MCP server errors"""
    
    def __init__(self, code: str, message: str, category: ErrorCategory = ErrorCategory.SYSTEM, 
                 details: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.category = category
        self.details = details
        self.context = context or {}
        super().__init__(f"{code}: {message}")


class ErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self):
        self.logger = logging.getLogger("ErrorHandler")
        self.error_counts: Dict[str, int] = {}
    
    def handle_error(self, error: Exception, operation: str, 
                    category: ErrorCategory = ErrorCategory.SYSTEM,
                    context: Optional[Dict[str, Any]] = None) -> ResponseMessage:
        """Handle any error and convert to standardized response"""
        
        # Increment error count
        error_key = f"{category.value}_{operation}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log error with context
        self._log_error(error, operation, category, context)
        
        # Create appropriate response based on error type
        if isinstance(error, MCPError):
            return self._handle_mcp_error(error)
        else:
            return self._handle_generic_error(error, operation, category, context)
    
    def _log_error(self, error: Exception, operation: str, 
                  category: ErrorCategory, context: Optional[Dict[str, Any]]):
        """Log error with appropriate level and context"""
        
        error_msg = f"[{category.value}] {operation} failed: {str(error)}"
        
        # Add context if available
        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            error_msg += f" (Context: {context_str})"
        
        # Log with appropriate level based on category
        if category in [ErrorCategory.SECURITY, ErrorCategory.BLENDER_API]:
            self.logger.error(error_msg)
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
        elif category in [ErrorCategory.VALIDATION, ErrorCategory.COMMAND]:
            self.logger.warning(error_msg)
        else:
            self.logger.info(error_msg)
    
    def _handle_mcp_error(self, error: MCPError) -> ResponseMessage:
        """Handle MCP-specific errors"""
        return ResponseMessage(
            success=False,
            error=f"{error.code}: {error.message}",
            data={
                "error_code": error.code,
                "category": error.category.value,
                "details": error.details,
                "context": error.context
            }
        )
    
    def _handle_generic_error(self, error: Exception, operation: str,
                            category: ErrorCategory, context: Optional[Dict[str, Any]]) -> ResponseMessage:
        """Handle generic Python exceptions"""
        
        # Map common exceptions to error codes
        error_code_map = {
            KeyError: "MISSING_KEY",
            ValueError: "INVALID_VALUE",
            TypeError: "TYPE_ERROR",
            FileNotFoundError: "FILE_NOT_FOUND",
            PermissionError: "PERMISSION_DENIED",
            TimeoutError: "TIMEOUT",
            ConnectionError: "CONNECTION_ERROR"
        }
        
        error_code = error_code_map.get(type(error), "UNKNOWN_ERROR")
        
        return ResponseMessage(
            success=False,
            error=f"{error_code}: {operation} failed - {str(error)}",
            data={
                "error_code": error_code,
                "category": category.value,
                "operation": operation,
                "details": str(error),
                "context": context or {}
            }
        )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts.copy(),
            "categories": {category.value: sum(
                count for key, count in self.error_counts.items() 
                if key.startswith(category.value)
            ) for category in ErrorCategory}
        }


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_blender_error(e: Exception, operation: str, 
                        context: Optional[Dict[str, Any]] = None) -> ResponseMessage:
    """Convert Blender API errors to standardized response"""
    handler = get_error_handler()
    return handler.handle_error(e, operation, ErrorCategory.BLENDER_API, context)


def handle_validation_error(message: str, details: Optional[str] = None) -> ResponseMessage:
    """Handle validation errors"""
    error = MCPError("VALIDATION_ERROR", message, ErrorCategory.VALIDATION, details)
    handler = get_error_handler()
    return handler._handle_mcp_error(error)


def handle_command_error(message: str, command: str, details: Optional[str] = None) -> ResponseMessage:
    """Handle command-specific errors"""
    error = MCPError("COMMAND_ERROR", message, ErrorCategory.COMMAND, details, {"command": command})
    handler = get_error_handler()
    return handler._handle_mcp_error(error)


def create_error_response(code: str, message: str, details: Optional[str] = None,
                         category: ErrorCategory = ErrorCategory.SYSTEM) -> ResponseMessage:
    """Create a standardized error response"""
    return ResponseMessage(
        success=False,
        error=f"{code}: {message}",
        data={
            "error_code": code,
            "category": category.value,
            "details": details
        }
    )