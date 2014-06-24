# -*- coding: utf-8 -*-


def get_failure_message(failure):
    """
    Try to get unicode representation of message about failure.
    """
    value = failure.value
    try:
        return unicode(value)
    except UnicodeDecodeError:
        return unicode(value.__doc__
                       or value.__class__.__name__
                       or value.osError)
