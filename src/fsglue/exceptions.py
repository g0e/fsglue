class FsglueException(Exception):
    """Common base exception"""

    pass


class FsglueValidationError(FsglueException):
    """Error caused by invalid input"""

    pass


class FsglueProgrammingError(FsglueException):
    """Error caused by misuse of fsglue"""

    pass
