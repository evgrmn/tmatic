import platform
import tkinter as tk
import tkinter.font
from datetime import datetime
from tkinter import ttk

from common.variables import Variables as var

if platform.system() == "Windows":
    from ctypes import windll

    windll.shcore.SetProcessDpiAwareness(1)


class AutoScrollbar(tk.Scrollbar):
    def resize_init(self, on_scroll_resize):
        self.on_scroll_resize = on_scroll_resize

    def set(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.tk.call("grid", "remove", self)
        else:
            if hasattr(self, "on_scroll_resize"):
                self.on_scroll_resize()
            self.grid()
        tk.Scrollbar.set(self, low, high)


class CustomButton(tk.Frame):
    def __init__(self, master, text, bg, fg, command=None, menu_items=None, **kwargs):
        super().__init__(master, **kwargs)
        self.label = tk.Label(self, text=text, bg=bg, fg=fg)
        self.label.pack(fill="both")
        # self.config(bg=bg)
        self.name = text
        self.bg = bg
        self.fg = fg
        self.command = command
        self.menu_items = menu_items
        self.state = None
        self.label.bind("<ButtonPress-1>", self.on_press)
        self.label.bind("<Enter>", self.on_enter)
        self.label.bind("<Leave>", self.on_leave)

        # Initialize the menu
        self.menu = tk.Menu(self, tearoff=0)
        if menu_items:
            for item in menu_items:
                self.menu.add_command(
                    label=item, command=lambda value=item: self.on_command(value)
                )

    def on_command(self, value):
        self.master.unbind_all("<Button-1>")
        self.command(value)

    def on_enter(self, event):
        if self.state != "Disabled":
            self.label.config(bg=Variables.bg_active)

    def on_leave(self, event):
        self.label.config(bg=self.bg, fg=self.fg)

    def on_press(self, event):
        if self.menu_items:
            if not self.is_bound_to_click():
                # Get the coordinates of the button relative to the root window
                x = self.winfo_rootx()
                y = self.winfo_rooty() + self.winfo_height()
                # Show the menu at the bottom-left corner of the button
                self.menu.post(x, y)
                # Bind a global event to detect clicks outside the button
                self.master.bind_all("<Button-1>", self.check_click_outside)
        else:
            if self.state != "Disabled":  # and self.command:
                self.command(self.name)

    def is_bound_to_click(self):
        # Check if <Button-1> is bound globally
        bind_list = self.master.bind_all()
        return "<Button-1>" in bind_list

    def check_click_outside(self, event):
        # Get the menu bounds
        menu_x1, menu_y1, menu_x2, menu_y2 = (
            self.menu.winfo_rootx(),
            self.menu.winfo_rooty(),
            self.menu.winfo_rootx() + self.menu.winfo_width(),
            self.menu.winfo_rooty() + self.menu.winfo_height(),
        )
        # Check if the click is outside the button and the menu
        if not (
            self.winfo_containing(event.x_root, event.y_root) == self
            or (
                menu_x1 <= event.x_root <= menu_x2
                and menu_y1 <= event.y_root <= menu_y2
            )
        ):
            self.menu.unpost()
            # Unbind the global event
            self.master.unbind_all("<Button-1>")

    def on_menu_select(value):
        print("______________on_menu_select")
        if value == "Bot Menu":
            Variables.pw_rest1.pack_forget()
            Variables.menu_robots.pack(fill="both", expand="yes")


class Variables:
    root = tk.Tk()
    platform_name = "Tmatic"
    root.title(platform_name)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    if screen_width > 1440:
        window_ratio = 0.7
        adaptive_ratio = 0.9
    elif screen_width > 1366:
        window_ratio = 0.72
        adaptive_ratio = 0.93
    elif screen_width > 1280:
        window_ratio = 0.75
        adaptive_ratio = 0.95
    elif screen_width > 1024:
        window_ratio = 0.8
        adaptive_ratio = 0.97
    else:
        window_ratio = 1
        adaptive_ratio = 1
    window_width = int(screen_width * window_ratio)
    window_height = int(screen_height)
    root.geometry("{}x{}".format(window_width, int(window_height * 0.7)))
    all_width = window_width
    left_width = window_width
    last_market = ""
    pw_ratios = {}

    if platform.system() == "Windows":
        ostype = "Windows"
    elif platform.system() == "Darwin":
        ostype = "Mac"
    else:
        ostype = "Linux"

    num_robots = 1
    num_book = 20  # Must be even
    col1_book = 0

    pw_main = tk.PanedWindow(
        root, orient=tk.HORIZONTAL, sashrelief="raised", bd=0, sashwidth=0
    )
    pw_main.pack(fill="both", expand="yes")

    # Adaptive frame to the left, always visible
    frame_left = tk.Frame()
    frame_left.pack(fill="both", expand="yes")
    frame_left.bind("<Configure>", lambda event: hide_columns(event))

    # Frame to the right, always blank
    frame_right = tk.Frame()
    frame_right.pack(fill="both", expand="yes")

    # Top state frame: trading on/off, time
    frame_state = tk.Frame(frame_left)
    frame_state.grid(row=0, column=0, sticky="NSWE")
    frame_left.grid_columnconfigure(0, weight=1)
    frame_left.grid_rowconfigure(0, weight=0)

    label_trading = tk.Label(frame_state, text="  TRADING: ")

    # Color map and styles
    fg_color = label_trading["foreground"]
    fg_select_color = fg_color
    bg_changed = "gold"
    green_color = "#07b66e"
    red_color = "#f53661"
    white_color = "#FFFFFF"
    black_color = "#000000"
    line_height = tkinter.font.Font(font="TkDefaultFont").metrics("linespace")
    symbol_width = tkinter.font.Font().measure("01234567890.") / 12
    button_height = 20
    style = ttk.Style()

    # Paned window: up - information field, down - the rest interface
    pw_info_rest = tk.PanedWindow(
        frame_left, orient=tk.VERTICAL, sashrelief="raised", bd=0
    )

    menu_frame = tk.Frame(pw_info_rest)
    menu_frame.pack(fill="both", expand="yes")

    # This technical PanedWindow contains most frames and widgets
    pw_rest1 = tk.PanedWindow(
        menu_frame, orient=tk.HORIZONTAL, sashrelief="raised", bd=0, sashwidth=0
    )
    pw_rest1.pack(fill="both", expand="yes")

    # This technical PanedWindow contains orderbook, positions, orders,
    # trades, fundings, results, currencies, robots
    pw_rest2 = tk.PanedWindow(
        pw_rest1,
        orient=tk.VERTICAL,
        sashrelief="raised",
        bd=0,
        sashwidth=0,
        height=1,
    )
    pw_rest2.pack(fill="both", expand="yes")

    # This technical PanedWindow contains orderbook, positions, orders,
    # trades, fundings, results
    pw_rest3 = tk.PanedWindow(
        pw_rest2, orient=tk.HORIZONTAL, sashrelief="raised", bd=0, sashwidth=0
    )
    pw_rest3.pack(fill="both", expand="yes")

    # This technical PanedWindow contains positions, orders, trades, fundings,
    # results
    pw_rest4 = tk.PanedWindow(
        pw_rest3,
        orient=tk.VERTICAL,
        sashrelief="raised",
        bd=0,
        sashwidth=0,
        height=1,
    )
    pw_rest4.pack(fill="both", expand="yes")

    # Paned window: up - orders, down - trades, fundings, results
    pw_orders_trades = tk.PanedWindow(
        pw_rest4, orient=tk.VERTICAL, sashrelief="raised", bd=0, height=1
    )
    pw_orders_trades.pack(fill="both", expand="yes")
    pw_ratios[pw_orders_trades] = 2

    # Notebook tabs: Trades / Funding / Results
    if ostype == "Mac":
        notebook = ttk.Notebook(pw_orders_trades, padding=(-9, 0, -9, -9))
    else:
        notebook = ttk.Notebook(pw_orders_trades, padding=0)
        style.theme_use("default")
    style.configure("free.TEntry", foreground=fg_color)
    style.configure("used.TEntry", foreground=red_color)
    # bg_combobox = style.lookup('TCombobox', 'fieldbackground')
    style.map(
        "changed.TCombobox",
        selectbackground=[("readonly", "")],
        selectforeground=[("readonly", fg_color)],
        fieldbackground=[("readonly", bg_changed)],
    )
    style.map(
        "default.TCombobox",
        selectbackground=[("readonly", "")],
        selectforeground=[("readonly", fg_color)],
    )
    if platform.system() == "Darwin":
        # ostype = "Mac"
        title_color = frame_state["background"]
        bg_select_color = "systemSelectedTextBackgroundColor"
        bg_active = bg_select_color
    else:
        frame_state.configure(bg="grey82")
        # if platform.system() == "Windows":
        #     ostype = "Windows"
        # else:
        #     ostype = "Linux"
        style.map(
            "Treeview",
            background=[("selected", "#b3d7ff")],
            foreground=[("selected", fg_color)],
        )
        style.map(
            "menu.Treeview",
            background=[("selected", "invalid", "#b3d7ff")],
        )
        title_color = frame_state["background"]
        label_trading.config(bg=title_color)
        bg_select_color = "#b3d7ff"
        bg_active = bg_select_color
        sell_bg_color = "#feede0"
        buy_bg_color = "#e3f3cf"
        frame_right.configure(background=title_color)
    style.configure(
        "Treeview",
        foreground=fg_color,
    )
    style.configure(
        "market.Treeview",
        fieldbackground=title_color,
        background=title_color,
        rowheight=line_height * 3,
    )
    style.configure(
        "bot_menu.Treeview",
        fieldbackground=title_color,
        background=title_color,
    )
    style.configure("Treeview.Heading", foreground=fg_color)
    style.configure("TNotebook", borderwidth=0, background="gray92", tabposition="n")
    style.configure("TNotebook.Tab", background="gray92")
    fg_disabled = tk.Entry()["disabledforeground"]
    bg_disabled = title_color  # tk.Entry()["disabledbackground"]
    fg_normal = tk.Entry()["foreground"]

    # frame_state.config(background=title_color)
    # label_trading.config(background=title_color)

    # Menu widget
    """menu_button = tk.Menubutton(
        frame_state, text=" MENU ", relief=tk.FLAT, padx=0, pady=0, bg=title_color
    )"""
    menu_button = CustomButton(
        frame_state,
        " MENU ",
        title_color,
        fg_color,
        command=CustomButton.on_menu_select,
        menu_items=["Trading ON", "Reload All", "Bot Menu", "Settings", "About"],
    )
    menu_button.pack(side="left", padx=4)

    menu_delimiter = tk.Label(frame_state, text="|", bg=title_color)
    menu_delimiter.pack(side="left", padx=0)

    label_trading.pack(side="left")
    label_f9 = tk.Label(
        frame_state, width=3, text="OFF", fg="white", bg="red", anchor="c"
    )
    label_f9.pack(side="left")

    label_time = tk.Label(frame_state, anchor="e", foreground=fg_color, bg=title_color)
    label_time.pack(side="right")

    pw_info_rest.grid(row=1, column=0, sticky="NSEW")
    frame_left.grid_rowconfigure(1, weight=1)
    pw_ratios[pw_info_rest] = 9

    # Information field
    frame_info = tk.Frame(pw_info_rest)
    frame_info.pack(fill="both", expand="yes")

    # Information widget
    if ostype == "Mac":
        text_info = tk.Text(
            frame_info,
            highlightthickness=0,
            wrap=tk.WORD,
        )
    else:
        text_info = tk.Text(
            frame_info,
            bg="gray98",
            highlightthickness=0,
            wrap=tk.WORD,
        )
    text_info.grid(row=0, column=0, sticky="NSEW")
    scroll_info = AutoScrollbar(frame_info, orient="vertical")
    scroll_info.config(command=text_info.yview)
    scroll_info.grid(row=0, column=1, sticky="NS")
    text_info.config(yscrollcommand=scroll_info.set)
    frame_info.grid_columnconfigure(0, weight=1)
    frame_info.grid_columnconfigure(1, weight=0)
    frame_info.grid_rowconfigure(0, weight=1)
    # text_info.configure(state="disabled")
    bg_color = text_info["background"]

    menu_robots = tk.Frame(menu_frame)

    # One or more exchages is put in this frame
    frame_market = tk.Frame(pw_rest1)

    # Frame for the order book
    frame_orderbook = tk.Frame(pw_rest3)

    # Frame for instruments and their positions
    frame_instrument = tk.Frame(pw_rest4)

    # Frame for active orders
    frame_orders = tk.Frame(pw_orders_trades)

    # Trades frame
    frame_trades = tk.Frame(notebook)

    # Funding frame
    frame_funding = tk.Frame(notebook)

    # Results frame
    frame_results = tk.Frame(notebook)

    # Positions frame
    frame_positions = tk.Frame(notebook)

    # Bots frame
    frame_bots = tk.Frame(notebook)

    notebook.add(frame_trades, text="Trades")
    notebook.add(frame_funding, text="Funding")
    notebook.add(frame_results, text="Results")
    notebook.add(frame_positions, text="Positions")
    notebook.add(frame_bots, text="Bots")
    pw_orders_trades.add(frame_orders)
    pw_orders_trades.add(notebook)
    pw_orders_trades.bind(
        "<Configure>",
        lambda event: resize_height(
            event,
            Variables.pw_orders_trades,
            Variables.pw_ratios[Variables.pw_orders_trades],
        ),
    )
    pw_orders_trades.bind(
        "<ButtonRelease-1>",
        lambda event: on_sash_move(event, Variables.pw_orders_trades),
    )

    # Paned window: up - currencies (account), down - robots
    pw_bottom = tk.PanedWindow(
        pw_rest2, orient=tk.VERTICAL, sashrelief="raised", bd=0, height=1
    )
    pw_bottom.pack(fill="both", expand="yes")
    pw_ratios[pw_bottom] = 2

    # Frame for currencies (account)
    frame_account = tk.Frame(pw_bottom)

    # Frame for the robots table
    frame_robots = tk.Frame(pw_bottom)

    pw_bottom.add(frame_account)
    pw_bottom.add(frame_robots)
    pw_bottom.bind(
        "<Configure>",
        lambda event: resize_height(
            event, Variables.pw_bottom, Variables.pw_ratios[Variables.pw_bottom]
        ),
    )
    pw_bottom.bind(
        "<ButtonRelease-1>", lambda event: on_sash_move(event, Variables.pw_bottom)
    )

    pw_rest4.add(frame_instrument)
    pw_rest4.add(pw_orders_trades)
    pw_rest4.bind(
        "<Configure>", lambda event: resize_height(event, Variables.pw_rest4, 5)
    )

    pw_rest3.add(frame_orderbook)
    pw_rest3.add(pw_rest4)
    pw_rest3.bind(
        "<Configure>",
        lambda event: Variables.resize_width(
            event, Variables.pw_rest3, Variables.window_width // 4.5, 3
        ),
    )

    pw_rest2.add(pw_rest3)
    pw_rest2.add(pw_bottom)
    pw_rest2.bind(
        "<Configure>", lambda event: resize_height(event, Variables.pw_rest2, 1.4)
    )

    pw_rest1.add(frame_market)
    pw_rest1.add(pw_rest2)
    pw_rest1.bind(
        "<Configure>",
        lambda event: Variables.resize_width(
            event, Variables.pw_rest1, Variables.window_width // 9.5, 6
        ),
    )

    pw_info_rest.add(frame_info)
    pw_info_rest.add(menu_frame)
    pw_info_rest.bind(
        "<Configure>",
        lambda event: resize_height(
            event, Variables.pw_info_rest, Variables.pw_ratios[Variables.pw_info_rest]
        ),
    )
    pw_info_rest.bind(
        "<ButtonRelease-1>", lambda event: on_sash_move(event, Variables.pw_info_rest)
    )

    pw_main.add(frame_left)
    pw_main.add(frame_right)
    pw_main.bind(
        "<Configure>",
        lambda event: Variables.resize_width(
            event, Variables.pw_main, Variables.window_width, 1
        ),
    )

    refresh_var = None
    nfo_display_counter = 0
    f9 = "OFF"
    f3 = False
    robots_window_trigger = "off"
    info_display_counter = 0
    handler_orderbook_symbol = tuple()
    book_window_trigger = "off"
    order_window_trigger = "off"
    table_limit = 200
    refresh_handler_orderbook = False

    def resize_width(event, pw, start_width, min_ratio):
        ratio = pw.winfo_width() / start_width
        if ratio < min_ratio:
            my_width = pw.winfo_width() // min_ratio
        else:
            my_width = start_width
        pw.paneconfig(pw.panes()[0], width=my_width)


class TreeviewTable(Variables):
    def __init__(
        self,
        frame: tk.Frame,
        name: str,
        title: list,
        size=0,
        style="",
        bind=None,
        hide=[],
        multicolor=False,
        autoscroll=False,
        hierarchy=False,
        lines=[],
        rollup=False,
    ) -> None:
        self.title = title
        self.max_rows = 200
        self.name = name
        self.title = title
        self.cache = list()
        self.bind = bind
        self.size = size
        self.count = 0
        self.hierarchy = hierarchy
        self.lines = lines
        self.rollup = rollup
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        if hierarchy:
            show = "tree headings"
            length = len(title)
        else:
            show = "headings"
            length = len(title) + 1
        columns = [num for num in range(1, length)]
        self.tree = ttk.Treeview(
            frame,
            style=style,
            columns=columns,
            show=show,
            selectmode="browse",
            height=self.size,
        )
        for num, name in enumerate(title, start=1):
            if hierarchy:
                if num == 1:
                    num = "#0"
                else:
                    num -= 1
            self.tree.heading(num, text=name)
            self.tree.column(num, anchor=tk.CENTER, width=50)
        if autoscroll:
            scroll = AutoScrollbar(frame, orient="vertical")
        else:
            scroll = tk.Scrollbar(frame, orient="vertical")
        scroll.config(command=self.tree.yview)
        self.tree.config(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="NSEW")
        scroll.grid(row=0, column=1, sticky="NS")
        self.children = list()
        self.children_hierarchical = dict()
        self.tree.tag_configure("Select", background=self.bg_select_color)
        self.tree.tag_configure("Buy", foreground=self.green_color)
        self.tree.tag_configure("Sell", foreground=self.red_color)
        self.tree.tag_configure("White", background=self.bg_color)
        self.tree.tag_configure("Normal", foreground=self.fg_color)
        self.tree.tag_configure("Reload", foreground=self.red_color)
        self.tree.tag_configure("Red", foreground=self.red_color)
        if self.ostype != "Mac":
            self.tree.tag_configure("Gray", background="gray90")
        else:
            self.tree.tag_configure("Gray", background=self.title_color)
        self.tree.tag_configure(
            "Market", background=self.title_color, foreground=self.fg_color
        )
        if bind:
            self.tree.bind("<<TreeviewSelect>>", bind)
        self.iid_count = 0
        self.init(size=size)
        if hide:
            self.column_hide = []
            self.hide_num = 0
            hide_begin = list(self.tree["columns"])
            self.column_hide.append(tuple(hide_begin))
            for num, id_col in enumerate(hide, start=1):
                self.column_hide.append(hide_begin)
                self.column_hide[num].remove(id_col)
                hide_begin = list(self.column_hide[num])
                self.column_hide[num] = tuple(hide_begin)
        if multicolor:
            self.setup_color_cell()
            self.tree.bind("<Configure>", self.on_window_resize)
            scroll.resize_init(self.on_scroll_resize)
            self.tree.bind("<B1-Motion>", self.on_window_resize)
            self.tree.update()

    def init(self, size):
        self.clear_all()
        self.cache = dict()
        if self.hierarchy:
            self.init_hierarchical()
            return
        blank = ["" for _ in self.title]
        for num in range(size):
            # self.insert(values=blank, market="")
            self.tree.insert("", tk.END, iid=num, values=blank)
            self.cache[num] = blank
        self.children = self.tree.get_children()

    def init_hierarchical(self):
        self.tree.column("#0", anchor=tk.W)
        if len(self.title) > 1:
            self.tree.column("1", anchor=tk.W)
        for line in self.lines:
            self.tree.insert("", tk.END, text=line, iid=line, open=True, tags="Gray")
            self.cache[line] = line
            self.children_hierarchical[line] = self.tree.get_children(line)
        self.children = self.tree.get_children()

    def insert(self, values: list, market="", iid="", configure="") -> None:
        if not iid:
            self.iid_count += 1
            iid = self.iid_count
        self.tree.insert("", 0, iid=iid, values=values, tags=configure, text=market)
        self.children = self.tree.get_children()
        if len(self.children) > self.max_rows:
            self.delete()

    def insert_hierarchical(
        self, parent: str, iid: str, values=[], configure="", text="", new=False
    ):
        if new:
            if "New_bot!" in self.children:
                indx = self.children.index("New_bot!")
        else:
            indx = tk.END
        self.tree.insert(
            parent, indx, iid=iid, values=values, tags=configure, text=text
        )
        self.children_hierarchical[parent] = self.tree.get_children(parent)
        self.children = self.tree.get_children()

    def delete(self, iid="") -> None:
        if not iid:
            iid = self.children[len(self.children) - 1]
        self.tree.delete(iid)
        self.children = self.tree.get_children()

    def delete_hierarchical(self, parent: str, iid="") -> None:
        self.tree.delete(iid)
        self.children_hierarchical[parent] = self.tree.get_children(parent)

    def update(self, row: int, values: list) -> None:
        self.tree.item(row, values=values)

    def update_hierarchical(self, parent: str, iid: str, values: list) -> None:
        self.tree.item(iid, values=values)

    def paint(self, row: int, configure: str) -> None:
        pass
        self.tree.item(self.children[row], tags=configure)
        if self.tree.selection():
            selected = len(self.children) - int(self.tree.selection()[0])
        if self.name == "market":
            if configure == "Reload" and row == selected:
                self.style.map(
                    "market.Treeview",
                    foreground=[("selected", self.red_color)],
                )
            else:
                self.style.map(
                    "market.Treeview",
                    foreground=[("selected", self.fg_color)],
                )

    def clear_all(self, market=None):
        if not market:
            self.tree.delete(*self.children)
        else:
            for child in self.children:
                line = self.tree.item(child)
                if line["text"] == market:
                    self.delete(iid=child)
        self.children = self.tree.get_children()

    def append_data(self, rows: list, market: str) -> list:
        data = list()
        if self.children:
            for child in self.children:
                line = self.tree.item(child)
                if line["text"] != market:
                    data.append(line["values"])
        data += rows
        self.clear_all()
        data = list(
            map(lambda x: x + [datetime.strptime(x[0], "%y%m%d %H:%M:%S")], data)
        )
        data.sort(key=lambda x: x[-1], reverse=True)
        data = list(map(lambda x: x[:-1], data))

        return reversed(data[: self.max_rows])

    def set_selection(self, index=0):
        self.tree.selection_add(self.children[index])

    def setup_color_cell(self):
        self._canvas = list()
        for _ in range(self.size):
            lst = list()
            for num in range(len(self.title)):
                lst.append(tk.Canvas(self.tree, borderwidth=0, highlightthickness=0))
                lst[num].text = lst[num].create_text(
                    10, self.line_height / 2, anchor="w"
                )
                lst[num].up = False
            self._canvas.append(lst)

    def show_color_cell(
        self,
        text: str,
        row: int,
        column: int,
        bg_color: str,
        fg_color: str,
    ):
        canvas = self._canvas[row][column]
        s_length = self.symbol_width * len(text)
        canvas.config(background=bg_color)
        canvas.itemconfigure(canvas.text, text=text, fill=fg_color)
        canvas.txt = text
        bbox = self.tree.bbox(self.children[row], column + 1)
        if bbox:
            x, y, width, height = bbox
            canvas.configure(width=width, height=height)
            canvas.coords(canvas.text, (max(0, (width - s_length)) / 2, height / 2))
            canvas.place(x=x, y=y)
            canvas.up = True
        else:
            canvas.up = "hidden"

    def resize_color_cell(self, bbox: tuple, row: int, column: int):
        x, y, width, height = bbox
        canvas = self._canvas[row][column]
        s_length = self.symbol_width * len(canvas.txt)
        canvas.configure(width=width, height=height)
        canvas.coords(canvas.text, (max(0, (width - s_length)) / 2, height / 2))
        canvas.place(x=x, y=y)

    def hide_color_cell(self, row: int, column: int):
        canvas = self._canvas[row][column]
        canvas.configure(width=0, height=0)
        canvas.place(x=0, y=0)
        canvas.up = False

    def clear_color_cell(self):
        for row in range(self.size):
            for column in range(len(self.title)):
                self.hide_color_cell(row, column)

    def on_window_resize(self, event):
        for row, canvas_list in enumerate(self._canvas):
            self.count += 1
            for column, canvas in enumerate(canvas_list):
                bbox = self.tree.bbox(self.children[row], column + 1)
                if bbox:
                    if canvas.up is True:
                        self.resize_color_cell(bbox, row, column)
                    elif canvas.up == "hidden":
                        x, y, width, height = bbox
                        canvas.configure(width=width, height=height)
                        s_length = self.symbol_width * len(canvas.txt)
                        canvas.coords(
                            canvas.text, (max(0, (width - s_length)) / 2, height / 2)
                        )
                        canvas.place(x=x, y=y)
                        canvas.up = True
                else:
                    if canvas.up is True:
                        self.hide_color_cell(row=row, column=column)
                        canvas.up = "hidden"

    def on_scroll_resize(self):
        self.on_window_resize("scroll")

    def on_rollup(self, iid=None):
        parent = iid.split("!")[0]
        for child in self.children:
            if child != parent:
                self.tree.item(child, open=False)
        """if parent in self.children:
            self.tree.item(parent, open=True)"""


class TreeTable:
    instrument: TreeviewTable
    robots: TreeviewTable
    account: TreeviewTable
    orderbook: TreeviewTable
    market: TreeviewTable
    results: TreeviewTable
    trades: TreeviewTable
    funding: TreeviewTable
    orders: TreeviewTable
    position: TreeviewTable
    bots: TreeviewTable
    bot_menu: TreeviewTable
    bot_info: TreeviewTable


def text_ignore(event):
    return "break"  # Prevents further handling of the event


def resize_col(event, pw, ratio):
    pw.paneconfig(pw.panes()[0], width=pw.winfo_width() // ratio)


def resize_height(event, pw, ratio):
    pw.paneconfig(pw.panes()[0], height=pw.winfo_height() // ratio)


def on_sash_move(event, pw):
    panes = pw.winfo_children()
    Variables.pw_ratios[pw] = pw.winfo_height() / panes[1].winfo_height()


def trim_col_width(tview, cols):
    width = tview.winfo_width() // len(cols)
    for col in cols:
        tview.column(col, width=width)


# Hide / show adaptive columns in order to save space in the tables
def hide_columns(event):
    if hasattr(TreeTable, "instrument"):
        ratio = (
            Variables.frame_left.winfo_width() / Variables.left_width
            if Variables.left_width > 1
            else 1.0
        )
        if ratio < Variables.adaptive_ratio - 0.2:
            if (
                TreeTable.instrument.hide_num != 3
                or var.current_market != Variables.last_market
            ):
                TreeTable.instrument.tree.config(
                    displaycolumns=TreeTable.instrument.column_hide[3]
                )
                TreeTable.instrument.hide_num = 3
                trim_col_width(
                    TreeTable.instrument.tree, TreeTable.instrument.column_hide[3]
                )
            if (
                TreeTable.orders.hide_num != 3
                or var.current_market != Variables.last_market
            ):
                TreeTable.orders.tree.config(
                    displaycolumns=TreeTable.orders.column_hide[3]
                )
                TreeTable.orders.hide_num = 3
                trim_col_width(TreeTable.orders.tree, TreeTable.orders.column_hide[3])
            if (
                TreeTable.trades.hide_num != 3
                or var.current_market != Variables.last_market
            ):
                TreeTable.trades.tree.config(
                    displaycolumns=TreeTable.trades.column_hide[3]
                )
                TreeTable.trades.hide_num = 3
                trim_col_width(TreeTable.trades.tree, TreeTable.trades.column_hide[3])
            if (
                TreeTable.funding.hide_num != 3
                or var.current_market != Variables.last_market
            ):
                TreeTable.funding.tree.config(
                    displaycolumns=TreeTable.funding.column_hide[3]
                )
                TreeTable.funding.hide_num = 3
                trim_col_width(TreeTable.funding.tree, TreeTable.funding.column_hide[3])
            if (
                TreeTable.robots.hide_num != 2
                or var.current_market != Variables.last_market
            ):
                TreeTable.robots.tree.config(
                    displaycolumns=TreeTable.robots.column_hide[2]
                )
                TreeTable.robots.hide_num = 2
                trim_col_width(TreeTable.robots.tree, TreeTable.robots.column_hide[2])
        elif ratio < Variables.adaptive_ratio - 0.1:
            if (
                TreeTable.instrument.hide_num != 2
                or var.current_market != Variables.last_market
            ):
                TreeTable.instrument.tree.config(
                    displaycolumns=TreeTable.instrument.column_hide[2]
                )
                TreeTable.instrument.hide_num = 2
                trim_col_width(
                    TreeTable.instrument.tree, TreeTable.instrument.column_hide[2]
                )
            if (
                TreeTable.orders.hide_num != 2
                or var.current_market != Variables.last_market
            ):
                TreeTable.orders.tree.config(
                    displaycolumns=TreeTable.orders.column_hide[2]
                )
                TreeTable.orders.hide_num = 2
                trim_col_width(TreeTable.orders.tree, TreeTable.orders.column_hide[2])
            if (
                TreeTable.trades.hide_num != 2
                or var.current_market != Variables.last_market
            ):
                TreeTable.trades.tree.config(
                    displaycolumns=TreeTable.trades.column_hide[2]
                )
                TreeTable.trades.hide_num = 2
                trim_col_width(TreeTable.trades.tree, TreeTable.trades.column_hide[2])
            if (
                TreeTable.funding.hide_num != 2
                or var.current_market != Variables.last_market
            ):
                TreeTable.funding.tree.config(
                    displaycolumns=TreeTable.funding.column_hide[2]
                )
                TreeTable.funding.hide_num = 2
                trim_col_width(TreeTable.funding.tree, TreeTable.funding.column_hide[2])
            if (
                TreeTable.robots.hide_num != 1
                or var.current_market != Variables.last_market
            ):
                TreeTable.robots.tree.config(
                    displaycolumns=TreeTable.robots.column_hide[1]
                )
                TreeTable.robots.hide_num = 1
                trim_col_width(TreeTable.robots.tree, TreeTable.robots.column_hide[1])
        elif ratio < Variables.adaptive_ratio:
            if (
                TreeTable.instrument.hide_num != 1
                or var.current_market != Variables.last_market
            ):
                TreeTable.instrument.tree.config(
                    displaycolumns=TreeTable.instrument.column_hide[1]
                )
                TreeTable.instrument.hide_num = 1
                trim_col_width(
                    TreeTable.instrument.tree, TreeTable.instrument.column_hide[1]
                )
            if (
                TreeTable.orders.hide_num != 1
                or var.current_market != Variables.last_market
            ):
                TreeTable.orders.tree.config(
                    displaycolumns=TreeTable.orders.column_hide[1]
                )
                TreeTable.orders.hide_num = 1
                trim_col_width(TreeTable.orders.tree, TreeTable.orders.column_hide[1])
            if (
                TreeTable.trades.hide_num != 1
                or var.current_market != Variables.last_market
            ):
                TreeTable.trades.tree.config(
                    displaycolumns=TreeTable.trades.column_hide[1]
                )
                TreeTable.trades.hide_num = 1
                trim_col_width(TreeTable.trades.tree, TreeTable.trades.column_hide[1])
            if (
                TreeTable.funding.hide_num != 1
                or var.current_market != Variables.last_market
            ):
                TreeTable.funding.tree.config(
                    displaycolumns=TreeTable.funding.column_hide[1]
                )
                TreeTable.funding.hide_num = 1
                trim_col_width(TreeTable.funding.tree, TreeTable.funding.column_hide[1])
            if TreeTable.robots.hide_num != 0:
                TreeTable.robots.tree.config(
                    displaycolumns=TreeTable.robots.column_hide[0]
                )
                TreeTable.robots.hide_num = 0
                trim_col_width(TreeTable.robots.tree, TreeTable.robots.column_hide[0])
        elif ratio > Variables.adaptive_ratio:
            if TreeTable.instrument.hide_num != 0:
                TreeTable.instrument.tree.config(
                    displaycolumns=TreeTable.instrument.column_hide[0]
                )
                TreeTable.instrument.hide_num = 0
                trim_col_width(
                    TreeTable.instrument.tree, TreeTable.instrument.column_hide[0]
                )
            if TreeTable.orders.hide_num != 0:
                TreeTable.orders.tree.config(
                    displaycolumns=TreeTable.orders.column_hide[0]
                )
                TreeTable.orders.hide_num = 0
                trim_col_width(TreeTable.orders.tree, TreeTable.orders.column_hide[0])
            if TreeTable.trades.hide_num != 0:
                TreeTable.trades.tree.config(
                    displaycolumns=TreeTable.trades.column_hide[0]
                )
                TreeTable.trades.hide_num = 0
                trim_col_width(TreeTable.trades.tree, TreeTable.trades.column_hide[0])
            if TreeTable.funding.hide_num != 0:
                TreeTable.funding.tree.config(
                    displaycolumns=TreeTable.funding.column_hide[0]
                )
                TreeTable.funding.hide_num = 0
                trim_col_width(TreeTable.funding.tree, TreeTable.funding.column_hide[0])
            if TreeTable.robots.hide_num != 0:
                TreeTable.robots.tree.config(
                    displaycolumns=TreeTable.robots.column_hide[0]
                )
                TreeTable.robots.hide_num = 0
                trim_col_width(TreeTable.robots.tree, TreeTable.robots.column_hide[0])
        Variables.last_market = var.current_market

    now_width = Variables.root.winfo_width()
    if now_width != Variables.all_width or var.current_market != Variables.last_market:
        if now_width > Variables.window_width:
            t = Variables.platform_name.ljust((now_width - Variables.window_width) // 4)
            Variables.root.title(t)
        else:
            Variables.root.title(Variables.platform_name)
        Variables.all_width = now_width
