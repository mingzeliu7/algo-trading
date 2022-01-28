# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import requests
import time

s= requests.Session()
s.headers.update({'X-API-key':'MCGARHJ6'})

#TARGET_SHARES = -100000 # UPDATE WHEN CASE STARTS FOR SELL OR BUY
#NUMBER_TRADERS = 4# UPDATE WHEN THE CASE STARS FOR THE NUMBER OF TEADESR IN THE ROOM
MAX_SHARES = 25000
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

def get_news_keys(news_item,index):
    if news_item[index]['body']=='':
        news_item[index]['body']= news_item[index]['headline'][12::]
        news_item[index]['headline']='NEWS ALERT'
        
    news_id = news_item[index]['news_id']# int
    news_tick = news_item[index]['tick'] # int
    news_headline = news_item[index]['headline']#str
    news_body = news_item[index]['body']#str
    
    return news_id, news_tick, news_headline, news_body


 
def get_news_info(news_id, news_tick, news_headline, news_body):
    
    if news_body.find("$")!=-1:
        price= float(news_body[news_body.find("$")+1:news_body.find("$")+6])
    else:
        price=0
    if news_headline.find("Valuation")!=-1:
        ticker="C"
    else:
        ticker="S"
        
    return news_id, news_tick, price, ticker
#    
    
    
def main():
   

   tick, status = get_tick_status()
   prev_news=0
   current_news=0
   lower=[]
   upper=[]
   
   while status== 'ACTIVE':
       
        news_item=get_news()
        news_id, news_tick, news_headline, news_body = get_news_keys(news_item,0)
        news_id, news_tick, price, ticker = get_news_info(news_id, news_tick, news_headline, news_body)
   
   
    #news_item=get_news()
    #news_id, news_tick, news_headline, news_body =  get_news_keys(news_item,0)
    #g_trend, f_trend, eff = get_trend(news_headline, news_body)
    
    #print("title:",news_headline)
    #print("body:", news_body)
    #print("gold trend:", g_trend)
    #print("financial trend:", f_trend)
    #print("effective now:", eff)
    
    
        new_news=0
        current_news=news_id
        
        
#    while status=="ACTIVE":
        if current_news - prev_news > 0:
            new_news=1
   
  
        
        if new_news==1:
            news_item=get_news()
            news_id, news_tick, news_headline, news_body = get_news_keys(news_item,0)
            news_id, news_tick, price, ticker = get_news_info(news_id, news_tick, news_headline, news_body)
            if ticker=="S":
                print("Sprint Offer:", price)
            elif ticker=="C":
                lower_bound=price-((500-tick)/50)
                upper_bound=price+((500-tick)/50)
                lower.append(lower_bound)
                upper.append(upper_bound)
                print("Range:",round(max(lower),2),round(min(upper),2))
                
            
            
        
        
        prev_news = current_news
        
        
        
        
        tick, status = get_tick_status()
#    print(news_body.find("$"))
#    print(float(news_body[news_body.find("$")+1:news_body.find("$")+6]))
       
    
    
#        if current_news - prev_news==1:
#            new_news=1
#            
#        if new_news == 1:
#            
#            goal_tick = current_tick + 30
#            news_item=get_news()
#            news_id, news_tick, news_headline, news_body =  get_news_keys(news_item,0)
#            g_trend, f_trend, eff = get_trend(news_headline, news_body)
#            
#            current_news = news_id
            
            
#            while current_tick != goal_tick and goal_tick < 300:
#                
#                position_f = get_position("RFIN")[0]
#                if f_trend=="if" and position_f < 25000:
#                    shares_to_buy_f = min(5000, 25000 - position_f)
#                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': "RFIN", 'type':'LIMIT', 'quantity': shares_to_buy_f,'price':bid_price_f+0.02,'action':'BUY'})
#                elif f_trend=="df" and position_f > -25000:
#                    shares_to_sell_f = min(5000, position_f + 25000)
#                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': "RFIN", 'type':'LIMIT', 'quantity': shares_to_sell_f,'price':ask_price_f-0.02,'action':'SELL'})
#                
#                time.sleep(0.5)
#       
#                s.post('http://localhost:9999/v1/commands/cancel',params={'ticker':"RFIN"})
#                current_tick, status = get_tick_status()
#        
#        print("f price:", get_position("RFIN")[0])
#        
        
    
 
       
                     
if __name__=='__main__':
    main()    
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