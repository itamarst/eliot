"""
Cross-process log tracing: HTTP client.
"""
from __future__ import unicode_literals

import sys
import requests

from eliot import Logger, to_file, start_task
to_file(sys.stdout)
logger = Logger()


def main():
    with start_task(logger, "http_request") as action:
        task_id = action.serialize_task_id()
        response = requests.get("http://localhost:1234/",
                                headers={"x-eliot-task-id": task_id})
        action.add_success_fields(response=response)


if __name__ == '__main__':
    main()
