tinyDisplay
-----------
**A widget library and window manager for small displays**

Python 3 library to simply the development of applications intended to drive
small displays such as the HD44780, WEH001602A, SSD1306.  Any display that you
can update with a PIL.Image input is supported.

It supports a collection of widgets including:

* text and staticText
* progressBar
* image
* line and rectangle
* slide, scroll and popUp

And a set of collection classes to organize the widgets into useful screens:

* canvas -- For designing a collection of widgets to display together
* sequence -- For rotating through a set of canvases
* windows -- For displaying a set of canvases simultaneously on a display
