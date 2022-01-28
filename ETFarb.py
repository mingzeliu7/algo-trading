# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import requests
import time

s= requests.Session()
s.headers.update({'X-API-key':'VCPOMBGC'})

#TARGET_SHARES = -100000 # UPDATE WHEN CASE STARTS FOR SELL OR BUY
#NUMBER_TRADERS = 4# UPDATE WHEN THE CASE STARS FOR THE NUMBER OF TEADESR IN THE ROOM

#EXPECTED_SHARES = 1000000 +(NUMBER_TRADERS/2)*100000
TICKER_SYMBOL = 'RFIN'

def get_tick_status():
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status']
   
def get_bid_ask(ticker):
    payload = {'ticker':ticker}
    resp = s.get('http://localhost:9999/v1/securities/book', params = payload)
    if resp.ok:
        book = resp.json()
        bid_book = book['bids']
        ask_book = book['asks']
       
        bid_price_fn = bid_book[0]['price']
        ask_price_fn = ask_book[0]['price']
       
        bid_volumn_fn = sum([item['quantity']-item['quantity_filled'] for item in bid_book if item['price'] == bid_price_fn])
        ask_volumn_fn = sum([item['quantity']-item['quantity_filled'] for item in ask_book if item['price'] == ask_price_fn])
       
        return bid_price_fn, bid_volumn_fn, ask_price_fn, ask_volumn_fn

def get_position(ticker):
   
    payload = {'ticker':ticker}
    resp = s.get('http://localhost:9999/v1/securities', params = payload)
   
    if resp.ok:
        securities = resp.json()
        current_position = securities[0]['position']
        market_volume = securities[0]['volume']
       
        return current_position, market_volume
    
    #new functions########################
def get_news():
    resp = s.get ('http://localhost:9999/v1/news')
    if resp.ok:
        news = resp.json()
    return news

def get_news_keys(news_item):
    if news_item[0]['body']=='':
        news_item[0]['body']= news_item[0]['headline'][12::]
        news_item[0]['headline']='NEWS ALERT'
        
    news_id = news_item[0]['news_id']# int
    news_tick = news_item[0]['tick'] # int
    news_headline = news_item[0]['headline']#str
    news_body = news_item[0]['body']#str
    
    return news_id, news_tick, news_headline, news_body



 
def main():
   
    tick, status = get_tick_status()
   
   # while status== 'ACTIVE':
    news_item=get_news()
    news_id, news_tick, news_headline, news_body =  get_news_keys(news_item)
    print(news_id)
    print(news_tick)
    print(news_headline)
    print(news_body)
    print(news_item)
    print("4")
    
    '''current_position, market_volume = get_position(TICKER_SYMBOL)
        bid_price, bid_volumn, ask_price, ask_volumn = get_bid_ask(TICKER_SYMBOL)
       
        market_percent = min(market_volume / EXPECTED_SHARES, 1)
        current_percent = current_position / TARGET_SHARES
       
        if market_percent > current_percent:
            shares_to_trade = abs(int((market_percent-current_percent) * TARGET_SHARES))
            shares_to_trade = min(shares_to_trade, abs(TARGET_SHARES - current_position))
        else:
            shares_to_trade = 0
       
        print('current_percent:', current_percent)
        print('market_percent:', market_percent)
        

       
        if TARGET_SHARES > 0 and current_position < TARGET_SHARES:
            if current_position == TARGET_SHARES - 1:
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_SYMBOL, 'type':'LIMIT', 'quantity': 1,'price':ask_price,'action':'BUY'})
            elif tick>=297:
                remaining_buy=TARGET_SHARES-current_position
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_SYMBOL, 'type':'LIMIT', 'quantity': remaining_buy,'price':ask_price,'action':'BUY'})
            else:
                shares_to_trade_active = int(shares_to_trade/2)
                shares_to_trade_passive = shares_to_trade-shares_to_trade_active
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_SYMBOL, 'type':'LIMIT', 'quantity': shares_to_trade_active,'price':ask_price,'action':'BUY'})
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_SYMBOL, 'type':'LIMIT', 'quantity': shares_to_trade_passive,'price':bid_price,'action':'BUY'})
              
   
        if TARGET_SHARES < 0 and current_position > TARGET_SHARES:
            if current_position==TARGET_SHARES + 1:
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_SYMBOL, 'type':'LIMIT', 'quantity': 1,'price':bid_price,'action':'SELL'})
            elif tick>=297: 
                remaining_sell = abs(current_position-TARGET_SHARES)
                resp = s.post('http://localhost:9999/v1/orders', params = {'ticker': TICKER_SYMBOL, 'type': 'LIMIT', 'quantity': remaining_sell, 'price': bid_price, 'action': 'SELL'})
            else :
                shares_to_trade_active = int(shares_to_trade/2)
                shares_to_trade_passive = shares_to_trade-shares_to_trade_active
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_SYMBOL, 'type':'LIMIT', 'quantity': shares_to_trade_active,'price':bid_price,'action':'SELL'})
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_SYMBOL, 'type':'LIMIT', 'quantity': shares_to_trade_passive,'price':ask_price,'action':'SELL'})
              
       
        time.sleep(0.5)
       
        s.post('http://localhost:9999/v1/commands/cancel',params={'ticker':TICKER_SYMBOL})
        
        if current_percent>=0.97:
            time.sleep(0.3)'''
            
        #tick, status = get_tick_status() #final oneeeeeee
   
             
if __name__=='__main__':
    main()    
