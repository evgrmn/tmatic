import json
import time
from datetime import datetime
from typing import Union

import requests

from api.variables import Variables
from display.functions import info_display

from .api_auth import API_auth


class Send(Variables):
    def request(
        self,
        path: str = None,
        verb: str = None,
        postData=None,
        timeout=7,
        theorPrice=None,
    ) -> Union[dict, list, None]:
        """
        Sends a request to the exchange
        """

        def info_warn_err(whatNow, textNow, codeNow=0):
            if whatNow == "INFO":
                self.logger.info(textNow)
            elif whatNow == "WARN":
                self.logger.warning(textNow)
                if codeNow > self.logNumFatal:
                    self.logNumFatal = codeNow
            else:
                self.logger.error(textNow)
                if codeNow > self.logNumFatal:
                    self.logNumFatal = codeNow

        url = self.http_url + path
        cur_retries = 1
        auth = API_auth(self.api_key, self.api_secret)
        while True:
            stop_retries = cur_retries
            # Makes the request
            response = None
            try:
                if theorPrice is None:
                    info_warn_err(
                        "INFO",
                        "("
                        + url[0]
                        + url[1]
                        + url[2]
                        + url[3]
                        + url[4]
                        + ") sending %s to %s: %s"
                        % (verb, path, json.dumps(postData or "")),
                    )
                else:
                    info_warn_err(
                        "INFO",
                        "("
                        + url[0]
                        + url[1]
                        + url[2]
                        + url[3]
                        + url[4]
                        + ") sending %s to %s: %s, theor: %s"
                        % (
                            verb,
                            path,
                            json.dumps(postData or ""),
                            theorPrice,
                        ),
                    )
                req = requests.Request(verb, url, json=postData, auth=auth, params=None)
                prepped = self.session.prepare_request(req)
                response = self.session.send(prepped, timeout=timeout)
                # Make non-200s throw
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response is None:
                    raise e
                cur_retries += 1
                # 401 - Auth error. This is fatal.
                if response.status_code == 401:
                    info_warn_err(
                        "ERROR",
                        "API Key or Secret incorrect (401): " + response.text,
                        2001,
                    )  # stop all

                # 404 - can be thrown if order does not exist
                elif response.status_code == 404:
                    if verb == "DELETE" and postData:
                        info_warn_err(
                            "WARN",
                            "DELETE orderID=%s: not found (404)" % postData["orderID"],
                            response.status_code,
                        )
                    elif verb == "PUT" and postData:
                        info_warn_err(
                            "WARN",
                            "PUT orderID=%s: not found (404)" % postData["orderID"],
                            response.status_code,
                        )
                    else:
                        info_warn_err(
                            "ERROR",
                            "Unable to contact API (404). %s: %s"
                            % (url, json.dumps(postData or "")),
                            1001,
                        )

                # 429 - ratelimit. If orders are posted or put too often
                elif response.status_code == 429:
                    info_warn_err(
                        "WARN",
                        "Rate limit exceeded (429). %s: %s"
                        % (url, json.dumps(postData or "")),
                        response.status_code,
                    )
                    time.sleep(1)

                # 503 - The exchange temporary downtime. Try again
                elif response.status_code == 503:
                    error = response.json()["error"]
                    message = error["message"] if error else ""
                    info_warn_err(
                        "WARN",
                        message + " (503). %s: %s" % (url, json.dumps(postData or "")),
                        response.status_code,
                    )

                elif response.status_code == 400:
                    error = response.json()["error"]
                    message = error["message"].lower() if error else ""
                    if (
                        verb == "PUT" and "invalid ordstatus" in message
                    ):  # move order with origClOrdID does not exist. Probably already executed
                        info_warn_err(
                            "WARN",
                            error["message"]
                            + " (400). %s: %s" % (url, json.dumps(postData or "")),
                            response.status_code,
                        )
                    elif verb == "POST" and "duplicate clordid" in message:
                        info_warn_err(
                            "ERROR",
                            error["message"]
                            + " (400). %s: %s" % (url, json.dumps(postData or "")),
                            1,
                        )  # impossible situation => stop trading
                    elif "insufficient available balance" in message:
                        info_display(self.name, error["message"])
                        info_warn_err(
                            "ERROR",
                            error["message"]
                            + " (400). %s: %s" % (url, json.dumps(postData or "")),
                            2,
                        )
                    elif (
                        "request has expired" in message
                    ):  # This request has expired - `expires` is in the past
                        info_warn_err(
                            "WARN",
                            error["message"]
                            + " (400)."
                            + " Your computer's system time may be incorrect. %s: %s"
                            % (url, json.dumps(postData or "")),
                            998,
                        )
                    elif (
                        "too many open orders" in message
                    ):  # When limit of 200 orders reached
                        info_warn_err(
                            "WARN",
                            error["message"]
                            + " (400). %s: %s" % (url, json.dumps(postData or "")),
                            5,
                        )
                    else:  # Example: wrong parameters set (tickSize, lotSize, etc)
                        errCode = 3 if postData else 997
                        info_warn_err(
                            "ERROR",
                            error["message"]
                            + " (400 else). %s: %s" % (url, json.dumps(postData or "")),
                            errCode,
                        )
                else:  # Unknown error type
                    errCode = 4 if postData else 996
                    info_warn_err(
                        "ERROR",
                        "Unhandled %s: %s. %s: %s"
                        % (e, response.text, url, json.dumps(postData or "")),
                        errCode,
                    )
            except (
                requests.exceptions.Timeout
            ) as e:  # sometimes there is no answer during timeout period (currently = 7 sec).
                if postData:  # (POST, PUT or DELETE) => terminal reloads
                    self.timeoutOccurred = "Timed out on request"  # reloads terminal
                    errCode = 0
                else:
                    errCode = 999
                    cur_retries += 1
                info_warn_err(
                    "WARN",
                    "Timed out on request. %s: %s" % (url, json.dumps(postData or "")),
                    errCode,
                )
                info_display(self.name, "Websocket. Timed out on request")

            except requests.exceptions.ConnectionError as e:
                info_warn_err(
                    "ERROR",
                    "Unable to contact API: %s. %s: %s"
                    % (e, url, json.dumps(postData or "")),
                    1002,
                )
                info_display(self.name, "Websocket. Unable to contact API")
                cur_retries += 1
            if postData:  # trading orders (POST, PUT, DELETE)
                if cur_retries == stop_retries:  # means no errors
                    if self.timeoutOccurred == "":
                        pos_beg = response.text.find('"orderID":"') + 11
                        pos_end = response.text.find('"', pos_beg)
                        self.myOrderID = response.text[pos_beg:pos_end]
                    else:
                        self.myOrderID = self.timeoutOccurred
                    if self.logNumFatal < 1000:
                        self.logNumFatal = 0
                break
            else:
                if cur_retries > self.maxRetryRest:
                    info_warn_err("ERROR", "Max retries hit. Reboot", 1003)
                    info_display(self.name, "ERROR, Max retries hit. Reboot")
                    break
                if cur_retries == stop_retries:  # means no errors
                    if self.logNumFatal < 1000:
                        self.logNumFatal = 0
                    break
            if path == "/announcement/urgent":
                break
            else:
                time.sleep(3)
        self.time_response = datetime.utcnow()
        if response:
            return response.json()
        else:
            return None
