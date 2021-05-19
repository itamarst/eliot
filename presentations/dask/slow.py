from eliot import log_call, to_file
import sys
to_file(open("out.log", "w"))

@log_call
def double(a):
    if a == 0:
        import time
        time.sleep(10)
    return a * 2

@log_call
def main():
    double(13)
    double(0)
    double(4)

main()
