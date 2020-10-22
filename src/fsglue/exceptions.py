
class FsglueException(Exception):
    """BaseException"""
    pass


class FsglueValidationError(FsglueException):
    pass


class FsglueProgrammingError(FsglueException):
    pass
