import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import threading
import time
import os
import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyttsx3
import speech_recognition as sr
from voice_browser_control import VoiceBrowserControl

class BrowserGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Browser Assistant")
        self.root.geometry("300x700")
        self.root.minsize(250, 500)
        
        # Set the window to stay on top and on the right side of the screen
        self.root.attributes('-topmost', True)
        self.position_window_right()
        
        # Configure the main frame
        self.main_frame = ttk.Frame(root)
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
        
        self.status_value = ttk.Label(self.status_frame, text="Ready")
        self.status_value.pack(side=tk.LEFT, padx=(5, 0))
        
        # Common commands section
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
        
        # Initialize the browser controller and voice engine
        self.browser_controller = None
        self.voice_engine = pyttsx3.init()
        self.recognizer = sr.Recognizer()
        
        # Start browser in the background
        self.start_browser_thread = threading.Thread(target=self.start_browser)
        self.start_browser_thread.daemon = True
        self.start_browser_thread.start()
        
        # Add system message to chat
        self.add_to_chat("System", "Welcome to Voice Browser Assistant! Type a command or use the voice button.")
        
        # Set up close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def position_window_right(self):
        """Position the window on the right side of the screen"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 300
        
        x_position = screen_width - window_width
        y_position = 0
        
        self.root.geometry(f"{window_width}x{screen_height}+{x_position}+{y_position}")
    
    def start_browser(self):
        """Initialize the browser controller"""
        try:
            self.update_status("Starting browser...")
            self.browser_controller = VoiceBrowserControl()
            self.update_status("Browser ready")
            self.add_to_chat("System", "Browser is ready. You can start giving commands.")
        except Exception as e:
            self.update_status("Error")
            self.add_to_chat("System", f"Error starting browser: {str(e)}")
    
    def send_command(self, event=None):
        """Process the command from the input field"""
        command = self.command_input.get().strip()
        if not command:
            return
        
        self.add_to_chat("You", command)
        self.command_input.delete(0, tk.END)
        
        if not self.browser_controller:
            self.add_to_chat("System", "Browser is not ready yet. Please wait.")
            return
        
        # Process the command in a thread to keep UI responsive
        self.update_status("Processing...")
        threading.Thread(target=self.process_command_thread, args=(command,)).start()
    
    def process_command_thread(self, command):
        """Thread to process commands"""
        try:
            # Check if we need to close the browser
            if command.lower() in ["exit", "quit", "close browser"]:
                self.add_to_chat("System", "Closing browser...")
                self.browser_controller.close_browser()
                self.update_status("Browser closed")
                return
            
            # Process the command using the browser controller
            result = self.browser_controller.process_command(command)
            
            # If no specific result was returned, use default response
            if not result:
                self.add_to_chat("System", "Command processed successfully.")
            else:
                self.add_to_chat("System", result)
            
            self.update_status("Ready")
        except Exception as e:
            self.add_to_chat("System", f"Error processing command: {str(e)}")
            self.update_status("Error")
    
    def listen_voice_command(self):
        """Listen for voice commands"""
        self.update_status("Listening...")
        self.voice_button.config(state=tk.DISABLED)
        
        # Start listening in a separate thread
        threading.Thread(target=self.listen_thread).start()
    
    def listen_thread(self):
        """Thread to handle voice input"""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)
                
            self.update_status("Processing...")
            try:
                command = self.recognizer.recognize_google(audio)
                
                # Update UI from the main thread
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
            # Re-enable the voice button
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
        """Update the status display"""
        self.root.after(0, lambda: self.status_value.config(text=status))
    
    def on_closing(self):
        """Handle window closing"""
        if self.browser_controller:
            try:
                self.browser_controller.close_browser()
            except:
                pass
        self.root.destroy()
        sys.exit(0)

def main():
    """Main function to start the GUI"""
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
    
    # Start the GUI
    root = tk.Tk()
    app = BrowserGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 