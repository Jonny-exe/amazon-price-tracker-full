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
        self.newVars()
        self.getJsonFileData()
        self.setGeometry(1000, 1600, 900, 900)
        self.setWindowTitle("Track amazon products")
        self.initUI()
        self.checkCurretDataValue()
        self.initLabels()

    def getJsonFileData(self):
        """Get the data from products file."""
        print(args)
        args.file.seek(0)
        data = ast.literal_eval(args.file.read())
        self.data = data
        self.savedData = self.data.copy()
        logging.debug(f"getJsonFileData:: current data: {self.savedData}")

    def saveData(self):
        """Save the self.data in the products file."""
        newdata = str(self.data) + "\n"
        args.file.seek(0)
        args.file.truncate(args.file.write(newdata))
        args.file.flush()
        if args.debug:
            logging.debug("saveData:: re-reading saved data:")

    def newVars(self):
        """Set initial vars."""
        self.height = 140
        self.width = 30
        self.widthButton = 600
        self.errorMesagge = "Too many requests, try again in 15 mins"
        self.args = args
        self.icon = "/home/a/"

    def initUI(self):
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
        b1.clicked.connect(self.mainButtonClicked)

        # Create main input
        self.input = QtWidgets.QLineEdit(self)
        self.input.move(self.width, height)
        self.input.resize(600, 30)

    def mainButtonClicked(self):
        """Do the action after the add products button is clicked."""
        url = self.input.text()
        self.newValue(url)
        self.checkCurretDataValue()

    def shortenUrl(self, url: str) -> str:
        """Shorten the URL to the product name."""
        url = url.split("/")
        return url[3]

    def initLabels(self):
        """Initialize labels."""
        self.products = []
        self.closeButtons = []
        self.productsIndex = 0
        self.productsSpaceDiference = 50
        logging.debug(f"initLabels:: {self.data}")
        self.addLabel(self.data)

    def addLabel(self, newdata):
        """Add label when the add label is called."""
        colorGreen = "background-color: lightgreen"
        colorRed = "background-color: red"
        for url in newdata:
            # Check if the current url is deleted
            if newdata[url] == "Deleted":
                continue

            try:
                if url in self.savedData:
                    bigger = self.whichIsMoreExpensive(
                        newdata[url], self.savedData[url]
                    )
                    logging.debug(f"addLabel:: Which is bigger {bigger}")
                    logging.debug(
                        f"addLabel:: {newdata[url]} vs {self.savedData[url]}"
                    )
                else:
                    bigger = 0
            except ValueError:  # catch *all* exceptions
                e = sys.exc_info()[0]
                logging.error(
                    f"addLabel:: Caught exception\n{e}\n{url}\n{self.data}."
                )

            shortUrl = self.shortenUrl(url)

            # Create the label
            newLabel = QtWidgets.QLabel(self)
            newLabel.setText(
                f"Product {(self.productsIndex+1)}: "
                f"{newdata[url]}€\n{shortUrl}"
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
                self.removeProduct,
                newLabel,
                newButton,
                self.productsIndex,
                False,
                url,
            )
            newButton.setGeometry(self.widthButton, self.height, 30, 25)
            newButton.clicked.connect(removeFunction)
            self.closeButtons.append(newButton)

            logging.debug(f"addLabel:: {newButton}")

            # Show the made items and increase iterators
            newLabel.show()
            newButton.show()
            self.height += self.productsSpaceDiference
            self.productsIndex += 1

    def removeProduct(self, label, button, index, checked, url):
        """Remove products when the x button is pressed."""
        logging.debug(f"removeProduct:: {self}")
        logging.debug(
            f"self: {self}, button: {type(button)} {button}, index: {index},",
            f"checked: {type(checked)}",
        )
        logging.debug(f"winid is {button.winId()}")

        # Hiding and removing the label and the button
        button.hide()
        label.hide()

        # Set url to deleted
        self.data[url] = "Deleted"
        self.saveData()
        self.replaceProducts(index)

    def replaceProducts(self, productIndex: int):
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

    def newValue(self, url: str):
        """Handle new value after the add product button is pressed."""
        price = str(getPrice(url))
        newdata = {}
        if url not in self.data:
            newdata[url] = price
            self.addLabel(newdata)
        self.data[url] = price

    def whichIsMoreExpensive(self, price1: str, price2: str) -> int:
        """Determine which is more expensive from the arguments."""
        try:
            price1 = price1.replace(",", ".")
            price2 = price2.replace(",", ".")
            price1 = float(price1)
            price2 = float(price2)
            if price1 > price2:
                # If prize1 is bigger return 1
                return 1
            elif price1 < price2:
                # If prize2 is bigger return -1
                return -1
            return 0
            # If they are the same return -1
        except ValueError:
            # If the input is a value you cant float
            return 0

    def checkCurretDataValue(self):
        """Check the products in data if the price is correct."""
        jsonData = self.data.copy()
        for url in jsonData:
            if self.data[url] == "Deleted":
                self.data.pop(url)
                continue
            price = getPrice(url)
            if price != self.data[url]:
                self.data[url] = price
        self.saveData()


def window(args):
    """Create the window and go into event loop."""
    app = QApplication([])
    win = MyWindow(args)
    win.show()
    sys.exit(app.exec())


def create_table():
    """Do creates a table."""
    c.execute(
        'CREATE TABLE IF NOT EXISTS amazon(url TEXT, price TEXT, datestamp TEXT, unix REAL, id INTEGER PRIMARY KEY AUTOINCREMENT,)'
    )


def accesData(url: str):
    "Get the price that corresponds to the "
    c.execute("SELECT price FROM amazon WHERE url = ?",
              (url,)
              )
    data = c.fetchall()
    for x in data:
        print(x)


def getPrice(url) -> str:
    """Get price for the url thats passed as an argument."""
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
