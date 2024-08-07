import threading
from collections import OrderedDict
from datetime import datetime, timezone
from enum import Enum
from typing import Union

from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit
from api.deribit.agent import Agent as DeribitAgent
from api.deribit.ws import Deribit
from common.variables import Variables as var
from services import display_exception

from .variables import Variables


class MetaMarket(type):
    dictionary = dict()
    names = {"Bitmex": Bitmex, "Bybit": Bybit, "Deribit": Deribit}

    def __getitem__(self, item) -> Union[Bitmex, Bybit, Deribit]:
        if item not in self.names:
            raise ValueError(f"{item} not found")
        if item not in self.dictionary:
            self.dictionary[item] = self.names[item]()
            return self.dictionary[item]
        else:
            return self.dictionary[item]


class Markets(Bitmex, Bybit, Deribit, metaclass=MetaMarket):
    pass


class Agents(Enum):
    Bitmex = BitmexAgent
    Bybit = BybitAgent
    Deribit = DeribitAgent


class WS(Variables):
    def start_ws(self: Markets) -> None:
        """
        Loading instruments, orders, user ID, wallet balance, position
        information and initializing websockets.
        """

        def start_ws_in_thread():
            try:
                Markets[self.name].start()
            except Exception as exception:
                display_exception(exception)
                self.logNumFatal = "SETUP"

        def get_in_thread(method):
            try:
                method(self)
            except Exception as exception:
                display_exception(exception)
                self.logNumFatal = "SETUP"

        try:
            if Agents[self.name].value.get_active_instruments(self):
                return -1
        except Exception as exception:
            display_exception(exception)
            self.logger.error(self.name + " Instruments not loaded. Reboot.")
            return -1
        self.logNumFatal = ""
        try:
            if Agents[self.name].value.open_orders(self):
                return -1
        except Exception as exception:
            display_exception(exception)
            self.logger.error(self.name + " Orders not loaded. Reboot.")
            return -1
        try:
            threads = []
            t = threading.Thread(target=start_ws_in_thread)
            threads.append(t)
            t.start()
            t = threading.Thread(
                target=get_in_thread, args=(Agents[self.name].value.get_user,)
            )
            threads.append(t)
            t.start()
            t = threading.Thread(
                target=get_in_thread, args=(Agents[self.name].value.get_wallet_balance,)
            )
            threads.append(t)
            t.start()
            t = threading.Thread(
                target=get_in_thread, args=(Agents[self.name].value.get_position_info,)
            )
            threads.append(t)
            t.start()
            [thread.join() for thread in threads]
        except Exception as exception:
            display_exception(exception)
            self.logNumFatal = "SETUP"
        if self.logNumFatal:
            self.logger.error(
                self.name
                + ": The websocket is not running, or the user information, wallet balance or position information is not loaded. Reboot."
            )
            return -1
        var.queue_info.put(
            {
                "market": self.name,
                "message": "Connected to websocket.",
                "time": datetime.now(tz=timezone.utc),
                "warning": False,
            }
        )

        return 0

    def exit(self: Markets) -> None:
        """
        Closes websocket
        """
        Markets[self.name].exit()

    def get_active_instruments(self: Markets) -> OrderedDict:
        """
        Gets all active instruments from the exchange REST API.
        """

        return Agents[self.name].value.get_active_instruments(self)

    def get_user(self: Markets) -> Union[dict, None]:
        """
        Gets account info.
        """

        return Agents[self.name].value.get_user(self)

    def get_instrument(self: Markets, ticker: str, category: str) -> None:
        """
        Gets a specific instrument by symbol name and category.
        """

        return Agents[self.name].value.get_instrument(
            self, ticker=ticker, category=category
        )

    def get_position(self: Markets, symbol: tuple) -> None:
        """
        Gets information about an open position for a specific instrument.
        """

        return Agents[self.name].value.get_position(self, symbol=symbol)

    def trade_bucketed(
        self: Markets, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, None]:
        """
        Gets kline data.
        """

        return Agents[self.name].value.trade_bucketed(
            self, symbol=symbol, start_time=time, timeframe=timeframe
        )

    def trading_history(self: Markets, histCount: int, start_time: datetime) -> list:
        """
        Gets all trades and funding from the exchange for the period starting
        from 'time'
        """

        return Agents[self.name].value.trading_history(
            self, histCount=histCount, start_time=start_time
        )

    def open_orders(self: Markets) -> list:
        """
        Gets open orders.
        """

        return Agents[self.name].value.open_orders(self)

    def get_funds(self: Markets) -> list:
        """
        Cash in the account
        """

        return self.data["margin"]

    def place_limit(
        self: Markets, quantity: int, price: float, clOrdID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Places a limit order
        """

        return Agents[self.name].value.place_limit(
            self, quantity=quantity, price=price, clOrdID=clOrdID, symbol=symbol
        )

    def replace_limit(
        self: Markets, quantity: int, price: float, orderID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Moves a limit order
        """

        return Agents[self.name].value.replace_limit(
            self, quantity=quantity, price=price, orderID=orderID, symbol=symbol
        )

    def remove_order(self: Markets, order: dict) -> Union[list, None]:
        """
        Deletes an order
        """

        return Agents[self.name].value.remove_order(self, order=order)

    def get_wallet_balance(self: Markets) -> dict:
        """
        Obtain wallet balance, query asset information of each currency, and
        account risk rate information.
        """

        return Agents[self.name].value.get_wallet_balance(self)

    def get_position_info(self: Markets) -> dict:
        """
        Get Position Info
        """

        return Agents[self.name].value.get_position_info(self)

    def ping_pong(self: Markets) -> None:
        """
        Check if websocket is working
        """

        return Markets[self.name].ping_pong()
