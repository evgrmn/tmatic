import importlib
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Tuple, Union

import services as service
from api.api import WS, Markets
from api.init import Variables
from botinit.variables import Variables as bot
from common.data import Bots
from common.variables import Variables as var
from display.bot_menu import bot_manager
from display.functions import info_display
from display.messages import ErrorMessage, Message
from display.variables import TreeTable
from display.variables import Variables as disp
from functions import Function


class Init(WS, Variables):
    def load_robots(self: Markets) -> dict:
        """
        This function loads robot settings from the SQL database from the 'robots'
        table. Since all transactions for the current account are saved in the
        database, the function also checks all robots that have open positions,
        but are not in the 'robots' table. Such robots are also loaded. Their
        status is indicated as 'NOT DEFINED'. The program must see orders and
        trades made from the standard exchange web interface, so reserved robot
        names are provided for each instrument that match the symbol of the
        instrument. Using this names, transactions are taken into account and
        financial results are calculated in the database for each instrument
        separately from the financial results of individual robots. The status of
        such robots is 'RESERVED'.
        """
        union = ""
        qwr = "select * from ("
        for symbol in self.symbol_list:
            qwr += (
                union
                + "select * from robots where SYMBOL = '"
                + symbol[0]
                + "' and CATEGORY = '"
                + self.Instrument[symbol].category
                + "' "
            )
            union = "union "
        qwr += ") T where MARKET = '" + self.name + "' order by SORT"
        data = service.select_database(qwr)
        for robot in data:
            emi = robot["EMI"]
            self.robots[emi] = robot
            self.robots[emi]["STATUS"] = "WORK"
            self.robots[emi]["SYMBOL"] = (
                self.robots[emi]["SYMBOL"],
                self.name,
            )

        # Searching for unclosed positions by robots that are not in the 'robots' table

        qwr = (
            "select SYMBOL, TICKER, CATEGORY, EMI, POS from (select EMI, SYMBOL, TICKER, CATEGORY, "
            + "sum(QTY) POS from coins where MARKET = '"
            + self.name
            + "' and account = "
            + str(self.user_id)
            + " and SIDE <> 'Fund' group by EMI, SYMBOL, CATEGORY) res where POS <> 0"
        )
        defuncts = service.select_database(qwr)
        for defunct in defuncts:
            symbol = (defunct["SYMBOL"], self.name)
            for emi in self.robots:
                if defunct["EMI"] == emi:
                    break
            else:
                emi = defunct["EMI"]
                if defunct["CATEGORY"] == "spot":
                    status = "RESERVED"
                    emi = symbol[0]
                elif symbol in self.symbol_list:
                    status = "NOT DEFINED"
                else:
                    status = "NOT IN LIST"
                self.robots[emi] = {
                    "SYMBOL": symbol,
                    "TICKER": defunct["TICKER"],
                    "CATEGORY": defunct["CATEGORY"],
                    "MARKET": self.name,
                    "POS": defunct["POS"],
                    "EMI": defunct["EMI"],
                    "STATUS": status,
                    "TIMEFR": "None",
                    "CAPITAL": "None",
                }

        # Adding RESERVED robots

        union = ""
        qwr = "select * from ("
        for symbol in self.symbol_list:
            qwr += (
                union
                + "select * from (select EMI, SYMBOL, TICKER, CATEGORY, ACCOUNT, MARKET, "
                + "sum(QTY) POS from coins where SIDE <> 'Fund' group by EMI, "
                + "SYMBOL, CATEGORY, ACCOUNT, MARKET) res where EMI = '"
                + symbol[0]
                + "' and CATEGORY = '"
                + self.Instrument[symbol].category
                + "' "
            )
            union = "union "
        qwr += (
            ") T where MARKET = '" + self.name + "' and ACCOUNT = " + str(self.user_id)
        )
        reserved = service.select_database(qwr)
        for symbol in self.symbol_list:
            for res in reserved:
                if symbol == (res["SYMBOL"], self.name):
                    pos = reserved[0]["POS"]
                    break
            else:
                pos = 0
            # if pos != 0:
            emi = symbol[0]
            self.robots[emi] = {
                "EMI": emi,
                "SYMBOL": symbol,
                "TICKER": self.Instrument[symbol].ticker,
                "CATEGORY": self.Instrument[symbol].category,
                "MARKET": self.name,
                "POS": pos,
                "STATUS": "RESERVED",
                "TIMEFR": "None",
                "CAPITAL": "None",
            }

        # Loading all transactions and calculating financial results for each robot

        for emi, robot in self.robots.items():
            Function.add_symbol(
                self,
                symbol=robot["SYMBOL"][0],
                ticker=robot["TICKER"],
                category=robot["CATEGORY"],
            )
            if isinstance(emi, tuple):
                _emi = emi[0]
            else:
                _emi = emi
            sql = (
                "SELECT IFNULL(sum(SUMREAL), 0) SUMREAL, IFNULL(sum(CASE WHEN "
                + "SIDE = 'Fund' THEN 0 ELSE QTY END), 0) "
                + "POS, IFNULL(sum(CASE WHEN SIDE = 'Fund' THEN 0 ELSE abs(QTY) "
                + "END), 0) VOL, IFNULL(sum(COMMISS), 0) "
                + "COMMISS, IFNULL(max(TTIME), '1900-01-01 01:01:01.000000') LTIME "
                + "FROM (SELECT SUMREAL, SIDE, QTY, COMMISS, TTIME FROM coins WHERE MARKET "
                + "= '%s' AND EMI = '%s' AND ACCOUNT = %s AND CATEGORY = '%s') aa"
                % (self.name, _emi, self.user_id, robot["CATEGORY"])
            )
            data = service.select_database(sql)
            for row in data:
                for col in row:
                    robot[col] = row[col]
                    if col == "POS" or col == "VOL":
                        robot[col] = round(
                            robot[col], self.Instrument[robot["SYMBOL"]].precision
                        )
                    if col == "COMMISS" or col == "SUMREAL":
                        robot[col] = float(robot[col])
                    if col == "LTIME":
                        robot[col] = service.time_converter(time=robot[col], usec=True)
            if robot["CATEGORY"] == "spot":
                robot["PNL"] = "None"
                robot["POS"] = "None"
            else:
                robot["PNL"] = 0
            robot["lotSize"] = self.Instrument[robot["SYMBOL"]].minOrderQty

        return 0

    def download_data(
        self, start_time: datetime, target: datetime, symbol: tuple, timeframe: int
    ) -> Tuple[Union[list, None], Union[datetime, None]]:
        res = list()
        while target > start_time:
            data = WS.trade_bucketed(
                self, symbol=symbol, time=start_time, timeframe=timeframe
            )
            if data:
                last = start_time
                res += data
                message = (
                    self.name
                    + " - loading klines, symbol="
                    + str(symbol)
                    + ", startTime="
                    + str(start_time)
                    + ", received: "
                    + str(len(res))
                    + " records."
                )
                start_time = data[-1]["timestamp"] + timedelta(minutes=timeframe)
                var.logger.info(message)
                if last == start_time or target <= data[-1]["timestamp"]:
                    return res

            else:
                message = (
                    "When downloading trade/bucketed data NoneType was recieved. Reboot"
                )
                var.logger.error(message)
                return None
        self.logNumFatal = ""
        return res

    def load_frames(
        self: Markets,
        symbol: tuple,
        timefr: int,
        frames: dict,
    ) -> Union[dict, None]:
        """
        Loading kline data from the exchange server. Data is recorded
        in files for each timeframe. Every time you reboot the files are
        overwritten.
        """
        self.filename = Function.timeframes_data_filename(
            self, symbol=symbol, timefr=timefr
        )
        with open(self.filename, "w"):
            pass
        target = datetime.now(tz=timezone.utc)
        target = target.replace(second=0, microsecond=0)
        start_time = target - timedelta(
            minutes=bot.CANDLESTICK_NUMBER * timefr - timefr
        )
        delta = timedelta(minutes=target.minute % timefr + (target.hour * 60) % timefr)
        target -= delta

        # Loading timeframe data

        res = Init.download_data(
            self,
            start_time=start_time,
            target=target,
            symbol=symbol,
            timeframe=timefr,
        )
        if not res:
            return None

        # Bitmex bug fix. Bitmex can send data with the next period's
        # timestamp typically for 5m and 60m.
        if target < res[-1]["timestamp"]:
            delta = timedelta(minutes=timefr)
            for r in res:
                r["timestamp"] -= delta

        # The 'frames' array is filled with timeframe data.

        if res[0]["timestamp"] > res[-1]["timestamp"]:
            res.reverse()
        for num, row in enumerate(res):
            tm = row["timestamp"] - timedelta(minutes=timefr)
            frames[symbol][timefr]["data"].append(
                {
                    "date": (tm.year - 2000) * 10000 + tm.month * 100 + tm.day,
                    "time": tm.hour * 10000 + tm.minute * 100,
                    "bid": float(row["open"]),
                    "ask": float(row["open"]),
                    "hi": float(row["high"]),
                    "lo": float(row["low"]),
                    "datetime": tm,
                }
            )
            if num < len(res[:-1]) - 1:
                Function.save_timeframes_data(
                    self,
                    frame=frames[symbol][timefr]["data"][-1],
                )
        frames[symbol][timefr]["time"] = tm

        message = (
            "Downloaded missing data, symbol=" + str(symbol) + " TIMEFR=" + str(timefr)
        )
        var.logger.info(message)

        return frames

    def init_timeframes(self: Markets) -> Union[dict, None]:
        def append_new(frames, symbol, timefr, time):
            frames[symbol][timefr] = {
                "time": time,
                "robots": [],
                "open": 0,
                "data": [],
            }
            frames[symbol][timefr]["robots"].append(emi)

            return frames

        success = []

        def get_in_thread(symbol, timefr, frames, number):
            nonlocal success
            res = Init.load_frames(
                self,
                symbol=symbol,
                timefr=timefr,
                frames=frames,
            )
            if not res:
                message = (
                    str(symbol) + " " + str(timefr) + " min kline data was not loaded!"
                )
                var.logger.error(message)
                return
            success[number] = "success"

        for emi in self.robots:
            # Initialize candlestick timeframe data using 'TIMEFR' fields
            # expressed in minutes.
            if self.robots[emi]["TIMEFR"] != "None":
                time = datetime.now(tz=timezone.utc)
                symbol = self.robots[emi]["SYMBOL"]
                timefr = self.robots[emi]["TIMEFR"]
                try:
                    self.frames[symbol][timefr]["robots"].append(emi)
                except KeyError:
                    try:
                        self.frames = append_new(self.frames, symbol, timefr, time)
                    except KeyError:
                        self.frames[symbol] = dict()
                        self.frames = append_new(self.frames, symbol, timefr, time)
        threads = []
        for symbol, timeframes in self.frames.items():
            for timefr in timeframes.keys():
                success.append(None)
                t = threading.Thread(
                    target=get_in_thread,
                    args=(symbol, timefr, self.frames, len(success) - 1),
                )

                threads.append(t)
                t.start()

        [thread.join() for thread in threads]
        for s in success:
            if not s:
                return

        return "success"

    def delete_unused_robot(self: Markets) -> None:
        """
        Deleting unused robots (if any)
        """
        emi_in_orders = set()
        for val in self.orders.values():
            emi_in_orders.add(val["EMI"])
        for emi in self.robots.copy():
            symbol = tuple(emi.split(".")) + (self.name,)
            if self.robots[emi]["STATUS"] in ("WORK", "OFF"):
                pass
            elif symbol in self.symbol_list:
                self.robots[emi]["STATUS"] = "RESERVED"
            elif self.robots[emi]["POS"] == 0 and emi not in emi_in_orders:
                info_display(self.name, "Robot EMI=" + emi + ". Deleting from 'robots'")
                del self.robots[emi]


def add_subscription(subscriptions: list) -> None:
    for symbol in subscriptions:
        if symbol[1] in var.market_list:
            ws = Markets[symbol[1]]
            ws.positions[symbol] = {"POS": 0}
            ws.symbol_list.append(symbol)
            ws.subscribe_symbol(symbol=symbol)
            qwr = (
                "select MARKET, SYMBOL, sum(abs(QTY)) as SUM_QTY from coins where "
                + "SYMBOL = '"
                + symbol[0]
                + "' and SIDE <> 'Fund' and market = '"
                + symbol[1]
                + "' and ACCOUNT = "
                + str(ws.user_id)
                + ";"
            )
            data = service.select_database(qwr)
            ws.Instrument[symbol].volume = data[0]["SUM_QTY"]
        else:
            message = (
                "You are trying to subscribe "
                + str(symbol)
                + " but "
                + symbol[1]
                + " is not active. Check the .env file."
            )
            var.logger.warning(message)
            var.queue_info.put(
                {
                    "market": symbol[1],
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": True,
                }
            )


def load_bots() -> None:
    """
    Loading bots into the new Bot class is under development.
    """

    qwr = "select * from robots order by DAT;"

    data = service.select_database(qwr)
    for value in data:
        # if value["MARKET"] in var.market_list:
        bot = Bots[value["EMI"]]
        # bot.name = value["EMI"]
        # bot.market = value["MARKET"]
        bot.timefr = value["TIMEFR"]
        bot.created = value["DAT"]
        bot.updated = value["UPDATED"]
        bot.state = value["STATE"]
        bot.position = dict()

    # Loading volumes for subscribed instruments

    if var.market_list:
        union = ""
        sql = ""
        for market in var.market_list:
            ws = Markets[market]
            sql += union
            qwr = (
                "select MARKET, SYMBOL, sum(QTY) as SUM_QTY from (select abs(QTY) "
                + "as QTY, MARKET, SYMBOL, SIDE, ACCOUNT from coins where "
            )
            _or = ""
            lst = ws.symbol_list.copy()
            if not lst:
                lst = [("MUST_NOT_BE_EMPTY", "MUST_NOT_BE_EMPTY")]
            for symbol in lst:
                qwr += _or
                qwr += "SYMBOL = '" + symbol[0] + "'"
                _or = " or "
            qwr += (
                ") T where SIDE <> 'Fund' and MARKET = '"
                + ws.name
                + "' and ACCOUNT = "
                + str(ws.user_id)
                + " group by SYMBOL, MARKET"
            )
            sql += qwr
            union = " union "
        sql += ";"
        data = service.select_database(sql)
        for value in data:
            ws = Markets[value["MARKET"]]
            symbol = (value["SYMBOL"], value["MARKET"])
            instrument = ws.Instrument[symbol]
            precision = instrument.precision
            instrument.volume = round(float(value["SUM_QTY"]), precision)

    # Searching for unclosed positions by bots that are not in the 'robots'
    # table. If found, EMI becomes the default SYMBOL name. If such a SYMBOL
    # is not subscribed, it is added to the subscription.

    qwr = (
        "select SYMBOL, TICKER, CATEGORY, EMI, POS, PNL, MARKET, TTIME from (select "
        + "EMI, SYMBOL, TICKER, CATEGORY, sum(QTY) POS, sum(SUMREAL) PNL, MARKET, "
        + "TTIME from coins where SIDE <> 'Fund' group by EMI, SYMBOL, "
        + "MARKET) res where POS <> 0;"
    )
    data = service.select_database(qwr)
    subscriptions = list()
    for value in data:
        if value["MARKET"] in var.market_list:
            name = value["EMI"]
            if name not in Bots.keys():
                ws = Markets[value["MARKET"]]
                Function.add_symbol(
                    ws,
                    symbol=value["SYMBOL"],
                    ticker=value["TICKER"],
                    category=value["CATEGORY"],
                )
                if isinstance(list(ws.ticker.keys())[0], str):
                    symbol = ws.ticker[value["TICKER"]]
                else:
                    symbol = ws.ticker[(value["TICKER"], value["CATEGORY"])]

                # Change EMI to default SYMBOL name.

                if symbol != value["EMI"]:
                    qwr = "select ID, EMI, SYMBOL from coins where EMI = '%s'" % (
                        value["EMI"]
                    )
                    data = service.select_database(qwr)
                    for row in data:
                        qwr = "update coins set EMI = '%s' where ID = %s;" % (
                            symbol,
                            row["ID"],
                        )
                        service.update_database(query=qwr)
                symb = (symbol, ws.name)
                if symb not in ws.symbol_list:
                    if ws.Instrument[symb].state == "Open":
                        subscriptions.append(symb)
                        message = Message.SUBSCRIPTION_ADDED.format(SYMBOL=symb)
                        var.logger.info(message)
                    else:
                        message = ErrorMessage.IMPOSSIBLE_SUBSCRIPTION.format(
                            SYMBOL=symb, STATE=ws.Instrument[symb].state
                        )
                        var.logger.warning(message)
                        var.queue_info.put(
                            {
                                "market": "",
                                "message": message,
                                "time": datetime.now(tz=timezone.utc),
                                "warning": True,
                            }
                        )
    add_subscription(subscriptions=subscriptions)

    # Loading trades and summing up the results for each bot.

    for name in Bots.keys():
        qwr = (
            "select * from (select SYMBOL, CATEGORY, MARKET, TICKER, "
            + "ifnull(sum(SUMREAL), 0) SUMREAL, ifnull(sum(case when SIDE = "
            + "'Fund' then 0 else QTY end), 0) POS, ifnull(sum(case when SIDE "
            + "= 'Fund' then 0 else abs(QTY) end), 0) VOL, ifnull(sum(COMMISS)"
            + ", 0) COMMISS, ifnull(max(TTIME), '1900-01-01 01:01:01.000000') "
            + "LTIME from coins where EMI = '"
            + name
            + "' group by SYMBOL) T;"
        )
        data = service.select_database(qwr)
        for value in data:
            symbol = (value["SYMBOL"], value["MARKET"])
            if value["MARKET"] in var.market_list:
                ws = Markets[value["MARKET"]]
                instrument = ws.Instrument[symbol]
                bot = Bots[name]
                precision = instrument.precision
                bot.position[symbol] = {
                    "emi": name,
                    "symbol": value["SYMBOL"],
                    "category": value["CATEGORY"],
                    "market": value["MARKET"],
                    "ticker": value["TICKER"],
                    "position": round(float(value["POS"]), precision),
                    "volume": round(float(value["VOL"]), precision),
                    "sumreal": float(value["SUMREAL"]),
                    "commiss": float(value["COMMISS"]),
                    "ltime": service.time_converter(time=value["LTIME"], usec=True),
                    "pnl": 0,
                    "lotSize": instrument.minOrderQty,
                    "currency": instrument.settlCurrency,
                }
                if instrument.category == "spot":
                    bot.position[symbol]["pnl"] = "None"
                    bot.position[symbol]["position"] = "None"
            else:
                message = (
                    name
                    + " bot has open position on "
                    + str(symbol)
                    + ", but "
                    + value["MARKET"]
                    + " is not enabled. Position on "
                    + str(symbol)
                    + " ignored. Add "
                    + value["MARKET"]
                    + " to the .env file."
                )
                var.logger.warning(message)
                var.queue_info.put(
                    {
                        "market": "",
                        "message": message,
                        "time": datetime.now(tz=timezone.utc),
                        "warning": True,
                    }
                )

    # Importing the strategy.py bot files

    for bot_name in Bots.keys():
        module = "algo." + bot_name + "." + bot_manager.strategy_file.split(".")[0]
        try:
            importlib.import_module(module)
        except ModuleNotFoundError:
            message = ErrorMessage.BOT_FOLDER_NOT_FOUND.format(BOT_NAME=bot_name)
            var.logger.warning(message)
            var.queue_info.put(
                {
                    "market": "",
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": True,
                }
            )
            Bots[bot_name].error_message = message
        except AttributeError as exception:
            message = ErrorMessage.BOT_MARKET_ERROR.format(
                EXCEPTION="AttributeError: " + str(exception),
                BOT_NAME=bot_name,
            )
            var.logger.warning(message)
            var.queue_info.put(
                {
                    "market": "",
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": True,
                }
            )
            Bots[bot_name].error_message = message
        except ValueError as exception:
            message = ErrorMessage.BOT_MARKET_ERROR.format(
                MODULE=module,
                EXCEPTION="ValueError: " + str(exception),
                BOT_NAME=bot_name,
            )
            var.logger.warning(message)
            var.queue_info.put(
                {
                    "market": "",
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": True,
                }
            )
            Bots[bot_name].error_message = message
        except Exception as exception:
            formated = service.display_exception(exception=exception)
            message = ErrorMessage.BOT_LOADING_ERROR.format(
                MODULE=module, EXCEPTION=exception, BOT_NAME=bot_name
            )
            var.logger.warning(message)
            var.queue_info.put(
                {
                    "market": "",
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": True,
                }
            )

    """for market in var.market_list:
        ws = Markets[market]
        print(ws.kline_list)

    os.abort()"""
