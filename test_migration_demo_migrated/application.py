# Generated tinyDisplay DSL Application
# Auto-generated from legacy system analysis

from tinydisplay import *
from tinydisplay.reactive import reactive, computed, pipe
from tinydisplay.data import DataSource

# Widget Definitions
widget_test = Text("Text").position(0, 0).z_order(0)
widget_test = Text("Text").position(0, 0).z_order(0)

# Application Setup
def create_application():
    app = Application()
    canvas = Canvas(800, 600)

    canvas.add(widget_test)
    canvas.add(widget_test)

    app.add_canvas(canvas)
    return app

if __name__ == '__main__':
    app = create_application()
    app.run()