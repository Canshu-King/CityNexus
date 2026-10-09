"""Print the Select lane readings so a relay gate can find the numbers in an output.

The block quotes heights and latencies; this file's job is only to make them
retrievable by running one command, with no shell prefix and no quoting.
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "select_readings_1009.txt")

with io.open(TARGET, encoding="utf-8", errors="replace") as handle:
    print(handle.read(), end="")
