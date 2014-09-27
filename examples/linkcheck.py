#!/usr/bin/env python

"""
Link checking: action logging demonstrating the flow of code.
"""

import sys
import json

from lxml import html
import requests


from eliot import start_action, Logger, add_destination

add_destination(lambda message: sys.stdout.write(json.dumps(message) + "\n"))
_logger = Logger()


def download(url):
    with start_action(_logger, "download", url=url):
        response = requests.get(url)
        response.raise_for_status()
        return response


def check_links(url):
    """Return dictionary of bad links in given HTML page."""
    with start_action(_logger, "check_links", url=url):
        response = download(url)
        bad_links = {}
        document = html.fromstring(response.text)
        document.make_links_absolute(response.url)
        for _, _, linked_url, _ in document.iterlinks():
            try:
                download(linked_url)
            except Exception as e:
                bad_links[linked_url] = e
        return bad_links


if __name__ == '__main__':
    check_links(sys.argv[1])
