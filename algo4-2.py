import requests
from time import sleep
from typing import List, Iterable
from collections import defaultdict
import sys
-
s = requests.Session()
s.headers.update({"X-API-key": "8DQ0XD4M"})
PORT = sys.argv[1] if len(sys.argv) >= 2 else "9999"
CONTRACT_SIZE = 10000
# PASSIVE_WAIT = 3
# OFF_BOOK_SIZE = 100000  # define 100000 away as off-book
# OFF_BOOK_PRICE_DIFF = 0.01  # also price difference needs to be over 0.02
REDEMPTION_COST = 0.0375
TRANSACTION_FEE = 0.01 * 2.5
MARKET_ORDER_SIZE = 2000
BUY_ETF_SPREAD = (
    REDEMPTION_COST + TRANSACTION_FEE
)  # we will redeem these ETF to balance out
SELL_ETF_SPREAD = TRANSACTION_FEE  # we will create these ETF to balance out
ASSET_LEASE_THRESHOLD = 100000
LEASE_MAX_SIZE = 100000

ETF = "INDX"
RGLD = "RGLD"
RFIN = "RFIN"

### Common Utils
def json_get(*args, **kwargs):
    return json_or_raise(s.get(*args, **kwargs))


def json_post(*args, **kwargs):
    return json_or_raise(s.post(*args, **kwargs))


def destruct(d, *keys):
    return tuple(d[k] for k in keys)


def json_or_raise(resp: requests.Response):
    if resp.ok:
        return resp.json()
    else:
        print(resp.text)
        resp.raise_for_status()


def wait(check_done, sleep_for=0.1):
    timeleft = 60
    while timeleft > 0:
        if check_done():
            break
        timeleft -= 1
        sleep(sleep_for)
    else:
        print("Timed-out")


### Case utils
def get_case():
    return json_get("http://localhost:" + PORT + "/v1/case")


def get_positions():
    return json_get("http://localhost:" + PORT + "/v1/securities")


def get_security(ticker: str):
    return json_get("http://localhost:9999/v1/securities", params={"ticker": ticker})[0]


def get_book(ticker: str):
    book = json_get(
        "http://localhost:" + PORT + "/v1/securities/book",
        params={"ticker": ticker, "limit": 100},
    )
    return book["bids"], book["asks"]


def market_order(ticker: str, quantity: int, side: str) -> int:
    return json_post(
        "http://localhost:" + PORT + "/v1/orders",
        params={
            "ticker": ticker,
            "type": "MARKET",
            "quantity": quantity,
            "action": side,
        },
    )["order_id"]


def wait_order_registrations(order_ids):
    unregistered = set(order_ids)
    # print("Registering", len(order_ids), "orders")
    timeout = 100
    while timeout > 0:
        order_id = unregistered.pop()
        resp = s.get(f"http://localhost:{PORT}/v1/orders/{order_id}")
        if not resp.ok:
            timeout -= 1
            # print(order_id, end=" ")
            unregistered.add(order_id)
            sleep(0.01)
        if not unregistered:
            break
    else:
        print("Register Timed-out")

    return order_ids


def get_PnL():
    resp = json_or_raise(s.get("http://localhost:" + PORT + "/v1/trader"))
    return resp["nlv"]


### Case Specific
def get_limits():
    return json_get("http://localhost:" + PORT + "/v1/limits")


def initialize_leases():
    # delete previous leases
    prev_leases = json_get("http://localhost:9999/v1/leases")
    for lease in prev_leases:
        s.delete(f"http://localhost:9999/v1/leases/{lease['id']}")
    if prev_leases:
        wait(lambda: len(json_get("http://localhost:9999/v1/leases")) == 0, 0.5)
    # create new leases
    creation_id = json_post(
        "http://localhost:" + PORT + "/v1/leases", params={"ticker": "ETF-Creation"}
    )["id"]
    redemption_id = json_post(
        "http://localhost:" + PORT + "/v1/leases", params={"ticker": "ETF-Redemption"}
    )["id"]
    wait(lambda: len(json_get("http://localhost:9999/v1/leases")) == 2, 0.5)

    def create(quantity: int):
        print("Create", quantity)
        while quantity > 0:
            size = min(quantity, LEASE_MAX_SIZE)
            tick_done = json_post(
                f"http://localhost:{PORT}/v1/leases/{creation_id}",
                params={
                    "from1": RGLD,
                    "quantity1": size,
                    "from2": RFIN,
                    "quantity2": size,
                },
            )["convert_finish_tick"]
            quantity -= size
            wait(lambda: get_case()["tick"] >= tick_done, 0.2)

    def redeem(quantity: int):
        print("Redeem", quantity)
        while quantity > 0:
            size = min(quantity, LEASE_MAX_SIZE)
            tick_done = json_post(
                f"http://localhost:{PORT}/v1/leases/{redemption_id}",
                params={
                    "from1": ETF,
                    "quantity1": size,
                    "from2": "CAD",
                    "quantity2": round(size * REDEMPTION_COST),
                },
            )["convert_finish_tick"]
            quantity -= size
            wait(lambda: get_case()["tick"] >= tick_done, 0.2)

    return create, redeem


def buy_stocks_sell_etf(quantity: int, abort_check):
    transacted = False
    while quantity > 0:
        if abort_check():
            break
        order_size = min(MARKET_ORDER_SIZE, quantity)
        security = {p["ticker"]: p for p in get_positions()}
        diff = security[ETF]["bid"] - security[RGLD]["ask"] - security[RFIN]["ask"]
        if diff > SELL_ETF_SPREAD:
            if diff > SELL_ETF_SPREAD * 2:
                order_size = min(MARKET_ORDER_SIZE * 2, quantity)
            wait_order_registrations(
                [
                    market_order(ETF, order_size, "SELL"),
                    market_order(RGLD, order_size, "BUY"),
                    market_order(RFIN, order_size, "BUY"),
                ]
            )
            print("+stocks-ETF", order_size, f"spread {diff:.4f}")
            quantity -= order_size
            transacted = True
        else:
            break
    return transacted


def sell_stocks_buy_etf(quantity: int, abort_check):
    transacted = False
    while quantity > 0:
        if abort_check():
            break
        order_size = min(MARKET_ORDER_SIZE, quantity)
        security = {p["ticker"]: p for p in get_positions()}
        diff = security[RGLD]["bid"] + security[RFIN]["bid"] - security[ETF]["ask"]
        if diff > BUY_ETF_SPREAD:
            if diff > BUY_ETF_SPREAD * 2:
                order_size = min(MARKET_ORDER_SIZE * 2, quantity)
            wait_order_registrations(
                [
                    market_order(ETF, order_size, "BUY"),
                    market_order(RGLD, order_size, "SELL"),
                    market_order(RFIN, order_size, "SELL"),
                ]
            )
            print("-stocks+ETF", order_size, f"spread {diff:.4f}")
            quantity -= order_size
            transacted = True
        else:
            break
    return transacted


def main():

    print("wait for case to start")
    wait((lambda: get_case()["status"] == "ACTIVE"), sleep_for=2)

    STOCK_LIMIT, CASH_LIMIT = get_limits()
    gross_limit, net_limit = destruct(STOCK_LIMIT, "gross_limit", "net_limit")
    # ETF count as 2
    gross_limit = gross_limit // 4
    # cash_limit = CASH_LIMIT["net_limit"]

    period = get_case()["ticks_per_period"]
    sleep(0.5)
    create, redeem = initialize_leases()

    while get_case()["status"] == "ACTIVE":
        tick = get_case()["tick"]
        print(tick, end=" ")
        if tick + 5 >= period:
            # clear position
            etf_position = get_security(ETF)["position"]
            if etf_position > 0:
                redeem(int(etf_position))
            elif etf_position < 0:
                create(-int(etf_position))
            break

        security = {p["ticker"]: p for p in get_positions()}
        sell_etf_quantity = min(
            # how much ETF can we sell
            gross_limit + security[ETF]["position"],
            # how much stock can we buy
            gross_limit - security[RFIN]["position"],
            gross_limit - security[RGLD]["position"],
        )
        sold = sell_etf_quantity and buy_stocks_sell_etf(
            sell_etf_quantity, abort_check=lambda: get_case()["tick"] + 6 >= period
        )

        buy_etf_quantity = min(
            # how much ETF can we buy
            gross_limit - security[ETF]["position"],
            # how much stock can we sell
            gross_limit + security[RFIN]["position"],
            gross_limit + security[RGLD]["position"],
        )

        bought = buy_etf_quantity and sell_stocks_buy_etf(
            buy_etf_quantity, abort_check=lambda: get_case()["tick"] + 6 >= period
        )

        if not bought and not sold:
            # reduce exposure, as lazy as possible to reduce redemption cost
            if security[ETF]["position"] >= ASSET_LEASE_THRESHOLD:
                redeem(ASSET_LEASE_THRESHOLD)
            elif security[ETF]["position"] <= -ASSET_LEASE_THRESHOLD:
                create(ASSET_LEASE_THRESHOLD)


if __name__ == "__main__":  # convenience to make it easier to run the code
    while True:
        main()
        sleep(10)
        print("P & L:", get_PnL())
