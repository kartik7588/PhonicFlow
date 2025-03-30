import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import time
import os
import sys
import webbrowser
import speech_recognition as sr
import pyttsx3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from voice_browser_control import VoiceBrowserControl

class SimpleWindowBrowserAssistant:
    def __init__(self):
        # Initialize the main window
        self.root = tk.Tk()
        self.root.title("Browser Assistant")
        self.root.geometry("400x700")
        self.root.minsize(350, 500)
        
        # Configure the main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a frame for current URL display
        self.url_frame = ttk.Frame(self.main_frame)
        self.url_frame.pack(fill=tk.X, pady=(0, 10))
        
        # URL label
        self.url_label = ttk.Label(self.url_frame, text="Current Page:")
        self.url_label.pack(side=tk.LEFT)
        
        self.url_value = ttk.Label(self.url_frame, text="Not connected")
        self.url_value.pack(side=tk.LEFT, padx=(5, 0))
        
        # Chat history
        self.chat_label = ttk.Label(self.main_frame, text="Chat History")
        self.chat_label.pack(pady=(0, 5), anchor=tk.W)
        
        self.chat_history = scrolledtext.ScrolledText(
            self.main_frame, 
            wrap=tk.WORD, 
            width=40, 
            height=20,
            font=("Arial", 10)
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.chat_history.config(state=tk.DISABLED)
        
        # Command input
        self.input_label = ttk.Label(self.main_frame, text="Enter Command")
        self.input_label.pack(pady=(0, 5), anchor=tk.W)
        
        self.command_input = ttk.Entry(self.main_frame, width=40)
        self.command_input.pack(fill=tk.X, pady=(0, 5))
        self.command_input.bind("<Return>", self.send_command)
        
        # Buttons frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)
        
        # Send button
        self.send_button = ttk.Button(
            self.button_frame, 
            text="Send", 
            command=self.send_command
        )
        self.send_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Voice command button
        self.voice_button = ttk.Button(
            self.button_frame, 
            text="🎤 Disable Voice", 
            command=self.toggle_voice_command
        )
        self.voice_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Open Browser button
        self.browser_button = ttk.Button(
            self.button_frame, 
            text="🔍 Focus Browser", 
            command=self.open_current_url_in_browser
        )
        self.browser_button.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(self.status_frame, text="Status:")
        self.status_label.pack(side=tk.LEFT)
        
        self.status_value = ttk.Label(self.status_frame, text="Starting...")
        self.status_value.pack(side=tk.LEFT, padx=(5, 0))
        
        # Quick commands section
        self.commands_label = ttk.Label(self.main_frame, text="Quick Commands")
        self.commands_label.pack(pady=(10, 5), anchor=tk.W)
        
        quick_commands = [
            "Open Google", 
            "Search for weather", 
            "Scroll down", 
            "Go back",
            "Describe page"
        ]
        
        self.quick_commands_frame = ttk.Frame(self.main_frame)
        self.quick_commands_frame.pack(fill=tk.X)
        
        for cmd in quick_commands:
            btn = ttk.Button(
                self.quick_commands_frame, 
                text=cmd,
                command=lambda c=cmd: self.execute_quick_command(c)
            )
            btn.pack(fill=tk.X, pady=2)
        
        # Initialize the recognizer
        self.recognizer = sr.Recognizer()
        
        # For voice output
        self.voice_engine = pyttsx3.init()
        
        # Thread for voice recognition
        self.voice_thread = None
        self.listening = False
        self.voice_enabled = True
        
        # Initialize browser
        self.browser_controller = None
        self.driver = None
        
        # Current URL tracking
        self.current_url = "about:blank"
        
        # Start browser in a separate thread
        threading.Thread(target=self.start_browser, daemon=True).start()
        
        # Add a welcome message
        self.add_to_chat("System", "Starting Browser Assistant...")
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start voice recognition automatically after 3 seconds
        self.root.after(3000, self.start_automatic_voice_listening)
    
    def start_browser(self):
        """Start the browser (visible, maximized)"""
        try:
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")  # Start maximized
            chrome_options.add_argument("--disable-redirects")  # Disable automatic redirects
            chrome_options.add_argument("--disable-popup-blocking")  # Disable popups
            chrome_options.add_experimental_option("prefs", {
                "homepage": "https://www.google.com/search",
                "homepage_is_newtabpage": False,
                "browser.startup_page": 1  # Open homepage on startup
            })
            
            # Start Chrome browser
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Initialize browser controller
            self.browser_controller = VoiceBrowserControl(self.driver)
            
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Calculate tkinter window size (compact but usable)
            tk_width = 400
            tk_height = min(700, screen_height - 100)
            
            # Position tkinter window at the top-right corner, not overlapping much
            self.root.geometry(f"{tk_width}x{tk_height}+{screen_width - tk_width - 20}+20")
            
            # Make tkinter window stay on top
            self.root.attributes('-topmost', True)
            
            # Store window handles for focusing
            self.browser_window_handle = self.driver.current_window_handle
            
            # Update status
            self.update_status("Ready")
            self.add_to_chat("System", "Browser is ready in full-screen mode.")
            
            # Start with Google homepage
            google_search_url = "https://www.google.com/search"
            self.driver.get(google_search_url)
            self.current_url = google_search_url
            self.update_url_display(google_search_url)
            
            # Verify we're on the search page and not a doodle page
            time.sleep(1)  # Give the page a moment to load
            current_url = self.driver.current_url
            if "google.com/doodles" in current_url or not "/search" in current_url:
                # We got redirected to a doodle page, force navigation back to search
                self.driver.get(google_search_url)
                self.current_url = google_search_url
                self.update_url_display(google_search_url)
            
            # Start a thread to monitor URL changes
            threading.Thread(target=self.monitor_url_changes, daemon=True).start()
            
            # Set up the reading interrupt mechanism
            self.is_reading = False
            self.should_stop_reading = False
            
            # Force focus on browser window immediately
            self.open_current_url_in_browser()
            
        except Exception as e:
            error_msg = f"Error starting browser: {str(e)}"
            self.update_status("Error")
            self.add_to_chat("System", error_msg)
            print(error_msg)
    
    def monitor_url_changes(self):
        """Monitor URL changes in the browser"""
        while True:
            try:
                if self.driver:
                    current_url = self.driver.current_url
                    if current_url != self.current_url:
                        self.current_url = current_url
                        self.root.after(0, lambda: self.update_url_display(current_url))
            except:
                pass
            time.sleep(1)
    
    def update_url_display(self, url):
        """Update the URL display"""
        if len(url) > 40:
            display_url = url[:37] + "..."
        else:
            display_url = url
        self.url_value.config(text=display_url)
    
    def open_current_url_in_browser(self):
        """Focus the browser window and bring it to front"""
        if self.driver:
            try:
                # Switch to the browser window
                self.driver.switch_to.window(self.driver.current_window_handle)
                
                # Multiple approaches to try to focus the window
                # 1. Use JavaScript to focus the window
                self.driver.execute_script("window.focus();")
                
                # 2. Perform window-manager specific actions
                if os.name == 'nt':  # Windows
                    # Get window handle for Windows OS
                    import ctypes
                    from ctypes import wintypes
                    
                    try:
                        # Get window handle by title
                        user32 = ctypes.WinDLL('user32', use_last_error=True)
                        
                        # Find window by Chrome title (which usually contains the page title)
                        FindWindowA = user32.FindWindowA
                        FindWindowA.argtypes = [wintypes.LPCSTR, wintypes.LPCSTR]
                        FindWindowA.restype = wintypes.HWND
                        
                        # Try to find by partial title match 
                        # (current URL might be in the title)
                        hwnd = None
                        if "chrome" in self.driver.title.lower():
                            hwnd = FindWindowA(None, self.driver.title.encode('utf-8'))
                        
                        # If not found, try with generic "Chrome" title
                        if not hwnd:
                            hwnd = FindWindowA(None, b"Google Chrome")
                        
                        if hwnd:
                            # Set foreground window
                            user32.SetForegroundWindow(hwnd)
                            
                            # Show window and restore if minimized
                            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    except Exception as win_error:
                        print(f"Windows-specific focus error: {win_error}")
                
                # 3. Alternative approach: refresh the page
                # Only do this as a last resort if the page isn't dynamic
                # self.driver.refresh()
                
                # 4. Click on the page body to focus
                try:
                    body = self.driver.find_element("tag name", "body")
                    body.click()
                except:
                    pass
                
                self.add_to_chat("System", "Browser window focused")
                
            except Exception as e:
                self.add_to_chat("System", f"Error focusing browser: {str(e)}")
        else:
            self.add_to_chat("System", "Browser is not ready yet.")
    
    def send_command(self, event=None):
        """Process a command from the input field"""
        command = self.command_input.get().strip()
        if not command:
            return
        
        # Add to chat history
        self.add_to_chat("You", command)
        self.command_input.delete(0, tk.END)
        
        # Check if browser is ready
        if not self.browser_controller:
            self.add_to_chat("System", "Browser is not ready yet. Please wait.")
            return
        
        # Update status
        self.update_status("Processing...")
        
        # Process command in a separate thread to keep UI responsive
        threading.Thread(target=self.process_command_thread, args=(command,), daemon=True).start()
    
    def process_command_thread(self, command):
        """Thread to process commands"""
        try:
            # Check for browser close command
            if command.lower() in ["exit", "quit", "close browser"]:
                self.add_to_chat("System", "Closing browser...")
                self.on_closing()
                return
                
            # Check if it's a stop reading command while reading is in progress
            if self.is_reading and command.lower() in ["stop", "wait", "interrupt", "stop reading", "pause"]:
                self.should_stop_reading = True
                self.add_to_chat("System", "Stopping page reading...")
                self.update_status("Ready")
                return
            
            # Process the command using the browser controller
            if command.lower() in ["read page", "read page aloud", "read aloud", "read this page", "describe page"]:
                # Set reading flag to track state for interruption
                self.is_reading = True
                self.should_stop_reading = False
                
                # Start a special thread for reading with interruption support
                threading.Thread(target=self.read_page_with_interruption, daemon=True).start()
                return
            
            # Process other commands normally
            result = self.browser_controller.process_command(command)
            
            # Display result
            if result and result != "EXIT":
                self.add_to_chat("System", result)
            else:
                self.add_to_chat("System", "Command processed successfully.")
            
            self.update_status("Ready")
            
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            self.add_to_chat("System", error_msg)
            self.update_status("Error")
            print(error_msg)
    
    def read_page_with_interruption(self):
        """Read the page with support for interruption"""
        try:
            self.update_status("Reading page...")
            self.add_to_chat("System", "Reading page. Say 'stop' to interrupt.")
            
            # Get the page content from the browser
            page_text = ""
            try:
                # Try to get visible text only
                body = self.driver.find_element("tag name", "body")
                page_text = body.text
            except:
                self.add_to_chat("System", "Could not extract page text.")
                self.is_reading = False
                self.update_status("Ready")
                return
            
            # Split page text into chunks for better interruptibility
            chunks = []
            current_chunk = ""
            
            # Split by paragraphs first
            paragraphs = page_text.split('\n\n')
            for paragraph in paragraphs:
                # If the paragraph is very long, split it into sentences
                if len(paragraph) > 200:
                    sentences = paragraph.replace('. ', '.\n').split('\n')
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) < 200:
                            current_chunk += sentence + " "
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sentence + " "
                else:
                    if len(current_chunk) + len(paragraph) < 200:
                        current_chunk += paragraph + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = paragraph + " "
            
            # Add the last chunk if it has content
            if current_chunk:
                chunks.append(current_chunk)
            
            # Initialize text-to-speech engine
            engine = pyttsx3.init()
            
            # Read chunks with interruption checks
            for i, chunk in enumerate(chunks):
                if self.should_stop_reading:
                    # Stop if interruption was requested
                    break
                
                # Set up a listener for the voice command while reading
                self.background_listen_for_stop()
                
                # Read the chunk
                engine.say(chunk)
                engine.runAndWait()
                
                # Brief pause between chunks to check for interruptions
                time.sleep(0.1)
                
                # Update progress periodically
                if i % 5 == 0:
                    progress = int((i + 1) / len(chunks) * 100)
                    self.update_status(f"Reading page... {progress}%")
            
            # Clean up after reading
            engine.stop()
            
            if self.should_stop_reading:
                self.add_to_chat("System", "Reading stopped by user.")
            else:
                self.add_to_chat("System", "Finished reading the page.")
                
        except Exception as e:
            self.add_to_chat("System", f"Error reading page: {str(e)}")
            
        finally:
            self.is_reading = False
            self.should_stop_reading = False
            self.update_status("Ready")
    
    def background_listen_for_stop(self):
        """Listen in background for stop commands while reading"""
        # Start a short-lived thread to listen for stop commands
        threading.Thread(target=self._quick_listen_for_stop, daemon=True).start()
    
    def _quick_listen_for_stop(self):
        """Quickly listen for a stop command without blocking the main thread"""
        try:
            # Only attempt to listen if voice is enabled
            if not self.voice_enabled:
                return
                
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.2)
                try:
                    audio = r.listen(source, timeout=0.5, phrase_time_limit=1.5)
                    text = r.recognize_google(audio)
                    
                    # Check for stop commands
                    if text and text.lower() in ["stop", "wait", "interrupt", "pause", "stop reading"]:
                        self.should_stop_reading = True
                except:
                    # Silently ignore any errors
                    pass
        except:
            # Silently ignore any setup errors
            pass
    
    def toggle_voice_command(self):
        """Toggle voice recognition on/off"""
        if self.listening:
            # If currently listening, stop it
            self.voice_enabled = False
            self.voice_button.config(text="🎤 Enable Voice")
            self.add_to_chat("System", "Voice recognition disabled.")
            # The current listening thread will end naturally
        else:
            # If not listening, start it again
            self.voice_enabled = True
            self.voice_button.config(text="🎤 Disable Voice")
            self.add_to_chat("System", "Voice recognition enabled.")
            self.start_automatic_voice_listening()
    
    def start_automatic_voice_listening(self):
        """Start voice listening automatically"""
        if not self.voice_enabled or self.listening:
            return
            
        self.update_status("Listening...")
        
        # Start listening in a separate thread
        self.listening = True
        self.voice_thread = threading.Thread(target=self.continuous_listen_thread, daemon=True)
        self.voice_thread.start()
    
    def continuous_listen_thread(self):
        """Thread to continuously handle voice input"""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                while self.voice_enabled:
                    try:
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        
                        self.update_status("Processing speech...")
                        try:
                            command = self.recognizer.recognize_google(audio)
                            if command.strip():
                                # Check if it's a stop command while reading
                                if self.is_reading and command.lower() in ["stop", "wait", "interrupt", "stop reading", "pause"]:
                                    self.should_stop_reading = True
                                    self.add_to_chat("System", f"Command recognized: '{command}'. Stopping reading...")
                                else:
                                    # Add command to input field and process it
                                    self.root.after(0, lambda cmd=command: self.command_input.insert(0, cmd))
                                    self.root.after(0, self.send_command)
                                
                                # Pause briefly before listening again
                                time.sleep(1)
                            
                        except sr.UnknownValueError:
                            # Silently ignore when nothing is understood
                            pass
                            
                        except sr.RequestError as e:
                            self.add_to_chat("System", f"Speech recognition service error: {e}")
                            
                        self.update_status("Listening..." if not self.is_reading else "Reading page...")
                        
                    except Exception as inner_e:
                        # Handle timeout or other errors silently
                        pass
                        
        except Exception as e:
            self.add_to_chat("System", f"Error in voice recognition: {str(e)}")
            
        finally:
            self.listening = False
            self.update_status("Ready")
            
            # Restart listening if it's still enabled
            if self.voice_enabled:
                self.root.after(1000, self.start_automatic_voice_listening)
    
    def execute_quick_command(self, command):
        """Execute one of the quick commands"""
        self.command_input.delete(0, tk.END)
        self.command_input.insert(0, command)
        self.send_command()
    
    def add_to_chat(self, sender, message):
        """Add a message to the chat history"""
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"{sender}: ", "sender")
        self.chat_history.insert(tk.END, f"{message}\n\n", "message")
        self.chat_history.see(tk.END)
        self.chat_history.config(state=tk.DISABLED)
        
        # Text tags for styling
        self.chat_history.tag_configure("sender", font=("Arial", 10, "bold"))
        self.chat_history.tag_configure("message", font=("Arial", 10))
    
    def update_status(self, status):
        """Update the status label"""
        self.root.after(0, lambda: self.status_value.config(text=status))
    
    def on_closing(self):
        """Handle window closing"""
        # Close browser if it's open
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        # Close the tkinter window
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """Start the main event loop"""
        self.root.mainloop()


def main():
    """Main function to start the application"""
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
    
    # Start the application
    app = SimpleWindowBrowserAssistant()
    app.run()


if __name__ == "__main__":
    main() 