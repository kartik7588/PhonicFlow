import json
import os
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

class FavoritesManager:
    def __init__(self, voice_engine=None):
        """Initialize the favorites manager"""
        self.favorites_file = 'browser_favorites.json'
        self.favorites = {}
        self.voice_engine = voice_engine  # For voice feedback (optional)
        self.load_favorites()
        
    def load_favorites(self):
        """Load user favorites from file or create with defaults"""
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r') as f:
                    self.favorites = json.load(f)
                logger.info("Loaded favorites from file")
            except Exception as e:
                logger.error(f"Error loading favorites: {e}")
                self.favorites = DEFAULT_CATEGORIES
        else:
            self.favorites = DEFAULT_CATEGORIES
            self.save_favorites()
            logger.info("Created new favorites file with defaults")
    
    def save_favorites(self):
        """Save user favorites to file"""
        try:
            with open(self.favorites_file, 'w') as f:
                json.dump(self.favorites, f, indent=4)
            logger.info("Saved favorites to file")
        except Exception as e:
            logger.error(f"Error saving favorites: {e}")
    
    def set_favorite(self, category, website, speak_callback=None):
        """Set a favorite website for a category"""
        # Ensure the website has a proper format
        if not website.startswith(('http://', 'https://')):
            if '.' not in website:
                website = website + ".com"
            website = 'https://' + website
            
        self.favorites[category.lower()] = website
        self.save_favorites()
        message = f"Set {category} favorite to {website}"
        logger.info(message)
        
        # Provide voice feedback if callback is provided
        if speak_callback:
            speak_callback(message)
            
        return message
    
    def get_favorite(self, category):
        """Get favorite website for a category"""
        return self.favorites.get(category.lower())
    
    def get_all_favorites(self):
        """Get all favorites as a formatted string"""
        favorites_list = [f"{category} is set to {website}" for category, website in self.favorites.items()]
        return ". ".join(favorites_list)
    
    def is_setting_favorite_command(self, command):
        """Check if the command is trying to set a favorite"""
        # First, handle 'when I say' as a special case
        if "when i say" in command.lower():
            parts = command.lower().split()
            if len(parts) >= 5:  # Need at least "when I say category use website"
                for i in range(len(parts)-2):
                    if parts[i:i+3] == ["when", "i", "say"] and i+3 < len(parts):
                        return True
        
        # Continue with other patterns
        set_patterns = [
            r'(?:set|make|change)\s+(?:favorite|default)\s+(\w+)\s+(?:to|as|website to)\s+(.+)',
            r'(?:set|make|change)\s+(\w+)\s+(?:favorite|default)\s+(?:to|as|website to)\s+(.+)',
            r'(?:use|save)\s+(.+)\s+(?:as|for)\s+(?:my|the)\s+(\w+)\s+(?:category|site|website)',
            r'(?:for)\s+(\w+)\s+(?:use|open|go to)\s+(.+)',
        ]
        
        for pattern in set_patterns:
            if re.search(pattern, command.lower()):
                return True
        return False
    
    def extract_favorite_settings(self, command):
        """Extract category and website from a set favorite command"""
        # First, handle 'when I say' as a special case
        if "when i say" in command.lower():
            parts = command.lower().split()
            for i in range(len(parts)-2):
                if parts[i:i+3] == ["when", "i", "say"] and i+4 < len(parts) and "use" in parts[i+4:]:
                    category = parts[i+3]
                    use_index = parts.index("use", i+4)
                    if use_index < len(parts) - 1:
                        website = " ".join(parts[use_index+1:])
                        # Clean up website string
                        website = website.rstrip('.').strip()
                        if not website.startswith(('http://', 'https://')):
                            if not ('.' in website and ' ' not in website):
                                website = website + ".com"
                            website = 'https://' + website
                        return category, website
        
        # Continue with other patterns
        set_patterns = [
            r'(?:set|make|change)\s+(?:favorite|default)\s+(\w+)\s+(?:to|as|website to)\s+(.+)',
            r'(?:set|make|change)\s+(\w+)\s+(?:favorite|default)\s+(?:to|as|website to)\s+(.+)',
            r'(?:use|save)\s+(.+)\s+(?:as|for)\s+(?:my|the)\s+(\w+)\s+(?:category|site|website)',
            r'(?:for)\s+(\w+)\s+(?:use|open|go to)\s+(.+)',
        ]
        
        for pattern in set_patterns:
            match = re.search(pattern, command.lower())
            if match:
                # Extract category and website, handling the order based on pattern
                if "as my" in pattern or "for my" in pattern:
                    website = match.group(1).strip()
                    category = match.group(2).lower()
                else:
                    category = match.group(1).lower()
                    website = match.group(2).strip()
                
                # Clean up website string
                website = website.rstrip('.').strip()
                if not website.startswith(('http://', 'https://')):
                    if not ('.' in website and ' ' not in website):
                        website = website + ".com"
                    website = 'https://' + website
                
                return category, website
        
        return None, None
    
    def is_open_category_command(self, command):
        """Check if the command is trying to open a category"""
        category_patterns = [
            r'open\s+(?:the|my)?\s*category\s+(\w+)',
            r'go\s+to\s+(?:the|my)?\s*category\s+(\w+)',
            r'launch\s+(?:the|my)?\s*category\s+(\w+)',
            r'navigate\s+to\s+(?:the|my)?\s*category\s+(\w+)'
        ]
        
        for pattern in category_patterns:
            if re.search(pattern, command.lower()):
                return True
        return False
    
    def extract_category(self, command):
        """Extract category from an open category command"""
        category_patterns = [
            r'open\s+(?:the|my)?\s*category\s+(\w+)',
            r'go\s+to\s+(?:the|my)?\s*category\s+(\w+)',
            r'launch\s+(?:the|my)?\s*category\s+(\w+)',
            r'navigate\s+to\s+(?:the|my)?\s*category\s+(\w+)'
        ]
        
        for pattern in category_patterns:
            match = re.search(pattern, command.lower())
            if match:
                return match.group(1).lower()
        
        return None
    
    def is_listing_favorites_command(self, command):
        """Check if the command is asking to list favorites"""
        list_patterns = [
            r'list favorites',
            r'show favorites', 
            r'display favorites', 
            r'what are my favorites', 
            r'tell me my favorites', 
            r'show my favorites',
            r'list my favorites'
        ]
        
        for pattern in list_patterns:
            if pattern in command.lower():
                return True
        return False 