import curses
import curses.textpad
import json


class Screen(object):
    UP = -1
    DOWN = 1

    def __init__(self, items):
        """ Initialize the screen window

        Attributes
            window: A full curses screen window

            width: The width of `window`
            height: The height of `window`

            max_lines: Maximum visible line count for `result_window`
            top: Available top line position for current page (used on scrolling)
            bottom: Available bottom line position for whole pages (as length of items)
            current: Current highlighted line number (as window cursor)
            page: Total page count which being changed corresponding to result of a query (starts from 0)

            ┌--------------------------------------┐
            |1. Item                               |
            |--------------------------------------| <- top = 1
            |2. Item                               |
            |3. Item                               |
            |4./Item///////////////////////////////| <- current = 3
            |5. Item                               |
            |6. Item                               |
            |7. Item                               |
            |8. Item                               | <- max_lines = 7
            |--------------------------------------|
            |9. Item                               |
            |10. Item                              | <- bottom = 10
            |                                      |
            |                                      | <- page = 1 (0 and 1)
            └--------------------------------------┘

        Returns
            None
        """
        self.window = None

        self.width = 0
        self.height = 0

        self.init_curses()

        self.items = items
        self.backup = None
        self.item = -1

        self.max_lines = curses.LINES
        self.top = 0
        self.bottom = len(self.items)
        self.current = 0
        self.page = self.bottom // self.max_lines

    def init_curses(self):
        """Setup the curses"""
        self.window = curses.initscr()
        self.window.keypad(True)

        curses.noecho()
        curses.cbreak()

        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        self.current = curses.color_pair(2)

        self.height, self.width = self.window.getmaxyx()

    def run(self):
        """Continue running the TUI until get interrupted"""
        try:
            self.input_stream()
        except KeyboardInterrupt:
            pass
        finally:
            curses.endwin()

    def get_input(self, current_value="", title="Value"):
        # Calculate the dimensions to center the new window
        rows = curses.LINES
        cols = curses.COLS
        prompt_window_height = 3
        prompt_window_width = int(cols / 3)
        prompt_window_y = int(rows / 2) - int(prompt_window_height / 2)
        prompt_window_x = int(cols / 2) - int(prompt_window_width / 2)

        # Create the window to show the surrounding border
        prompt_window_border = curses.newwin(
            prompt_window_height, prompt_window_width, prompt_window_y, prompt_window_x)
        prompt_window_border.box()
        prompt_window_border.addstr(0, 1, " " + title + " ")
        prompt_window_border.refresh()

        # Create the innder window to accept user input
        curses.curs_set(1)
        prompt_window_input = curses.newwin(
            prompt_window_height - 2, prompt_window_width - 2, prompt_window_y + 1, prompt_window_x + 1)
        prompt_window_input.addstr(str(current_value))
        prompt_window_text_box = curses.textpad.Textbox(
            prompt_window_input, insert_mode=True)
        prompt_window_text_box.edit()
        user_input = prompt_window_text_box.gather().strip()
        curses.curs_set(0)

        return user_input

    def input_stream(self):
        """Waiting an input and run a proper method according to type of input"""
        while True:
            self.display()

            ch = self.window.getch()
            if ch == curses.KEY_UP:
                self.scroll(self.UP)
            elif ch == curses.KEY_DOWN:
                self.scroll(self.DOWN)
            elif ch == curses.KEY_LEFT:
                self.paging(self.UP)
            elif ch == curses.KEY_RIGHT:
                self.paging(self.DOWN)
            elif ch == 114:  # r
                if self.backup is not None:
                    self.backup, self.items = self.items, self.backup
                    self.backup = None
            elif ch == 102:  # s
                search = self.get_input("", "Filter:")
                self.backup = self.items
                self.items = []
                for item in self.backup:
                    if search in item:
                        self.items.append(item)
            elif ch == 113:  # q
                break
            elif ch == curses.KEY_ENTER or ch == 10 or ch == 13:
                self.item = self.current
            elif ch == curses.ascii.ESC:
                self.item = -1

    def scroll(self, direction):
        """Scrolling the window when pressing up/down arrow keys"""
        # next cursor position after scrolling
        next_line = self.current + direction

        # Up direction scroll overflow
        # current cursor position is 0, but top position is greater than 0
        if (direction == self.UP) and (self.top > 0 and self.current == 0):
            self.top += direction
            return
        # Down direction scroll overflow
        # next cursor position touch the max lines, but absolute position of max lines could not touch the bottom
        if (direction == self.DOWN) and (next_line == self.max_lines) and (self.top + self.max_lines < self.bottom):
            self.top += direction
            return
        # Scroll up
        # current cursor position or top position is greater than 0
        if (direction == self.UP) and (self.top > 0 or self.current > 0):
            self.current = next_line
            return
        # Scroll down
        # next cursor position is above max lines, and absolute position of next cursor could not touch the bottom
        if (direction == self.DOWN) and (next_line < self.max_lines) and (self.top + next_line < self.bottom):
            self.current = next_line
            return

    def paging(self, direction):
        """Paging the window when pressing left/right arrow keys"""
        current_page = (self.top + self.current) // self.max_lines
        next_page = current_page + direction
        # The last page may have fewer items than max lines,
        # so we should adjust the current cursor position as maximum item count on last page
        if next_page == self.page:
            self.current = min(self.current, self.bottom % self.max_lines - 1)

        # Page up
        # if current page is not a first page, page up is possible
        # top position can not be negative, so if top position is going to be negative, we should set it as 0
        if (direction == self.UP) and (current_page > 0):
            self.top = max(0, self.top - self.max_lines)
            return
        # Page down
        # if current page is not a last page, page down is possible
        if (direction == self.DOWN) and (current_page < self.page):
            self.top += self.max_lines
            return

    def display(self):
        """Display the items on window"""
        self.window.erase()
        if self.item != -1:
            for idx, item in enumerate(self.items[self.top:self.top + self.max_lines]):
                # Highlight the current cursor line
                if idx == self.current:
                    items = json.loads(item)
                    for sub_idx, item in enumerate(items):
                        self.window.addstr(
                            5 + sub_idx, 5, f'{item} :{str(items[item])}', curses.color_pair(3))
                    break
        else:
            for idx, item in enumerate(self.items[self.top:self.top + self.max_lines]):
                # Highlight the current cursor line
                if idx == self.current:
                    self.window.addstr(idx, 0, item, curses.color_pair(2))
                else:
                    self.window.addstr(idx, 0, item, curses.color_pair(1))
        self.window.refresh()


def main():
    f = open('data.json')
    items = json.load(f)
    lines = []
    for item in items:
        line = json.dumps(item)
        lines.append(line)
    screen = Screen(lines)
    screen.run()
    f.close()


if __name__ == '__main__':
    main()
