import speech_recognition as sr
import re
import time
import json
import os
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import pyttsx3  # For voice feedback
import threading  # For managing background reading
from bs4 import BeautifulSoup  # For parsing HTML
import groq  # For LLM-based intent analysis
from advanced_page_analyzer import AdvancedPageAnalyzer  # Import our advanced page analyzer
from youtube_controller import YouTubeController  # Import our YouTube controller
from favorites_manager import FavoritesManager  # Import our favorites manager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Download NLTK data (first time only)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Default categories and their websites
DEFAULT_CATEGORIES = {
    "videos": "https://www.youtube.com",
    "shopping": "https://www.amazon.in",
    "social": "https://www.facebook.com",
    "search": "https://www.google.com",
    "news": "https://www.cnn.com",
    "mail": "https://www.gmail.com",
    "movies": "https://www.netflix.com",
    "music": "https://www.spotify.com",
    "maps": "https://www.google.com/maps"
}

# NLP keywords for intent recognition
INTENT_KEYWORDS = {
    "watch_video": ["watch", "video", "youtube", "videos", "film", "stream", "streaming", "watch video"],
    "shopping": ["shop", "buy", "purchase", "shopping", "amazon", "order", "cart"],
    "social_media": ["social", "facebook", "twitter", "instagram", "post", "friend", "connect", "social media"],
    "search": ["search", "find", "google", "look up", "lookup", "query"],
    "news": ["news", "headlines", "current events", "world news", "breaking news"],
    "mail": ["mail", "email", "gmail", "message", "inbox"],
    "movies": ["movie", "movies", "netflix", "film", "cinema", "watch movie"],
    "music": ["music", "song", "listen", "spotify", "playlist", "album", "artist"]
}

# Define commands for LLM understanding
SUPPORTED_COMMANDS = [
    "Open website",
    "Search for",
    "Scroll down/up", 
    "Click on element",
    "Go back/forward",
    "Refresh page",
    "Read page aloud",
    "Stop reading",
    "Set favorite category",
    "Open category website",
    "Show favorites",
    "Close browser",
    "Describe page",
    "Describe products",
    "Describe videos",
    "Describe images",
    "Describe music",
    "Search YouTube",
    "Describe video number",
    "Play video number",
    "List videos"
]

COMMAND_EXAMPLES = {
    "Open website": ["Open Google", "Go to YouTube", "Visit Wikipedia"],
    "Search for": ["Search for weather forecast", "Look up news about technology"],
    "Scroll down/up": ["Scroll down", "Scroll up", "Scroll down a bit"],
    "Click on element": ["Click sign in", "Click on first link", "Click submit button"],
    "Go back/forward": ["Go back", "Previous page", "Go forward", "Next page"],
    "Refresh page": ["Refresh page", "Reload", "Refresh the site"],
    "Read page aloud": ["Read page", "Read this to me", "Read article", "Read aloud"],
    "Stop reading": ["Stop reading", "Stop", "Be quiet", "Silence"],
    "Set favorite category": ["Set favorite videos to YouTube", "When I say music use Spotify", "For shopping use Amazon"],
    "Open category website": ["Open category shopping", "I want to watch videos", "I'm in the mood for shopping"],
    "Show favorites": ["Show favorites", "List my favorites", "What are my favorites"],
    "Close browser": ["Close browser", "Exit", "Quit", "Close"],
    "Describe page": ["Tell me what's on this page", "Describe this page", "What can you see?"],
    "Describe products": ["Tell me about the products", "What products are available", "Tell me about products on this page"],
    "Describe videos": ["Tell me about the videos", "What videos are on this page", "Describe the videos"],
    "Describe images": ["Describe the images", "What images do you see", "Tell me about the pictures"],
    "Describe music": ["Tell me about the music", "What songs are on this page", "Describe the tracks"],
    "Search YouTube": ["Search YouTube for cat videos", "Find music videos on YouTube", "YouTube search for cooking recipes"],
    "Describe video number": ["Tell me about video number 2", "What's video 3 about", "Describe the first video"],
    "Play video number": ["Play video number 2", "Play the third video", "Start video 1"],
    "List videos": ["List the videos", "What videos did you find", "Summarize search results"]
}

class VoiceBrowserControl:
    def __init__(self, existing_driver=None):
        self.recognizer = sr.Recognizer()
        # Initialize voice engine for feedback
        self.voice_engine = pyttsx3.init()
        
        # Use existing driver if provided, otherwise initialize a new browser
        if existing_driver:
            self.driver = existing_driver
            self.current_url = self.driver.current_url
        else:
            # Initialize browser
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")  # Start maximized
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            self.driver.implicitly_wait(10)  # Wait up to 10 seconds for elements to appear
            self.current_url = None
        
        # Initialize favorites manager
        self.favorites_manager = FavoritesManager()
        
        # For read aloud functionality
        self.reading_thread = None
        self.stop_reading = False
        
        # Initialize Groq client for LLM-based intent analysis
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            logger.warning("GROQ_API_KEY not found in environment variables. LLM functionality will be limited.")
            self.groq_client = None
        else:
            self.groq_client = groq.Client(api_key=groq_api_key)
        
        # Initialize advanced page analyzer
        self.page_analyzer = AdvancedPageAnalyzer(groq_api_key)
        
        # Initialize YouTube controller
        self.youtube_controller = YouTubeController(self.driver, self.speak)
        
        # State for YouTube interaction
        self.awaiting_video_confirmation = False
        self.video_to_confirm = None
        
        logger.info("Voice Browser Control initialized")
        self.speak("Voice Browser Control ready")
    
    def speak(self, text):
        """Provide voice feedback to the user"""
        logger.info(f"Speaking: {text}")
        self.voice_engine.say(text)
        self.voice_engine.runAndWait()
    
    # Remove the old favorites methods and replace with these delegate methods
    def set_favorite(self, category, website):
        """Delegate to favorites manager"""
        return self.favorites_manager.set_favorite(category, website, self.speak)
    
    def get_favorite(self, category):
        """Delegate to favorites manager"""
        return self.favorites_manager.get_favorite(category)
    
    def load_favorites(self):
        """Delegate to favorites manager"""
        self.favorites_manager.load_favorites()
    
    def save_favorites(self):
        """Delegate to favorites manager"""
        self.favorites_manager.save_favorites()
    
    def analyze_intent(self, text):
        """Analyze text to determine user intent using NLP"""
        # First check if this is a set favorite command - if so, don't process as open category
        if self.favorites_manager.is_setting_favorite_command(text):
            return None

        # Simple tokenization
        words = text.lower().split()
        
        # Check for direct category mentions
        for category in self.favorites_manager.favorites.keys():
            if category in words:
                return {"intent": "open_category", "category": category}
        
        # Check for intent keywords
        for intent, keywords in INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text.lower():
                    if intent == "watch_video":
                        return {"intent": "open_category", "category": "videos"}
                    elif intent == "shopping":
                        return {"intent": "open_category", "category": "shopping"}
                    elif intent == "social_media":
                        return {"intent": "open_category", "category": "social"}
                    elif intent == "search":
                        return {"intent": "open_category", "category": "search"}
                    elif intent == "news":
                        return {"intent": "open_category", "category": "news"}
                    elif intent == "mail":
                        return {"intent": "open_category", "category": "mail"}
                    elif intent == "movies":
                        return {"intent": "open_category", "category": "movies"}
                    elif intent == "music":
                        return {"intent": "open_category", "category": "music"}
        
        # Check for mood-based intents
        mood_keywords = {
            "videos": ["in the mood for watching", "want to watch", "feel like watching"],
            "shopping": ["in the mood for shopping", "want to shop", "feel like shopping"],
            "social": ["check social media", "see what friends are doing"],
            "movies": ["in the mood for a movie", "want to watch a film", "feel like a movie"],
            "music": ["in the mood for music", "want to listen", "feel like listening"]
        }
        
        for category, phrases in mood_keywords.items():
            for phrase in phrases:
                if phrase in text.lower():
                    return {"intent": "open_category", "category": category}
        
        return None

    def listen_to_command(self):
        """Listen for voice commands using the microphone"""
        with sr.Microphone() as source:
            logger.info("Listening for command...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                logger.info("Processing speech...")
                text = self.recognizer.recognize_google(audio)
                logger.info(f"Recognized: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                logger.warning("No speech detected within timeout period")
                return None
            except sr.UnknownValueError:
                logger.warning("Could not understand audio")
                return None
            except sr.RequestError as e:
                logger.error(f"Could not request results; {e}")
                return None

    def extract_page_text(self):
        """Extract readable text from the current web page"""
        try:
            # Get page source
            page_source = self.driver.page_source
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from page: {e}")
            return "Error extracting text from this page."

    def read_page_aloud(self):
        """Reads the current page aloud"""
        page_text = self.extract_page_text()
        
        # Split text into manageable paragraphs
        paragraphs = page_text.split('\n')
        
        # Announce the start of reading
        self.speak("Beginning to read the page")
        
        # Function to read in a separate thread
        def read_text():
            for paragraph in paragraphs:
                if paragraph and len(paragraph.split()) > 3:  # Skip very short lines
                    if self.stop_reading:
                        break
                    self.voice_engine.say(paragraph)
                    self.voice_engine.runAndWait()
                    if self.stop_reading:
                        break
            
            logger.info("Finished reading page or reading was stopped")
        
        # Reset stop flag
        self.stop_reading = False
        
        # Start reading in a separate thread
        self.reading_thread = threading.Thread(target=read_text)
        self.reading_thread.daemon = True
        self.reading_thread.start()
        
        return "READING"

    def stop_reading_aloud(self):
        """Stops reading the page aloud"""
        if self.reading_thread and self.reading_thread.is_alive():
            self.stop_reading = True
            logger.info("Stopping read aloud")
            self.speak("Stopped reading")
    
    def analyze_with_llm(self, user_query):
        """Analyze user query with LLM to determine command intent"""
        if not self.groq_client:
            logger.warning("Groq client not available. Falling back to basic intent recognition.")
            return None
            
        try:
            # Create the system prompt with command definitions
            system_prompt = f"""
            You are an assistant that interprets natural language commands for a voice-controlled browser.
            Your task is to analyze the user's query and determine which command they want to execute.
            
            Here are the supported commands:
            {", ".join(SUPPORTED_COMMANDS)}
            
            Some example phrasings for each command:
            """
            
            for command, examples in COMMAND_EXAMPLES.items():
                system_prompt += f"\n{command}: {', '.join(examples)}"
            
            system_prompt += """
            
            Respond with a JSON object in the following format:
            {
              "command": "The matched command name from the list above",
              "parameters": {
                "param1": "value1",
                "param2": "value2"
              }
            }
            
            Examples:
            User: "Open Google"
            Response: {"command": "Open website", "parameters": {"website": "google.com"}}
            
            User: "I want to watch some videos"
            Response: {"command": "Open category website", "parameters": {"category": "videos"}}
            
            User: "Set my shopping favorite to Amazon"
            Response: {"command": "Set favorite category", "parameters": {"category": "shopping", "website": "amazon.com"}}
            
            User: "Tell me what's on this page" 
            Response: {"command": "Describe page", "parameters": {}}
            
            DO NOT include any explanation, just the JSON object.
            """
            
            # Send query to Groq LLM
            response = self.groq_client.chat.completions.create(
                model="llama3-70b-8192",  # Using a fast, economical model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.0  # Low temperature for consistent results
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to parse the response as JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error using Groq API: {str(e)}")
            return None
    
    def analyze_page_structure(self):
        """Analyze the current page structure and extract important elements and their information"""
        try:
            # Get page source
            page_source = self.driver.page_source
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Container for all the extracted information
            page_info = {
                "title": soup.title.string if soup.title else "No title found",
                "url": self.driver.current_url,
                "products": [],
                "videos": [],
                "articles": [],
                "cards": [],
                "music": [],
                "images": [],
                "links": []
            }
            
            # Extract product information (common in e-commerce sites)
            product_elements = soup.select('.product, [class*=product], [id*=product], .item, [data-component*=product]')
            for product in product_elements[:10]:  # Limit to 10 products for manageability
                product_info = {
                    "name": self._extract_text(product.select_one('.product-title, .name, h2, h3, [class*=title]')),
                    "price": self._extract_text(product.select_one('.price, [class*=price]')),
                    "seller": self._extract_text(product.select_one('.seller, .vendor, [class*=seller], [class*=vendor]')),
                    "rating": self._extract_text(product.select_one('.rating, [class*=rating], .stars')),
                    "description": self._extract_text(product.select_one('.description, [class*=description]'))
                }
                if any(product_info.values()):
                    page_info["products"].append(product_info)
            
            # Extract video information
            video_elements = soup.select('video, [class*=video], [id*=video], iframe[src*=youtube], iframe[src*=vimeo]')
            for video in video_elements[:10]:
                video_info = {
                    "title": video.get('title') or video.get('alt') or video.get('aria-label') or 
                             self._extract_text(video.find_previous(['h1', 'h2', 'h3', 'h4', '.title', '[class*=title]'])),
                    "creator": self._extract_text(video.find_previous('[class*=creator], [class*=author], [class*=channel]')),
                    "duration": video.get('duration') or self._extract_text(video.select_one('[class*=duration], [class*=length], [class*=time]')),
                    "src": video.get('src') or (video.select_one('source').get('src') if video.select_one('source') else None)
                }
                if any(video_info.values()):
                    page_info["videos"].append(video_info)
            
            # Extract article/content card information
            card_elements = soup.select('article, .card, [class*=card], .post, [class*=post], .item, [class*=item]')
            for card in card_elements[:10]:
                card_info = {
                    "title": self._extract_text(card.select_one('h1, h2, h3, h4, .title, [class*=title], [class*=heading]')),
                    "author": self._extract_text(card.select_one('.author, [class*=author], [class*=byline]')),
                    "date": self._extract_text(card.select_one('.date, [class*=date], [class*=time], time')),
                    "summary": self._extract_text(card.select_one('p, .summary, [class*=summary], [class*=excerpt]'))
                }
                if any(card_info.values()):
                    page_info["cards"].append(card_info)
            
            # Extract music information
            music_elements = soup.select('audio, [class*=track], [class*=song], [class*=music], [class*=playlist]')
            for music in music_elements[:10]:
                music_info = {
                    "title": self._extract_text(music.select_one('[class*=title], .name, [class*=name]')) or music.get('title') or music.get('aria-label'),
                    "artist": self._extract_text(music.select_one('[class*=artist], .artist, [class*=singer], .singer')),
                    "album": self._extract_text(music.select_one('[class*=album]')),
                    "duration": self._extract_text(music.select_one('[class*=duration], [class*=length], [class*=time]'))
                }
                if any(music_info.values()):
                    page_info["music"].append(music_info)
            
            # Extract image information (focus on meaningful images, not icons)
            img_elements = soup.select('img[alt]:not([width="16"]):not([width="24"]):not([width="32"]):not([height="16"]):not([height="24"]):not([height="32"])')
            for img in img_elements[:15]:
                if img.get('alt') and img.get('alt').strip():
                    img_info = {
                        "alt": img.get('alt'),
                        "src": img.get('src')
                    }
                    page_info["images"].append(img_info)
            
            # Extract main links
            links = soup.select('a[href]:not([href^="#"]):not([href=""]) h1, a[href]:not([href^="#"]):not([href=""]) h2, a[href]:not([href^="#"]):not([href=""]) h3, a.main-link, a.primary-link')
            for link in links[:10]:
                link_info = {
                    "text": link.get_text(strip=True),
                    "href": link.get('href')
                }
                if link_info["text"]:
                    page_info["links"].append(link_info)
            
            return page_info
            
        except Exception as e:
            logger.error(f"Error analyzing page structure: {e}")
            return {"error": f"Could not analyze page: {str(e)}"}
    
    def _extract_text(self, element):
        """Safely extract text from an element that might be None"""
        if element:
            return element.get_text(strip=True)
        return None
    
    def describe_page(self):
        """Generate a description of what's on the current page using advanced LLM analysis"""
        # First gather basic page information using existing parsing
        page_info = self.analyze_page_structure()
        
        if "error" in page_info:
            self.speak(f"I had trouble analyzing this page. {page_info['error']}")
            return
            
        # Use the advanced analyzer to get LLM-enhanced description
        logger.info("Sending page info to advanced analyzer")
        self.speak("Analyzing the page content...")
        
        enhanced_analysis = self.page_analyzer.analyze_with_llm(page_info)
        
        # Get the human-friendly description
        if enhanced_analysis and 'description' in enhanced_analysis:
            description = enhanced_analysis['description']
        else:
            # If LLM analysis failed, get a human-friendly description from the analyzer
            description = self.page_analyzer.generate_human_friendly_description(enhanced_analysis)
        
        # If we still don't have a description, use the old method as fallback
        if not description:
            logger.warning("Advanced analysis failed. Using basic description.")
            description = self._generate_basic_description(page_info)
        
        logger.info(f"Page description: {description}")
        self.speak(description)
        return description
    
    def _generate_basic_description(self, page_info):
        """Generate a basic description as fallback method"""
        # Build a human-friendly description
        description = f"You're on {page_info['title']} at {page_info['url']}. "
        
        # Describe products if any
        if page_info["products"]:
            description += f"I found {len(page_info['products'])} products. "
            for i, product in enumerate(page_info["products"][:3]):
                product_desc = f"Product {i+1} is "
                if product.get("name"):
                    product_desc += f"{product['name']}, "
                if product.get("price"):
                    product_desc += f"priced at {product['price']}, "
                if product.get("seller"):
                    product_desc += f"sold by {product['seller']}, "
                description += product_desc.rstrip(", ") + ". "
            
            if len(page_info["products"]) > 3:
                description += f"And {len(page_info['products']) - 3} more products. "
        
        # Describe videos if any
        if page_info["videos"]:
            description += f"I found {len(page_info['videos'])} videos. "
            for i, video in enumerate(page_info["videos"][:3]):
                video_desc = f"Video {i+1} "
                if video.get("title"):
                    video_desc += f"is titled '{video['title']}', "
                if video.get("creator"):
                    video_desc += f"by {video['creator']}, "
                if video.get("duration"):
                    video_desc += f"with duration {video['duration']}, "
                description += video_desc.rstrip(", ") + ". "
            
            if len(page_info["videos"]) > 3:
                description += f"And {len(page_info['videos']) - 3} more videos. "
        
        # Describe cards/articles if any
        if page_info["cards"]:
            description += f"I found {len(page_info['cards'])} articles or content cards. "
            for i, card in enumerate(page_info["cards"][:3]):
                card_desc = f"Card {i+1} "
                if card.get("title"):
                    card_desc += f"is titled '{card['title']}', "
                if card.get("author"):
                    card_desc += f"by {card['author']}, "
                if card.get("date"):
                    card_desc += f"dated {card['date']}, "
                description += card_desc.rstrip(", ") + ". "
            
            if len(page_info["cards"]) > 3:
                description += f"And {len(page_info['cards']) - 3} more cards. "
        
        # Describe music if any
        if page_info["music"]:
            description += f"I found {len(page_info['music'])} music tracks. "
            for i, track in enumerate(page_info["music"][:3]):
                track_desc = f"Track {i+1} "
                if track.get("title"):
                    track_desc += f"is '{track['title']}', "
                if track.get("artist"):
                    track_desc += f"by {track['artist']}, "
                if track.get("album"):
                    track_desc += f"from album {track['album']}, "
                description += track_desc.rstrip(", ") + ". "
            
            if len(page_info["music"]) > 3:
                description += f"And {len(page_info['music']) - 3} more tracks. "
        
        # Describe images if any
        if page_info["images"]:
            description += f"I found {len(page_info['images'])} images with descriptions. "
            for i, img in enumerate(page_info["images"][:5]):
                if img.get("alt"):
                    description += f"Image {i+1} shows {img['alt']}. "
            
            if len(page_info["images"]) > 5:
                description += f"And {len(page_info['images']) - 5} more images. "
        
        # Describe main links if any
        if page_info["links"]:
            description += f"I found {len(page_info['links'])} main links including: "
            link_texts = [link.get("text", "unnamed link") for link in page_info["links"][:5]]
            description += ", ".join(link_texts)
            if len(page_info["links"]) > 5:
                description += f", and {len(page_info['links']) - 5} more."
        
        # If no content found
        content_types = ["products", "videos", "cards", "music", "images", "links"]
        if not any(len(page_info[content_type]) > 0 for content_type in content_types):
            description += "I didn't identify any specific content like products, videos, or articles on this page."
        
        return description
    
    def describe_content_type(self, content_type):
        """Generate a detailed description for a specific type of content on the page"""
        # First get the page structure
        page_info = self.analyze_page_structure()
        
        if "error" in page_info:
            self.speak(f"I had trouble analyzing this page. {page_info['error']}")
            return
        
        # Map the content type to the corresponding key in page_info
        content_map = {
            "products": "products",
            "videos": "videos",
            "images": "images",
            "music": "music",
            "articles": "cards",  # cards in page_info contains articles
            "links": "links"
        }
        
        target_key = content_map.get(content_type.lower())
        if not target_key or target_key not in page_info:
            self.speak(f"I don't know how to describe {content_type}.")
            return
            
        items = page_info[target_key]
        
        if not items:
            self.speak(f"I didn't find any {content_type} on this page.")
            return
            
        # Try to get enhanced descriptions using LLM
        if hasattr(self, 'page_analyzer') and self.page_analyzer.llm_client:
            try:
                # Create a focused prompt for just this content type
                system_prompt = f"""
                You are a specialized web content analyzer. For the given {content_type} information from a webpage,
                provide a detailed, conversational description of these {content_type}.
                Focus only on the {content_type} and their characteristics.
                """
                
                user_prompt = f"""
                I found {len(items)} {content_type} on the page "{page_info['title']}".
                Here are the details:
                
                {json.dumps(items[:10], indent=2)}
                
                Please provide a detailed, conversational description of these {content_type}.
                For products: describe what's being sold, price ranges, brands, etc.
                For videos: describe the content themes, creators, topics, etc.
                For images: explain what they show based on alt text.
                For music: describe the artists, genres, themes, etc.
                For articles: summarize the topics and themes.
                """
                
                response = self.page_analyzer.llm_client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1024,
                )
                
                description = response.choices[0].message.content.strip()
                self.speak(description)
                return description
                
            except Exception as e:
                logger.error(f"Error getting enhanced {content_type} description: {e}")
                # Fall back to basic description
        
        # Basic description fallback
        description = f"I found {len(items)} {content_type} on this page. "
        
        # Different handling based on content type
        if content_type == "products":
            for i, item in enumerate(items[:5]):
                product_desc = f"Product {i+1}: "
                if item.get("name"):
                    product_desc += f"{item['name']}, "
                if item.get("price"):
                    product_desc += f"priced at {item['price']}, "
                if item.get("seller"):
                    product_desc += f"sold by {item['seller']}, "
                if item.get("rating"):
                    product_desc += f"rated {item['rating']}, "
                description += product_desc.rstrip(", ") + ". "
        
        elif content_type == "videos":
            for i, item in enumerate(items[:5]):
                video_desc = f"Video {i+1}: "
                if item.get("title"):
                    video_desc += f"'{item['title']}', "
                if item.get("creator"):
                    video_desc += f"by {item['creator']}, "
                if item.get("duration"):
                    video_desc += f"duration {item['duration']}, "
                description += video_desc.rstrip(", ") + ". "
        
        elif content_type == "images":
            for i, item in enumerate(items[:8]):
                if item.get("alt"):
                    description += f"Image {i+1} shows {item['alt']}. "
        
        elif content_type == "music":
            for i, item in enumerate(items[:5]):
                music_desc = f"Track {i+1}: "
                if item.get("title"):
                    music_desc += f"'{item['title']}', "
                if item.get("artist"):
                    music_desc += f"by {item['artist']}, "
                if item.get("album"):
                    music_desc += f"from album {item['album']}, "
                description += music_desc.rstrip(", ") + ". "
        
        elif content_type == "articles":
            for i, item in enumerate(items[:5]):
                article_desc = f"Article {i+1}: "
                if item.get("title"):
                    article_desc += f"'{item['title']}', "
                if item.get("author"):
                    article_desc += f"by {item['author']}, "
                if item.get("date"):
                    article_desc += f"dated {item['date']}, "
                description += article_desc.rstrip(", ") + ". "
        
        elif content_type == "links":
            link_texts = [f"'{link.get('text', 'unnamed link')}'" for link in items[:8] if link.get('text')]
            if link_texts:
                description += f"Main links include: {', '.join(link_texts)}"
        
        # For more than shown items
        content_count = len(items)
        if content_count > 5 and content_type != "images" and content_type != "links":
            description += f"And {content_count - 5} more {content_type}."
        elif content_count > 8 and (content_type == "images" or content_type == "links"):
            description += f"And {content_count - 8} more {content_type}."
        
        self.speak(description)
        return description
    
    def execute_llm_command(self, command_info):
        """Execute a command based on LLM analysis"""
        if not command_info:
            return None
            
        command = command_info.get("command")
        params = command_info.get("parameters", {})
        
        logger.info(f"Executing LLM command: {command} with params {params}")
        
        if command == "Open website":
            website = params.get("website", "")
            if website:
                return self.open_website(website)
                
        elif command == "Search for":
            query = params.get("query", "")
            if query:
                return self.search(query)
                
        elif command == "Scroll down/up":
            direction = params.get("direction", "down")
            return self.scroll(direction)
            
        elif command == "Click on element":
            element = params.get("element", "")
            if element:
                return self.click_element(element)
                
        elif command == "Go back/forward":
            direction = params.get("direction", "back")
            return self.navigate(direction)
            
        elif command == "Refresh page":
            return self.refresh_page()
            
        elif command == "Read page aloud":
            return self.read_page_aloud()
            
        elif command == "Stop reading":
            return self.stop_reading_aloud()
            
        elif command == "Set favorite category":
            category = params.get("category", "")
            website = params.get("website", "")
            if category and website:
                return self.set_favorite(category, website)
                
        elif command == "Open category website":
            category = params.get("category", "")
            if category:
                website = self.get_favorite(category)
                if website:
                    self.speak(f"Opening {category}")
                    return self.open_website(website)
                    
        elif command == "Show favorites":
            favorites_text = "Your favorites are: "
            favorites_list = self.favorites_manager.get_all_favorites()
            full_text = favorites_text + favorites_list
            
            logger.info(f"Favorites: {favorites_list}")
            self.speak(full_text)
            return True
            
        elif command == "Close browser":
            return self.close_browser()
            
        elif command == "Describe page":
            return self.describe_page()
            
        elif command.startswith("Describe ") and "video number" not in command.lower():
            content_type = command.replace("Describe ", "").lower()
            return self.describe_content_type(content_type)
            
        # YouTube specific commands
        elif command == "Search YouTube":
            query = params.get("query", "")
            if query:
                return self.youtube_controller.search_youtube(query)
                
        elif command == "Describe video number":
            position = params.get("position", 0)
            if position:
                # Store the video position for potential confirmation
                self.awaiting_video_confirmation = True
                self.video_to_confirm = position
                return self.youtube_controller.describe_video(position)
                
        elif command == "Play video number":
            position = params.get("position", 0)
            if position:
                return self.youtube_controller.play_video(position)
                
        elif command == "List videos":
            return self.youtube_controller.summarize_search_results()
            
        return None
    
    def process_command(self, command):
        """Process the voice command and determine the action to take"""
        if not command:
            return
        
        # Special handling for YouTube video confirmation
        if self.awaiting_video_confirmation:
            if any(confirmation in command.lower() for confirmation in ["yes", "yeah", "sure", "okay", "play it", "confirm"]):
                self.awaiting_video_confirmation = False
                position = self.video_to_confirm
                self.video_to_confirm = None
                return self.youtube_controller.play_video(position)
            elif any(rejection in command.lower() for rejection in ["no", "nope", "don't", "cancel", "stop", "don't play"]):
                self.awaiting_video_confirmation = False
                self.video_to_confirm = None
                self.speak("Video playback cancelled.")
                return
        
        # Stop reading command (check this first to ensure responsiveness)
        if any(phrase in command for phrase in ["stop reading", "stop", "quiet", "silence", "be quiet", "shut up"]):
            self.stop_reading_aloud()
            return
        
        # First try LLM-based intent analysis if available
        llm_analysis = self.analyze_with_llm(command)
        if llm_analysis:
            result = self.execute_llm_command(llm_analysis)
            if result:
                return result
        
        # If LLM failed or isn't available, fall back to traditional methods
        # Read aloud command
        if any(phrase in command for phrase in [
            "read page", "read this page", "read aloud", "read the page", 
            "read to me", "read this to me", "read this", "read the article",
            "read this article", "start reading"
        ]):
            return self.read_page_aloud()
        
        # YouTube search command patterns
        youtube_search_patterns = [
            r"(?:search|find|look for)(?:.+?)(?:on|in|at)(?:.+?)youtube(?:.+?)(?:for\s+)(.+)",
            r"youtube(?:.+?)(?:search|find|look for)(?:.+?)(?:for\s+)(.+)",
            r"(?:search|find|look for)(?:.+?)youtube(?:\s+for\s+)(.+)"
        ]
        
        for pattern in youtube_search_patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                search_query = match.group(1).strip()
                if search_query:
                    self.youtube_controller.search_youtube(search_query)
                    return
        
        # YouTube video selection patterns
        video_number_pattern = r"(?:tell me about|what's|describe|play|show|start)(?:.+?)(?:video|) (?:number |#)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|[1-9])"
        match = re.search(video_number_pattern, command, re.IGNORECASE)
        if match:
            position_text = match.group(1).lower()
            position = 1  # Default to first
            
            # Convert position text to number
            if position_text in ["first", "1st", "1"]:
                position = 1
            elif position_text in ["second", "2nd", "2"]:
                position = 2
            elif position_text in ["third", "3rd", "3"]:
                position = 3
            elif position_text in ["fourth", "4th", "4"]:
                position = 4
            elif position_text in ["fifth", "5th", "5"]:
                position = 5
            elif position_text.isdigit():
                position = int(position_text)
            
            # Determine if it's a describe or play command
            if any(action in command.lower() for action in ["tell me about", "what's", "describe"]):
                self.awaiting_video_confirmation = True
                self.video_to_confirm = position
                self.youtube_controller.describe_video(position)
            elif any(action in command.lower() for action in ["play", "show", "start"]):
                self.youtube_controller.play_video(position)
            return
        
        # YouTube list videos command
        if any(phrase in command.lower() for phrase in ["list videos", "show videos", "what videos", "summarize videos", "summarize results"]):
            self.youtube_controller.summarize_search_results()
            return
        
        # Check for setting favorites first - this needs to take precedence
        if self.favorites_manager.is_setting_favorite_command(command):
            category, website = self.favorites_manager.extract_favorite_settings(command)
            if category and website:
                result = self.set_favorite(category, website)
                logger.info(result)
                return
               
        # Check if this is a direct open category command
        if self.favorites_manager.is_open_category_command(command):
            category = self.favorites_manager.extract_category(command)
            if category:
                website = self.get_favorite(category)
                if website:
                    self.speak(f"Opening {category}")
                    self.open_website(website)
                    return
        
        # Check if user wants to list favorites
        if self.favorites_manager.is_listing_favorites_command(command):
            favorites_text = "Your favorites are: "
            favorites_list = self.favorites_manager.get_all_favorites()
            full_text = favorites_text + favorites_list
            
            logger.info(f"Favorites: {favorites_list}")
            self.speak(full_text)
            return
        
        # Open website commands
        if "open" in command or "go to" in command:
            website = None
            
            # Extract website from command
            if "open" in command:
                match = re.search(r'open\s+(.*?)(?:\s+in browser|\s+website|\s+site|\s*$)', command)
                if match:
                    website = match.group(1)
            elif "go to" in command:
                match = re.search(r'go to\s+(.*?)(?:\s+website|\s+site|\s*$)', command)
                if match:
                    website = match.group(1)
            
            if website:
                self.open_website(website)
                return
        
        # Scroll commands
        if "scroll" in command:
            if "down" in command:
                self.scroll(direction="down")
            elif "up" in command:
                self.scroll(direction="up")
            return
        
        # Click commands
        if "click" in command:
            # Look for elements to click based on the command
            element_text = command.replace("click", "").strip()
            if element_text:
                self.click_element(element_text)
            return
        
        # Back/forward navigation
        if "back" in command or "previous page" in command:
            self.navigate("back")
            return
        
        if "forward" in command or "next page" in command:
            self.navigate("forward")
            return
        
        # Search commands
        if "search for" in command:
            search_query = command.replace("search for", "").strip()
            self.search(search_query)
            return
        
        # Refresh page
        if "refresh" in command or "reload" in command:
            self.refresh_page()
            return
        
        # Close browser
        if "close browser" in command or "exit" in command:
            self.close_browser()
            return
        
        # Page description command
        if any(phrase in command for phrase in [
            "what's on this page", "what is on this page", "describe this page", 
            "tell me about this page", "what's on the page", "what can you see", 
            "describe what you see", "analyze this page", "page content"
        ]):
            self.describe_page()
            return
        
        # Specialized content description commands
        content_patterns = [
            (r"(?:tell|describe|what|list)(?:.+?)products", "products"),
            (r"(?:tell|describe|what|list)(?:.+?)videos", "videos"),
            (r"(?:tell|describe|what|list)(?:.+?)images", "images"),
            (r"(?:tell|describe|what|list)(?:.+?)pictures", "images"),
            (r"(?:tell|describe|what|list)(?:.+?)music", "music"),
            (r"(?:tell|describe|what|list)(?:.+?)songs", "music"),
            (r"(?:tell|describe|what|list)(?:.+?)tracks", "music"),
            (r"(?:tell|describe|what|list)(?:.+?)articles", "articles"),
            (r"(?:tell|describe|what|list)(?:.+?)posts", "articles")
        ]
        
        for pattern, content_type in content_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                self.describe_content_type(content_type)
                return
        
        # Help command
        if any(phrase in command for phrase in ["help", "how to use", "instructions", "what can I say", "available commands"]):
            help_text = "You can use the following commands: Open a website like Google, Search for information, Scroll up or down, Click on links or buttons, Go back or forward between pages, Refresh the page, Set favorites for categories, Open websites by category, Show all your favorites, Read the current page aloud, Ask what's on the page, and Stop reading. Say Close browser when you're done."
            logger.info("Help requested")
            self.speak(help_text)
            return
        
        # Continue with existing intent analysis as fallback
        intent_info = self.analyze_intent(command)
        if intent_info:
            if intent_info["intent"] == "open_category":
                category = intent_info["category"]
                website = self.get_favorite(category)
                if website:
                    logger.info(f"Opening favorite {category}: {website}")
                    self.speak(f"Opening {category}")
                    self.open_website(website)
                    return
                   
        logger.info(f"Command not recognized: {command}")

    def open_website(self, website):
        """Open a website in the browser"""
        # Check if website has http/https prefix
        if not website.startswith(('http://', 'https://')):
            # Check if it's a domain name
            if '.' in website and ' ' not in website:
                website = 'https://' + website
            else:
                # Assume it's a search query
                website = f'https://www.google.com/search?q={website.replace(" ", "+")}'
        
        logger.info(f"Opening website: {website}")
        self.driver.get(website)
        self.current_url = self.driver.current_url

    def scroll(self, direction):
        """Scroll the page up or down"""
        if direction == "down":
            logger.info("Scrolling down")
            self.driver.execute_script("window.scrollBy(0, 500);")
        elif direction == "up":
            logger.info("Scrolling up")
            self.driver.execute_script("window.scrollBy(0, -500);")

    def click_element(self, element_text):
        """Click an element containing the specified text"""
        logger.info(f"Looking for element containing: '{element_text}'")
        try:
            # Try to find by link text
            element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, element_text))
            )
            element.click()
            logger.info(f"Clicked link containing '{element_text}'")
            return
        except Exception:
            pass
        
        try:
            # Try by button text
            button_xpath = f"//button[contains(text(), '{element_text}')]"
            element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            element.click()
            logger.info(f"Clicked button containing '{element_text}'")
            return
        except Exception:
            pass
        
        try:
            # Try by any element with text
            xpath = f"//*[contains(text(), '{element_text}')]"
            element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            element.click()
            logger.info(f"Clicked element containing '{element_text}'")
            return
        except Exception as e:
            logger.error(f"Could not find or click element with text '{element_text}': {e}")

    def navigate(self, direction):
        """Navigate back or forward in browser history"""
        if direction == "back":
            logger.info("Navigating back")
            self.driver.back()
        elif direction == "forward":
            logger.info("Navigating forward")
            self.driver.forward()

    def search(self, query):
        """Perform a search using Google"""
        if not self.driver.current_url.startswith('https://www.google.com'):
            self.open_website('https://www.google.com')
        
        logger.info(f"Searching for: {query}")
        try:
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)
        except Exception as e:
            logger.error(f"Error while searching: {e}")

    def refresh_page(self):
        """Refresh the current page"""
        logger.info("Refreshing page")
        self.driver.refresh()

    def close_browser(self):
        """Close the browser"""
        logger.info("Closing browser")
        self.driver.quit()
        return "EXIT"

    def run(self):
        """Main loop to listen for commands and process them"""
        logger.info("Starting Voice Browser Control...")
        # Open Google as starting page
        self.open_website("https://www.google.com")
        
        self.speak("I'm ready for your commands. Say help for instructions.")
        
        while True:
            command = self.listen_to_command()
            if command:
                result = self.process_command(command)
                if result == "EXIT":
                    self.speak("Closing browser. Goodbye!")
                    break
            time.sleep(0.5)


if __name__ == "__main__":
    print("Voice Browser Control starting...")
    print("Speak commands clearly after you see 'Listening for command...'")
    
    print("\n=== BASIC NAVIGATION COMMANDS ===")
    print("- 'Open website name' (e.g., 'Open Google')")
    print("- 'Search for query' (e.g., 'Search for weather forecast')")
    print("- 'Scroll down/up'")
    print("- 'Click text on page' (e.g., 'Click Sign in')")
    print("- 'Go back/forward'")
    print("- 'Refresh page'")
    print("- 'Close browser'")
    
    print("\n=== READ ALOUD COMMANDS ===")
    print("- 'Read page' or 'Read this to me'")
    print("- 'Stop reading' or simply 'Stop'")
    
    print("\n=== CATEGORY & FAVORITES COMMANDS ===")
    print("- 'I'm in the mood for watching videos' (goes to YouTube)")
    print("- 'Set favorite videos to youtube.com'")
    print("- 'When I say videos use youtube.com'")
    print("- 'For shopping use amazon.com'")
    print("- 'Open category shopping'")
    print("- 'Show favorites'")
    print("- 'Help' or 'What can I say'")
    
    print("\n=== PAGE ANALYSIS COMMANDS ===")
    print("- 'What's on this page?' (describes products, videos, images, etc.)")
    print("- 'Describe this page' or 'Tell me about this page'")
    print("- 'What can you see?' (extracts structured content)")
    print("- 'Tell me about the products/videos/images/music' (for specific content types)")
    print("- 'What products are on this page?' (lists all products)")
    print("- 'Describe the images' (describes images based on alt text)")
    
    print("\n=== YOUTUBE COMMANDS ===")
    print("- 'Search YouTube for query' (searches for videos)")
    print("- 'Tell me about video number X' (describes video with confirmation)")
    print("- 'Play video number X' (plays the specified video)")
    print("- 'List videos' (summarizes search results)")
    
    print("\n=== NATURAL LANGUAGE UNDERSTANDING ===")
    print("This version includes LLM-based understanding for more natural commands.")
    print("Set GROQ_API_KEY environment variable to enable full LLM capabilities.")
    print("Example: 'I want to check my email and then search for the weather'")
    
    print("\nAvailable categories in defaults:")
    for category in DEFAULT_CATEGORIES.keys():
        print(f"- {category}")
    print("\nYou can set any new category you want by saying 'Set favorite CATEGORY to WEBSITE'")
    
    # Inform user about Groq API key
    if not os.getenv("GROQ_API_KEY"):
        print("\nNOTE: GROQ_API_KEY not set. Run 'set GROQ_API_KEY=your_api_key' to enable advanced voice commands.")
    
    try:
        control = VoiceBrowserControl()
        control.run()
    except Exception as e:
        logger.error(f"Error in Voice Browser Control: {e}")
        print(f"An error occurred: {e}")