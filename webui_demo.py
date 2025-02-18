import gradio as gr
from Prompt import MessageHandler, OpenAI, system_message
from Emotion import get_emotion, parse_emotion_result, listen
import speech_recognition as sr
import threading
import time
import json
import os

# 全局变量控制录音状态
recording = False
audio = None
recognizer = sr.Recognizer()
css = """
#warning {background-color: #e83413}
.warning {background-color: #e83413 !important; color: #ffffff !important}
"""

def start_recording():
    """开始录音"""
    global recording, audio
    recording = True
    return "正在调整环境噪声，请稍后...", gr.update(interactive=False), gr.update(interactive=True)

def update_recording_status():
    """更新录音状态"""
    time.sleep(2.5)  # 等待环境噪声调整完成
    return "正在录音...请说话"

def stop_recording():
    """停止录音并处理音频"""
    global recording, audio
    print("语音输入停止")
    recording = False

    # 确保audio不为None
    if audio is None:
        return ("", 
                gr.update(interactive=True), 
                gr.update(interactive=False),
                "未检测到录音")
    
    try:
        # 保存并处理音频
        with open("recording.wav", "wb") as f:
            f.write(audio.get_wav_data())
            print("音频保存成功")
        
        # 使用OpenAI的Whisper进行语音识别
        text = listen("recording.wav")
        
        if text:
            # 情绪分析
            emotion_data = get_emotion(text)
            parse_emotion_result(emotion_data)
            print("情绪分析结果：", emotion_data)
            
            # 构建格式化的显示文本，修复引号问题
            formatted_text = f'用户："{text}"\n{emotion_data}'
            
            return (formatted_text, 
                    gr.update(interactive=True), 
                    gr.update(interactive=False),
                    "录音完成")
        else:
            return ("", 
                    gr.update(interactive=True), 
                    gr.update(interactive=False),
                    "语音识别失败")
            
    except Exception as e:
        print(f"Error: {e}")
        return ("", 
                gr.update(interactive=True), 
                gr.update(interactive=False),
                "录音处理失败")

def record_audio():
    """后台录音线程"""
    global recording, audio, recognizer
    
    try:
        with sr.Microphone(sample_rate=16000) as source:
            # 增加降噪时间
            print("正在调整环境噪声...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print("开始录音...")
            
            # 设置动态能量阈值
            recognizer.energy_threshold = 4000
            recognizer.dynamic_energy_threshold = True
            
            while recording:
                try:
                    # 增加等待时间到10秒，保持语音片段最大时间为10秒
                    print("等待语音输入...")
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
                    print(f"捕获到音频，大小: {len(audio.get_wav_data())} 字节")
                except sr.WaitTimeoutError:
                    print("等待语音输入超时")
                    continue
                except Exception as e:
                    print(f"录音出错: {e}")
                time.sleep(0.1)
    except Exception as e:
        print(f"麦克风初始化错误: {e}")
        recording = False

def process_input(preference_file, manual_text, voice_text, history):
    """处理输入并返回API响应"""
    try:
        # 获取当前输入，并立即清空输入框
        current_input = manual_text or voice_text
        if not current_input:
            return "请输入文本或使用语音输入", "", "", history
        
        # 添加详细的日志
        print("="*50)
        print("新的请求开始处理")
        print(f"输入文本: {current_input}")
        print(f"偏好文件: {preference_file.name if preference_file else 'None'}")
        print("="*50)
        
        # 检查偏好文件
        preference_path = ""
        if preference_file and os.path.exists(preference_file.name):
            preference_path = preference_file.name
        else:
            print("警告：偏好文件不存在或未提供")
        
        # 初始化OpenAI客户端
        client_openai = OpenAI(
            base_url="https://api.gptsapi.net/v1",
            api_key="sk-zc47213449f70a2328e93d2ea4e73aa410f26a20511GgIPP"
        )
        
        # 确保临时文件目录存在
        os.makedirs("temp", exist_ok=True)
        
        # 将当前输入写入临时文件
        temp_emotion_path = os.path.join("temp", "temp_emotion.txt")
        with open(temp_emotion_path, "w", encoding='utf-8') as f:
            f.write(current_input)
        
        # 构建文档列表
        documents = [
            {'path': preference_path, 'prefix': 'Document 1:', 'tag': '偏好'},
            {'path': temp_emotion_path, 'prefix': 'Document 2:', 'tag': '情绪'},
        ]
        
        # 创建MessageHandler实例并调用处理方法
        handler = MessageHandler(client_openai, documents, system_message)
        
        # 获取响应
        print(f"发送到API的请求内容：{current_input}")
        response = handler.process_message(current_input)
        print(f"API响应内容：{response}")
        
        try:
            # 解析JSON响应
            response_dict = json.loads(response)
            
            # 格式化输出文本
            formatted_response = f"情绪状态：{response_dict['emotion']}\n\n建议行动：{response_dict['advice']}\n\n对话示例：{response_dict['dialogue']}"
            
            # 更新对话历史，添加用户输入
            new_history = f"{history}\n### 用户\n{current_input}\n\n### 助手\n{formatted_response}\n"
            
            # 创建新的语音播放线程
            if 'dialogue' in response_dict:
                print("开始新的语音播放")
                threading.Thread(
                    target=handler.voice_manager.play_voice,
                    args=(response_dict['dialogue'],),
                    daemon=True
                ).start()
            
            return formatted_response, "", "", new_history
            
        except json.JSONDecodeError as e:
            print(f"响应格式解析失败: {e}")
            print(f"原始响应: {response}")
            return f"响应格式解析失败: {e}", "", "", history
        except Exception as e:
            print(f"处理响应时出错: {e}")
            return f"处理响应时出错: {e}", "", "", history
        
    except Exception as e:
        print(f"详细错误信息: {str(e)}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return f"处理请求时出错: {str(e)}", "", "", history

def clear_history(chat_history):
    """清除对话历史"""
    return ""

def save_history(chat_history):
    """保存对话历史为JSON文件"""
    if not chat_history:
        return "对话历史为空"
    
    try:
        from datetime import datetime
        import tkinter as tk
        from tkinter import filedialog
        
        # 将对话历史按段落分割并解析为列表
        conversations = []
        sections = chat_history.split('### ')
        current_user_msg = ""
        
        for section in sections:
            if section.startswith('用户\n'):
                current_user_msg = section.replace('用户\n', '').strip()
            elif section.startswith('助手\n') and current_user_msg:
                assistant_msg = section.replace('助手\n', '').strip()
                conversations.append({
                    "user": current_user_msg,
                    "assistant": assistant_msg
                })
                current_user_msg = ""
        
        # 创建保存对话的文件选择器
        root = tk.Tk()
        root.withdraw()
        
        # 设置默认文件名（使用当前时间）
        default_filename = f"对话历史_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 打开文件选择对话框
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=default_filename,
            filetypes=[("JSON files", "*.json")]
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
            return f"对话历史已保存至：{file_path}"
        else:
            return "取消保存"
            
    except Exception as e:
        return f"保存失败：{str(e)}"

def main():
    with gr.Blocks(title="护理助手对话系统", css=css) as demo:
        gr.Markdown("# 护理助手对话系统")
        
        with gr.Row():
            # 左侧列 - 输入部分
            with gr.Column(scale=1):
                # 文件选择器
                file_input = gr.File(
                    label="选择偏好文件",
                    file_types=[".txt"]
                )
                
                gr.Markdown("### 可选择手动输入或语音输入任意一种输入方法。")
                
                # 手动输入框
                with gr.Group(visible=True):
                    gr.Markdown("&nbsp;⚪")
                    manual_input = gr.Textbox(
                        label="手动输入情绪状态",
                        placeholder="请输入情绪状态描述。参考：对话:\"...\", 情绪:\"...\"",
                        lines=3
                    )
                
                # 语音输入框
                with gr.Group(visible=True):
                    gr.Markdown("&nbsp;⚪")
                    record_status = gr.Textbox(
                        label="录音状态",
                        value="准备就绪",
                        interactive=False
                    )
                    voice_text = gr.Textbox(
                        label="语音输入结果",
                        placeholder="识别结果将自动转换，无需操作。如果同时有语音与文本输入，将优先使用文本输入。",
                        interactive=False,
                        lines=3
                    )
                    with gr.Row():
                        start_button = gr.Button("开始录音")
                        stop_button = gr.Button("停止录音", interactive=False)
                # 提交按钮
                submit_btn = gr.Button("获取建议", variant="primary")
            
            # 右侧列 - 输出部分
            with gr.Column(scale=1):
                with gr.Group(visible=True):
                    gr.Markdown("#### 助手回复")
                    output_text = gr.Textbox(
                        label="助手建议",
                        lines=15,
                        interactive=False
                    )
        
        gr.Markdown("***")
        gr.HTML("<hr style='height: 5px; background-color: black; border: none;'>")
        gr.Markdown("# 对话历史")
        
        # 对话历史（使用Markdown）
        chat_history = gr.Markdown(value="")
            
        with gr.Row():
            # 清除和保存按钮
            clear_btn = gr.Button("清除对话历史", elem_id="warning", elem_classes="warning")
            save_btn = gr.Button("存储对话历史")
        
        # 处理录音事件
        start_button.click(
            fn=start_recording,
            outputs=[record_status, start_button, stop_button],
            queue=False
        ).then(
            fn=lambda: threading.Thread(target=record_audio).start(),
            queue=False
        ).then(
            fn=update_recording_status,
            outputs=[record_status],
            queue=False
        )
        
        stop_button.click(
            fn=stop_recording,
            outputs=[voice_text, start_button, stop_button, record_status]
        )
        
        # 处理提交事件
        submit_btn.click(
            fn=process_input,
            inputs=[file_input, manual_input, voice_text, chat_history],
            outputs=[output_text, manual_input, voice_text, chat_history]
        )
        
        # 处理清除和保存事件
        clear_btn.click(
            fn=clear_history,
            inputs=[chat_history],
            outputs=[chat_history]
        )
        
        save_btn.click(
            fn=save_history,
            inputs=[chat_history],
            outputs=[output_text]
        )

    # 启动界面
    demo.launch(share=False, server_name="127.0.0.1", server_port=7860)

if __name__ == "__main__":
    main() 