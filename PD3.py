import requests
from time import sleep
from itertools import takewhile
import os

s = requests.Session()
s.headers.update({"X-API-key": "3FX0NAIP"})


def json_or_raise(resp: requests.Response):
    if resp.ok:
        return resp.json()
    else:
        resp.raise_for_status()


def get_news():
    news = json_or_raise(s.get("http://localhost:9999/v1/news"))
    return news


def get_estimates(news):
    estimates = {}
    for n in news:
        headline, body = n["headline"], n["body"]
        if "Private Information" in headline:
            ticker = headline.split()[-1]
            body_split = body.split()
            t, price = int(body_split[1]), float(body_split[-1][1:])
            price_range = (
                round(price - (300 - t) / 50, 4),
                round(price + (300 - t) / 50, 4),
            )
            if ticker in estimates:
                old_range = estimates[ticker]
                estimates[ticker] = (
                    max(old_range[0], price_range[0]),
                    min(old_range[1], price_range[1]),
                )
            else:
                estimates[ticker] = price_range
    return estimates


def get_tick_status():
    return json_or_raise(s.get("http://localhost:9999/v1/case"))


def get_position(ticker):
    resp = s.get("http://localhost:9999/v1/securities", params={"ticker": ticker})
    security = json_or_raise(resp)[0]
    return security["bid"], security["ask"], security["position"]


def main():

    #     wait for case to start
    waittime = 60
    while get_tick_status()["status"] != "ACTIVE" and waittime > 0:
        sleep(1)
        waittime -= 1
    #
    sleep(1)

    prevmsg = ""

    while get_tick_status()["status"] == "ACTIVE":
        msg = []

        estimates = get_estimates(get_news())
        combined = [0, 0]

        for ticker, price_range in sorted(estimates.items()):
            low, high = price_range
            combined[0] += low
            combined[1] += high
            bid, ask, position = get_position(ticker)
            if bid > high:
                msg.append(
                    f"{ticker.ljust(6)} SELL until {high} for {round(bid - high,1)}"
                )
            elif ask < low:
                msg.append(f"{ticker.ljust(6)} BUY  until {low} for {round(low - ask,1)}")
            else:
                msg.append(f"{ticker.ljust(6)} \t\t\t\t within range {price_range}")
        # price the ETF
        if len(estimates) == 2:
            low, high = combined
            ticker = "ETF"
            bid, ask, position = get_position(ticker)
            if bid > high:
                msg.append(
                    f"{ticker.ljust(6)} SELL until {high} for {round(bid - high,1)}"
                )
            elif ask < low:
                msg.append(f"{ticker.ljust(6)} BUY  until {low} for {round(low - ask,1)}")
            else:
                msg.append(f"{ticker.ljust(6)} \t\t\t\t within range {combined}")
        combined_msg = "\n".join(msg)
        if combined_msg != prevmsg:
            print(get_tick_status()["tick"],end="\n\n")
            print(combined_msg)
            prevmsg = combined_msg
        sleep(0.05)


if __name__ == "__main__":  # convenience to make it easier to run the code
    main()
