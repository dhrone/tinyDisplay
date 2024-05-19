"""TinyDisplay Exceptions module."""


class Error(Exception):
    """Main error class for tinyDisplay."""

    pass


class NoChangeToValue(Error):
    """Used to indicate that onUpdate did not update the current Value of the attribute."""

    pass


class NoResult(Error):
    """Used to indicate that the the function being animated did not provide output."""

    pass


class RenderError(Error):
    """Used when render does not success."""

    pass


class DataError(Error):
    """Base Database Error class."""

    pass


class UpdateError(DataError):
    """Error when updating a database within a dataset fails."""

    pass


class CompileError(DataError):
    """Error when compiling a dynamicValue."""

    pass


class EvaluationError(DataError):
    """Error when evaluating a dynamicValue."""

    pass


class ValidationError(DataError):
    """Error validating a data value during an update."""

    pass


class RegistrationError(DataError):
    """Error registering a validation rule."""

    pass
