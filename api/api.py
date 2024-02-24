from collections import OrderedDict
from datetime import datetime
from typing import Union

from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit


class WS(Bitmex, Bybit):
    select_ws = {"Bitmex": Bitmex.start, "Bybit": Bybit.start}
    get_active_instruments_agent = {
        "Bitmex": BitmexAgent.get_active_instruments,
        "Bybit": BybitAgent.get_active_instruments,
    }
    get_user_agent = {"Bitmex": BitmexAgent.get_user, "Bybit": BybitAgent.get_user}
    get_instrument_agent = {
        "Bitmex": BitmexAgent.get_instrument,
        "Bybit": BybitAgent.get_instrument,
    }
    get_position_agent = {
        "Bitmex": BitmexAgent.get_position,
        "Bybit": BybitAgent.get_position,
    }
    trade_bucketed_agent = {
        "Bitmex": BitmexAgent.trade_bucketed,
        "Bybit": BybitAgent.trade_bucketed,
    }
    trading_history_agent = {
        "Bitmex": BitmexAgent.trading_history,
        "Bybit": BybitAgent.trading_history,
    }

    def start_ws(self, name) -> None:
        self.select_ws[name](self)

    def get_active_instruments(self, name) -> OrderedDict:
        """
        Gets all active instruments from the exchange REST API.
        """

        return self.get_active_instruments_agent[name](self)

    def get_user(self, name: str) -> Union[dict, None]:
        """
        Gets account info.
        """

        return self.get_user_agent[name](self)

    def get_instrument(self, name: str, symbol: tuple) -> None:
        """
        Gets a specific instrument by symbol name and category.
        """

        return self.get_instrument_agent[name](self, symbol=symbol)

    def get_position(self, name: str, symbol: tuple) -> None:
        """
        Gets information about an open position for a specific instrument.
        """

        return self.get_position_agent[name](self, symbol=symbol)

    def trade_bucketed(
        self, name: str, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, None]:
        """
        Gets timeframe data.
        """

        return self.trade_bucketed_agent[name](
            self, symbol=symbol, time=time, timeframe=timeframe
        )

    def trading_history(self, name: str, histCount: int, time: datetime):
        """
        Gets all trades and funding from the exchange for the period starting
        from 'time'
        """

        return self.trading_history_agent[name](self, histCount=histCount, time=time)