#!/usr/bin/python3
"""Do the necessary imports."""
import argparse
import datetime
import logging
import signal
import sqlite3
import sys
import time
import urllib.request
from functools import partial

import bs4 as bs
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pyperclip
from matplotlib import style
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMainWindow

conn = sqlite3.connect('amazon.db')
c = conn.cursor()


class my_window(QMainWindow):
    """Handle GUI for Amazon price tracking."""

    def __init__(self):
        """Initialize the class functions."""
        super(my_window, self).__init__()
        self.new_vars()
        self.setGeometry(1000, 1600, 900, 900)
        self.setWindowTitle("Track amazon products")
        self.init_ui()
        self.check_current_data_value()
        self.init_labels()

    def new_vars(self):
        """Set initial vars."""
        self.height = 140
        self.width = 30
        self.WIDTH_CLOSE_BUTTON = 600
        self.WIDTH_LINK_BUTTON = 635
        self.WIDTH_GRAPH_BUTTON = 670
        self.data = get_one_from_each_url()
        # self.args = args
        self.icon = "/home/a/"

    def init_ui(self):
        """Perform initial setup."""
        height = 50

        # Create main label
        # TODO: make an to show what each button does
        label = QtWidgets.QLabel(self)
        # self.label[0].setStyleSheet("background-color: red")
        label.setText("Introduce the link of the product you want to track")
        label.setFont(QFont("Ubuntu", 15))
        label.move(self.width, height - 35)
        label.adjustSize()

        # Create main button
        b1 = QtWidgets.QPushButton(self)
        b1.setText("Add product")
        b1.setGeometry(650, height, 100, 30)
        b1.move(650, height)
        b1.clicked.connect(self.main_button_clicked)

        # Create main input
        self.input = QtWidgets.QLineEdit(self)
        self.input.move(self.width, height)
        self.input.resize(600, 30)

    def main_button_clicked(self):
        """Do the action after the add products button is clicked."""
        url = self.input.text()
        self.new_value(url)
        self.check_current_data_value()

    def shorten_url(self, url: str) -> str:
        """Shorten the URL to the product name."""
        split_url = url.split("/")
        if split_url[3] == "dp":
            return get_product_name(url)
        else:
            return split_url[3]

    def convert_price_in_str(price: str) -> int:
        """Convert the price string into and integer."""
        # I think should work without a self argument
        try:
            price_int = price.replace(",", ".")
            price_int = float(price_int)
            return price_int
        except ValueError:
            return 9999

    def init_labels(self):
        """Initialize labels."""
        self.products = []
        self.close_buttons = []
        self.link_buttons = []
        self.graph_buttons = []
        self.products_index = 0
        self.PRODUCTS_SPACE_DIFFERENCE = 50
        logging.debug(f"init_labels:: {self.data}")
        data = get_one_from_each_url()
        self.add_label(data)

    def add_label(self, newData):
        """Add label when the add label is called."""
        COLOR_GREEN = "background-color: lightgreen"
        COLOR_RED = "background-color: red"
        for row in newData:
            url = row[0]
            price = row[1]
            last_data = get_last_data(url)
            try:
                # This may fail
                print("hihi")
                # TODO: this is still old fix it, and try to not have to
                # use the price into int only once and save it like and int in
                # the db
                if url in newData:
                    bigger = self.which_is_more_expensive(
                        price, last_data[1]
                    )
                    logging.debug(f"add_label:: Which is bigger {bigger}")
                    logging.debug(
                        f"add_label:: {last_data[0]} vs {row[0]}"
                    )
                else:
                    bigger = 0
            except ValueError:  # catch *all* exceptions
                e = sys.exc_info()[0]
                logging.error(
                    f"add_label:: Caught exception\n{e}\n{url}\n{self.data}."
                )

            # Create the label and define the color
            new_label = self.create_new_label(url, price)

            if bigger > 0:
                new_label.setStyleSheet(COLOR_RED)
            elif bigger < 0:
                new_label.setStyleSheet(COLOR_GREEN)
            elif bigger == 0:
                new_label.setStyleSheet("background-color: lightblue")

            self.products.append(new_label)

            # Create the close button
            close_button = self.create_new_close_button(url, new_label)
            self.close_buttons.append(close_button)

            # Create the link button
            link_button = self.create_new_link_button(url)
            self.link_buttons.append(link_button)
            logging.debug(f"add_label:: {link_button}")

            # Create the show graph button ⇵
            graph_button = self.create_new_graph_button(url)
            self.graph_buttons.append(graph_button)
            # Show the made items and increase iterators
            new_label.show()
            close_button.show()
            link_button.show()
            graph_button.show()
            self.height += self.PRODUCTS_SPACE_DIFFERENCE
            self.products_index += 1

    def copy_link(self, url: str):
        """Set the copy buffer to product url on link_button pressed."""
        print(type(url), url)
        pyperclip.copy(url)

    def create_new_label(self, url, price):
        """Create a new label."""
        short_url = self.shorten_url(url)

        new_label = QtWidgets.QLabel(self)
        new_label.setText(
            f"Product {(self.products_index+1)}: "
            f"{price}€\n{short_url}"
        )
        new_label.move(self.width, self.height)
        new_label.adjustSize()
        return new_label

    def create_new_close_button(self, url: str, new_label):
        """Create a new close button."""
        close_button = QtWidgets.QPushButton(self)
        close_button.setText("⨉")
        removeFunction = partial(
            self.remove_products,
            new_label,
            close_button,
            self.products_index,
            False,
            url,
        )
        close_button.setGeometry(self.WIDTH_CLOSE_BUTTON,
                                 self.height, 30, 25)
        close_button.clicked.connect(removeFunction)
        return close_button

    def create_new_link_button(self, url: str):
        """Create a new link button."""
        link_button = QtWidgets.QPushButton(self)
        link_button.setText("©")
        copy_link = partial(
            self.copy_link,
            url,
        )
        link_button.setGeometry(self.WIDTH_LINK_BUTTON,
                                self.height, 30, 25)
        link_button.clicked.connect(copy_link)
        return link_button

    def create_new_graph_button(self, url):
        """Create a new show graph button."""
        graph_button = QtWidgets.QPushButton(self)
        graph_button.setText("⇵")
        show_product_price_graph = partial(
            self.show_product_price_graph,
            url,
        )
        graph_button.setGeometry(self.WIDTH_GRAPH_BUTTON,
                                 self.height, 30, 25)
        graph_button.clicked.connect(show_product_price_graph)
        return graph_button

    def remove_products(self, label, button, index, checked, url):
        """Remove products when the x button is pressed."""
        logging.debug(f"remove_products:: {self}")
        logging.debug(
            f"self: {self}, button: {type(button)} {button}, index: {index},",
            f"checked: {type(checked)}",
        )
        logging.debug(f"winid is {button.winId()}")

        # Hiding and removing the label and the button
        button.hide()
        label.hide()

        # Set url to deleted
        c.execute("DELETE FROM amazon WHERE url = ?", (url,))
        conn.commit()
        self.replace_products(index)

    def replace_products(self, product_index: int):
        """Replace the products in the correct spot."""
        logging.debug(
            "replace_products:: prodecuts where replaced"
        )
        for index in range(product_index, len(self.products)):
            button = []
            label = self.products[index]
            close_button = self.close_buttons[index]
            link_button = self.link_buttons[index]
            button.extend((close_button, link_button))

            y_pos_label = label.y()
            y_pos_button = close_button.y()

            self.height -= self.PRODUCTS_SPACE_DIFFERENCE

            label.move(
                self.width, y_pos_label - self.PRODUCTS_SPACE_DIFFERENCE)

            close_button.move(
                self.WIDTH_CLOSE_BUTTON, y_pos_button -
                self.PRODUCTS_SPACE_DIFFERENCE
            )
            link_button.move(
                self.WIDTH_LINK_BUTTON, y_pos_button -
                self.PRODUCTS_SPACE_DIFFERENCE
            )

    def show_product_price_graph(self, url):
        """Show a graph of the products price passed through the argument."""
        c.execute('SELECT unix, price FROM amazon WHERE url = ?', (url,))
        data = c.fetchall()

        dates = []
        values = []
        print(data)

        for row in data:
            print(row[0], row[1])
            dates.append(datetime.datetime.fromtimestamp(row[0]))
            values.append(row[1])

        plt.plot_date(dates, values, '-')
        plt.show()

    def new_value(self, url: str):
        """Handle new value after the add product button is pressed."""
        value_exists = self.value_already_exists(url)
        if not value_exists:
            price = str(get_price(url))
            values = [(url, price)]
            self.add_item_to_db(url, price)
            self.add_label(values)

    def add_item_to_db(self, url: str, price: str):
        """Add a new value to the Db."""
        unix = time.time()
        date = str(datetime.datetime.fromtimestamp(unix).strftime(
            '%Y-%m-%-d %H: %M: %S'))
        c.execute("INSERT INTO amazon (url, price, datestamp, unix)"
                  "VALUES(?, ?, ?, ?)",
                  (url, price, date, unix))
        conn.commit()

    def value_already_exists(self, url: str) -> bool:
        """Determine if the value already exists."""
        c.execute("SELECT id FROM amazon WHERE url= ?",
                  (url,)
                  )
        data = c.fetchone()
        if data:
            return True
        return False

    def which_is_more_expensive(self, price1: str, price2: str) -> int:
        """Determine which is more expensive from the arguments."""
        print(type(price1))
        price1 = self.convert_price_in_str(price1)
        price2 = self.convert_price_in_str(price2)
        if price1 > price2:
            # If prize1 is bigger return 1
            return 1
        elif price1 < price2:
            # If prize2 is bigger return -1
            return -1
        return 0

    def check_current_data_value(self):
        """Check the products in data if the price is correct."""
        data_copy = self.data.copy()
        for row in data_copy:
            if row[1] == "Deleted":
                c.execute("DELETE FROM amazon WHERE price = ?", ("Deleted"))
                conn.commit()
                continue
            price = get_price(row[0])

            if price != row[1]:
                c.execute("UPDATE amazon SET price = ? WHERE id = ?",
                          (price, row[2],))
                conn.commit()
        # self.save_data()


def window():
    """Create the window and go into event loop."""
    app = QApplication([])
    # win = my_window(args)
    win = my_window()
    win.show()
    sys.exit(app.exec())


def create_table():
    """Do creates a table."""
    c.execute(
        'CREATE TABLE IF NOT EXISTS amazon(url TEXT, price TEXT,\
        datestamp TEXT, unix REAL, id INTEGER PRIMARY KEY AUTOINCREMENT)'
    )


def get_last_data(url):
    """Get the second last data."""
    c.execute("SELECT price FROM amazon WHERE url = ?\
     ORDER BY unix DESC LIMIT 2",
              (url,))
    data = c.fetchall()
    return data[0]


def get_one_from_each_url():
    """Get one from each url."""
    c.execute("SELECT url, price, id FROM amazon GROUP BY url\
            ORDER BY Id ASC")
    data = c.fetchall()
    return data


def get_price(url: str) -> str:
    """Get price for the url that is passed as an argument."""
    print(url, type(url))
    try:
        sauce = urllib.request.urlopen(url)
        soup = bs.BeautifulSoup(sauce, "lxml")
        try:
            search = soup.find("span", {"id": "priceblock_dealprice"})
            tag = search.text
        except AttributeError:
            try:
                search = soup.find("span", {"id": "priceblock_ourprice"})
                tag = search.text
            except AttributeError:
                tag = "Not available"

        # pylama:ignore=E203
        tag = tag[0: len(tag) - 2]
        logging.debug(tag)
    except urllib.request.HTTPError:
        logging.debug("except ocurred")
        tag = "Too many requests, try again in 15 mins"
    return tag


def get_product_name(url: str) -> str:
    """Get the product name for the url passed in the arg."""
    try:
        sauce = urllib.request.urlopen(url)
        soup = bs.BeautifulSoup(sauce, "lxml")
        search = soup.find("span", {"id": "productTitle"})
        tag = search.text
        tag = tag.split('\n')
        # pylama:ignore=E203
        logging.debug(tag)
        tag = tag[8]
    except urllib.request.HTTPError:
        logging.debug("except ocurred")
        tag = url
    if len(tag) > 30:
        return f"{tag[0:30]}..."
    return tag


def init() -> argparse.Namespace:
    """Initialize the program.

    Process argument and open file.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # Argparse
    parser = argparse.ArgumentParser(description="Track amazon prices")
    parser.add_argument(
        "-d",
        "--debug",
        default=True,
        action="store_true",
        help="Turn debug on",
    )
    # parser.add_argument(
    #     "-f",
    #     "--file",
    #     # r...read, w...write, +...update(read and write),
    #     # t...text mode, b...binary
    #     # see: https://docs.python.org/3/library/functions.html#open
    #     type=argparse.FileType("r+"),
    #     default=filenameDefault,
    #     # const=filenameDefault,
    #     # nargs="?",
    #     help="file for product listings",
    # )
    # args = parser.parse_args()
    # if args.debug:
    #     logging.basicConfig(level=logging.DEBUG)
    # else:
    #     logging.basicConfig(level=logging.INFO)
    # logging.debug(f"init:: args is set to: {args}")
    # logging.debug(f"init:: debug is set to: {args.debug}")
    # logging.debug(f"init:: file is set to: {args.file.name}")
    create_table()
    # get the file content jsonData = ast.literal_eval(args.file.read())
    # logging.debug(f"init:: Initial state of file is: {jsonData}.")
    # return args


# main
try:
    args = init()
    # window(args)
    window()
    # args.file.close()
except KeyboardInterrupt:
    logging.debug("Received keyboard interrupt.")
    raise
    sys.exit()
except Exception as e:
    logging.error(f"Caught exception {e}.")
    raise
    sys.exit()
