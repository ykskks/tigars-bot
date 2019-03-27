import os
import sys
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime

app = Flask(__name__)

# get your environment variables
channel_secret = os.getenv('YOUR_CHANNEL_SECRET')
channel_access_token = os.getenv('YOUR_CHANNEL_ACCESS_TOKEN')

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

#time_zone = os.getenv('TZ')


@app.route("/")
def hello_world():
    return "hello world!"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


def game_scheduled():
    url = os.getenv('URL')
    today = datetime.date.today().strftime('%-m/%-d')
    res = requests.get(url).text
    soup = BeautifulSoup(res, 'html.parser')
    #check if there is a match scheduled today and return True if so
    for p in soup.find_all('p'):
        if p.string == today:
            return True
            break
    else:
        return False

def get_broadcast_info():
    url = os.getenv('URL')
    #get broadcasters table for today and extract broadcasters that is available for me
    broadcasters = pd.read_html(url)[0]
    broadcasters = broadcasters[(broadcasters['種別'] == '地上波') | (broadcasters['放送局'] == 'DAZN')].reset_index(drop=True)
    return broadcasters


@app.route("/push_broadcast_info", methods=['GET'])
def push_broadcast_info():
    today = datetime.date.today().strftime('%-m/%-d')
    
    if game_scheduled():
        broadcasters = get_broadcast_info()
        #試合はあるが中継がないとき
        if len(broadcasters) == 0:
            push_text = today + 'の中継予定なし\n'
        else:
            push_text = today + 'の中継予定:\n'
            for i in range(len(broadcasters)):
                broadcaster_name = broadcasters.loc[i, '放送局']
                broadcast_time = broadcasters.loc[i,  '時間']
                push_text += broadcaster_name + ' ' + broadcast_time + '\n'
    else:
        push_text = today + 'の試合予定なし:\n'

    to = os.getenv('YOUR_USER_ID')
    line_bot_api.push_message(to, TextSendMessage(text=push_text))

    return 'OK'



@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    txt = '\nオウム返ししたよ！'
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text+txt)
    )


if __name__ == "__main__":
    port = int(os.getenv('PORT'))
    app.run(host='0.0.0.0', port=port)