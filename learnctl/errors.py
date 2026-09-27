class LearnctlError(Exception):
    """带有 CLI 退出码的预期错误。"""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class DataError(LearnctlError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 3)


class UsageError(LearnctlError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 2)


class BlockedError(LearnctlError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 1)
