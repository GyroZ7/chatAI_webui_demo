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
import threading
import json
import queue

#openai.api_key = config.openai_api_key
openai.api_key = "your_api_key"
model = "gpt-4o"
APP_ID='107510510'
API_KEY='4fXMb0q9hDMWES2Ws3vQBuNq'
SECRET_KEY='JvX5mgQuGrCTiE2kYZmWSZdtWTg9BWW1'
client=AipSpeech (APP_ID, API_KEY, SECRET_KEY)

client_OpenAI = OpenAI(
      base_url="your_url",
      api_key="your_api_key"
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

# 全局语音引擎管理器
class GlobalVoiceManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GlobalVoiceManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """初始化语音引擎管理器"""
        self.engine = None
        self.voice_queue = queue.Queue()
        self.current_task = None
        self.is_speaking = False
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
    
    def _init_engine(self):
        """初始化语音引擎"""
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if "chinese" in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            return True
        except Exception as e:
            print(f"语音引擎初始化失败: {e}")
            self.engine = None
            return False
    
    def _process_queue(self):
        """处理语音队列的工作线程"""
        while True:
            try:
                if self._stop_event.is_set():
                    self.voice_queue.queue.clear()
                    continue
                    
                text = self.voice_queue.get()
                self.is_speaking = True
                
                if self._init_engine():
                    try:
                        self.engine.say(text)
                        self.engine.runAndWait()
                    except Exception as e:
                        print(f"语音播放出错: {e}")
                    finally:
                        if self.engine:
                            try:
                                self.engine.stop()
                            except:
                                pass
                            self.engine = None
                
                self.is_speaking = False
                self.voice_queue.task_done()
                
            except queue.Empty:
                time.sleep(0.1)
            except Exception as e:
                print(f"语音处理出错: {e}")
                self.is_speaking = False
    
    def stop_current(self):
        """停止当前语音播放"""
        self._stop_event.set()
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
        self.voice_queue.queue.clear()
        time.sleep(0.1)  # 给予一点时间让队列清空
        self._stop_event.clear()
    
    def play(self, text):
        """添加文本到语音队列"""
        self.stop_current()  # 停止当前播放
        self.voice_queue.put(text)

# 使用全局语音管理器的VoiceManager类
class VoiceManager:
    def __init__(self):
        self.global_manager = GlobalVoiceManager()
    
    def play_voice(self, text):
        """播放语音"""
        try:
            self.global_manager.play(text)
        except Exception as e:
            print(f"语音播放出错: {e}")

class MessageHandler:
    def __init__(self, client, documents, system_message):
        self.client = client
        self.documents = documents
        self.system_message = system_message
        self.voice_manager = VoiceManager()
        self.conversation_history = []  # 添加对话历史列表

    def process_message(self, input_text):
        """
        处理输入消息并返回JSON格式的响应
        Args:
            input_text (str): 输入的文本消息
        Returns:
            str: JSON格式的响应
        """
        # 更新临时用户发言&情绪文件的内容
        temp_emotion_path = os.path.join("temp", "temp_emotion.txt")
        os.makedirs("temp", exist_ok=True)
        with open(temp_emotion_path, "w", encoding='utf-8') as f:
            f.write(input_text)
        
        # 确保文档列表使用最新的临时文件
        current_documents = []
        for doc in self.documents:
            if doc['tag'] == '用户发言&情绪':
                doc = {'path': temp_emotion_path, 'prefix': doc['prefix'], 'tag': doc['tag']}
                current_documents.append(doc)
        
        # 获取响应
        response = self.get_completion_from_document(
            current_documents, 
            self.system_message
        )
        
        try:
            # 解析响应并更新对话历史
            response_dict = json.loads(response)
            # 更新对话历史，添加用户输入和助手回复
            self.conversation_history.append({
                "role": "user",
                "content": f"Document 2:\n<用户发言&情绪>\n{input_text}\n</用户发言&情绪>\n"
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response_dict['dialogue']
            })
        except json.JSONDecodeError:
            print("无法解析响应JSON")
        
        return response

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
        """获取API响应"""
        try:
            # 读取文档内容
            full_prompt = ""
            for doc_info in documents:
                if not os.path.exists(doc_info['path']):
                    print(f"警告：文件不存在 {doc_info['path']}")
                    continue
                    
                try:
                    with open(doc_info['path'], 'r', encoding='utf-8') as file:
                        document_content = file.read().strip()
                        if document_content:
                            tagged_content = xml(doc_info['prefix'], document_content, doc_info['tag'])
                            full_prompt += tagged_content
                except Exception as e:
                    print(f"读取文件出错 {doc_info['path']}: {e}")
                    continue

            # 构建消息列表
            messages = [{"role": "system", "content": system_message}]
            
            # 添加历史对话记录（最多保留最近的10轮对话）
            if self.conversation_history:
                recent_history = self.conversation_history[-10:]
                messages.extend(recent_history)
            
            # 添加当前用户输入
            if full_prompt:
                messages.append({"role": "user", "content": full_prompt})
            
            print("发送到 API 的完整消息列表：", messages)
            
            # 调用 OpenAI API
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"API 调用出错: {e}")
            return json.dumps({
                "emotion": "错误",
                "advice": f"系统处理出错: {str(e)}",
                "dialogue": "对不起，系统暂时出现了问题，请稍后再试。"
            })

system_message = f"""
[Personality]
    1. You are a caregiving assistant skilled in communicating with the care recipients. You excel at using communication techniques to address different emotional states of the care recipient. 
    2. You need to select one caregiving technique based on the care recipients' personality, preferences, and current state. 
    3. You should offer advice using concise declarative sentences and directly present actions.
    [Background]
        Caregivers face the challenging to manage the emotional states of care recipients and lack of response methods. 
        Providing informations on [用户发言&情绪] and [偏好] will help facilitate caregiving with care recipients.  
[Think]
    1. The care recipient's emotional state.
    2. Based on [用户发言&情绪], select one of the most appropriate caregiving methods provided.
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
                You need to choose one of the most appropriate approachs based on the content of the [用户发言&情绪]:
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
    1. Advice should briefly and concisely, excluding the impact and consequences of the advice.
    2. Advice must use the declarative sentence format.
    3. Advice should be tailored from [偏好].
    4. Your service target is one caregiver. 
    5. Default advice language is Chinese. 
    6. Your responses must consider both [用户发言&情绪] and [偏好].
    7. You must combine with two documents and generate one advice.
    8. Please firstly consider that the caregivers may not have time at the moment.
    9. The dialogue example should be warm and empathetic, showing how to communicate with the care recipient.
    10. The response should be in valid JSON format.
[偏好]
    ***

[output format:json]
    emotion: （应该表达给被照护者的情绪）,
    advice: （根据情绪状态和个人偏好提供的具体建议行动）,
    dialogue: （模拟照护者的口吻，参考advice回复被照护者）
"""

documents = [
    {'path': "zhaonainai.txt", 'prefix': 'Document 1:', 'tag': '偏好'},
    {'path': "temp_emotion.txt", 'prefix': 'Document 2:', 'tag': '用户发言&情绪'}, 
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







