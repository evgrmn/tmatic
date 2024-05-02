import logging
import sqlite3
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from sqlite3 import Error

from api.api import WS, Markets
from api.init import Variables
from common.variables import Variables as var
from display.functions import info_display
from display.variables import Variables as disp
from functions import Function, funding, orders, trades

db_sqlite = var.env["SQLITE_DATABASE"]


class Init(WS, Variables):
    file_lock = threading.Lock()

    def clear_params(self: Markets) -> None:
        self.connect_count += 1
        for emi, values in self.robots.items():
            self.robot_status[emi] = values["STATUS"]
        self.robots = OrderedDict()
        # Function.rounding(self)
        self.frames = dict()
        self.account_disp = self.name + "\nAcc." + str(self.user_id) + "\n"

    def save_history_file(self: Markets, time: datetime):
        Init.file_lock.acquire(True)
        with open("history.ini", "r") as f:
            lst = list(f)
        with open("history.ini", "w") as f:
            for row in lst:
                row = row.replace("\n", "")
                res = row.split()
                if res[0] == self.name:
                    row = res[0] + " " + str(time)[:19]
                f.write(row + "\n")
        Init.file_lock.release()

    def load_trading_history(self: Markets) -> None:
        """
        Load trading history (if any)
        """
        tm = datetime.now(tz=timezone.utc)
        with open("history.ini", "r") as f:
            lst = list(f)
        last_history_time = ""
        for row in lst:
            row = row.replace("\n", "")
            res = row.split()
            if res:
                if res[0] == self.name:
                    time = " ".join(res[1:])
                    last_history_time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
                    last_history_time = last_history_time.replace(tzinfo=timezone.utc)
        if not last_history_time:
            message = self.name + " was not found in the history.ini file."
            var.logger.error(message)
            raise Exception(message)
        if last_history_time > tm:
            message = (
                "history.ini error. The time in the history.ini file is "
                + "greater than the current time."
            )
            var.logger.error(message)
            raise Exception(message)
        count_val = 500
        history = WS.trading_history(self, histCount=count_val, time=last_history_time)
        if history == "error":
            var.logger.error("history.ini error")
            exit(1)
        while history:
            for row in history:
                data = Function.select_database(  # read_database
                    self,
                    "select EXECID from coins where EXECID='%s' and account=%s"
                    % (row["execID"], self.user_id),
                )
                if not data:
                    Function.transaction(self, row=row, info=" History ")
            last_history_time = history[-1]["transactTime"]
            if self.logNumFatal == 0:
                Init.save_history_file(self, time=last_history_time)
            if len(history) < count_val:
                break
            history = WS.trading_history(
                self, histCount=count_val, time=last_history_time
            )

    def account_balances(self: Markets) -> None:
        """
        Calculates the account by currency according to data from the SQLite
        'coins' table.
        """
        data = Function.select_database(
            self,
            "select SYMBOL, CATEGORY from "
            + "coins where ACCOUNT=%s and MARKET='%s' group by SYMBOL, CATEGORY"
            % (self.user_id, self.name),
        )

        symbols = list(map(lambda x: (x["SYMBOL"], x["CATEGORY"], self.name), data))
        for symbol in symbols:
            Function.add_symbol(self, symbol=symbol)
        if not symbols:
            symbols = [("MUST_NOT_BE_EMPTY", "MUST_NOT_BE_EMPTY")]
        for currency in self.currencies:
            union = ""
            sql = (
                "select sum(commiss) commiss, sum(sumreal) sumreal, "
                + "sum(funding) funding from ("
            )
            for symbol in symbols:
                sql += (
                    union
                    + "select IFNULL(sum(COMMISS),0.0) commiss, "
                    + "IFNULL(sum(SUMREAL),0.0) sumreal, IFNULL((select "
                    + "sum(COMMISS) from "
                    + "coins where SIDE = 'Fund' and ACCOUNT = "
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
                    + "coins where SIDE <> 'Fund' and ACCOUNT = "
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
            data = Function.select_database(self, sql)
            settlCurrency = (currency, self.name)
            self.Result[settlCurrency].commission = float(data[0]["commiss"])
            self.Result[settlCurrency].funding = float(data[0]["funding"])
            self.Result[settlCurrency].sumreal = float(data[0]["sumreal"])
            self.Result[settlCurrency].result = 0

    def load_orders(self: Markets) -> None:
        """
        Load Orders (if any)
        """
        myOrders = WS.open_orders(self)
        copy = var.orders.copy()
        for clOrdID, order in copy.items():
            if order["MARKET"] == self.name:
                del var.orders[clOrdID]
        for val in reversed(myOrders):
            if val["leavesQty"] != 0:
                emi = ".".join(val["symbol"][:2])
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
                    emi = ".".join(s[1:3])
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
                            "LTIME": val["transactTime"],
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
        orders.clear_all()
        values = list(var.orders.values())
        values.sort(key=lambda x: x["transactTime"])
        var.orders = OrderedDict()
        for val in reversed(values):
            var.orders[val["clOrdID"]] = val
        for val in list(var.orders.values()):
            if val["MARKET"] == self.name:
                Function.fill_columns(
                    self, func=Function.orders_display, table=orders, val=val
                )

    def load_database(self: Markets) -> None:
        """
        Download the latest trades and funding data from the database (if any)
        """
        sql = (
            "select ID, EMI, SYMBOL, CATEGORY, MARKET, SIDE, QTY, "
            + "PRICE, TTIME, COMMISS from "
            + "coins where SIDE = 'Fund' and ACCOUNT = "
            + str(self.user_id)
            + " and MARKET = '"
            + self.name
            + "' "
            + "order by TTIME desc limit "
            + str(disp.table_limit)
        )
        data = Function.select_database(self, sql)
        for val in data:
            val["SYMBOL"] = (val["SYMBOL"], val["CATEGORY"], self.name)
            Function.fill_columns(
                self, func=Function.funding_display, table=funding, val=val
            )
        sql = (
            "select ID, EMI, SYMBOL, CATEGORY, MARKET, SIDE, QTY,"
            + "TRADE_PRICE, TTIME, COMMISS, SUMREAL from "
            + "coins where SIDE <> 'Fund' and ACCOUNT = "
            + str(self.user_id)
            + " and MARKET = '"
            + self.name
            + "' "
            + "order by TTIME desc limit "
            + str(disp.table_limit)
        )
        data = Function.select_database(self, sql)
        for val in data:
            val["SYMBOL"] = (val["SYMBOL"], val["CATEGORY"], self.name)
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
        var.connect_sqlite = sqlite3.connect(db_sqlite, check_same_thread=False)
        var.connect_sqlite.row_factory = sqlite3.Row
        var.cursor_sqlite = var.connect_sqlite.cursor()
        var.error_sqlite = Error

        sql_create_robots = """
        CREATE TABLE IF NOT EXISTS robots (
        EMI varchar(20) DEFAULT NULL UNIQUE,
        SYMBOL varchar(20) DEFAULT NULL,
        CATEGORY varchar(10) DEFAULT NULL,
        MARKET varchar(20) DEFAULT NULL,
        SORT tinyint DEFAULT NULL,
        DAT timestamp NULL DEFAULT CURRENT_TIMESTAMP,
        TIMEFR tinyint DEFAULT 0,
        CAPITAL int DEFAULT 0,
        MARGIN int DEFAULT 0)"""

        sql_create_coins = """
        CREATE TABLE IF NOT EXISTS coins (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        EXECID varchar(45) DEFAULT NULL,
        EMI varchar(25) DEFAULT NULL,
        REFER varchar(20) DEFAULT NULL,
        MARKET varchar(20) DEFAULT NULL,
        CURRENCY varchar(10) DEFAULT NULL,
        SYMBOL varchar(20) DEFAULT NULL,
        CATEGORY varchar(10) DEFAULT NULL,
        SIDE varchar(4) DEFAULT NULL,
        QTY decimal(20,8) DEFAULT NULL,
        QTY_REST decimal(20,8) DEFAULT NULL,
        PRICE decimal(20,8) DEFAULT NULL,
        THEOR_PRICE decimal(20,8) DEFAULT NULL,
        TRADE_PRICE decimal(20,8) DEFAULT NULL,
        SUMREAL decimal(30,12) DEFAULT NULL,
        COMMISS decimal(30,16) DEFAULT 0.0000000000000000,
        TTIME datetime DEFAULT NULL,
        DAT timestamp NULL DEFAULT CURRENT_TIMESTAMP,
        CLORDID int DEFAULT 0,
        ACCOUNT int DEFAULT 0)"""

        var.cursor_sqlite.execute(sql_create_robots)
        var.cursor_sqlite.execute(sql_create_coins)
        var.cursor_sqlite.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ID_UNIQUE ON coins (ID)"
        )
        var.cursor_sqlite.execute(
            "CREATE INDEX IF NOT EXISTS EXECID_ix ON coins (EXECID)"
        )
        var.cursor_sqlite.execute(
            "CREATE INDEX IF NOT EXISTS EMI_QTY_ix ON coins (EMI, QTY)"
        )
        var.cursor_sqlite.execute("CREATE INDEX IF NOT EXISTS SIDE_ix ON coins (SIDE)")
        var.connect_sqlite.commit()

    except Exception as error:
        var.logger.error(error)
        raise
