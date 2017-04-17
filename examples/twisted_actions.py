# Copyright Hybrid Logic Ltd.  See LICENSE file for details.
"""
Download a URL and log information about the response.
"""
from __future__ import absolute_import, division, print_function
import sys
from pprint import pprint

from twisted.internet import task
from twisted.web import client, http
from twisted.python import failure, util

from eliot import startAction, Logger, addDestination, writeFailure
from eliot.twisted import DeferredContext

def printMessage(message):
    pprint(message)
    print('\n\n\n')

addDestination(printMessage)


logger = Logger()


class UnhandledHTTPResponse(util.FancyStrMixin, Exception):
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
        raise UnhandledHTTPResponse(response.code)
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



def writeAndReturnFailure(failure, logger, system):
    """
    Log a full traceback for unexpected exceptions. Things like DNS lookup
    errors or TimeoutErrors.
    """
    try:
        failure.trap(UnhandledHTTPResponse)
    except:
        writeFailure(failure, logger, system)
    return failure



def main(reactor, url):
    """
    Download a URL, check and log the response.
    """
    action = startAction(logger, u'twisted_actions:main')
    with action.context():
        agent = client.Agent(reactor)
        d = agent.request('GET', url)
        dc = DeferredContext(d)
        dc.addCallback(checkStatus)
        dc.addCallback(logResponse, action)
        dc.addCallback(client.readBody)
        dc.addCallback(logBody, action)
        dc.addErrback(writeAndReturnFailure, logger, u'twisted_actions:main')
        dc.addActionFinish()

    # Exit with status code 1 if there are errors.
    d.addErrback(lambda e: failure.Failure(SystemExit(1)))
    return d


if __name__ == '__main__':
    raise SystemExit(task.react(main, sys.argv[1:]))
