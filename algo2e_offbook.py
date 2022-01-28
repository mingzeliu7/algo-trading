import requests
from time import sleep
from typing import List, Iterable
from collections import defaultdict
import sys

s = requests.Session()
s.headers.update({"X-API-key": "3FX0NAIP"})
PORT = sys.argv[1] if len(sys.argv) >= 2 else "9999"
CONTRACT_SIZE = 5000
PASSIVE_WAIT = 4
MIN_SPREAD = 0.05
SPREAD_OUT_SIZE = 26000  # add my order to the 100000th on the book
OFF_BOOK_SIZE = 1000000  # define one million away as off-book
OFF_BOOK_PRICE_DIFF = 0.02


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
    return json_get(
        "http://localhost:" + PORT + "/v1/securities", params={"ticker": ticker}
    )[0]


def get_orders():
    return json_get(
        "http://localhost:" + PORT + "/v1/orders", params={"status": "OPEN"}
    )


def get_order(order_id: int):
    return json_get(f"http://localhost:{PORT}/v1/orders/{order_id}")


def cancel_order(order_id: int):
    s.delete(f"http://localhost:{PORT}/v1/orders/{order_id}")
    wait(lambda: get_order(order_id)["status"] != "OPEN")
    return get_order(order_id)


def cancel_all():
    s.post("http://localhost:" + PORT + "/v1/commands/cancel", params={"all": 1})
    # print("Cancelling previous orders...", end=" ")
    wait(lambda: len(get_orders()) == 0)


def get_book(ticker: str):
    book = json_get(
        "http://localhost:" + PORT + "/v1/securities/book",
        params={"ticker": ticker, "limit": 100},
    )
    return book["bids"], book["asks"]


def limit_order(ticker: str, quantity: int, side: str, price: float) -> int:
    return json_post(
        "http://localhost:" + PORT + "/v1/orders",
        params={
            "ticker": ticker,
            "type": "LIMIT",
            "quantity": quantity,
            "price": price,
            "action": side,
        },
    )["order_id"]


def wait_order_registrations(order_ids):
    unregistered = set(order_ids)
    # print("Registering", len(order_ids), "orders")
    timeout = 10
    while timeout > 0:
        order_id = unregistered.pop()
        resp = s.get(f"http://localhost:{PORT}/v1/orders/{order_id}")
        if not resp.ok:
            timeout -= 1
            # print(order_id, end=" ")
            unregistered.add(order_id)
            sleep(0.1)
        if not unregistered:
            break
    else:
        print("Register Timed-out")

    # print("Done")
    return order_ids


def get_PnL():
    resp = json_or_raise(s.get("http://localhost:" + PORT + "/v1/trader"))
    return resp["nlv"]


def is_off_book(my_order):
    ticker, price, side, status, order_id = destruct(
        my_order, "ticker", "price", "action", "status", "order_id"
    )
    bids, asks = get_book(ticker)
    book = bids if side == "BUY" else asks
    best_price = book[0]["price"]
    if abs(best_price - price) <= OFF_BOOK_PRICE_DIFF:
        return False
    cum_size = 0
    for order in book:
        # found my order before the off book size threshold
        if order["order_id"] == order_id:
            return False
        cum_size += order["quantity"] - order["quantity_filled"]
        if cum_size >= OFF_BOOK_SIZE:
            # off book if the order is still open
            print(best_price, "vs", price, round(abs(best_price - price), 4))
            return get_order(order_id)["status"] == "OPEN"


def wait_execution(order_ids: List[int], timeout_flag):
    # print("Executing", len(order_ids), "orders")
    order_idset = set(order_ids)
    while True:
        if timeout_flag():
            print("Refresh")
            break
        if not order_idset:
            print("Executed")
            break
        order_id = order_idset.pop()
        order = get_order(order_id)
        if order["status"] == "OPEN":
            if is_off_book(order):
                print("Off book")
                break
            order_idset.add(order_id)
            sleep(0.1)


### Case Specific
def get_limits():
    return json_get("http://localhost:" + PORT + "/v1/limits")[0]


def limit_order_sliced(
    ticker: str, total_quantity: int, side: str, price: float
) -> Iterable[int]:
    while total_quantity > 0:
        quantity = min(CONTRACT_SIZE, total_quantity)
        yield limit_order(ticker, quantity, side, price)
        total_quantity -= quantity


def update_spreads(spreads):
    for sec in get_positions():
        ticker = sec["ticker"]
        bids, asks = get_book(ticker)
        # use the liquid bid-ask spread
        bid, ask = determine_best_price(bids, asks)
        spreads[ticker] = (ask - bid) * 0.5 + spreads[ticker] * 0.5


def determine_best_price(bids, asks):
    """assume none of my orders are on the book"""
    best_prices = []
    for book in (bids, asks):
        cum_size = 0
        for order in book:
            cum_size += order["quantity"] - order["quantity_filled"]
            if cum_size >= SPREAD_OUT_SIZE:
                best_prices.append(order["price"])
                break
        else:
            best_prices.append(book[-1]["price"] if book else 0)
    if best_prices[0] == 0:
        best_prices[0] = best_prices[1] * 0.95
    if best_prices[1] == 0:
        best_prices[1] = best_prices[0] * 1.05
    return best_prices


def main():

    # wait for case to start
    wait((lambda: get_case()["status"] == "ACTIVE"), sleep_for=1)

    gross_limit = get_limits()["gross_limit"]
    period = get_case()["ticks_per_period"]

    spreads = defaultdict(lambda: 0)  # a running EWMA of spreads for each ticker

    while get_case()["status"] == "ACTIVE":
        tick = get_case()["tick"]
        if tick < 2:
            continue
        if tick + 1 >= period:
            break
        print(tick, end=" ")

        # determine the security to trade
        update_spreads(spreads)
        most_spread_ticker = max(spreads.keys(), key=spreads.get)
        # cancel all orders such that the positions are accurate
        cancel_all()
        # submit orders to clear positions of all other tickers
        positions = get_positions()
        mm_security = None
        order_ids = []
        for security in positions:
            if security["ticker"] == most_spread_ticker:
                mm_security = security
                continue
            elif security["position"] == 0:
                continue
            ticker, bid, ask, position = destruct(
                security, "ticker", "bid", "ask", "position"
            )
            if position > 0:
                order_ids.extend(
                    limit_order_sliced(ticker, position, "SELL", ask - 0.01)
                )
            elif position < 0:
                order_ids.extend(
                    limit_order_sliced(ticker, -position, "BUY", bid + 0.01)
                )
            print("Clear position", ticker, position)

        # market make the chosen ticker
        gross = get_limits()["gross"]
        room = gross_limit - gross
        position = mm_security["position"]
        buy_quantity = room - 2 * min(0, position)
        sell_quantity = room + 2 * max(0, position)
        #   choose the best prices at the first 100,000 non-self orders on both sides
        bids, asks = get_book(most_spread_ticker)
        buy_price, sell_price = determine_best_price(bids, asks)
        spread = round(sell_price - buy_price, 4)
        if spread < MIN_SPREAD:
            print("Not enough spread", spread, "adding spread 0.01")
            buy_price -= 0.01
            sell_price += 0.01
        order_ids.extend(
            limit_order_sliced(most_spread_ticker, sell_quantity, "SELL", sell_price)
        )
        order_ids.extend(
            limit_order_sliced(most_spread_ticker, buy_quantity, "BUY", buy_price)
        )
        print(
            "MM", most_spread_ticker, f"({buy_quantity},{sell_quantity})", spread,
        )
        wait_order_registrations(order_ids)
        # wait for execution
        wait_execution(order_ids, lambda: get_case()["tick"] > tick + PASSIVE_WAIT)


if __name__ == "__main__":  # convenience to make it easier to run the code
    while True:
        main()
        print("P & L:", get_PnL())
        sleep(20)

