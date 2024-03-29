import logging
from collections import OrderedDict
from datetime import datetime

import pymysql
import pymysql.cursors

from api.api import WS
from api.init import Variables
from api.websockets import Websockets
from common.variables import Variables as var
from display.functions import info_display
from display.variables import Variables as disp
from functions import Function, funding, orders, trades

db = var.env["MYSQL_DATABASE"]


class Init(WS, Variables):
    def clear_params(self) -> None:
        self.connect_count += 1
        for emi, values in self.robots.items():
            self.robot_status[emi] = values["STATUS"]
        self.robots = OrderedDict()
        Function.rounding(self)
        self.frames = dict()

    def load_trading_history(self) -> None:
        """
        Load trading history (if any)
        """
        tm = datetime.utcnow()
        with open("history.ini", "r") as f:
            lst = list(f)
        if not lst or len(lst) < 1:
            message = "history.ini error. No data in history.ini"
            var.logger.error(message)
            raise Exception(message)
        lst = [x.replace("\n", "") for x in lst]
        last_history_time = datetime.strptime(lst[0], "%Y-%m-%d %H:%M:%S")
        if last_history_time > tm:
            message = "history.ini error. The time in the history.ini file is \
                greater than the current time."
            var.logger.error(message)
            raise Exception(message)
        count_val = 500
        history = self.trading_history(
            name=self.name, histCount=count_val, time=last_history_time
        )
        if history == "error":
            var.logger.error("history.ini error")
            exit(1)
        tmp = datetime(2000, 1, 1)
        """
        A premature exit from the loop is possible due to a small count_val
        value. This will happen in the case of a large number of trades or
        funding with the same time greater than or equal to count_val, when
        the first and last line will have the same transactTime accurate to
        the second.
        """
        while history:
            for row in history:
                data = Function.read_database(
                    self, execID=row["execID"], user_id=self.user_id
                )
                if not data:
                    Function.transaction(self, row=row, info=" History ")
            last_history_time = datetime.strptime(
                history[-1]["transactTime"][0:19], "%Y-%m-%dT%H:%M:%S"
            )
            history = self.trading_history(
                name=self.name, histCount=count_val, time=last_history_time
            )
            if last_history_time == tmp:
                break
            tmp = last_history_time
        if self.logNumFatal == 0:
            with open("history.ini", "w") as f:
                f.write(str(last_history_time))

    def account_balances(self) -> None:
        """
        Calculates the account by currency according to data from the MySQL
        'coins' table.
        """
        sql = (
            "select SYMBOL, CATEGORY from "
            + db
            + ".coins where ACCOUNT=%s \
            and MARKET=%s group by SYMBOL, CATEGORY"
        )
        var.cursor_mysql.execute(sql, (self.user_id, self.name))
        data = var.cursor_mysql.fetchall()
        symbols = list(map(lambda x: (x["SYMBOL"], x["CATEGORY"]), data))
        for symbol in symbols:
            Function.add_symbol(self, symbol=symbol)
        for currency in self.currencies:
            union = ""
            sql = "select sum(commiss) commiss, sum(sumreal) sumreal, \
                sum(funding) funding from ("
            for symbol in symbols:
                sql += (
                    union
                    + "select IFNULL(sum(COMMISS),0.0) commiss, \
                IFNULL(sum(SUMREAL),0.0) sumreal, IFNULL((select \
                sum(COMMISS) from "
                    + db
                    + ".coins where SIDE < 0 and ACCOUNT = "
                    + str(self.user_id)
                    + " and MARKET = '"
                    + self.name
                    + "' and CURRENCY = '"
                    + currency
                    + "' and SYMBOL = '"
                    + symbol[0]
                    + "' and CATEGORY = '"
                    + symbol[1]
                    + "'),0.0) funding from "
                    + db
                    + ".coins where SIDE >= 0 and ACCOUNT = "
                    + str(self.user_id)
                    + " and MARKET = '"
                    + self.name
                    + "' and CURRENCY = '"
                    + currency
                    + "' and SYMBOL = '"
                    + symbol[0]
                    + "' and CATEGORY = '"
                    + symbol[1]
                    + "'"
                )
                union = "union "
            sql += ") T"
            var.cursor_mysql.execute(sql)
            data = var.cursor_mysql.fetchall()
            self.accounts[currency]["COMMISS"] = float(data[0]["commiss"])
            self.accounts[currency]["SUMREAL"] = float(data[0]["sumreal"])
            self.accounts[currency]["FUNDING"] = float(data[0]["funding"])

    def load_orders(self) -> None:
        """
        Load Orders (if any)
        """
        myOrders = self.open_orders(self.name)
        copy = var.orders.copy()
        for clOrdID, order in copy.items():
            if order["MARKET"] == self.name:
                del var.orders[clOrdID]
        for val in reversed(myOrders):
            if val["leavesQty"] != 0:
                emi = ".".join(val["symbol"])
                if "clOrdID" not in val:
                    # The order was placed from the exchange interface
                    var.last_order += 1
                    clOrdID = str(var.last_order) + "." + emi
                    info_display(
                        self.name,
                        "Outside placement: price="
                        + str(val["price"])
                        + " side="
                        + val["side"]
                        + ". Assigned clOrdID="
                        + clOrdID,
                    )
                else:
                    clOrdID = val["clOrdID"]
                    s = clOrdID.split(".")
                    emi = ".".join(s[1:])
                    if emi not in self.robots:
                        self.robots[emi] = {
                            "STATUS": "NOT DEFINED",
                            "TIMEFR": None,
                            "EMI": emi,
                            "SYMBOL": val["symbol"],
                            "CATEGORY": val["symbol"][1],
                            "MARKET": self.name,
                            "POS": 0,
                            "VOL": 0,
                            "COMMISS": 0,
                            "SUMREAL": 0,
                            "LTIME": datetime.strptime(
                                val["transactTime"][0:19], "%Y-%m-%dT%H:%M:%S"
                            ),
                            "PNL": 0,
                            "CAPITAL": None,
                        }
                        message = (
                            "Robot EMI="
                            + emi
                            + ". Adding to 'robots' with STATUS='NOT DEFINED'"
                        )
                        info_display(self.name, message)
                        var.logger.info(message)
                var.orders[clOrdID] = {}
                var.orders[clOrdID]["EMI"] = emi
                var.orders[clOrdID]["leavesQty"] = val["leavesQty"]
                var.orders[clOrdID]["transactTime"] = val["transactTime"]
                var.orders[clOrdID]["price"] = val["price"]
                var.orders[clOrdID]["SYMBOL"] = val["symbol"]
                var.orders[clOrdID]["CATEGORY"] = val["symbol"][1]
                var.orders[clOrdID]["MARKET"] = self.name
                var.orders[clOrdID]["SIDE"] = val["side"]
                var.orders[clOrdID]["orderID"] = val["orderID"]
        for clOrdID, order in var.orders.items():
            order["clOrdID"] = clOrdID
            order["datetime"] = datetime.strptime(
                order["transactTime"][0:19], "%Y-%m-%dT%H:%M:%S"
            )
        orders.clear_all()
        values = list(var.orders.values())
        values.sort(key=lambda x: x["datetime"])
        var.orders = OrderedDict()
        for val in reversed(values):
            var.orders[val["clOrdID"]] = val
        for val in list(var.orders.values()):
            Function.fill_columns(
                self, func=Function.orders_display, table=orders, val=val
            )

    def initial_ticker_values(self) -> None:
        for symbol in self.symbol_list:
            self.ticker[symbol]["open_ask"] = self.ticker[symbol]["ask"]
            self.ticker[symbol]["open_bid"] = self.ticker[symbol]["bid"]
            self.ticker[symbol]["fundingRate"] = self.instruments[symbol]["fundingRate"]

    def load_database(self) -> None:
        """
        Download the latest trades and funding data from the database (if any)
        """
        sql = "select * from("
        union = ""
        for name in var.market_list:
            user_id = Websockets.connect[name].user_id
            sql += (
                union
                + "select ID, EMI, SYMBOL, CATEGORY, MARKET, SIDE, QTY, \
            PRICE, TTIME, COMMISS from "
                + db
                + ".coins where SIDE = -1 and ACCOUNT = "
                + str(user_id)
                + " and MARKET = '"
                + name
                + "' "
            )
            union = "union "
        sql += ") T order by TTIME desc limit " + str(disp.table_limit)
        var.cursor_mysql.execute(sql)
        data = var.cursor_mysql.fetchall()
        for val in data:
            val["SYMBOL"] = (val["SYMBOL"], val["CATEGORY"])
            Function.fill_columns(
                self, func=Function.funding_display, table=funding, val=val
            )
        sql = "select * from("
        union = ""
        for name in var.market_list:
            user_id = Websockets.connect[name].user_id
            sql += (
                union
                + "select ID, EMI, SYMBOL, CATEGORY, MARKET, SIDE, QTY, \
            TRADE_PRICE, TTIME, COMMISS, SUMREAL from "
                + db
                + ".coins where SIDE <> -1 and ACCOUNT = "
                + str(user_id)
                + " and MARKET = '"
                + name
                + "' "
            )
            union = "union "
        sql += ") T order by TTIME desc limit " + str(disp.table_limit)
        var.cursor_mysql.execute(sql)
        data = var.cursor_mysql.fetchall()
        for val in data:
            val["SYMBOL"] = (val["SYMBOL"], val["CATEGORY"])
            Function.fill_columns(
                self, func=Function.trades_display, table=trades, val=val
            )


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler("logfile.log")
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    handler.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(handler)
    logger.info("\n\nhello\n")

    return logger


def setup_database_connecion() -> None:
    try:
        var.connect_mysql = pymysql.connect(
            host=var.env["MYSQL_HOST"],
            user=var.env["MYSQL_USER"],
            password=var.env["MYSQL_PASSWORD"],
            database=var.env["MYSQL_DATABASE"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        var.cursor_mysql = var.connect_mysql.cursor()

    except Exception as error:
        var.logger.error(error)
        raise
