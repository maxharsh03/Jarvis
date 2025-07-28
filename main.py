import os
import logging
import time
from dotenv import load_dotenv

from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from tools.weather import get_current_weather_tool

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory

# Load environment variables
load_dotenv()

# === Configuration ===
MIC_INDEX = 0
TRIGGER_WORD = "jarvis"
CONVERSATION_TIMEOUT = 30  # seconds

# === Logging ===
logging.basicConfig(level=logging.DEBUG)

# === Initialize Voice IO ===
stt = SpeechToText(mic_index=MIC_INDEX)
tts = TextToSpeech()

# === LLM ===
llm = ChatOllama(model="llama3.2")  # Replace with your Ollama model name

# === Tools ===
tools = [get_current_weather_tool]

# === Prompt ===
prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "You are Jarvis, a helpful, witty, and intelligent AI assistant with access to various tools. "
        "You should use tools when needed, explain your reasoning when appropriate, and always respond in a clear, human-like tone. "
        "Keep your answers concise and friendly. If the user says 'Jarvis shut down', you must terminate the program immediately."
    )),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# === Memory ===
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# === Agent ===
agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)


# === Main Interaction Loop ===
def write():
    conversation_mode = False
    last_interaction_time = None

    try:
        while True:
            try:
                if not conversation_mode:
                    logging.info("🎤 Listening for wake word...")
                    audio = stt.listen()
                    transcript = stt.transcribe(audio)

                    if transcript and TRIGGER_WORD in transcript.lower():
                        logging.info(f"🗣 Triggered by: {transcript}")
                        tts.speak("Yes sir?")
                        conversation_mode = True
                        last_interaction_time = time.time()
                    else:
                        logging.debug("Wake word not detected.")
                else:
                    logging.info("🎤 Listening for next command...")
                    audio = stt.listen()
                    command = stt.transcribe(audio)

                    if not command:
                        continue

                    logging.info(f"📥 Command: {command}")
                    
                    if "shut down" in command.lower():
                        tts.speak("Shutting down, sir.")
                        break

                    logging.info("🤖 Sending command to agent...")
                    response = executor.invoke({"input": command})
                    content = response["output"]
                    logging.info(f"✅ Agent responded: {content}")

                    print("Jarvis:", content)
                    tts.speak(content)
                    last_interaction_time = time.time()

                    if time.time() - last_interaction_time > CONVERSATION_TIMEOUT:
                        logging.info("⌛ Timeout: Returning to wake word mode.")
                        conversation_mode = False

            except Exception as e:
                logging.error(f"❌ Error in interaction loop: {e}")
                time.sleep(1)

    except KeyboardInterrupt:
        logging.info("🛑 Manual interrupt received. Exiting.")
    except Exception as e:
        logging.critical(f"❌ Critical error in main loop: {e}")


if __name__ == "__main__":
    write()
