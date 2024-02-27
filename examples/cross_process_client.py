"""
Cross-process log tracing: HTTP client.
"""

import sys
import requests

from eliot import to_file, start_action, add_global_fields
add_global_fields(process="client")
to_file(sys.stdout)


def remote_divide(x, y):
    with start_action(action_type="http_request", x=x, y=y) as action:
        task_id = action.serialize_task_id()
        response = requests.get(
            "http://localhost:5000/?x={}&y={}".format(x, y),
            headers={"x-eliot-task-id": task_id})
        response.raise_for_status()  # ensure this is a successful response
        result = float(response.text)
        action.add_success_fields(result=result)
        return result


if __name__ == '__main__':
    with start_action(action_type="main"):
        remote_divide(int(sys.argv[1]), int(sys.argv[2]))
