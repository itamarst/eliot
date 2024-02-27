"""
Cross-process log tracing: HTTP server.
"""

import sys
from flask import Flask, request

from eliot import to_file, Action, start_action, add_global_fields
add_global_fields(process="server")
to_file(sys.stdout)


app = Flask("server")


def divide(x, y):
    with start_action(action_type="divide", x=x, y=y) as action:
        result = x / y
        action.add_success_fields(result=result)
        return result


@app.route("/")
def main():
    with Action.continue_task(task_id=request.headers["x-eliot-task-id"]):
        x = int(request.args["x"])
        y = int(request.args["y"])
        return str(divide(x, y))


if __name__ == '__main__':
    app.run()
