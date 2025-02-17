import openai
from openai import OpenAI
import os
import pyttsx3
from playsound import playsound
import io
from aip import AipSpeech
from pynput import keyboard
import sys
import time

#openai.api_key = config.openai_api_key
openai.api_key = "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"
#os.environ["OPENAI_API_KEY"] = 'sk-o3bQNa5VAcsu1FbkD36d67Db1a264861Bf1c09766570Ee2d '
model = "gpt-4o"
APP_ID='107510510'
API_KEY='4fXMb0q9hDMWES2Ws3vQBuNq'
SECRET_KEY='JvX5mgQuGrCTiE2kYZmWSZdtWTg9BWW1'
client=AipSpeech (APP_ID, API_KEY, SECRET_KEY)

client_OpenAI = OpenAI(
      base_url="https://api.gptsapi.net/v1",
      api_key="sk-zc47213449f70a2328e93d2ea4e73aa410f26a20511GgIPP"
  )

def xml(prefix, content, tag):
    """
    将内容包装在XML标签中
    Args:
        prefix (str): 前缀
        content (str): 要包装的内容
        tag (str): XML标签名
    Returns:
        str: 包装后的XML字符串
    """
    return f"{prefix}\n<{tag}>\n{content}\n</{tag}>\n"

class VoiceManager:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', self.voices[0].id)
        self.engine.setProperty('rate', 150)

    def play_voice(self, text):
        """
        将文本转换为语音并播放
        Args:
            text (str): 需要播放的文本内容
        """
        self.engine.say(text)
        self.engine.runAndWait()

class MessageHandler:
    def __init__(self, client_openai, documents, system_message):
        self.client_openai = client_openai
        self.documents = documents
        self.system_message = system_message
        self.voice_manager = VoiceManager()

    def get_and_play_response(self):
        """
        获取API响应并播放语音
        Returns:
            str: API的响应内容
        """
        response = self.get_completion_from_document(
            self.documents, 
            self.system_message
        )
        self.voice_manager.play_voice(response)
        return response

    def get_completion_from_document(self, documents, system_message, model="gpt-4o"):
        # 读取文档内容
        full_prompt = ""
        for idx, doc_info in enumerate(documents):
            # 读取每个文档的内容
            with open(doc_info['path'], 'r', encoding='utf-8') as file:
                document_content = file.read()

            # 使用xml函数对文档内容进行标签处理
            tagged_content = xml(doc_info['prefix'], document_content, doc_info['tag'])
            
            # 将处理后的内容添加到完整的 prompt 中
            full_prompt += tagged_content
        full_prompt += f"\n{system_message}"
        # 构建消息列表
        messages = [{"role": "user", "content": full_prompt}]
        # 调用 OpenAI API 获取生成的响应
        response = self.client_openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content

system_message = f"""
[Personality]
    1. You are a caregiving assistant skilled in communicating with the care recipients. You excel at using communication techniques to address different emotional states of the care recipient. 
    2. You need to select one caregiving technique based on the care recipients' personality, preferences, and current state. 
    3. You should offer advice using concise declarative sentences and directly present actions.
    [Background]
        Caregivers face the challenging to manage the emotional states of care recipients and lack of response methods. 
        Providing informations on [情绪] and [偏好] will help facilitate caregiving with care recipients.  
[Think]
    1. The care recipient's emotional state.
    2. Based on [情绪], select one of the most appropriate caregiving methods provided.
    3. Based on [偏好] and caregiving methods, provide advice.
    
    [Caregiving methods]
        You need to follow the guidelines. 
        [Approach 1: Default attention]
            [Description] 
                When the care recipient is in great emotion (more positive and less negative emotions), willing to actively cooperate with the caregivers.
            [Purpose] 
                Maintain continuous attention on the care recipient and praise the caregiver's work.
            [conditions]
                The care recipient currently does not require caregiving and has a high willingness to communicate.
            [Content format reference]
                1. The elderly are in good condition; well done.
                2. Everything is fine and willing to communicate.
        [Approach 2: Reassurance]
            [Description] 
                The care recipient is feeling depressed (few positive emotions, more negative emotions). 
            [Purpose] 
                The caregiver needs to pay attention to the care recipient's negative emotions and take appropriate approachs.
            [conditions]
                You need to choose one of the most appropriate approachs based on the content of the [情绪]:
                1. When negative emotions stem from the experiences and feelings, take an encouraging and soothing approach.
                2. When negative emotions arise from the caregivings, take a break approach.
            [Content format reference]
                when negative emotions stem from the experiences and feelings, format reference: 
                    1. Communicate and provide reassurance during idle times.
                    2. Encourage her more during idle times.
                when negative emotions stem from the caregivers, format reference:
                    1. Take a break before communication.
                    2. Take a break now, try to communicate later.
        [Approach 3: Elicitation]
            [Description] 
                When the care recipient's emotion is stable (more neutral emotion and less positive and negative emotions).
            [Purpose] 
                Based on the content of [偏好], tailor conversation topics and contents to elicit emotions.
            [conditions]
                The care recipient is willing to chat and emotion remains neutral.
            [Content format reference]
                1. Talk his/her personal experiences during idle times. 
                2. Do a good job; let her/him be alone for a while.

[Rules to follow]
    1. Advice should briefly and concisely,  excluding the impact and consequences of the advice.
    2. Advice must use the declarative sentence format.
    3. Advice should be tailored from [偏好. 
    4. Your service target is one caregiver. 
    5. Default advice language is Chinese. 
    6. Your responses must consider both [情绪] and [偏好].
    7. You must combine with two documents and generate one advice.
    8. Please fiestly consider that the caregivers may not have time at the moment. For example: 1. ... when you have free time. 2. Once you're free, you can...
[output format]
    情绪: content(综合判断，直接输出：积极/稳定/消极)     
    建议: content(参考content format reference。直接输出行动)
"""

documents = [
    {'path': "Generated\Text\zhaonainai.txt" , 'prefix': 'Document 1:', 'tag': '偏好'},
    {'path': "Generated\Text\emotion.txt", 'prefix': 'Document 2:', 'tag': '情绪'}, 
    # 可以继续添加更多的文档
]

def old_abandoned():
    global canStart
    global needQuit
    canStart = False
    needQuit = False
    # use keyboard listerner  
    def KeyPress(key):
        if key == keyboard.Key.space:
            global canStart
            print("getkey space needsleep:{}".format(canStart))
            canStart=True       
        if key== keyboard.Key.esc:
            global needQuit
            print('get esc key needquit:{}'.format(needQuit))
            needQuit=True

    def KeyRelease(key):
        print("release")
    listner = keyboard.Listener(
        on_press = KeyPress,
        on_release=KeyRelease)
    listner.start()

    while needQuit == False:
        if canStart == False:
            continue
        completion = get_completion_from_document (documents, system_message)
        engine.say(completion)  # 编辑待转为语音的文字
        engine.runAndWait()  # 文字转语音
        print(completion)
        # speak(completion)
        canStart=False
    
    print("退出")
    # Exit the program
    sys.exit()







