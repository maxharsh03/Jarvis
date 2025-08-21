import sys
sys.path.append('.')

from voice.tts import TextToSpeech
import logging

logging.basicConfig(level=logging.DEBUG)

def test_tts():
    print("Testing TTS...")
    tts = TextToSpeech()
    
    print("\n1. Testing simple phrase...")
    tts.speak("Hello world")
    
    print("\n2. Testing longer response (like agent would give)...")
    tts.speak("The current time is 3:45 PM. Is there anything else I can help you with?")
    
    print("\n3. Testing special characters...")
    tts.speak("Here's a response with quotes, commas, and numbers: 123!")
    
    print("\nTTS test complete")

if __name__ == "__main__":
    test_tts()