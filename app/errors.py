"""Small app-specific exception used for business-rule failures.

Kept separate from Pydantic's RequestValidationError so routers can raise
one consistent error type for anything that isn't a shape/type problem
(e.g. "Incorrect admin PIN", "Code not recognised").
"""


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
