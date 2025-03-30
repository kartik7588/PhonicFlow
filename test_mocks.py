"""
Mock classes for testing voice_browser_control.py
"""

class MockSpeechRecognizer:
    def adjust_for_ambient_noise(self, *args, **kwargs):
        pass
    
    def listen(self, *args, **kwargs):
        pass
    
    def recognize_google(self, *args, **kwargs):
        return ""

class MockMicrophone:
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass

class MockService:
    pass

class MockOptions:
    def add_argument(self, *args, **kwargs):
        pass

class MockDriver:
    def __init__(self):
        self.current_url = "http://mock.url"
    
    def get(self, url):
        pass
    
    def implicitly_wait(self, time):
        pass
    
    def execute_script(self, script):
        pass
    
    def back(self):
        pass
    
    def forward(self):
        pass
    
    def refresh(self):
        pass
    
    def quit(self):
        pass
    
    @property
    def page_source(self):
        return "<html><body>Mock page</body></html>"

class MockTTS:
    def say(self, text):
        pass
    
    def runAndWait(self):
        pass
    
    def init(self):
        return self

# Mock modules that would be imported
import sys
from unittest.mock import MagicMock

# Create mocks for all the imported modules
sys.modules['speech_recognition'] = MagicMock()
sys.modules['speech_recognition'].Recognizer = MockSpeechRecognizer
sys.modules['speech_recognition'].Microphone = MockMicrophone
sys.modules['speech_recognition'].WaitTimeoutError = Exception
sys.modules['speech_recognition'].UnknownValueError = Exception
sys.modules['speech_recognition'].RequestError = Exception

sys.modules['selenium'] = MagicMock()
sys.modules['selenium.webdriver'] = MagicMock()
sys.modules['selenium.webdriver'].Chrome = MockDriver
sys.modules['selenium.webdriver.common'] = MagicMock()
sys.modules['selenium.webdriver.common.by'] = MagicMock()
sys.modules['selenium.webdriver.common.keys'] = MagicMock()
sys.modules['selenium.webdriver.chrome.service'] = MagicMock()
sys.modules['selenium.webdriver.chrome.service'].Service = MockService
sys.modules['selenium.webdriver.chrome.options'] = MagicMock()
sys.modules['selenium.webdriver.chrome.options'].Options = MockOptions
sys.modules['selenium.webdriver.support.ui'] = MagicMock()
sys.modules['selenium.webdriver.support'] = MagicMock()

sys.modules['pyttsx3'] = MagicMock()
sys.modules['pyttsx3'].init = lambda: MockTTS()

sys.modules['webdriver_manager'] = MagicMock()
sys.modules['webdriver_manager.chrome'] = MagicMock()
sys.modules['webdriver_manager.chrome'].ChromeDriverManager = lambda: MagicMock()

sys.modules['groq'] = MagicMock()
sys.modules['bs4'] = MagicMock()
sys.modules['nltk'] = MagicMock()
sys.modules['nltk.tokenize'] = MagicMock()
sys.modules['nltk.corpus'] = MagicMock()

# Mock our custom imported modules
sys.modules['advanced_page_analyzer'] = MagicMock()
sys.modules['advanced_page_analyzer'].AdvancedPageAnalyzer = lambda x: MagicMock()
sys.modules['youtube_controller'] = MagicMock()
sys.modules['youtube_controller'].YouTubeController = lambda x, y: MagicMock() 