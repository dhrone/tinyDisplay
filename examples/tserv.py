#!/usr/bin/env python

import argparse
import json
import logging
import webbrowser
from io import BytesIO
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from time import monotonic, sleep, time

from flask import Flask, Response, render_template
from PIL import Image, ImageDraw, ImageFont
from pyattention.collection import collection
from pyattention.media import volumio
from pyattention.source import rss, system

from tinyDisplay import setup_logging
from tinyDisplay.cfg import _tdLoader, load
from tinyDisplay.exceptions import NoResult
from tinyDisplay.render.collection import canvas, index, stack
from tinyDisplay.render.widget import image, text
from tinyDisplay.utility import animate, dataset

# Parse command line arguments
parser = argparse.ArgumentParser(description="tinyDisplay web server")
parser.add_argument(
    "--log-level", 
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default="INFO",
    help="Set the logging level"
)
parser.add_argument(
    "--log-file",
    help="Path to log file (logs to console if not specified)"
)
args = parser.parse_args()

# Setup logger
log_level = getattr(logging, args.log_level)
logger = setup_logging(log_level=log_level, log_file=args.log_file)

app = Flask(__name__)


def get_pil_image_data(im):
    b = BytesIO()
    im.save(b, format="jpeg")
    return b.getvalue()


def create_frame(a):
    while True:
        if not a.running:
            break
        img = a.get(10)
        if img is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + img + b"\r\n"
            )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    ma.start()
    return Response(
        create_frame(ma), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


class MakeAnimation:
    def __init__(
        self, pageFile, fps=30, resize=1, dataQ=None, debug=False, demo=False
    ):
        self.fps = fps
        self.resize = resize
        self._pageFile = pageFile
        self._main = load(pageFile, debug=debug, demo=demo)
        self._animate = animate(cps=fps, function=self.render, queueSize=100)
        logger.debug(f"animate started with {self._animate._speed}")
        self._dataQ = dataQ
        self._rc = 0

    def start(self):
        if "_started" not in dir(self):
            self._animate.start()
            self._started = True

    def stop(self):
        self._animate.stop()

    def reset(self, debug=False, demo=False):
        self._animate.pause()
        self._main = load(self._pageFile, debug=debug, demo=demo)
        self._animate.restart()

    def get(self, wait):
        return self._animate.get(wait)

    @property
    def dataset(self):
        return self._main._dataset

    @property
    def running(self):
        return self._animate._running

    def render(self):
        data_expectation = 0.1
        render_expectation = 0.1
        self._timer = monotonic()
        self._renderTime = self._timer
        if self._dataQ is not None:
            # Wait up to 1/10 of a second to get new data
            new_data = []
            while True:
                data = self._dataQ.get(0.01)
                if data is None:
                    break
                new_data.append(data)

            for ditem in new_data:
                if "vol" in ditem:
                    if "pushQueue" in ditem["vol"]:
                        self._main._dataset.update(
                            "pl", {"playlist": ditem["vol"]["pushQueue"]}
                        )
                    if "pushState" in ditem["vol"]:
                        # logger.debug(f"RECEIVED\n========\n{json.dumps(v, indent=4)}")
                        self._main._dataset.update(
                            "db", ditem["vol"]["pushState"]
                        )
                if "sys" in ditem:
                    self._main._dataset.update("sys", ditem["sys"])

                if "wea" in ditem:
                    if "data" in ditem["wea"]:
                        if len(ditem["wea"]["data"]) == 4:
                            # Got expected data
                            wd = {
                                "current": ditem["wea"]["data"][0],
                                "today": ditem["wea"]["data"][1],
                                "tomorrow": ditem["wea"]["data"][2],
                            }
                            self._main._dataset.update("wea", wd)

                        else:
                            logger.warning(
                                f"Weather: Expected four data elements: {len(ditem['wea'])}"
                            )
                    else:
                        logger.warning(
                            f"Weather: Received message but no data: {ditem['wea']}"
                        )

        self._renderTime = monotonic()
        self._rc += 1
        if self._rc % 600 == 0:  # Once per minute
            mt = monotonic()
            logger.debug(
                f"Render #{self._rc}: loop time {mt-self._timer:.3f}  queue size {self._animate.qsize}"
            )
            logger.debug("==============================================")
            logger.debug("=                 CURRENT DATA               =")
            logger.debug("==============================================")
            logger.debug(f"{json.dumps(self._main._dataset.db, indent=4)}")
            logger.debug(f"========\n{json.dumps(self._main._dataset.wea, indent=4)}")
            logger.debug(f"========\n{json.dumps(self._main._dataset.sys, indent=4)}")
            logger.debug("==============================================")
            self._timer = mt
        img = self._main.render()[0]
        result = None
        if img is not None:
            if img.mode != "RGB":
                img = img.convert("RGB")
            if self.resize != 1:
                img = img.resize(
                    (img.size[0] * self.resize, img.size[1] * self.resize)
                )
                result = get_pil_image_data(img)

        return result


if __name__ == "__main__":
    logger.info("Starting tinyDisplay server")
    
    pf = "tests/reference/pageFiles/sampleMedia.yaml"
    fps = 10
    resize = 2
    col = collection()
    srcV = volumio("http://volumio.local", loop=col.tloop)
    srcS = system(loop=col.tloop)
    srcW = rss(
        "http://rss.accuweather.com/rss/liveweather_rss.asp?locCode=18-327659_1_al",
        loop=col.tloop,
        frequency=7200,
    )  # Poll 4x per day
    col.register("vol", srcV)
    col.register("sys", srcS)
    col.register("wea", srcW)
    
    logger.info(f"Loading page file: {pf}")
    ma = MakeAnimation(pf, fps=fps, resize=resize, dataQ=col, debug=True)
    
    logger.info("Starting web server")
    Thread(target=lambda: app.run(host="0.0.0.0", debug=False)).start()
    
    webbrowser.get("open -a /Applications/Google\ Chrome.app %s").open(
        "http://localhost:5000"
    ) 