#!/usr/bin/env python

"""
Link checking: action logging demonstrating the flow of code.
"""

import sys

from lxml import html
import requests


from eliot import start_action, Logger, pretty_print
pretty_print()

_logger = Logger()


def download(url):
    with start_action(_logger, "download", url=url) as action:
        response = requests.get(url)
        response.raise_for_status()
        action.add_success_fields(final_url=response.url)
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
