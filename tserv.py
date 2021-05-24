#!/usr/bin/env python

import webbrowser
from io import BytesIO
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from time import sleep, time

from flask import Flask, Response, render_template
from PIL import Image, ImageDraw, ImageFont

from tinyDisplay.cfg import _tdLoader, load
from tinyDisplay.render.collection import canvas, index, stack
from tinyDisplay.render.widget import image, text
from tinyDisplay.utility import animate, dataset


app = Flask(__name__)


def get_pil_image_data(im):
    b = BytesIO()
    im.save(b, format="jpeg")
    return b.getvalue()


def create_frame(a):
    while True:
        if not a.running:
            break
        img = a.get(1)
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
    def __init__(self, pageFile, fps=30, resize=1):
        self.fps = fps
        self.resize = resize
        self._main = load(pageFile, demo=True)
        self._animate = animate(cps=fps, function=self.render, queueSize=100)

    def start(self):
        self._animate.start()

    def stop(self):
        self._animate.stop()

    def get(self, wait):
        return self._animate.get(wait)

    @property
    def dataset(self):
        return self._main._dataset

    @property
    def running(self):
        return self._animate._running

    def render(self):
        img = self._main.render()[0]
        if img is not None:
            if img.mode != "RGB":
                img = img.convert("RGB")
            if self.resize != 1:
                img = img.resize(
                    (img.size[0] * self.resize, img.size[1] * self.resize)
                )
                return get_pil_image_data(img)
        else:
            return None


pf = "tests/reference/pageFiles/sampleMedia.yaml"
fps = 15
resize = 2
ma = MakeAnimation(pf, fps, resize)

Thread(target=lambda: app.run(host="0.0.0.0", debug=False)).start()

webbrowser.get("open -a /Applications/Google\ Chrome.app %s").open(
    "http://localhost:5000"
)
