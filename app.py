import os
import sys
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime

app = Flask(__name__)

#get environment variables for the bot channel
channel_secret = os.getenv('YOUR_CHANNEL_SECRET')
channel_access_token = os.getenv('YOUR_CHANNEL_ACCESS_TOKEN')

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)


@app.route("/callback", methods=['POST'])
def callback():
    #get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    #get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    #handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    #if the sent message was in the stats list, reply with the latest info, else just reply with the same message as the sent message
    stats = ['順位', '試合', '勝利', '敗戦', '引分', '勝率', '勝差', '残試合', '得点', '失点', '本塁打', '盗塁', '打率', '防御率']
    if event.message.text in stats:
        url = 'https://baseball.yahoo.co.jp/npb/standings/'
        info = pd.read_html(url)[0]
        info = info[1:]
        teams = info[1]
        info.drop(1, axis=1, inplace=True)
        info.index = teams
        info.columns = stats

        info_wanted = info.loc['阪神', event.message.text]
        info_wanted = round(info_wanted, 2) if event.message.text == '防御率' else info_wanted

        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text=info_wanted + 'です！'))
    
    else:
        txt = '\nオウム返ししたよ！'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text+txt))


def game_scheduled():
    #check if there is a match scheduled today and return True if so
    url = os.getenv('URL')
    today = datetime.date.today().strftime('%-m/%-d')
    res = requests.get(url).text
    soup = BeautifulSoup(res, 'html.parser')
    
    for p in soup.find_all('p'):
        if p.string == today:
            return True
            break
    else:
        return False

def get_broadcast_info():
    #get broadcasters table for today and extract broadcasters that is available for me
    url = os.getenv('URL')
    broadcasters = pd.read_html(url)[0]
    broadcasters = broadcasters[(broadcasters['種別'] == '地上波') | (broadcasters['放送局'] == 'DAZN')].reset_index(drop=True)
    return broadcasters

@app.route("/push_broadcast_info", methods=['GET'])
def push_broadcast_info():
    today = datetime.date.today().strftime('%-m/%-d')
    
    if game_scheduled():
        broadcasters = get_broadcast_info()
        #when there is a game scheduled but no broadcasting 
        if len(broadcasters) == 0:
            push_text = today + 'の中継予定なし'
        else:
            push_text = today + 'の中継予定:\n'
            for i in range(len(broadcasters)):
                broadcaster_name = broadcasters.loc[i, '放送局']
                broadcast_time = broadcasters.loc[i,  '時間']
                push_text += broadcaster_name + ' ' + broadcast_time + '\n'
            push_text += '楽しみですね！'
    else:
        #when there is no game scheduled 
        push_text = today + 'の試合予定なし'

    to = os.getenv('YOUR_USER_ID')
    line_bot_api.push_message(to, TextSendMessage(text=push_text))

    return 'OK'


if __name__ == "__main__":
    port = int(os.getenv('PORT'))
    app.run(host='0.0.0.0', port=port)