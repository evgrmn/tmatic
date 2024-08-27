import traceback
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Union

from api.bybit.errors import exception
from common.data import BotData, Bots, Instrument
from common.variables import Variables as var


def ticksize_rounding(price: float, ticksize: float) -> float:
    """
    Rounds the price depending on the tickSize value
    """
    arg = 1 / ticksize
    res = round(price * arg, 0) / arg

    return res


def time_converter(
    time: Union[int, float, str, datetime], usec=False
) -> Union[datetime, int]:
    """
    The datetime always corresponds to utc time, the timestamp always
    corresponds to local time.
    int, float      -> datetime (utc)
    datetime utc    -> Unix timestamp (local time)
    str utc         -> datetime (utc)
    """
    if isinstance(time, int) or isinstance(time, float):
        return datetime.fromtimestamp(time, tz=timezone.utc)
    elif isinstance(time, datetime):
        return int(time.timestamp() * 1000)
    elif isinstance(time, str):
        time = time.replace("T", " ")
        time = time.replace("Z", "")
        f = time.find("+")
        if f > 0:
            time = time[:f]
        if usec:
            try:
                dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")
            except Exception:
                dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(time[:19], "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt

    else:
        raise TypeError(type(time))


def exceptions_manager(cls):
    for attr in cls.__dict__:
        if callable(getattr(cls, attr)):
            if attr not in [
                "exit",
                "Position",
                "Instrument",
                "Account",
                "Result",
                "__init__",
            ]:
                setattr(cls, attr, exception(getattr(cls, attr)))
    return cls


def precision(number: float) -> int:
    r = str(number)
    if "e" in r:
        r = r.replace("e", "")
        r = r.replace(".", "")
        r = r.split("-")
        precision = len(r[0]) - 1 + int(r[1])
    elif "." in r:
        r = r.split(".")
        if int(r[1]) == 0:
            precision = 0
        else:
            precision = len(r[1])
    else:
        precision = 0

    return precision


def add_space(line: list) -> str:
    n = max(map(lambda x: len(x), line))
    lst = list()
    for l in line:
        lst.append((n - len(l)) * " " + l)

    return "\n".join(lst)


def close(markets):
    for bot_name in var.bot_thread_active:
        var.bot_thread_active[bot_name] = False
    for name in var.market_list:
        ws = markets[name]
        ws.exit()


def display_exception(exception) -> str:
    formated = "".join(
        traceback.format_exception(type(exception), exception, exception.__traceback__)
    )
    print(formated)

    return formated


def select_database(query: str) -> list:
    err_locked = 0
    while True:
        try:
            var.sql_lock.acquire(True)
            var.cursor_sqlite.execute(query)
            orig = var.cursor_sqlite.fetchall()
            var.sql_lock.release()
            data = []
            if orig:
                data = list(map(lambda x: dict(zip(orig[0].keys(), x)), orig))
            return data
        except Exception as e:  # var.error_sqlite
            if "database is locked" not in str(e):
                print("_____query:", query)
                var.logger.error("Sqlite Error: " + str(e) + ")")
                var.sql_lock.release()
                break
            else:
                err_locked += 1
                var.logger.error(
                    "Sqlite Error: Database is locked (attempt: "
                    + str(err_locked)
                    + ")"
                )
                var.sql_lock.release()


def insert_database(values: list, table: str) -> None:
    err_locked = 0
    while True:
        try:
            var.sql_lock.acquire(True)
            if table == "coins":
                var.cursor_sqlite.execute(
                    "insert into coins (EXECID,EMI,REFER,CURRENCY,SYMBOL,"
                    + "TICKER,CATEGORY,MARKET,SIDE,QTY,QTY_REST,PRICE,"
                    + "THEOR_PRICE,TRADE_PRICE,SUMREAL,COMMISS,CLORDID,TTIME,"
                    + "ACCOUNT) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    values,
                )
            elif table == "robots":
                var.cursor_sqlite.execute(
                    "insert into robots (EMI,STATE,TIMEFR) VALUES (?,?,?)",
                    values,
                )
            else:
                return "Sqlite Error: Unknown database table."
            var.connect_sqlite.commit()
            var.sql_lock.release()
            return None
        except Exception as ex:  # var.error_sqlite
            if "database is locked" not in str(ex):
                err_str = f"Sqlite Error: {str(ex)} for: {values[0]}"
                var.logger.error(err_str)
                var.sql_lock.release()
                return err_str
            else:
                err_locked += 1
                var.logger.error(
                    "Sqlite Error: Database is locked (attempt: "
                    + str(err_locked)
                    + ")"
                )
                var.connect_sqlite.rollback()
                var.sql_lock.release()


def update_database(query: list) -> Union[str, None]:
    err_locked = 0
    while True:
        try:
            var.sql_lock.acquire(True)
            var.cursor_sqlite.execute(query)
            var.connect_sqlite.commit()
            var.sql_lock.release()
            return None
        except Exception as e:  # var.error_sqlite
            if "database is locked" not in str(e):
                err_str = f"Sqlite Error: {str(e)}"
                var.logger.error(err_str)
                var.sql_lock.release()
                return err_str
            else:
                err_locked += 1
                var.logger.error(
                    "Sqlite Error: Database is locked (attempt: "
                    + str(err_locked)
                    + ")"
                )
                var.connect_sqlite.rollback()
                var.sql_lock.release()


def set_clOrdID(emi: str) -> str:
    var.last_order += 1
    clOrdID = f"{var.last_order}.{emi}"

    return clOrdID


def fill_order(emi: str, clOrdID: str, category: str, value: dict) -> None:
    if emi not in var.orders:
        var.orders[emi] = OrderedDict()
    var.orders[emi][clOrdID] = dict()
    var.orders[emi][clOrdID]["emi"] = emi
    var.orders[emi][clOrdID]["leavesQty"] = value["leavesQty"]
    var.orders[emi][clOrdID]["transactTime"] = value["transactTime"]
    var.orders[emi][clOrdID]["price"] = value["price"]
    var.orders[emi][clOrdID]["symbol"] = value["symbol"]
    var.orders[emi][clOrdID]["category"] = category
    var.orders[emi][clOrdID]["market"] = value["symbol"][1]
    var.orders[emi][clOrdID]["side"] = value["side"]
    var.orders[emi][clOrdID]["orderID"] = value["orderID"]
    var.orders[emi][clOrdID]["clOrdID"] = clOrdID


def fill_bot_position(
    bot_name: str, symbol: tuple, instrument: Instrument, user_id: int
) -> None:
    bot = Bots[bot_name]
    bot.bot_positions[symbol] = {
        "emi": bot_name,
        "symbol": instrument.symbol,
        "category": instrument.market,
        "market": instrument.market,
        "ticker": instrument.ticker,
        "position": 0,
        "volume": 0,
        "sumreal": 0,
        "commiss": 0,
        "ltime": None,
        "pnl": 0,
        "lotSize": instrument.minOrderQty,
        "currency": instrument.settlCurrency[0],
        "limits": instrument.minOrderQty,
    }
    # Checks if this bot has any records in the database on this instrument.
    qwr = (
        "select MARKET, SYMBOL, sum(abs(QTY)) as SUM_QTY, "
        + "sum(SUMREAL) as SUM_SUMREAL, sum(COMMISS) as "
        + "SUM_COMMISS, TTIME from (select * from coins where EMI = '"
        + bot_name
        + "' and SYMBOL = '"
        + instrument.symbol
        + "' and MARKET = '"
        + instrument.market
        + "' and ACCOUNT = "
        + str(user_id)
        + " and SIDE <> 'Fund' order by ID desc) T;"
    )
    data = select_database(qwr)[0]
    if data and data["SUM_QTY"]:
        bot.bot_positions[symbol]["volume"] = float(data["SUM_QTY"])
        bot.bot_positions[symbol]["sumreal"] = float(data["SUM_SUMREAL"])
        bot.bot_positions[symbol]["commiss"] = float(data["SUM_COMMISS"])


def timeframe_seconds(timefr: str) -> int:
    """
    Converts a time interval in a string to seconds.
    """
    timefr_minutes = var.timeframe_human_format[timefr]

    return timefr_minutes * 60


def bot_error(bot: BotData) -> str:
    if not bot.error_message:
        error = "None"
    else:
        error = bot.error_message["error_type"]

    return error


def kline_hi_lo_values(ws, symbol: tuple, instrument: Instrument) -> None:
    """
    Updates the high and low values of kline data when websocket updates the
    order book.

    Parameters
    ----------
    ws: Markets
        Bitmex, Bybit, Deribit
    symbol: tuple
        Instrument symbol in (symbol, market name) format, e.g.
        ("BTCUSD", "Bybit").
    instrument: Instrument
        The Instrument instance for this symbol.
    """
    if symbol in ws.klines:
        for timeframe in ws.klines[symbol].values():
            if timeframe["data"]:
                ask = instrument.asks[0][0]
                bid = instrument.bids[0][0]
                if ask > timeframe["data"][-1]["hi"]:
                    timeframe["data"][-1]["hi"] = ask
                if bid < timeframe["data"][-1]["lo"]:
                    timeframe["data"][-1]["lo"] = bid


def count_orders():
    """Temporarily created function for debugging"""
    count = 0
    for values in var.orders.values():
        for _ in values.keys():
            count += 1

    # print("___________________orders", count)
