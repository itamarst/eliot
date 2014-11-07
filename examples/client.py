"""
Cross-process log tracing: HTTP client.
"""
from __future__ import unicode_literals

import sys
import requests

from eliot import Logger, to_file, start_action
to_file(sys.stdout)
logger = Logger()


def request():
    with start_action(logger, "http_request") as action:
        task_id = action.serialize_task_id()
        response = requests.get("http://localhost:5000/?x=1&y=3",
                                headers={"x-eliot-task-id": task_id})
        action.add_success_fields(response=response.text)


if __name__ == '__main__':
    with start_action(logger, "main"):
        request()
