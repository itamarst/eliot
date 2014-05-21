# Copyright Hybrid Logic Ltd.  See LICENSE file for details.
"""
Download a URL and log information about the response.
"""
import sys
from pprint import pprint

from twisted.internet import task
from twisted.web import client, http
from twisted.python.util import FancyStrMixin

from eliot import startAction, Logger, addDestination, writeFailure
from eliot.twisted import DeferredContext

def _pprint(message):
    pprint(message)
    print '\n\n\n'

addDestination(_pprint)


_logger = Logger()


class UnexpectedResponse(FancyStrMixin, Exception):
    """
    Response code was not 200
    """
    showAttributes = ('code',)

    def __init__(self, code):
        self.code = code


def _checkStatus(response):
    """
    Raise an exception if the response code is not OK. The exception will be
    logged.
    """
    if response.code != http.OK:
        raise UnexpectedResponse(response.code)
    return response


def _logResponse(response, log):
    """
    Add HTTP header information to the success log.
    """
    log.addSuccessFields(headers=response.headers)
    return response


def _logBody(body, log):
    """
    Add a snippet of the response body to the success log.
    """
    log.addSuccessFields(body=body[:100])


def main(reactor, url):
    """
    Download a URL, check and log the response.
    """
    log = startAction(_logger, u'twisted_actions:main')
    agent = client.Agent(reactor)
    d = agent.request('GET', url)
    with log.context():
        d = DeferredContext(d)
        d.addCallback(_checkStatus)
        d.addCallback(_logResponse, log)
        d.addCallback(client.readBody)
        d.addCallback(_logBody, log)
        d.addErrback(writeFailure, _logger, u'twisted_actions:main')
        d.addActionFinish()
    return d.result


if __name__ == '__main__':
    task.react(main, sys.argv[1:])
