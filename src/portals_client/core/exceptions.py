class PortalsError(Exception):
    """Base exception for Portals Finance client"""
    pass

class PortalsAPIError(PortalsError):
    """API request errors"""
    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class RateLimitError(PortalsAPIError):
    """Rate limiting errors"""
    pass

class ValidationError(PortalsError):
    """Input validation errors"""
    pass

class InsufficientBalanceError(PortalsError):
    """Insufficient balance for transaction"""
    pass

class TransactionError(PortalsError):
    """Transaction execution errors (on-chain or signing issues)"""
    def __init__(self, message, tx_hash=None, receipt=None):
        super().__init__(message)
        self.tx_hash = tx_hash
        self.receipt = receipt

class ConfigurationError(PortalsError):
    """Errors related to SDK configuration"""
    pass 