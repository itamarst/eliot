"""
Cross-process log tracing: HTTP server.
"""
from __future__ import unicode_literals

import sys
from flask import Flask, request

from eliot import Logger, to_file, Action, start_action
to_file(sys.stdout)
logger = Logger()


app = Flask("server")


def divide(x, y):
    with start_action(logger, "divide", x=x, y=y) as action:
        result = x / y
        action.add_success_fields(result=result)
        return result


@app.route("/")
def main():
    with Action.continue_task(logger, request.headers["x-eliot-task-id"]):
        x = int(request.args["x"])
        y = int(request.args["y"])
        return str(divide(x, y))


if __name__ == '__main__':
    app.run()
