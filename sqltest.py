import datetime
import random
import sqlite3
import time
from dateutil import parser
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import style

conn = sqlite3.connect("amazon.db")
c = conn.cursor()


def getPriceFromDb(URL: str) -> int:
    """Read the database and return the price of the url in the arguments."""
    c.execute("SELECT url, price FROM amazon WHERE url = ? ORDER BY id DESC", (URL,))
    data = c.fetchall()
    print(f"data [0] is : {data[0]}")

    return data[0][0]


def getSaveData(url):
    c.execute(
        "SELECT price FROM amazon WHERE url = ?\
     ORDER BY unix DESC LIMIT 2",
        (url,),
    )
    data = c.fetchall()

    print(f"This is the data: {data[1]}")
    return data[0]


def getPriceFromDb2(URL: str) -> int:
    """Read the database and return the price of the url in the arguments."""
    c.execute("SELECT url, price FROM amazon ORDER BY id DESC")
    data = c.fetchall()
    print(f"data [0] is : {data}")
    value = [(1, 2)]
    print(f"values: {value[0][1]}")


def create_table():
    """Do creates a table."""
    c.execute(
        "CREATE TABLE IF NOT EXISTS amazon(url TEXT, price INTEGER,\
        datestamp TEXT, unix REAL, count REAL, id INTEGER PRIMARY KEY AUTOINCREMENT)"
    )


def getAllData():
    c.execute("SELECT * FROM amazon ORDER BY id DESC")
    data = c.fetchall()
    for row in data:
        print(row)


def getOneFromEachUrl():
    c.execute("SELECT id, price, url FROM amazon GROUP BY price")
    data = c.fetchall()
    for x in data:
        print(x)


def dynamic_data_entry():
    url = "holabro.com"
    for x in range(10):
        time.sleep(1)
        unix = time.time()
        date = str(
            datetime.datetime.fromtimestamp(unix).strftime("%Y-%m-%-d %H: %M: %S")
        )
        price = random.randrange(0, 10)
        c.execute(
            "INSERT INTO amazon (url, price, datestamp, unix)" "VALUES(?, ?, ?, ?)",
            (url, price, date, unix),
        )
    conn.commit()


def accesData(url):
    c.execute("SELECT price FROM amazon WHERE url= ? ORDER BY price DESC", ("hi",))
    data = c.fetchone()
    print("Hi")
    print(data)
    if data:
        print("hi there")


def deleteSomeRow(url):
    c.execute("DELETE FROM amazon WHERE url = ?", (url,))
    conn.commit()


def graph_data():
    c.execute('SELECT unix, price FROM amazon')
    data = c.fetchall()

    dates = []
    values = []

    for row in data:
        dates.append(datetime.datetime.fromtimestamp(row[0]))
        values.append(row[1])

    plt.plot_date(dates, values, '-')
    plt.show()


graph_data()


# create_table()
# dynamic_data_entry()
# getPriceFromDb("asdfas.com")
# getPriceFromDb2("asdfas.com")
# getSaveData("asdfas.com")
# getOneFromEachUrl()
# accesData("asdfas.com")
getAllData()
