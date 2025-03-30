import os
import time
import threading
import json
import speech_recognition as sr
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from voice_browser_control import VoiceBrowserControl

class BrowserPanel:
    def __init__(self):
        # Initialize the voice recognizer
        self.recognizer = sr.Recognizer()
        
        # Start the browser with custom panel
        self.start_browser()
        
        # Initialize controller
        self.browser_controller = VoiceBrowserControl(self.driver)
        
        # Thread for handling voice recognition
        self.voice_thread = None
        self.listening = False
        
        # Start polling thread for JS callbacks
        self.polling_thread = threading.Thread(target=self.poll_js_callbacks)
        self.polling_thread.daemon = True
        self.polling_thread.start()
        
    def start_browser(self):
        """Initialize browser with custom UI panel"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-web-security")  # Disable CORS and some security features
        chrome_options.add_argument("--allow-running-insecure-content")  # Allow mixed content
        chrome_options.add_argument("--disable-redirects")  # Disable automatic redirects
        chrome_options.add_argument("--disable-popup-blocking")  # Disable popups
        chrome_options.add_experimental_option("prefs", {
            "homepage": "https://www.google.com/search",
            "homepage_is_newtabpage": False,
            "browser.startup_page": 1  # Open homepage on startup
        })
        
        # Create a custom Chrome profile to allow JavaScript modifications
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # Open Google as initial page
        google_search_url = "https://www.google.com/search"
        self.driver.get(google_search_url)
        
        # Verify we're on the search page and not a doodle page
        time.sleep(1)  # Give the page a moment to load
        current_url = self.driver.current_url
        if "google.com/doodles" in current_url or not "/search" in current_url:
            # We got redirected to a doodle page, force navigation back to search
            self.driver.get(google_search_url)
        
        # Wait for page to fully load
        time.sleep(2)
        
        # Once page is loaded, inject our panel
        self.inject_panel()
        
    def inject_panel(self):
        """Inject the side panel HTML/CSS/JS into the browser"""
        try:
            # Create a container iframe to avoid CSP issues
            iframe_js = """
            if (!document.getElementById('assistant-frame')) {
                // Create iframe to host our panel
                const iframe = document.createElement('iframe');
                iframe.id = 'assistant-frame';
                iframe.style.position = 'fixed';
                iframe.style.top = '0';
                iframe.style.right = '0';
                iframe.style.width = '300px';
                iframe.style.height = '100%';
                iframe.style.border = 'none';
                iframe.style.zIndex = '2147483647'; // Max possible z-index
                document.body.appendChild(iframe);
            }
            """
            self.driver.execute_script(iframe_js)
            
            # Create the HTML for our panel
            panel_html = """
            <div id="assistant-panel">
                <div class="panel-header">
                    <h3>Browser Assistant</h3>
                    <button id="minimize-panel">_</button>
                </div>
                <div class="panel-body">
                    <div class="chat-container" id="chat-container">
                        <div class="system-message">Welcome to Browser Assistant! Type a command below or use voice.</div>
                    </div>
                    <div class="input-container">
                        <input type="text" id="command-input" placeholder="Enter command...">
                        <button id="send-command">Send</button>
                        <button id="voice-command">🎤</button>
                    </div>
                    <div class="status-container">
                        <span>Status: </span><span id="status-value">Ready</span>
                    </div>
                    <div class="quick-commands">
                        <h4>Quick Commands</h4>
                        <button class="quick-cmd" data-cmd="Open Google">Open Google</button>
                        <button class="quick-cmd" data-cmd="Search for weather">Search for weather</button>
                        <button class="quick-cmd" data-cmd="Scroll down">Scroll down</button>
                        <button class="quick-cmd" data-cmd="Go back">Go back</button>
                        <button class="quick-cmd" data-cmd="Describe page">Describe page</button>
                    </div>
                </div>
            </div>
            """
            
            # CSS for the panel
            panel_css = """
            <style>
                body, html {
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    font-family: Arial, sans-serif;
                }
                
                #assistant-panel {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: white;
                    display: flex;
                    flex-direction: column;
                    border-left: 1px solid #ddd;
                }
                
                .panel-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 10px;
                    background-color: #4285f4;
                    color: white;
                }
                
                .panel-header h3 {
                    margin: 0;
                    font-size: 16px;
                }
                
                .panel-header button {
                    background: none;
                    border: none;
                    color: white;
                    cursor: pointer;
                    font-weight: bold;
                }
                
                .panel-body {
                    display: flex;
                    flex-direction: column;
                    flex: 1;
                    padding: 10px;
                    overflow: hidden;
                }
                
                .chat-container {
                    flex: 1;
                    overflow-y: auto;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 10px;
                    margin-bottom: 10px;
                    background-color: #f9f9f9;
                }
                
                .input-container {
                    display: flex;
                    margin-bottom: 10px;
                }
                
                .input-container input {
                    flex: 1;
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    margin-right: 5px;
                }
                
                .input-container button {
                    padding: 8px 12px;
                    background-color: #4285f4;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-left: 5px;
                }
                
                .status-container {
                    margin-bottom: 10px;
                    font-size: 12px;
                }
                
                .quick-commands {
                    border-top: 1px solid #ddd;
                    padding-top: 10px;
                }
                
                .quick-commands h4 {
                    margin: 0 0 10px 0;
                    font-size: 14px;
                }
                
                .quick-cmd {
                    display: block;
                    width: 100%;
                    text-align: left;
                    padding: 8px;
                    margin-bottom: 5px;
                    background-color: #f1f1f1;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    cursor: pointer;
                }
                
                .system-message {
                    background-color: #e8f0fe;
                    padding: 8px;
                    border-radius: 4px;
                    margin-bottom: 10px;
                }
                
                .user-message {
                    background-color: #e6f7e6;
                    padding: 8px;
                    border-radius: 4px;
                    margin-bottom: 10px;
                    text-align: right;
                }
            </style>
            """
            
            # JavaScript for panel functionality
            panel_js = """
            <script>
                // Helper to add messages
                function addMessage(type, text) {
                    const container = document.getElementById('chat-container');
                    const messageDiv = document.createElement('div');
                    messageDiv.className = type + '-message';
                    messageDiv.textContent = text;
                    container.appendChild(messageDiv);
                    container.scrollTop = container.scrollHeight;
                }
                
                // Update status
                function updateStatus(status) {
                    document.getElementById('status-value').textContent = status;
                }
                
                // Set up event listeners for panel UI
                document.getElementById('minimize-panel').addEventListener('click', function() {
                    // Signal parent window to minimize
                    parent.postMessage('minimize-panel', '*');
                });
                
                // Event for command input
                document.getElementById('command-input').addEventListener('keyup', function(event) {
                    if (event.key === 'Enter') {
                        sendCommand();
                    }
                });
                
                // Send command button
                document.getElementById('send-command').addEventListener('click', sendCommand);
                
                // Voice command button
                document.getElementById('voice-command').addEventListener('click', function() {
                    updateStatus('Listening...');
                    // Signal parent window for voice command
                    parent.postMessage('voice-command', '*');
                });
                
                // Quick command buttons
                document.querySelectorAll('.quick-cmd').forEach(function(btn) {
                    btn.addEventListener('click', function() {
                        const cmd = this.getAttribute('data-cmd');
                        document.getElementById('command-input').value = cmd;
                        sendCommand();
                    });
                });
                
                // Function to send command to Python backend
                function sendCommand() {
                    const input = document.getElementById('command-input');
                    const command = input.value.trim();
                    
                    if (command) {
                        addMessage('user', command);
                        updateStatus('Processing...');
                        input.value = '';
                        
                        // Post to parent window
                        parent.postMessage({type: 'execute-command', command: command}, '*');
                    }
                }
                
                // Function to be called to add system message
                window.addSystemMessage = function(message) {
                    addMessage('system', message);
                    updateStatus('Ready');
                }
                
                // Listen for messages from parent
                window.addEventListener('message', function(event) {
                    if (event.data && event.data.type === 'system-message') {
                        addSystemMessage(event.data.message);
                    }
                });
                
                // Signal ready
                parent.postMessage('panel-ready', '*');
            </script>
            """
            
            # Combine HTML, CSS, and JavaScript into a complete document
            panel_document = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Browser Assistant</title>
                {panel_css}
            </head>
            <body>
                {panel_html}
                {panel_js}
            </body>
            </html>
            """
            
            # Inject the complete document into the iframe
            iframe_doc_js = f"""
            const iframe = document.getElementById('assistant-frame');
            if (iframe) {{
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                iframeDoc.open();
                iframeDoc.write(`{panel_document}`);
                iframeDoc.close();
            }}
            """
            self.driver.execute_script(iframe_doc_js)
            
            # Add message listeners in parent window
            parent_js = """
            // Setup message listener for iframe communication
            window.addEventListener('message', function(event) {
                if (event.data === 'minimize-panel') {
                    const iframe = document.getElementById('assistant-frame');
                    if (iframe) {
                        if (iframe.style.width === '30px') {
                            iframe.style.width = '300px';
                        } else {
                            iframe.style.width = '30px';
                        }
                    }
                } else if (event.data === 'voice-command') {
                    // Store in localStorage for python to detect
                    localStorage.setItem('voiceCommandRequested', 'true');
                } else if (event.data && event.data.type === 'execute-command') {
                    // Store command in localStorage for python to retrieve
                    localStorage.setItem('pendingCommand', event.data.command);
                }
            });
            
            // Function to send message to iframe
            window.sendMessageToPanel = function(message) {
                const iframe = document.getElementById('assistant-frame');
                if (iframe && iframe.contentWindow) {
                    iframe.contentWindow.postMessage({
                        type: 'system-message',
                        message: message
                    }, '*');
                }
            };
            """
            self.driver.execute_script(parent_js)
            
            # Create a maximize button for minimized state
            maximize_js = """
            const maximizeBtn = document.createElement('button');
            maximizeBtn.id = 'maximize-panel';
            maximizeBtn.style.position = 'fixed';
            maximizeBtn.style.top = '50%';
            maximizeBtn.style.right = '0';
            maximizeBtn.style.background = '#4285f4';
            maximizeBtn.style.color = 'white';
            maximizeBtn.style.border = 'none';
            maximizeBtn.style.padding = '15px 5px';
            maximizeBtn.style.writingMode = 'vertical-rl';
            maximizeBtn.style.textOrientation = 'mixed';
            maximizeBtn.style.cursor = 'pointer';
            maximizeBtn.style.display = 'none';
            maximizeBtn.style.zIndex = '2147483646';
            maximizeBtn.textContent = 'Open Assistant';
            
            maximizeBtn.addEventListener('click', function() {
                const iframe = document.getElementById('assistant-frame');
                if (iframe) {
                    iframe.style.width = '300px';
                    this.style.display = 'none';
                }
            });
            
            document.body.appendChild(maximizeBtn);
            """
            self.driver.execute_script(maximize_js)
            
            print("Panel injected successfully")
            
        except Exception as e:
            print(f"Error injecting panel: {e}")
    
    def add_message_to_ui(self, message):
        """Add a system message to the UI"""
        js_code = f'window.sendMessageToPanel("{message}");'
        try:
            self.driver.execute_script(js_code)
        except Exception as e:
            print(f"Error adding message to UI: {e}")
    
    def process_command(self, command):
        """Process a command from the UI"""
        try:
            # Check for special commands
            if command.lower() in ["exit", "quit", "close browser"]:
                self.add_message_to_ui("Closing browser...")
                # Allow time for message to be displayed
                time.sleep(1)
                self.driver.quit()
                return
            
            # Process the command using the browser controller
            result = self.browser_controller.process_command(command)
            
            # Display result in UI
            if result:
                self.add_message_to_ui(result)
            else:
                self.add_message_to_ui("Command processed successfully.")
                
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            print(error_msg)
            self.add_message_to_ui(error_msg)
    
    def start_voice_recognition(self):
        """Start voice recognition in a separate thread"""
        if self.listening:
            return
            
        self.listening = True
        self.voice_thread = threading.Thread(target=self.listen_for_command)
        self.voice_thread.daemon = True
        self.voice_thread.start()
    
    def listen_for_command(self):
        """Listen for voice command and process it"""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)
                
            try:
                command = self.recognizer.recognize_google(audio)
                # Update UI
                js_code = f"document.getElementById('command-input').value = '{command}';"
                self.driver.execute_script(js_code)
                # Process command
                self.process_command(command)
                
            except sr.UnknownValueError:
                self.add_message_to_ui("Sorry, I couldn't understand that.")
            except sr.RequestError as e:
                self.add_message_to_ui(f"Speech recognition service error: {e}")
                
        except Exception as e:
            self.add_message_to_ui(f"Error listening: {str(e)}")
        finally:
            self.listening = False
    
    def poll_js_callbacks(self):
        """Poll for JavaScript callbacks from the UI"""
        while True:
            try:
                # Check for pending command
                pending_command = self.driver.execute_script("return localStorage.getItem('pendingCommand')")
                if pending_command:
                    # Clear the pending command
                    self.driver.execute_script("localStorage.removeItem('pendingCommand')")
                    # Process the command
                    self.process_command(pending_command)
                
                # Check for voice command request
                voice_requested = self.driver.execute_script("return localStorage.getItem('voiceCommandRequested')")
                if voice_requested and not self.listening:
                    # Clear the request
                    self.driver.execute_script("localStorage.removeItem('voiceCommandRequested')")
                    # Start voice recognition
                    self.start_voice_recognition()
                
                # Sleep to prevent excessive CPU usage
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error in polling thread: {e}")
                # If browser is closed, exit
                try:
                    self.driver.current_url
                except:
                    break
    
    def run(self):
        """Main run loop"""
        try:
            # Keep the main thread running until browser is closed
            while True:
                try:
                    # Check if browser is still open
                    self.driver.current_url
                    time.sleep(1)
                except:
                    break
        except KeyboardInterrupt:
            print("Closing browser...")
        finally:
            try:
                self.driver.quit()
            except:
                pass

def main():
    """Main function to start the browser panel"""
    # Check if API key is already set
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        # Ask user for API key
        api_key = input("Enter your Groq API key (press Enter to skip): ").strip()
        
        if api_key:
            # Set environment variable for this session
            os.environ["GROQ_API_KEY"] = api_key
            print(f"API key set for this session.")
        else:
            print("No API key provided. Voice Browser Control will use basic intent recognition only.")
    
    # Start the browser with panel
    panel = BrowserPanel()
    panel.run()

if __name__ == "__main__":
    main() 