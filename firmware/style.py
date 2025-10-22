import lvgl as lv

from lv_colors import lv_colors as color

# colors
blue = lv.color_hex(0x0099ff)
red = lv.color_hex(0xff0000)
white = lv.color_hex(0xffffff)
black = lv.color_hex(0x000000)
yellow = lv.color_hex(0xFFFF00)
green = lv.color_hex(0xff0000)
grey = lv.color_hex(0x303a40)
lightblue = lv.color_hex(0x77aaff)

HIDDEN = const(1)

# default styles
s = lv.style_t()
s.set_border_width(0)
s.set_outline_width(0)
s.set_pad_all(0)
s.set_bg_color(black)
s.set_text_color(white)
s.set_radius(0)
s.set_text_align(lv.TEXT_ALIGN.RIGHT)
DEFAULT = s
del(s)

text_line = lv.style_t()
text_line.set_text_align(lv.TEXT_ALIGN.RIGHT)
text_line.set_text_color(white)
text_line.set_border_width(0)
text_line.set_pad_all(0)
text_line.set_pad_right(3)
text_line.set_bg_color(black)
text_line.set_radius(0)

text_selected = lv.style_t()
text_selected.set_text_color(black)
text_selected.set_bg_color(yellow)

text_cursor = lv.style_t()
text_cursor.set_bg_opa(100)
text_cursor.set_border_width(0)
text_cursor.set_outline_width(0)
text_cursor.set_text_color(white)
text_cursor.set_bg_color(blue)

text_focused = lv.style_t()
text_focused.set_radius(0)
text_focused.set_outline_width(0)
text_focused.set_outline_color(black)
text_focused.set_border_width(1)
text_focused.set_border_color(lightblue)
text_focused.set_bg_color(grey)
text_focused.set_text_color(white)
text_focused.set_border_side(lv.BORDER_SIDE.BOTTOM)


def set_style(widget):
    """apply some default styles and flags to a widget"""
    widget.add_flag(widget.FLAG.SCROLL_ON_FOCUS)
    widget.add_flag(widget.FLAG.EVENT_BUBBLE)
    widget.add_style(DEFAULT, lv.PART.MAIN)
    widget.add_style(text_line, lv.PART.MAIN)
    widget.add_style(text_focused, lv.STATE.FOCUSED)
    widget.add_style(text_cursor, lv.PART.CURSOR)

# menus
menu_pages = (
    ('a1','b1','c1','d1'),
    ('a2','b2','c2','d2'),
    ('a3','b3','c3','d3'),
    ('a4','b4','c4','d4'),
)

class Menu:
    def __init__(self, app):
        self.app = app
        self.index = None
        self.pages = [ self.menu_page(menu_items) for menu_items in menu_pages ]

    def menu_page(self, items):
        page = lv.obj()
        page.align(lv.ALIGN.TOP_MID, 0, 2);
        page.set_flex_flow(lv.FLEX_FLOW.ROW);
        page.set_flex_align(lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.END,
                                lv.FLEX_ALIGN.END)
        for i in items:
            self.label(page, i)

        return page

    def active_page(self):
        if self.index is not None:
            return self.pages[self.index]
        else:
            return None

    def show(self, index):
        self.index = index
        lv.screen_load(self.pages[index])

    def hide(self):
        if self.index is not None:
            self.index = None
            lv.screen_load(self.app.scr)

    def label(self, page, text):
        line = lv.label(page)
        #line.set_style_text_font(self.mono_font, 0)
        line.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        line.set_style_text_color(white, lv.PART.SELECTED)
        line.set_style_bg_color(yellow, lv.PART.SELECTED)
        line.set_text(text)
        return line
