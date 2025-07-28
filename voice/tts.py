import pyttsx3
import logging
import time

class TextToSpeech:
    def __init__(self):
        # Store voice preferences but don't initialize engine yet
        self.preferred_voice = None
        self.rate = 180
        self.volume = 1.0
        
        # Get voice preferences on first init
        try:
            temp_engine = pyttsx3.init()
            voices = temp_engine.getProperty('voices')
            logging.info(f"Available voices: {[voice.name for voice in voices]}")
            
            # Try to find jamie voice, fallback to first available
            for voice in voices:
                if "daniel" in voice.name.lower():
                    self.preferred_voice = voice.id
                    logging.info(f"Will use voice: {voice.name}")
                    break
            
            if not self.preferred_voice and voices:
                self.preferred_voice = 'Zarvox'
                logging.info(f"Will use default voice: Zarvox")
            
            # Clean up temp engine
            temp_engine.stop()
            del temp_engine
        except Exception as e:
            logging.error(f"❌ Failed to get voice preferences: {e}")
    
    def _create_engine(self):
        """Create a fresh TTS engine for each speak operation"""
        try:
            engine = pyttsx3.init()
            if self.preferred_voice:
                engine.setProperty('voice', self.preferred_voice)
            engine.setProperty('rate', self.rate)
            engine.setProperty('volume', self.volume)
            return engine
        except Exception as e:
            logging.error(f"❌ Failed to create TTS engine: {e}")
            return None

    def speak(self, text: str):
        if not text or not text.strip():
            logging.warning("⚠️ Empty text provided to TTS")
            return
            
        # Clean the text for better TTS compatibility
        cleaned_text = text.strip()
        logging.info(f"🔊 Speaking: '{cleaned_text}'")
        
        # Create fresh engine for this speak operation
        engine = self._create_engine()
        if not engine:
            logging.error("❌ Could not create TTS engine")
            return
            
        try:
            engine.say(cleaned_text)
            engine.runAndWait()
            logging.info("✅ TTS completed successfully")
        except Exception as e:
            logging.error(f"❌ TTS failed: {e}")
        finally:
            # Always clean up the engine
            try:
                engine.stop()
                del engine
            except:
                pass
            time.sleep(0.3)