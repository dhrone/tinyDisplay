#!/usr/bin/env python3

import cProfile
import io
import logging
import pstats
import timeit
from pathlib import Path

from PIL import Image, ImageFont

from tinyDisplay.render.collection import canvas, index, sequence, stack
from tinyDisplay.render.profileWidget import profileText
from tinyDisplay.render.widget import rectangle, text
from tinyDisplay.utility import dataset

# Setup logger
logger = logging.getLogger("tinyDisplay")

canvases = []
stacks = []
indexes = []
sequences = []


def make_canvases():
    """Make canvases to profile."""

    global canvases

    for i in range(10):
        c = canvas(name=f"sample {i}", dataset=None, size=(64, 32))
        c.place(rectangle(size=(64, 32), fill=128))
        c.place(rectangle(size=(60, 28), offset=(2, 2), fill=255))
        c.place(text(size=(60, 10), offset=(2, 2), text=f"This is line {i}"))
        c.place(
            text(
                size=(60, 10),
                offset=(2, 12),
                text="This is another line",
                font="FreeSans.ttf",
                fontsize=10,
            )
        )
        canvases.append(c)


def make_stacks():
    """Make stacks with canvases to profile."""

    global stacks

    i = index(dataset=None, active=0)
    i.append(canvases[0])
    i.append(canvases[1])
    i.append(canvases[2])
    i.append(canvases[3])

    s = stack(dataset=None)
    s.append(canvases[0])
    s.append(canvases[1], showIf=False)
    s.append(canvases[2], showIf=True)
    s.append(canvases[3], showIf=False)

    stacks.append(s)


def make_indexes():
    """Make indexes with canvases to profile."""

    global indexes

    i = index(dataset=None, active=0)
    i.append(canvases[0])
    i.append(canvases[1])
    i.append(canvases[2])
    i.append(canvases[3])

    indexes.append(i)


def make_sequences():
    """Make sequences with canvases to profile."""

    global sequences

    s = sequence(dataset=None, duration=10)
    s.append(canvases[0], duration=2)
    s.append(canvases[1], duration=3)
    s.append(canvases[2], duration=4, showIf="True")
    s.append(canvases[3], duration=5, showIf="False")

    sequences.append(s)


def main():
    """Profile collection rendering."""
    logger.info("Starting profiling...")

    make_canvases()

    logger.info("\nProfiling canvas operations...")
    cProfile.run("canvases[0].render()", "canvas.prof")
    s = io.StringIO()
    ps = pstats.Stats("canvas.prof", stream=s).sort_stats("cumtime")
    ps.print_stats()
    print(s.getvalue())

    logger.info("\nProfiling stack operations...")
    make_stacks()
    cProfile.run("stacks[0].render()", "stack.prof")
    s = io.StringIO()
    ps = pstats.Stats("stack.prof", stream=s).sort_stats("cumtime")
    ps.print_stats()
    print(s.getvalue())

    logger.info("\nProfiling index operations...")
    make_indexes()
    cProfile.run("indexes[0].render()", "index.prof")
    s = io.StringIO()
    ps = pstats.Stats("index.prof", stream=s).sort_stats("cumtime")
    ps.print_stats()
    print(s.getvalue())

    logger.info("\nProfiling sequence operations...")
    make_sequences()
    cProfile.run("sequences[0].render()", "sequence.prof")
    s = io.StringIO()
    ps = pstats.Stats("sequence.prof", stream=s).sort_stats("cumtime")
    ps.print_stats()
    print(s.getvalue())


if __name__ == "__main__":
    main()
