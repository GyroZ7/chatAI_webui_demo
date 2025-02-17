import urllib.request
import json
from http import HTTPStatus
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Role
import dashscope
import datetime
import speech_recognition as sr
from aip import AipSpeech

dashscope.api_key='sk-0db9c8b38b3149d4a0248b52d1c80413'
APP_ID = '62638968'
API_KEY = 'hONMgNeQUw7jivk9BzVhmupV'
SECRET_KEY = 'NYuVHHoynxKT42St6OiGMGW93SwWDZyU'
client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
client_id='xPJX1UekpflBJWbrvIfYFyil'
client_secret='tQjn3j7k9Iaym2MGHDvYYDu9K4jZ3TzF'

now = datetime.datetime.now()
time_string = now.strftime("%Y-%m-%d") 
filename = "Generated\Text\emotion.txt"


#Token授权
def get_token():
    host = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=' + client_id + '&client_secret=' + client_secret
    request = urllib.request.Request(host)
    request.add_header('Content-Type', 'application/json; charset=UTF-8')
    response = urllib.request.urlopen(request)
    token_content = response.read()
    if token_content:
        token_info = json.loads(token_content)
        token_key = token_info['access_token']
    return token_key

#麦克风语音录入
def rec(rate=16000):
    try:
        r = sr.Recognizer()
        with sr.Microphone(sample_rate=rate) as source:
            print("请说话")
            audio = r.listen(source)
        with open("recording.wav", "wb") as f:
            f.write(audio.get_wav_data())
    except:
        print("语音录入发生错误")

def listen(filename):
    with open('recording.wav', 'rb') as f:
        audio_data = f.read()
        result = client.asr(audio_data, 'wav', 16000, {
        'dev_pid': 1536,
    })
        try:
            result_text = result["result"][0]
            print(result_text)
            with open(filename, "a",encoding="utf-8") as f:  # 使用模式"a"以追加方式打开文件
                    f.write("对话:" + result_text + "\n") 
        except:
            return ""
    return result_text

#情绪识别 
def get_emotion(content):
    try:
        token = get_token()
        url = 'https://aip.baidubce.com/rpc/2.0/nlp/v1/emotion'
        params = dict()
        params['scene'] = 'talk'
        params['text'] = content
        params = json.dumps(params).encode('utf-8')
        
        # 验证token
        if not token:
            print("错误：无法获取token")
            return {}
            
        access_token = token
        url = url + "?access_token=" + access_token
        url = url + "&charset=UTF-8"
        
        request = urllib.request.Request(url=url, data=params)
        request.add_header('Content-Type', 'application/json')
        
        # 添加超时设置
        response = urllib.request.urlopen(request, timeout=10)
        content = response.read()
        
        if content:
            content = content.decode('utf-8')
            data = json.loads(content)
            return data
        else:
            print("警告：情绪识别返回空结果")
            return {}
            
    except Exception as e:
        print(f"情绪识别发生错误: {e}")
        return {}
    
def parse_emotion_result(data):  
    items = data.get('items', [])
    for item in items:
        label = item.get('label', '')
        if label != 'neutral':
            subitems = item.get('subitems', [])
            for subitem in subitems:
                sub_label = subitem.get('label', '')
                if sub_label:
                    print(f"Emotion: {label}, Sub-Emotion: {sub_label}")
                    with open(filename, "a", encoding="utf-8") as f:  # 使用模式"a"以追加方式打开文件
                        f.write("情绪:" + f"Emotion: {label}, Sub-Emotion: {sub_label}" + "\n") 
        else:
            print("")