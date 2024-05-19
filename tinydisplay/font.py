# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
tinyDisplay implementation of BMFONT.

Support pydPiper's (hacked) BMFONT implementation
and multipage (e.g. >256 char) font files

.. versionadded:: 0.0.1
"""

from PIL import Image, ImageFont


def _readGlyphData(fileName):
    def _readGlyphPage(fp, pages, count, glyphs):
        from os.path import dirname

        sketches = {}
        for p, fn in pages.items():
            try:
                sketches[p] = Image.open(fn)
            except FileNotFoundError:
                sketches[p] = Image.open(dirname(fileName) + "/" + fn)
            sketches[p].convert(mode="1")

        i = 0
        for s in fp:
            s = (
                s.strip()
            )  # char id=8 x=48 y=0 width=5 height=8 xoffset=0 yoffset=0 xadvance=5 page=0 chnl=0 # 'x': Lowercase X
            if s == "" or s[0] == "#":
                # Skip empty lines or lines that start with a '#'
                continue
            i += 1
            if i > count:
                break
            db = {
                x: y
                for x, y in (x.split("=") for x in s.split("#")[0].split()[1:])
            }

            w, h, l, d = (
                int(db["width"]),
                int(db["height"]),
                int(db["xoffset"]),
                int(db["yoffset"]),
            )
            x, y = int(db["x"]), int(db["y"])
            dx, dy = int(db["xadvance"]), 0
            try:
                ch = int(db["id"])
            except ValueError:
                ch = int(db["id"], 16)
            p = int(db["page"])

            gImg = sketches[p].crop((x, y, x + w, y + h))

            glyphs[ch] = (dx, dy), (l, -d - h, w + l, -d), (0, 0, w, h), gImg

        return glyphs

    with open(fileName) as fp:
        s = (
            fp.readline()
        )  # info face="upperascii" size=6 bold=0 italic=0 charset="" unicode=1 stretchH=100 smooth=0 aa=1 padding=0,0,0,0 spacing=0,0
        if s[:9] != "info face":
            raise SyntaxError("not a valid BMFONT file")
        s = (
            fp.readline()
        )  # common lineHeight=5 base=6 scaleW=80 scaleH=30 pages=1 packed=0
        lineHeight = int(s.split()[1].split("=")[1])

        glyphs = {}
        pages = {}
        for s in fp:  # page id=0 file="upperasciiwide_3x5.png"
            if s[0:4].lower() == "page":
                pages[int(s.split()[1].split("=")[1])] = (
                    s.split()[2].split("=")[1].strip("\"'")
                )
            else:
                if s[0:5].lower() == "chars":
                    count = int(s.split()[1].split("=")[1])
                break
                raise ValueError(f"Expected chars count line.  Received {s}")

        glyphs = _readGlyphPage(fp, pages, count, glyphs)

    return (lineHeight, glyphs)


class bmImageFont(ImageFont.ImageFont):
    """
    Load BMFONT using a PIL ImageFont style interface.

    Allows a BMFONT to be used anywhere an `PIL.ImageFont` is accepted

    :param fileName: the name of the file containing the BMFONT
    :type fileName: str
    :param defaultChar: Character to display if a glyph is requested that
        does not exist in the font
    :type defaultChar: str
    """

    def __init__(self, fileName, defaultChar=" ", *args, **kwargs):
        self._defaultChar = defaultChar
        self._load(fileName, **kwargs)
        self.font = self

    def _load(self, fileName, *args, **kwargs):
        self.lineHeight, self.tdGlyphs = _readGlyphData(fileName)
        self.xadvance = kwargs["xadvance"] if "xadvance" in kwargs else None

    def getsize(self, text, *args, **kwargs):
        """
        Get the size that the rendered text will require.

        :param text: The text value to measure
        :type text: str
        :param args:  Any extra arguments
        :type args: tuple
        :param kwargs: Any extra arguments
        :type kwargs: dict
        :returns: The size in pixels (x, y)
        :rtype: (int, int)

        ..note:
            The `PIL.ImageFont.getsize` method uses more than one version of
            getsize but bmImageFont.getsize only requires the text argument.  The
            inclusion of args and kwargs is to prevent an exception if getsize
            is passed arguments that it does not need.
        """
        xsize = xLineSize = 0
        ysize = yLineSize = 0

        for line in text.split("\n"):
            xLineSize = 0
            yLineSize = self.lineHeight
            for s in line:
                i = (
                    ord(s)
                    if ord(s) in self.tdGlyphs
                    else ord(self._defaultChar)
                )
                xLineSize += (
                    self.xadvance if self.xadvance else self.tdGlyphs[i][0][0]
                )
                yLineSize = max(yLineSize, self.tdGlyphs[i][2][3])
            xsize = max(xsize, xLineSize)
            ysize += yLineSize
        return (xsize, ysize)

    def getmask(self, text, mode="1", *args, **kwargs):
        """
        Get the mask for the image that results from rendering the text input.

        :param text: The text to render
        :type text: str
        :param mode: The image mode to use for the returned mask (default "1")
        :type mode: str
        :param args:  Any extra arguments
        :type args: tuple
        :param kwargs: Any extra arguments
        :type kwargs: dict
        :returns: the rendered mask
        :rtype: `PIL.Image.im`

        ..note:
            The `PIL.ImageFont.getmask` method uses more than one version of getmask
            but bmImageFont.getmask only requires the text and mode arguments.  The
            inclusion of args and kwargs is to prevent an exception if getmask is passed arguments that it does not need.
        """
        img = Image.new(mode, self.getsize(text))
        yp = 0
        for line in text.split("\n"):
            ls = self.getsize(line)
            xp = 0
            yp += ls[1]
            for s in line:
                i = (
                    ord(s)
                    if ord(s) in self.tdGlyphs
                    else ord(self._defaultChar)
                )
                img.paste(
                    self.tdGlyphs[i][3],
                    (xp + self.tdGlyphs[i][1][0], yp + self.tdGlyphs[i][1][1]),
                )
                xp += (
                    self.xadvance if self.xadvance else self.tdGlyphs[i][0][0]
                )
        img.load()
        self.gmImage = img
        return img.im
