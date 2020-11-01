#!/usr/bin/python3
"""Track prices of Amazon products over time."""

#
# import sorted with: isort
# linted with: pylama with pydocstyle-pep8, pydocstyle-257, pyflakes, McCabe
# line length: 79
# beautified with: black (line length 79)
# pydocstyle: convention=numpy
#    ~/.pydocstyle
#    [pydocstyle]
#    inherit = false
#    match = .*\.py
#    convention=numpy

# Imports, sorted by isort
import argparse
import datetime
import logging
import random
import signal
import sqlite3
import sys
import time
import urllib.request
from functools import partial

import bs4 as bs
import matplotlib.pyplot as plot
import pyperclip
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMainWindow

# Global Constants
DEFAULT_DB_FILENAME = "amazon.db"
MAX_PRODUCT_NAME_LENGTH = 30  # max length for display
# HTTP error code 429 ... Too Many Requests
# ERROR_MSG_429 = "Too many requests, try again in 15 mins"
ERROR_MSG_429 = "Price unavailable."

# Global Variables
# avoid them if possible
# example_global_var = 12


################################################################
# Class ProductDatabase
################################################################


class ProductDatabase:
    """Handle database for Amazon price tracking."""

    # class variables here, use only when required

    def __init__(self, args: argparse.Namespace, db_file_path: str):
        """Initialize the class methods and instance variables.

        Arguments:
        ---------
            args: argparse.Namespace -- arguments from argparse
            db_file_path: str -- path and name of sqlite3 database file

        """
        self.connection = sqlite3.connect(db_file_path)
        self.cursor = self.connection.cursor()  # sqlite3.Cursor
        self.create_table()
        logging.debug(f"init:: rows in db: {self.get_row_count()}")
        logging.debug(f"init:: db rows: {self.get_all_rows()}")

    def create_table(self):
        """Create table iff does not exist."""
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS amazon(url TEXT, price TEXT, "
            "datestamp TEXT, unix REAL, id INTEGER PRIMARY KEY AUTOINCREMENT)"
        )
        self.cursor.connection.commit()

    def close(self):
        """Close database."""
        logging.debug("close:: closing down database.")
        self.cursor.connection.commit()
        logging.debug(f"close:: rows in db: {self.get_row_count()}")
        logging.debug(f"close:: db rows: {self.get_all_rows()}")
        self.cursor.close()
        self.cursor.connection.close()

    def add_item_to_db(self, url: str, price: str):
        """Add a new product to the database."""
        unix = time.time()
        date = str(
            datetime.datetime.fromtimestamp(unix).strftime(
                "%Y-%m-%-d %H:%M:%S"
            )
        )
        self.cursor.execute(
            "INSERT INTO amazon (url, price, datestamp, unix)"
            "VALUES(?, ?, ?, ?)",
            (url, price, date, unix),
        )
        self.cursor.connection.commit()
        logging.debug(f"add_item_to_db: product for {url} added to db.")

    def get_last_data(self, url: str):
        """Get the last 2 rows.

        Arguments:
        ---------
            url:str -- URL entry in db, used to search for rows

        """
        self.cursor.execute(
            "SELECT price FROM amazon WHERE url = ? "
            "ORDER BY unix DESC LIMIT 2",
            (url,),
        )
        data = self.cursor.fetchall()
        return data[0]

    def get_one_from_each_url(self):
        """Get one row for each URL."""
        self.cursor.execute(
            "SELECT url, price, id FROM amazon GROUP BY url ORDER BY Id ASC"
        )
        data = self.cursor.fetchall()
        return data

    def get_all_rows(self):
        """Get all rows."""
        self.cursor.execute(
            "SELECT url, price, id FROM amazon ORDER BY Id ASC"
        )
        data = self.cursor.fetchall()
        return data

    def get_unixtime_price_for_url(self, url: str):
        """Get unixtime and price for rows matching URL.

        Arguments:
        ---------
            url:str -- URL entry in db, used to search for rows

        """
        self.cursor.execute(
            "SELECT unix, price FROM amazon WHERE url = ?", (url,)
        )
        data = self.cursor.fetchall()
        return data

    def get_row_count(self) -> int:
        """Get number of rows.

        Returns
        -------
            int -- number of rows in table pointed to by cursor

        """
        self.cursor.execute("SELECT COUNT(*) AS count FROM amazon")
        data = self.cursor.fetchall()  # e.g [(18,)]
        return data[0][0]

    def delete_rows_for_url(self, url: str):
        """Delete rows matching URL.

        Arguments:
        ---------
            url:str -- URL entry in db, used to delete rows

        """
        # Set url to deleted
        self.cursor.execute("DELETE FROM amazon WHERE url = ?", (url,))
        self.cursor.connection.commit()

    def value_already_exists(self, url: str) -> bool:
        """Determine if the product already exists."""
        self.cursor.execute("SELECT id FROM amazon WHERE url= ?", (url,))
        return self.cursor.fetchone()  # True if one is found


################################################################
# Class ProductWindow
################################################################


class ProductWindow(QMainWindow):
    """Handle GUI for Amazon price tracking."""

    # class variables here, use only when required

    def __init__(self, args: argparse.Namespace, db: ProductDatabase):
        """Initialize the class methods and instance variables.

        Arguments:
        ---------
            args: argparse.Namespace -- arguments from argparse
            db: ProductDatabase -- sqlite3 database object

        """
        super(ProductWindow, self).__init__()
        self.new_vars(args, db)  # sets instance variables
        self.setGeometry(1000, 1600, 900, 900)
        self.setWindowTitle("Track Amazon products")
        self.init_ui()
        self.update_current_data_value()
        self.init_labels()  # requires cursor set

    def new_vars(self, args: argparse.Namespace, db: ProductDatabase):
        """Create and initialize instance variables."""
        self.args = args
        self.db = db
        self.cursor = db.cursor  # sqlite3 db cursor
        # we can get the sqlite3 connection from cursor: cursor.connection
        self.height = 140
        self.width = 30
        self.WIDTH_CLOSE_BUTTON = 600
        self.WIDTH_LINK_BUTTON = 635
        self.WIDTH_GRAPH_BUTTON = 670
        self.data = self.db.get_one_from_each_url()
        # self.icon = "/home/a/"
        # self.error_message = ERROR_MSG_429

    def init_ui(self):
        """Perform initial GUI setup."""
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
        """Perform action after "add product" button is clicked."""
        url = self.input.text().strip()  # remove white spaces
        self.new_value(url)

    def shorten_url(self, url: str) -> str:
        """Shorten the URL to the product name."""
        try:
            split_url = url.split("/")
            if split_url[3] == "dp":  # index 3 might not exist
                return get_product_name(url)
            else:
                return split_url[3]
        except Exception as e:
            logging.info(f"shorten_url:: exception occurred: {e}")
            return get_product_name(url)

    def init_labels(self):
        """Initialize labels."""
        self.products = []
        self.close_buttons = []
        self.link_buttons = []
        self.graph_buttons = []
        self.products_index = 0
        self.PRODUCTS_SPACE_DIFFERENCE = 50
        logging.debug(f"init_labels:: {self.data}")
        data = self.db.get_one_from_each_url()
        self.add_label(data)

    def add_label(self, newData):
        """Add label when the add label is called."""
        COLOR_GREEN = "background-color: lightgreen"
        COLOR_RED = "background-color: red"
        for row in newData:
            url = row[0]
            price = row[1]
            last_data = self.db.get_last_data(url)
            try:
                # TODO: this is still old. fix it, and try to not have to
                # use the price into int only once and save it like an int in
                # the db
                if url in newData:
                    bigger = self.which_is_more_expensive(price, last_data[1])
                    logging.debug(f"add_label:: Which is bigger {bigger}")
                    logging.debug(f"add_label:: {last_data[0]} vs {row[0]}")
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

            # Create the link button
            link_button = self.create_new_link_button(url)
            self.link_buttons.append(link_button)
            logging.debug(f"add_label:: {link_button}")

            # Create the show graph button ⇵
            graph_button = self.create_new_graph_button(url)
            self.graph_buttons.append(graph_button)

            # Create the close button
            close_button = self.create_new_close_button(
                url, new_label, link_button, graph_button
            )
            self.close_buttons.append(close_button)

            # Show the made items and increase iterators
            new_label.show()
            close_button.show()
            link_button.show()
            graph_button.show()
            self.height += self.PRODUCTS_SPACE_DIFFERENCE
            self.products_index += 1

    def create_new_label(self, url, price):
        """Create a new label."""
        short_url = self.shorten_url(url)

        new_label = QtWidgets.QLabel(self)
        new_label.setText(
            f"Product {(self.products_index+1)}: {price}€\n{short_url}"
        )
        new_label.move(self.width, self.height)
        new_label.adjustSize()
        return new_label

    def create_new_close_button(
        self, url: str, new_label, link_button, graph_button
    ):
        """Create a new close button."""
        close_button = QtWidgets.QPushButton(self)
        # remove icon ⨉ ✖ ❌, unicode
        close_button.setText("❌")
        remove_function = partial(
            self.remove_products,
            new_label,
            close_button,
            link_button,
            graph_button,
            self.products_index,
            False,
            url,
        )
        close_button.setGeometry(self.WIDTH_CLOSE_BUTTON, self.height, 30, 25)
        close_button.clicked.connect(remove_function)
        return close_button

    def create_new_link_button(self, url: str):
        """Create a new link button."""
        link_button = QtWidgets.QPushButton(self)
        # copy © icon, link 🔗 ⛓ url unicode
        link_button.setText("🔗")
        copy_link = partial(copy_link_to_clipboard, url)
        link_button.setGeometry(self.WIDTH_LINK_BUTTON, self.height, 30, 25)
        link_button.clicked.connect(copy_link)
        return link_button

    def create_new_graph_button(self, url):
        """Create a new show graph button."""
        graph_button = QtWidgets.QPushButton(self)
        # graph ⇵, chart icon 💹, chart 📉 📈 unicode
        graph_button.setText("📉")
        show_product_price_graph = partial(self.show_product_price_graph, url)
        graph_button.setGeometry(self.WIDTH_GRAPH_BUTTON, self.height, 30, 25)
        graph_button.clicked.connect(show_product_price_graph)
        return graph_button

    def remove_products(
        self,
        label,
        close_button,
        link_button,
        graph_button,
        index: int,
        checked: bool,
        url: str,
    ):
        """Remove products when the x close_button is pressed."""
        logging.debug(
            f"remove_products:: self: {self}, "
            f"close_button: {type(close_button)} {close_button}, "
            f"index: {index}, checked: {type(checked)}, "
            f"remove_products:: winid is {close_button.winId()}"
        )

        # Hiding and removing the label and the close_button
        link_button.hide()
        close_button.hide()
        graph_button.hide()
        label.hide()

        self.db.delete_rows_for_url(url)
        self.replace_products(index)

    def replace_products(self, product_index: int):
        """Replace the products in the correct spot."""
        for index in range(product_index, len(self.products)):
            label = self.products[index]
            close_button = self.close_buttons[index]
            link_button = self.link_buttons[index]
            graph_button = self.graph_buttons[index]

            y_pos_label = label.y()
            y_pos_button = close_button.y()

            self.height -= self.PRODUCTS_SPACE_DIFFERENCE

            label.move(
                self.width, y_pos_label - self.PRODUCTS_SPACE_DIFFERENCE
            )

            close_button.move(
                self.WIDTH_CLOSE_BUTTON,
                y_pos_button - self.PRODUCTS_SPACE_DIFFERENCE,
            )
            link_button.move(
                self.WIDTH_LINK_BUTTON,
                y_pos_button - self.PRODUCTS_SPACE_DIFFERENCE,
            )
            graph_button.move(
                self.WIDTH_GRAPH_BUTTON,
                y_pos_button - self.PRODUCTS_SPACE_DIFFERENCE,
            )
        logging.debug("replace_products:: products were replaced")

    def show_product_price_graph(self, url):
        """Show a graph of the products price passed through the argument."""
        data = self.db.get_unixtime_price_for_url(url)
        # do not use strings with plot, use float and datetime
        dates_datetime = []
        prices_float = []

        for row in data:
            dates_datetime.append(datetime.datetime.fromtimestamp(row[0]))
            prices_float.append(float(row[1]))

        # already set logger level to INFO in init() to avoid spam
        plot.plot_date(dates_datetime, prices_float, "-")
        plot.show()

    def new_value(self, url: str):
        """Handle new product after the add product button is pressed."""
        if url is None or url == "":
            logging.debug("new_value: empty URL ignored.")
            return
        value_exists = self.db.value_already_exists(url)
        if not value_exists:
            price = str(get_price(self.args, url))
            if price != ERROR_MSG_429:
                values = [(url, price)]
                self.db.add_item_to_db(url, price)
                self.add_label(values)
                logging.debug(f"new_value: product for {url} added.")
        else:
            # already exists, but update the price
            price = str(get_price(self.args, url))
            if price != ERROR_MSG_429:
                self.db.add_item_to_db(url, price)
                logging.debug(f"new_value: product price for {url} updated.")

    def update_current_data_value(self):
        """Check products in self.data if the price is correct."""
        data_copy = self.data.copy()
        for row in data_copy:
            url = row[0]
            price = get_price(self.args, url)
            if price != ERROR_MSG_429:
                self.db.add_item_to_db(url, price)
        # self.save_data()


################################################################
# Regular functions
################################################################


def which_is_more_expensive(price1: str, price2: str) -> int:
    """Determine which price is higher."""
    price1 = convert_price_in_str(price1)
    price2 = convert_price_in_str(price2)
    if price1 > price2:
        return 1  # If price1 is bigger return 1
    elif price1 < price2:
        return -1  # If price2 is bigger return -1
    return 0


def copy_link_to_clipboard(url: str):
    """Copy URL to system clipboard."""
    pyperclip.copy(url)
    logging.debug(f"copy_link_to_clipboard:: copied URL {url} to clipboard.")


def convert_price_in_str(price: str) -> int:
    """Convert the price string into an integer."""
    try:
        price_int = price.replace(",", ".")
        price_int = float(price_int)
        return price_int
    except ValueError as e:
        logging.debug(f"convert_price_in_str:: failed to convert price: {e}")
        return 0


def get_price(args: argparse.Namespace, url: str) -> str:
    """Get price for given URL via web scraping.

    Arguments:
    ---------
        args:argparse.Namespace -- arguments from argparse
        url:str -- Amazon product URL
    Returns:
    -------
        str -- product price

    """
    if args.fake_prices:
        random_price = str(random.randint(10, 100))
        logging.debug(
            f"get_price:: faking price {random_price}. Avoid URL scraping."
        )
        return random_price
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
                tag = "Not available "

        tag = tag[0 : len(tag) - 2]  # noqa
        logging.debug(f"get_price:: tag is {tag}")
    except urllib.request.HTTPError as e:
        logging.debug(f"get_price:: exception occurred: {e}")
        logging.debug("get_price:: Looks like Amazon responded with an error.")
        tag = ERROR_MSG_429
    except Exception as e:
        logging.debug(f"get_price:: exception occurred: {e}")
        logging.debug("get_price:: Did you enter a valid URL?")
        tag = ERROR_MSG_429
    return tag


def get_product_name(url: str) -> str:
    """Get the product name for a given URL via web scraping.

    Arguments:
    ---------
        url:str -- Amazon product URL
    Returns:
    -------
        str -- product name

    """
    try:
        sauce = urllib.request.urlopen(url)
        soup = bs.BeautifulSoup(sauce, "lxml")
        search = soup.find("span", {"id": "productTitle"})
        tag = search.text
        tag = tag.split("\n")
        logging.debug(f"get_product_name:: tag is {tag}")
        tag = tag[8]
    except urllib.request.HTTPError as e:
        logging.debug(f"get_product_name:: exception occurred: {e}")
        tag = url
    except Exception as e:  # handle the rest of the possible errors
        logging.debug(f"get_product_name:: exception occurred: {e}")
        logging.debug(
            "get_product_name:: Looks like there "
            f"is an invalid URL {url} in the database?"
        )
        tag = url
    if len(tag) > MAX_PRODUCT_NAME_LENGTH:
        return f"{tag[0:MAX_PRODUCT_NAME_LENGTH]}..."
    return tag


def init_args() -> argparse.Namespace:
    """Initialize the arguments.

    Returns
    -------
        argparse.Namespace -- namespace with all arguments

    """
    # argparse
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # argparse
    parser = argparse.ArgumentParser(description="Track Amazon prices")
    parser.add_argument(
        "-d",
        "--debug",
        default=True,
        action="store_true",
        help="Turn debug on",
    )
    parser.add_argument(
        "-f",
        "--fake-prices",
        default=False,
        action="store_true",
        help="Fake random prices instead of scraping them from Amazon",
    )
    parser.add_argument(
        "-db",
        "--database",
        # r...read, w...write, +...update(read and write),
        # t...text mode, b...binary
        # w ... create if not existing, overwrite if existing
        # r+ ... do not create if not existing but give warning
        # a ... open for writing, appending to the end of the file if it exists
        #       create if not existing,
        #       do not overwrite (but append) if existing
        # see: https://docs.python.org/3/library/functions.html#open
        type=argparse.FileType("a"),
        default=DEFAULT_DB_FILENAME,
        # const=DEFAULT_DB_FILENAME,
        # nargs="?",
        help="Path and name of sqlite3 database file. "
        f"Default is {DEFAULT_DB_FILENAME}.",
    )
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logging.debug(f"init_args:: args is set to: {args}")
    logging.debug(f"init_args:: debug is set to: {args.debug}")
    logging.debug(f"init_args:: database is set to: {args.database.name}")
    return args


def init() -> argparse.Namespace:
    """Initialize the program.

    Returns
    -------
        argparse.Namespace -- namespace with all arguments from argparse

    """
    # general
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # for PyQt5 GUI
    # arguments
    args = init_args()
    args.database.close()  # the file is opened by default by argparse
    # matplotlib
    # plot has a lot of DEBUG logging which we do not want to see
    # so we raise log level to INFO
    plot_logger = logging.getLogger("matplotlib")
    plot_logger.setLevel(level=logging.INFO)
    # style.use("fivethirtyeight")  # style for plotting output diagram
    return args


def window(args: argparse.Namespace, db: ProductDatabase) -> int:
    """Create the window and go into event loop.

    Arguments:
    ---------
        args:argparse.Namespace -- namespace with all arguments from argparse
        db: ProductDatabase -- sqlite3 database object
    Returns:
    -------
        int -- return code from QApplication app

    """
    app = QApplication([])
    win = ProductWindow(args, db)
    win.show()
    ret = app.exec()  # enter event loop
    return ret


def main():
    """Track Amazon prices."""
    args = init()
    db = ProductDatabase(args, args.database.name)
    ret = window(args, db)
    db.close()
    logging.debug(f"main:: exiting with code {ret}.")
    sys.exit(ret)


try:
    main()
except KeyboardInterrupt:
    logging.debug("Received keyboard interrupt.")
    raise
    sys.exit()
except Exception as e:
    logging.error(f"Caught exception {e}.")
    raise
    sys.exit()
