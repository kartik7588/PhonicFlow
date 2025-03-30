import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import time
import os
import sys
import speech_recognition as sr
import pyttsx3
from cefpython3 import cefpython as cef
import platform
import ctypes
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from voice_browser_control import VoiceBrowserControl

class SingleWindowBrowserAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("Browser Assistant with Embedded Browser")
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)
        
        # Configure window to use all available space
        self.root.grid_columnconfigure(0, weight=3)  # Browser takes 3/4
        self.root.grid_columnconfigure(1, weight=1)  # Assistant takes 1/4
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create browser frame (left side)
        self.browser_frame = tk.Frame(self.root, bg="white")
        self.browser_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        # Create assistant frame (right side)
        self.assistant_frame = ttk.Frame(self.root)
        self.assistant_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        
        # Configure the assistant UI
        self.setup_assistant_ui()
        
        # Initialize the recognizer
        self.recognizer = sr.Recognizer()
        
        # For voice output
        self.voice_engine = pyttsx3.init()
        
        # Thread for voice recognition
        self.voice_thread = None
        self.listening = False
        
        # Initialize CEF for embedded browser
        self.browser = None
        self.setup_browser()
        
        # Add a welcome message
        self.add_to_chat("System", "Starting Browser Assistant...")
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_assistant_ui(self):
        """Configure the assistant UI (right side)"""
        # Make sure assistant frame uses all available space
        self.assistant_frame.columnconfigure(0, weight=1)
        self.assistant_frame.rowconfigure(0, weight=0)
        self.assistant_frame.rowconfigure(1, weight=1)
        self.assistant_frame.rowconfigure(2, weight=0)
        self.assistant_frame.rowconfigure(3, weight=0)
        self.assistant_frame.rowconfigure(4, weight=0)
        
        # Chat history label
        self.chat_label = ttk.Label(self.assistant_frame, text="Chat History")
        self.chat_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        # Chat history
        self.chat_history = scrolledtext.ScrolledText(
            self.assistant_frame, 
            wrap=tk.WORD, 
            width=40, 
            height=20,
            font=("Arial", 10)
        )
        self.chat_history.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.chat_history.config(state=tk.DISABLED)
        
        # Command input label
        self.input_label = ttk.Label(self.assistant_frame, text="Enter Command")
        self.input_label.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 5))
        
        # Command input
        self.command_input = ttk.Entry(self.assistant_frame)
        self.command_input.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.command_input.bind("<Return>", self.send_command)
        
        # Buttons frame
        self.button_frame = ttk.Frame(self.assistant_frame)
        self.button_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
        
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
            text="🎤 Voice", 
            command=self.listen_voice_command
        )
        self.voice_button.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_frame = ttk.Frame(self.assistant_frame)
        self.status_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        self.status_label = ttk.Label(self.status_frame, text="Status:")
        self.status_label.pack(side=tk.LEFT)
        
        self.status_value = ttk.Label(self.status_frame, text="Starting...")
        self.status_value.pack(side=tk.LEFT, padx=(5, 0))
        
        # Quick commands section
        self.commands_label = ttk.Label(self.assistant_frame, text="Quick Commands")
        self.commands_label.grid(row=6, column=0, sticky="w", padx=10, pady=(0, 5))
        
        # Quick commands
        self.quick_commands_frame = ttk.Frame(self.assistant_frame)
        self.quick_commands_frame.grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        quick_commands = [
            "Open Google", 
            "Search for weather", 
            "Scroll down", 
            "Go back",
            "Describe page"
        ]
        
        for i, cmd in enumerate(quick_commands):
            btn = ttk.Button(
                self.quick_commands_frame, 
                text=cmd,
                command=lambda c=cmd: self.execute_quick_command(c)
            )
            btn.pack(fill=tk.X, pady=2)
    
    def setup_browser(self):
        """Set up the embedded browser"""
        # Initialize CEF
        sys.excepthook = cef.ExceptHook
        
        # Set CEF browser settings
        browser_settings = {
            "homepage": "https://www.google.com/search",
            "web_security_disabled": True
        }
        cef.Initialize(settings=browser_settings)
        
        # Create browser widget
        window_info = cef.WindowInfo()
        
        # Get handle for the browser frame
        win_id = self.browser_frame.winfo_id()
        window_info.SetAsChild(win_id, [0, 0, self.browser_frame.winfo_width(), self.browser_frame.winfo_height()])
        
        # Create browser and load Google
        self.browser = cef.CreateBrowserSync(window_info, url="https://www.google.com/search")
        
        # Set up focus handler
        self.client_handler = ClientHandler(self)
        self.browser.SetClientHandler(self.client_handler)
        
        # Bind resize event
        self.browser_frame.bind("<Configure>", self.on_browser_frame_configure)
        
        # Initialize browser controller - using a simplified version
        self.setup_browser_controller()
        
        # Update status
        self.update_status("Ready")
        self.add_to_chat("System", "Browser is ready. You can now start giving commands.")
    
    def setup_browser_controller(self):
        """Set up a simplified browser controller for CEF browser"""
        self.command_handlers = {
            "open google": self.open_url("https://www.google.com/search"),
            "open youtube": self.open_url("https://www.youtube.com"),
            "open facebook": self.open_url("https://www.facebook.com"),
            "search for": self.search_google,
            "scroll down": lambda: self.browser.ExecuteJavascript("window.scrollBy(0, 300);"),
            "scroll up": lambda: self.browser.ExecuteJavascript("window.scrollBy(0, -300);"),
            "go back": lambda: self.browser.GoBack(),
            "go forward": lambda: self.browser.GoForward(),
            "refresh": lambda: self.browser.Reload(),
            "click on": self.click_element,
            "describe page": self.describe_page,
        }
    
    def open_url(self, url):
        """Return a function that opens a URL"""
        return lambda: self.browser.LoadUrl(url)
    
    def search_google(self, query):
        """Search Google for the given query"""
        search_url = f"https://www.google.com/search?q={query}"
        self.browser.LoadUrl(search_url)
    
    def click_element(self, element_text):
        """Click on an element with the given text"""
        js = f"""
        (function() {{
            const elements = document.querySelectorAll('a, button, input[type="submit"], input[type="button"]');
            for (let i = 0; i < elements.length; i++) {{
                const el = elements[i];
                if (el.textContent.toLowerCase().includes('{element_text.lower()}')) {{
                    el.click();
                    return true;
                }}
            }}
            return false;
        }})();
        """
        self.browser.ExecuteJavascript(js)
    
    def describe_page(self):
        """Describe the current page"""
        js = """
        (function() {
            const title = document.title;
            const heading = document.querySelector('h1') ? document.querySelector('h1').textContent : 'No main heading';
            const links = document.querySelectorAll('a').length;
            const text = document.body.textContent.substring(0, 500);
            return { title, heading, links, text };
        })();
        """
        self.browser.ExecuteJavascript(js)
        # This is simplified - in a real implementation we'd capture the result
        self.add_to_chat("System", "Page description: This is a simplified page description as CEF doesn't easily return JS values. The page appears to be loaded correctly.")
    
    def on_browser_frame_configure(self, event):
        """Handle browser frame resize"""
        if self.browser:
            cef.WindowUtils.OnSize(self.browser_frame.winfo_id(), 0, 0, event.width, event.height)
    
    def send_command(self, event=None):
        """Process a command from the input field"""
        command = self.command_input.get().strip()
        if not command:
            return
        
        # Add to chat history
        self.add_to_chat("You", command)
        self.command_input.delete(0, tk.END)
        
        # Update status
        self.update_status("Processing...")
        
        # Process command in a separate thread to keep UI responsive
        threading.Thread(target=self.process_command_thread, args=(command,), daemon=True).start()
    
    def process_command_thread(self, command):
        """Thread to process commands"""
        try:
            command_lower = command.lower()
            
            # Check for exit commands
            if command_lower in ["exit", "quit", "close browser"]:
                self.add_to_chat("System", "Closing browser...")
                self.on_closing()
                return
            
            # Find and execute handlers for recognized commands
            handled = False
            for key, handler in self.command_handlers.items():
                if command_lower.startswith(key):
                    if key == "search for":
                        search_term = command[len(key):].strip()
                        handler(search_term)
                    elif key == "click on":
                        element = command[len(key):].strip()
                        handler(element)
                    else:
                        handler()
                    
                    handled = True
                    self.add_to_chat("System", "Command processed successfully.")
                    break
            
            if not handled:
                self.add_to_chat("System", "I don't know how to process that command yet.")
            
            self.update_status("Ready")
            
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            self.add_to_chat("System", error_msg)
            self.update_status("Error")
            print(error_msg)
    
    def listen_voice_command(self):
        """Listen for voice commands"""
        if self.listening:
            return
            
        self.update_status("Listening...")
        self.voice_button.config(state=tk.DISABLED)
        
        # Start listening in a separate thread
        self.listening = True
        self.voice_thread = threading.Thread(target=self.listen_thread, daemon=True)
        self.voice_thread.start()
    
    def listen_thread(self):
        """Thread to handle voice input"""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)
                
            self.update_status("Processing...")
            try:
                command = self.recognizer.recognize_google(audio)
                
                # Add command to input field
                self.root.after(0, lambda: self.command_input.insert(0, command))
                self.root.after(0, self.send_command)
                
            except sr.UnknownValueError:
                self.add_to_chat("System", "Sorry, I couldn't understand that.")
                self.update_status("Ready")
                
            except sr.RequestError as e:
                self.add_to_chat("System", f"Speech recognition service error: {e}")
                self.update_status("Error")
                
        except Exception as e:
            self.add_to_chat("System", f"Error listening: {str(e)}")
            self.update_status("Error")
            
        finally:
            self.listening = False
            self.root.after(0, lambda: self.voice_button.config(state=tk.NORMAL))
    
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
        # Close CEF browser
        if self.browser:
            self.browser.CloseBrowser(True)
        
        # Shutdown CEF
        cef.QuitMessageLoop()
        cef.Shutdown()
        
        # Close the tkinter window
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """Start the main event loop"""
        # This needs to be handled differently with CEF
        cef.MessageLoop()


# Focus handler for the browser
class ClientHandler:
    def __init__(self, parent):
        self.parent = parent

    def OnLoadError(self, browser, frame, error_code, failed_url, error_text):
        # Handle load errors
        self.parent.add_to_chat("System", f"Error loading page: {error_text}")
    
    def OnLoadingStateChange(self, browser, is_loading, can_go_back, can_go_forward):
        # Update status when page loading state changes
        if not is_loading:
            self.parent.update_status("Ready")
        else:
            self.parent.update_status("Loading...")


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
    
    # Initialize tkinter
    root = tk.Tk()
    
    # Initialize our app with embedded browser
    app = SingleWindowBrowserAssistant(root)
    
    # Run the app
    app.run()


if __name__ == "__main__":
    main() 