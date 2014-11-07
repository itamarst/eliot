"""
Cross-process log tracing: HTTP server.
"""
from __future__ import unicode_literals

import sys
from flask import Flask, request

from eliot import Logger, to_file, Action, Message
to_file(sys.stdout)
logger = Logger()


app = Flask("server")

@app.route("/")
def main():
    with Action.deserialize(request.headers["x-eliot-task-id"]):
        Message.new(message_type="got_request").write(logger)
        return "the result"


if __name__ == '__main__':
    app.run()
