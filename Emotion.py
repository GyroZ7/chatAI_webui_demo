import datetime
import speech_recognition as sr
from openai import OpenAI
from pathlib import Path

# OpenAI配置
client = OpenAI(
    api_key='sk-zc47213449f70a2328e93d2ea4e73aa410f26a20511GgIPP',  # 请替换为您的OpenAI API密钥
    base_url="https://api.gptsapi.net/v1"  # 设置自定义API基础地址
)

now = datetime.datetime.now()
time_string = now.strftime("%Y-%m-%d") 
filename = "Generated/Text/emotion.txt"

#麦克风语音录入
def rec(rate=16000):
    try:
        r = sr.Recognizer()
        with sr.Microphone(sample_rate=rate) as source:
            print("请说话")
            audio = r.listen(source)
        with open("recording.wav", "wb") as f:
            f.write(audio.get_wav_data())
    except Exception as e:
        print(f"语音录入发生错误: {e}")

def listen(filename):
    try:
        audio_file = Path(filename)
        with open(audio_file, "rb") as audio:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                response_format="text"
            )
            print(result)
            with open("temp_emotion.txt", "a", encoding="utf-8") as f:
                f.write("对话:" + result + "\n")
            return result
    except Exception as e:
        print(f"语音识别错误: {e}")
        return ""

#情绪识别 
def get_emotion(content):
    try:
        prompt = f"""
        请分析以下文本的情绪，并按照以下格式返回：
        主要情绪：[情绪标签]
        次要情绪：[具体情绪]
        仅返回情绪标签，不要其他解释。
        文本：{content}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个情绪分析专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"情绪识别发生错误: {e}")
        return {}

def parse_emotion_result(emotion_text):
    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write("情绪:" + emotion_text + "\n")
        print(emotion_text)
    except Exception as e:
        print(f"解析情绪结果时发生错误: {e}")