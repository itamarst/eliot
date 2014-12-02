"""
Cross-process log tracing: HTTP client.
"""
from __future__ import unicode_literals

import sys
import requests

from eliot import Logger, to_file, start_action
to_file(sys.stdout)
logger = Logger()


def remote_divide(x, y):
    with start_action(logger, "http_request", x=x, y=y) as action:
        task_id = action.serialize_task_id()
        response = requests.get(
            "http://localhost:5000/?x={}&y={}".format(x, y),
            headers={"x-eliot-task-id": task_id})
        response.raise_for_status()  # ensure this is a successful response
        result = float(response.text)
        action.add_success_fields(result=result)
        return result


if __name__ == '__main__':
    with start_action(logger, "main"):
        remote_divide(int(sys.argv[1]), int(sys.argv[2]))
