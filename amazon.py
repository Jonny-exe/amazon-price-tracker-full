#!/usr/bin/python3
"""Do the necessary imports."""
import argparse
import ast
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
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import style
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMainWindow

filenameDefault = "products.json"
conn = sqlite3.connect('amazon.db')
c = conn.cursor()


class MyWindow(QMainWindow):
    """Handle GUI for Amazon price tracking."""

    def __init__(self, args):
        """Initialize the class functions."""
        super(MyWindow, self).__init__()
        self.new_vars()
        self.get_file_data()
        self.setGeometry(1000, 1600, 900, 900)
        self.setWindowTitle("Track amazon products")
        self.init_ui()
        self.check_current_data_value()
        self.init_labels()

    def get_file_data(self):
        """Get the data from products file."""
        print(args)
        args.file.seek(0)
        # data = ast.literal_eval(args.file.read())
        self.data = getOneFromEachUrl()
        logging.debug(f"get_file_data:: current data: {self.data}")

    def save_data(self):
        """Save the self.data in the products file."""
        newData = str(self.data) + "\n"
        args.file.seek(0)
        args.file.truncate(args.file.write(newData))
        args.file.flush()
        if args.debug:
            logging.debug("save_data:: re-reading saved data:")

    def new_vars(self):
        """Set initial vars."""
        self.height = 140
        self.width = 30
        self.widthButton = 600
        self.errorMesagge = "Too many requests, try again in 15 mins"
        self.args = args
        self.icon = "/home/a/"

    def init_ui(self):
        """Perform initial setup."""
        height = 50

        # Create main label
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
        url = url.split("/")
        return url[3]

    def convert_price_in_str(price: str) -> int:
        """Convert the price string into and integer."""
        # I think should work without a self argument
        try:
            priceInt = price.replace(",", ".")
            priceInt = float(priceInt)
            return priceInt
        except ValueError:
            return 9999

    def init_labels(self):
        """Initialize labels."""
        self.products = []
        self.closeButtons = []
        self.productsIndex = 0
        self.productsSpaceDiference = 50
        logging.debug(f"init_labels:: {self.data}")
        data = getOneFromEachUrl()
        self.add_label(data)

    def add_label(self, newData):
        """Add label when the add label is called."""
        colorGreen = "background-color: lightgreen"
        colorRed = "background-color: red"
        for row in newData:
            url = row[0]
            price = row[1]
            lastData = getsave_data(url)
            # Check if the current url is deleted
            if row[1] == -1:
                continue

            try:
                # This may fail
                if url in newData:
                    bigger = self.which_is_more_expensive(
                        # self.lastData has to be something like
                        # self.lastData[0][0]
                        price, lastData[1]
                    )
                    logging.debug(f"add_label:: Which is bigger {bigger}")
                    logging.debug(
                        f"add_label:: {lastData[0]} vs {row[0]}"
                    )
                else:
                    bigger = 0
            except ValueError:  # catch *all* exceptions
                e = sys.exc_info()[0]
                logging.error(
                    f"add_label:: Caught exception\n{e}\n{url}\n{self.data}."
                )

            shortUrl = self.shorten_url(url)

            # Create the label
            newLabel = QtWidgets.QLabel(self)
            newLabel.setText(
                f"Product {(self.productsIndex+1)}: "
                f"{price}€\n{shortUrl}"
            )
            newLabel.move(self.width, self.height)
            newLabel.adjustSize()
            if bigger > 0:
                newLabel.setStyleSheet(colorRed)
            elif bigger < 0:
                newLabel.setStyleSheet(colorGreen)
            elif bigger == 0:
                newLabel.setStyleSheet("background-color: lightblue")
            self.products.append(newLabel)

            # Create the close button
            newButton = QtWidgets.QPushButton(self)
            newButton.setText("⨉")
            removeFunction = partial(
                self.remove_products,
                newLabel,
                newButton,
                self.productsIndex,
                False,
                url,
            )
            newButton.setGeometry(self.widthButton, self.height, 30, 25)
            newButton.clicked.connect(removeFunction)
            self.closeButtons.append(newButton)

            logging.debug(f"add_label:: {newButton}")

            # Show the made items and increase iterators
            newLabel.show()
            newButton.show()
            self.height += self.productsSpaceDiference
            self.productsIndex += 1

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
        c.commit()
        self.replace_products(index)

    def replace_products(self, productIndex: int):
        """Replace the products in the correct spot."""
        for index in range(productIndex, len(self.products)):
            label = self.products[index]
            button = self.closeButtons[index]

            yPosLabel = label.y()
            yPosButton = button.y()

            self.height -= self.productsSpaceDiference

            label.move(self.width, yPosLabel - self.productsSpaceDiference)
            button.move(
                self.widthButton, yPosButton - self.productsSpaceDiference
            )

    def new_value(self, url: str):
        """Handle new value after the add product button is pressed."""
        valueExists = self.value_already_exists()
        if not valueExists:
            price = str(getPrice(url))
            values = [(url, price)]
            self.add_item_to_db(url, price)
            self.add_label(values)

    def add_item_to_db(url, price):
        """Add a new value to the Db."""
        unix = time.time()
        date = str(datetime.datetime.fromtimestamp(unix).strftime(
            '%Y-%m-%-d %H: %M: %S'))
        c.execute("INSERT INTO amazon (url, price, datestamp, unix)"
                  "VALUES(?, ?, ?, ?)",
                  (url, price, date, unix))
        conn.commit()

    def value_already_exists(url) -> bool:
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
        dataCopy = self.data.copy()
        for row in dataCopy:
            if row[1] == "Deleted":
                c.execute("DELETE FROM amazon WHERE price = ?", ("Deleted"))
                continue
            price = getPrice(row[0])
            if price != self.data[url]:
                self.data[url] = price
        self.save_data()


def window(args):
    """Create the window and go into event loop."""
    app = QApplication([])
    win = MyWindow(args)
    win.show()
    sys.exit(app.exec())


def create_table():
    """Do creates a table."""
    c.execute(
        'CREATE TABLE IF NOT EXISTS amazon(url TEXT, price TEXT,\
        datestamp TEXT, unix REAL, id INTEGER PRIMARY KEY AUTOINCREMENT)'
    )


def getAllData():
    c.execute("SELECT * FROM amazon")
    return c.fetchall()


def getsave_data(url):
    """Get the second last data."""
    c.execute("SELECT price FROM amazon WHERE url = ?\
     ORDER BY unix DESC LIMIT 2",
              (url,))
    data = c.fetchall()
    return data[1]


def getPriceFromDb(URL: str) -> int:
    """Read the database and return the price of the url in the arguments."""
    c.execute('SELECT price, id FROM amazon WHERE url = ? ORDER BY id DESC',
              (URL,)
              )
    data = c.fetchall()
    print(f"data [0] is : {data[0]}")

    return data[0][0]


def getOneFromEachUrl():
    """Get one from each url."""
    c.execute("SELECT url, price FROM amazon GROUP BY price\
            ORDER BY Id ASC")
    data = c.fetchall()
    return data


def getPrice(url) -> str:
    """Get price for the url that is passed as an argument."""
    try:
        sauce = urllib.request.urlopen(url)
        soup = bs.BeautifulSoup(sauce, "lxml")
        try:
            search = soup.find("span", {"id": "priceblock_dealprice"})
            tag = search.text
        except AttributeError:
            search = soup.find("span", {"id": "priceblock_ourprice"})
            tag = search.text
        # pylama:ignore=E203
        tag = tag[0: len(tag) - 2]
        logging.debug(tag)
    except urllib.request.HTTPError:
        logging.debug("except ocurred")
        tag = "Too many requests, try again in 15 mins"
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
    parser.add_argument(
        "-f",
        "--file",
        # r...read, w...write, +...update(read and write),
        # t...text mode, b...binary
        # see: https://docs.python.org/3/library/functions.html#open
        type=argparse.FileType("r+"),
        default=filenameDefault,
        # const=filenameDefault,
        # nargs="?",
        help="file for product listings",
    )
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logging.debug(f"init:: args is set to: {args}")
    logging.debug(f"init:: debug is set to: {args.debug}")
    logging.debug(f"init:: file is set to: {args.file.name}")
    create_table()
    # get the file content jsonData = ast.literal_eval(args.file.read())
    # logging.debug(f"init:: Initial state of file is: {jsonData}.")
    return args


# main
try:
    args = init()
    window(args)
    args.file.close()
except KeyboardInterrupt:
    logging.debug("Received keyboard interrupt.")
    raise
    sys.exit()
except Exception as e:
    logging.error(f"Caught exception {e}.")
    raise
    sys.exit()
