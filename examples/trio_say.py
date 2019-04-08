from eliot import start_action, to_file
import trio

to_file(open("trio.log", "w"))


async def say(message, delay):
    with start_action(action_type="say", message=message):
        await trio.sleep(delay)

async def main():
    async with trio.open_nursery() as nursery:
        with start_action(action_type="main"):
            nursery.start_soon(say, "hello", 1)
            nursery.start_soon(say, "world", 0.5)

trio.run(main)
