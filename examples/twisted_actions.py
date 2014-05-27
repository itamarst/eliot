# Copyright Hybrid Logic Ltd.  See LICENSE file for details.
"""
Download a URL and log information about the response.
"""
from __future__ import absolute_import, division, print_function
import sys
from pprint import pprint

from twisted.internet import task
from twisted.web import client, http
from twisted.python.util import FancyStrMixin

from eliot import startAction, Logger, addDestination, writeFailure
from eliot.twisted import DeferredContext

def printMessage(message):
    pprint(message)
    print('\n\n\n')

addDestination(printMessage)


_logger = Logger()


class UnexpectedHTTPResponse(FancyStrMixin, Exception):
    """
    Response code was not 200
    """
    showAttributes = ('code',)

    def __init__(self, code):
        self.code = code


def checkStatus(response):
    """
    Raise an exception if the response code is not OK. The exception will be
    logged.
    """
    if response.code != http.OK:
        raise UnexpectedHTTPResponse(response.code)
    return response


def logResponse(response, log):
    """
    Add HTTP header information to the success log.
    """
    log.addSuccessFields(headers=response.headers)
    return response


def logBody(body, log):
    """
    Add a snippet of the response body to the success log.
    """
    log.addSuccessFields(body=body[:100])


def main(reactor, url):
    """
    Download a URL, check and log the response.
    """
    action = startAction(_logger, u'twisted_actions:main')
    agent = client.Agent(reactor)
    d = agent.request('GET', url)
    with action.context():
        d = DeferredContext(d)
        d.addCallback(checkStatus)
        d.addCallback(logResponse, action)
        d.addCallback(client.readBody)
        d.addCallback(logBody, action)
        def writeAndReturnFailure(failure, logger, system):
            try:
                failure.trap(UnexpectedHTTPResponse)
            except:
                writeFailure(failure, logger, system)
            return failure
        d.addErrback(writeAndReturnFailure, _logger, u'twisted_actions:main')
        d.addActionFinish()
    return d.result


if __name__ == '__main__':
    task.react(main, sys.argv[1:])
