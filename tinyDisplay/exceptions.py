"""TinyDisplay Exceptions module."""


class Error(Exception):
    """Main error class for tinyDisplay."""

    pass


class NoChangeToValue(Error):
    """Used to indicate that onUpdate did not update the current Value of the attribute."""

    pass


class DataError(Error):
    """Base Database Error class."""

    pass


class UpdateError(DataError):
    """Error when updating a database within a dataset fails."""

    pass


class CompileError(DataError):
    """Error when compiling a dynamic variable."""

    pass


class ValidationError(DataError):
    """Error validating a data value during an update."""

    pass
