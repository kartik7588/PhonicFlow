import logging
import sys
import os
import re

# Set up logging to file for testing
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("test_favorites.log"), 
                              logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Import our mocks first
import test_mocks

# Now import the modules we want to test
from favorites_manager import FavoritesManager
import voice_browser_control

def test_favorites():
    """
    Test the favorites functionality in voice_browser_control.py
    """
    # Disable actual browser opening for testing
    class MockVoiceBrowserControl:
        def __init__(self):
            # Initialize the favorites manager
            self.favorites_manager = FavoritesManager()
            
            # Set up mock attributes
            self.reading_thread = None
            self.stop_reading = False
            self.groq_client = None
            self.awaiting_video_confirmation = False
            self.video_to_confirm = None
            
            logger.info("Mock Voice Browser Control initialized")
            
        def speak(self, text):
            """Mock speak method that just logs the text"""
            logger.info(f"MOCK SPEAK: {text}")
        
        def open_website(self, website):
            """Mock open_website method that just logs the website"""
            # Check if this is a category name - try to use favorite if available
            if website.lower() in self.favorites_manager.favorites:
                logger.info(f"Recognized '{website}' as a category name, using favorite site")
                website = self.favorites_manager.get_favorite(website.lower())
                
            logger.info(f"MOCK OPEN: Would open website: {website}")
        
        def set_favorite(self, category, website):
            """Delegate to favorites manager"""
            return self.favorites_manager.set_favorite(category, website, self.speak)
        
        def get_favorite(self, category):
            """Delegate to favorites manager"""
            return self.favorites_manager.get_favorite(category)
        
        def process_command(self, command):
            """Simplified command processing focused on favorites"""
            logger.info(f"Processing command: {command}")
            
            # First check the exact patterns for set favorites
            if self.favorites_manager.is_setting_favorite_command(command):
                logger.info("Command identified as a 'set favorite' command")
                category, website = self.favorites_manager.extract_favorite_settings(command)
                if category and website:
                    result = self.set_favorite(category, website)
                    logger.info(f"Set favorite result: {result}")
                    return True
                else:
                    logger.error(f"Failed to extract category and website from '{command}'")
            else:
                # Debug "when I say" pattern matching
                when_i_say_pattern = r'when\s+I\s+say\s+(\w+)\s+(?:use|open|go to)\s+(.+)'
                match = re.search(when_i_say_pattern, command.lower())
                if match:
                    logger.info(f"'when I say' pattern matched but not caught by is_setting_favorite_command")
                    logger.info(f"Match groups: {match.groups()}")
                elif "when i say" in command.lower():
                    logger.info(f"'when I say' phrase found but pattern did not match")
            
            # Special handling for "when I say [category]" commands without "use"
            if "when i say" in command.lower():
                # Simple parsing to extract just the category
                words = command.lower().split()
                for i, word in enumerate(words):
                    if i >= 2 and words[i-2:i] == ["when", "i"] and word == "say" and i+1 < len(words):
                        category = words[i+1]
                        if category in self.favorites_manager.favorites:
                            website = self.get_favorite(category)
                            if website:
                                logger.info(f"Opening favorite {category} from 'when I say' command: {website}")
                                self.speak(f"Opening {category}")
                                self.open_website(website)
                                return True
                        # Even if we don't find a matching category, mark the command as handled
                        else:
                            self.speak(f"I don't have a favorite set for {category}")
                            logger.info(f"No favorite found for category '{category}'")
                            return True
                        break
            
            # Check if this is a direct open category command
            if self.favorites_manager.is_open_category_command(command):
                category = self.favorites_manager.extract_category(command)
                if category:
                    website = self.get_favorite(category)
                    if website:
                        logger.info(f"Opening category {category}")
                        self.speak(f"Opening {category}")
                        self.open_website(website)
                        return True
            
            # Check if user wants to list favorites
            if self.favorites_manager.is_listing_favorites_command(command):
                favorites_text = "Your favorites are: "
                favorites_list = self.favorites_manager.get_all_favorites()
                full_text = favorites_text + favorites_list
                
                logger.info(f"Listing favorites: {favorites_list}")
                self.speak(full_text)
                return True
            
            # If command not recognized
            logger.info(f"Command not recognized: {command}")
            return False
    
    logger.info("Starting favorites test...")
    
    # Create a controller
    controller = MockVoiceBrowserControl()
    
    # Test 1: Get initial favorite for videos
    initial_videos = controller.get_favorite("videos")
    logger.info(f"Initial videos favorite: {initial_videos}")
    
    # Test 2: Set favorite with different commands
    test_commands = [
        "set favorite videos to vimeo.com",
        "for music use spotify.com", 
        "when I say shopping use amazon.in",
        "set news favorite to bbc.com",
        "make movies favorite website to disney.com"
    ]
    
    for command in test_commands:
        logger.info(f"\nTesting command: '{command}'")
        controller.process_command(command)
        
        # Extract category from command for verification
        if "videos" in command:
            category = "videos"
        elif "music" in command:
            category = "music"
        elif "shopping" in command:
            category = "shopping"
        elif "news" in command:
            category = "news"
        elif "movies" in command:
            category = "movies"
            
        # Verify the favorite was set
        current_favorite = controller.get_favorite(category)
        logger.info(f"After command, {category} favorite is: {current_favorite}")
    
    # Test 3: Try to trigger the "set favorite" command followed by "open category" command
    # This tests that our fix prevents "open category" from being triggered when it's actually a "set favorite" command
    
    # First test setting a favorite
    logger.info("\nTesting potential conflict resolution...")
    set_cmd = "set favorite videos to vimeo.com"
    logger.info(f"Command: '{set_cmd}'")
    controller.process_command(set_cmd)
    videos_fav = controller.get_favorite("videos")
    logger.info(f"Videos favorite is now: {videos_fav}")
    
    # Now test opening the category - should open vimeo.com, not youtube.com
    open_cmd = "open category videos"
    logger.info(f"Command: '{open_cmd}'")
    controller.process_command(open_cmd)
    
    # Test 4: List favorites
    list_cmd = "show favorites"
    logger.info(f"\nCommand: '{list_cmd}'")
    controller.process_command(list_cmd)
    
    # Test special cases
    logger.info("\nTesting 'when I say' command specifically...")
    special_cmd = "when I say shopping use amazon.in"
    logger.info(f"Command: '{special_cmd}'")
    # Directly test the pattern
    pattern = r'when\s+I\s+say\s+(\w+)\s+(?:use|open|go to)\s+(.+)'
    match = re.search(pattern, special_cmd.lower())
    if match:
        logger.info(f"Pattern matches: {match.groups()}")
    else:
        logger.info("Pattern does not match")
        
    # Try with variations of the pattern
    patterns_to_try = [
        r'when\s+I\s+say\s+(\w+)\s+use\s+(.+)',
        r'when\s+I\s+say\s+(\w+)(?:\s+)use(?:\s+)(.+)',
        r'when I say (\w+) use (.+)',
        r'when\s+I\s+say\s+(\w+)\s+use\s+([\w\.]+)'
    ]
    
    for i, test_pattern in enumerate(patterns_to_try):
        match = re.search(test_pattern, special_cmd.lower())
        if match:
            logger.info(f"Test pattern {i+1} matches: {match.groups()}")
        else:
            logger.info(f"Test pattern {i+1} does not match")
    
    # Now test with controller
    controller.process_command(special_cmd)
    shopping_fav = controller.get_favorite("shopping")
    logger.info(f"Shopping favorite is now: {shopping_fav}")
    
    # Test the "when I say [category]" command without setting a favorite
    logger.info("\nTesting just 'when I say shopping' (without 'use')...")
    simple_cmd = "when I say shopping"
    logger.info(f"Command: '{simple_cmd}'")
    controller.process_command(simple_cmd)
    
    logger.info("\nAll tests completed!")

if __name__ == "__main__":
    # Create a backup of the favorites file if it exists
    favorites_file = 'browser_favorites.json'
    backup_file = 'browser_favorites.json.bak'
    
    if os.path.exists(favorites_file):
        import shutil
        shutil.copy2(favorites_file, backup_file)
        logger.info(f"Created backup of favorites file: {backup_file}")
    
    try:
        test_favorites()
    finally:
        # Restore the backup if it exists
        if os.path.exists(backup_file):
            import shutil
            shutil.copy2(backup_file, favorites_file)
            os.remove(backup_file)
            logger.info(f"Restored original favorites file")
        elif os.path.exists(favorites_file):
            os.remove(favorites_file)
            logger.info(f"Removed test favorites file") 