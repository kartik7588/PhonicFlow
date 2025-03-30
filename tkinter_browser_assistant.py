import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import time
import os
import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pyttsx3
import speech_recognition as sr
from voice_browser_control import VoiceBrowserControl

class TkinterBrowserAssistant:
    def __init__(self):
        # Initialize the main window
        self.root = tk.Tk()
        self.root.title("Browser Assistant")
        self.root.geometry("400x700")
        self.root.minsize(350, 500)
        
        # Center the window on screen
        self.center_window()
        
        # Configure the main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
            text="🎤 Voice", 
            command=self.listen_voice_command
        )
        self.voice_button.pack(side=tk.LEFT)
        
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
        
        # Initialize browser
        self.browser_controller = None
        self.driver = None
        
        # Start browser in a separate thread
        threading.Thread(target=self.start_browser, daemon=True).start()
        
        # Add a welcome message
        self.add_to_chat("System", "Starting Browser Assistant...")
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def center_window(self):
        """Center the window on the screen"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 400
        window_height = 700
        
        # Calculate position coordinates
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        
        # Set window position
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    
    def start_browser(self):
        """Start the browser"""
        try:
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-redirects")  # Disable automatic redirects
            chrome_options.add_argument("--disable-popup-blocking")  # Disable popups
            chrome_options.add_experimental_option("prefs", {
                "homepage": "https://www.google.com/search",
                "homepage_is_newtabpage": False,
                "browser.startup_page": 1  # Open homepage on startup
            })
            
            # Start Chrome browser in a new window without positioning constraints
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Initialize browser controller
            self.browser_controller = VoiceBrowserControl(self.driver)
            
            # Update status
            self.update_status("Ready")
            self.add_to_chat("System", "Browser is ready. You can now start giving commands.")
            
            # Start with Google homepage
            google_search_url = "https://www.google.com/search"
            self.driver.get(google_search_url)
            
            # Verify we're on the search page and not a doodle page
            time.sleep(1)  # Give the page a moment to load
            current_url = self.driver.current_url
            if "google.com/doodles" in current_url or not "/search" in current_url:
                # We got redirected to a doodle page, force navigation back to search
                self.driver.get(google_search_url)
            
        except Exception as e:
            error_msg = f"Error starting browser: {str(e)}"
            self.update_status("Error")
            self.add_to_chat("System", error_msg)
            print(error_msg)
    
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
            
            # Process the command using the browser controller
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
    app = TkinterBrowserAssistant()
    app.run()

if __name__ == "__main__":
    main() 