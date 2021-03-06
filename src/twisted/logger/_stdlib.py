# -*- test-case-name: twisted.logger.test.test_stdlib -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Integration with Python standard library logging.
"""

import logging as stdlibLogging

from zope.interface import implementer

from twisted.python.compat import currentframe
from ._levels import LogLevel
from ._format import formatEvent
from ._observer import ILogObserver



# Mappings to Python's logging module
toStdlibLogLevelMapping = {
    LogLevel.debug: stdlibLogging.DEBUG,
    LogLevel.info: stdlibLogging.INFO,
    LogLevel.warn: stdlibLogging.WARNING,
    LogLevel.error: stdlibLogging.ERROR,
    LogLevel.critical: stdlibLogging.CRITICAL,
}

def _reverseLogLevelMapping():
    """
    Reverse the above mapping, adding both the numerical keys used above and
    the corresponding string keys also used by python logging.
    @return: the reversed mapping
    """
    mapping = {}
    for logLevel, pyLogLevel in toStdlibLogLevelMapping.items():
        mapping[pyLogLevel] = logLevel
        mapping[stdlibLogging.getLevelName(pyLogLevel)] = logLevel
    return mapping

fromStdlibLogLevelMapping = _reverseLogLevelMapping()



@implementer(ILogObserver)
class STDLibLogObserver:
    """
    Log observer that writes to the python standard library's C{logging}
    module.

    @note: Warning: specific logging configurations (example: network) can lead
        to this observer blocking.  Nothing is done here to prevent that, so be
        sure to not to configure the standard library logging module to block
        when used in conjunction with this module: code within Twisted, such as
        twisted.web, assumes that logging does not block.

    @cvar defaultStackDepth: This is the default number of frames that it takes
        to get from L{STDLibLogObserver} through the logging module, plus one;
        in other words, the number of frames if you were to call a
        L{STDLibLogObserver} directly.  This is useful to use as an offset for
        the C{stackDepth} parameter to C{__init__}, to add frames for other
        publishers.
    """

    defaultStackDepth = 4

    def __init__(self, name="twisted", stackDepth=defaultStackDepth):
        """
        @param loggerName: logger identifier.
        @type loggerName: C{str}

        @param stackDepth: The depth of the stack to investigate for caller
            metadata.
        @type stackDepth: L{int}
        """
        self.logger = stdlibLogging.getLogger(name)
        self.logger.findCaller = self._findCaller
        self.stackDepth = stackDepth


    def _findCaller(self, stackInfo=False, stackLevel=1):
        """
        Based on the stack depth passed to this L{STDLibLogObserver}, identify
        the calling function.

        @param stackInfo: Whether or not to construct stack information.
            (Currently ignored.)
        @type stackInfo: L{bool}

        @param stackLevel: The number of stack frames to skip when determining
            the caller (currently ignored; use stackDepth on the instance).
        @type stackLevel: L{int}

        @return: Depending on Python version, either a 3-tuple of (filename,
            lineno, name) or a 4-tuple of that plus stack information.
        @rtype: L{tuple}
        """
        f = currentframe(self.stackDepth)
        co = f.f_code
        extra = (None,)
        return (co.co_filename, f.f_lineno, co.co_name) + extra


    def __call__(self, event):
        """
        Format an event and bridge it to Python logging.
        """
        level = event.get("log_level", LogLevel.info)
        failure = event.get('log_failure')
        if failure is None:
            excInfo = None
        else:
            excInfo = (
                failure.type, failure.value, failure.getTracebackObject())
        stdlibLevel = toStdlibLogLevelMapping.get(level, stdlibLogging.INFO)
        self.logger.log(
            stdlibLevel, StringifiableFromEvent(event), exc_info=excInfo)



class StringifiableFromEvent:
    """
    An object that implements C{__str__()} in order to defer the work of
    formatting until it's converted into a C{str}.
    """
    def __init__(self, event):
        """
        @param event: An event.
        @type event: L{dict}
        """
        self.event = event


    def __unicode__(self):
        return formatEvent(self.event)


    def __bytes__(self):
        return str(self).encode("utf-8")

    __str__ = __unicode__
