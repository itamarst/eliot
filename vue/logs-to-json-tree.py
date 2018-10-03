from json import loads, dumps
from sys import stdin, stdout
from eliot._parse import Parser, WrittenAction
from eliot.prettyprint import pretty_format

def get_messages():
    for line in stdin:
        yield loads(line)


def to_json(obj):
    if isinstance(obj, WrittenAction):
        start = obj.start_message.as_dict()
        return {
            "name": start["action_type"],
            "body": pretty_format(start),
            "children": [to_json(o) for o in obj.children] + [{
                "name": "Result",
                "body": pretty_format(obj.end_message.as_dict()),
            }]
        }
    else:
        obj = obj.as_dict()
        return {
            "name": obj["message_type"],
            "body": pretty_format(obj)
        }


def main():
    for task in Parser.parse_stream(get_messages()):
        json_tree = to_json(task.root())
        stdout.write(dumps(json_tree))
        stdout.flush()
        break


if __name__ == '__main__':
    main()
