import speech_recognition as sr
import logging

class SpeechToText:
    def __init__(self, mic_index=0):
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone(device_index=mic_index)

    def listen(self, timeout=10):
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source, timeout=timeout)
            return audio

    def transcribe(self, audio):
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            logging.warning("⚠️ Could not understand audio.")
            return None
        except sr.RequestError as e:
            logging.error(f"❌ STT request failed: {e}")
            return None