from enum import Enum


class Message(str, Enum):
    SUBSCRIPTION_ADDED = "Added subscription to {SYMBOL}."

    def __str__(self) -> str:
        return self.value


class ErrorMessage(str, Enum):
    BOT_FOLDER_NOT_FOUND = (
        "``{BOT_NAME}`` bot is in the database but there is no subdirectory named "
        + "``{BOT_NAME}`` or the strategy.py file in this subdirectory. You "
        + "should either restore the subdirectory in the ``algo`` folder, "
        + "then restart <f3> Tmatic, or delete this bot using ``Bot menu``.\n"
    )
    BOT_MARKET_ERROR = (
        "There was an error loading {MODULE}:\n\n{EXCEPTION}\n\n"
        + "You are probably trying to use an exchange that is not connected. "
        + "You should either add the exchange in the .env file or correct "
        + "the strategy file or delete ``{BOT_NAME}`` using the ``Bot Menu``.\n"
    )
    BOT_LOADING_ERROR = (
        "There was an error loading {MODULE}:\n\n{EXCEPTION}\n\n"
        + "You should either correct the strategy file or delete ``{BOT_NAME}`` "
        + "using the ``Bot Menu``.\n"
    )
    IMPOSSIBLE_SUBSCRIPTION = (
        "The {SYMBOL} instrument has a {STATE} status, but is normally Open. "
        + "The instrument has probably expired, but in the database there are "
        + " still positions that should not exist. Check your trading history."
    )
    IMPOSSIBLE_DATABASE_POSITION = (
        "{SYMBOL} expired and a delivery in the amount of {DELIVERY} is "
        + "received from {MARKET} but there is a position of {POSITION} "
        + "{SYMBOL} in the database, which cannot be possible. The delivery "
        + "amount and the position in the database must be equal. This "
        + "delivery is not recorded in the database. Please check the "
        + "database and your trading history."
    )
    EMPTY_ORDERBOOK = (
        "Failed to place order {ORDER} because {SYMBOL} order book is empty."
    )

    def __str__(self) -> str:
        return self.value