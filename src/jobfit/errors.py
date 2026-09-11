"""Structured application failures."""


class JobFitError(Exception):
    """Base class for expected failures."""


class InputError(JobFitError):
    """Invalid user input."""


class SourceError(JobFitError):
    """A job source could not return a usable public document."""


class AccessRestrictedError(SourceError):
    """The source presented an authentication, CAPTCHA, or access wall."""


class ParseError(JobFitError):
    """A document did not contain a usable job posting."""


class ConfigurationError(JobFitError):
    """Invalid profile or rule configuration."""

