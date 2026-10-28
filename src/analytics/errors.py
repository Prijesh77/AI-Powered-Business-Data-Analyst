"""Errors raised by the analytics engine.

Each one carries a message that can be shown to a non-technical user, so the
app can explain a limitation instead of crashing or guessing.
"""


class AnalyticsError(Exception):
    """Base class for all expected analytics errors."""


class MissingColumnError(AnalyticsError):
    """A column needed for the calculation is not in the data or the mapping."""


class InvalidDataError(AnalyticsError):
    """Values in a required column cannot be converted to the expected type."""


class InvalidParameterError(AnalyticsError):
    """A function was called with an unsupported option (e.g. n = 0)."""


class MetricUnavailableError(AnalyticsError):
    """The dataset does not contain the information this metric needs."""
