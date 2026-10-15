"""Arrow-key menus using Python's standard terminal library."""
import curses


class MenuCancelled(Exception):
    pass


def choose(title, items, *, multiple=False, default=0, selected=()):
    if not items:
        raise ValueError("Nabídka je prázdná.")
    return curses.wrapper(_menu, title, items, multiple, default, set(selected))


def _menu(screen, title, items, multiple, cursor, selected):
    cursor = max(0, min(cursor, len(items) - 1))
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.keypad(True)
    while True:
        screen.erase()
        height, width = screen.getmaxyx()

        def line(row, text):
            if 0 <= row < height and width > 1:
                try:
                    screen.addnstr(row, 0, text, width - 1)
                except curses.error:
                    pass

        line(0, title)
        hint = "↑/↓ pohyb · mezerník označit · a vše · Enter potvrdit · q/Esc konec" if multiple else "↑/↓ pohyb · Enter potvrdit · q/Esc konec"
        line(1, hint)
        visible = max(1, height - 5)
        start = max(0, min(cursor - visible + 1, len(items) - visible))
        for index in range(start, min(len(items), start + visible)):
            prefix = "> " if index == cursor else "  "
            if multiple:
                prefix += "[x] " if index in selected else "[ ] "
            line(3 + index - start, prefix + items[index])
        if multiple:
            line(height - 1, f"Označeno: {len(selected)}. Enter bez označení vybere aktuální řádek.")
        screen.refresh()
        key = screen.get_wch()
        if key in (curses.KEY_UP, "k"):
            cursor = (cursor - 1) % len(items)
        elif key in (curses.KEY_DOWN, "j"):
            cursor = (cursor + 1) % len(items)
        elif key == curses.KEY_HOME:
            cursor = 0
        elif key == curses.KEY_END:
            cursor = len(items) - 1
        elif key in ("q", "Q", "\x1b", "\x03"):
            raise MenuCancelled()
        elif multiple and key == " ":
            selected.symmetric_difference_update({cursor})
        elif multiple and key in ("a", "A"):
            selected = set() if len(selected) == len(items) else set(range(len(items)))
        elif key in ("\n", "\r", curses.KEY_ENTER):
            return sorted(selected or {cursor}) if multiple else cursor
