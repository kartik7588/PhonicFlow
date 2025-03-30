import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Set up logging
logger = logging.getLogger(__name__)

class YouTubeController:
    """
    Controller for YouTube-specific functionality.
    Handles searching for videos, extracting video information, and playing videos.
    """
    
    def __init__(self, driver, speech_engine):
        """
        Initialize the YouTube controller
        
        Args:
            driver: Selenium webdriver instance
            speech_engine: Text-to-speech engine for voice feedback
        """
        self.driver = driver
        self.speak = speech_engine
        self.current_videos = []  # Store the most recent search results
        
    def search_youtube(self, query):
        """
        Search YouTube for the given query
        
        Args:
            query: Search query string
        
        Returns:
            True if search was successful, False otherwise
        """
        # Check if already on YouTube, if not, navigate to it
        current_url = self.driver.current_url
        if "youtube.com" not in current_url:
            logger.info(f"Navigating to YouTube from {current_url}")
            try:
                self.driver.get("https://www.youtube.com")
                time.sleep(2)  # Wait for page to load
            except Exception as e:
                logger.error(f"Error navigating to YouTube: {e}")
                self.speak("I couldn't open YouTube.")
                return False
        
        try:
            # Look for the search box
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "search_query"))
            )
            
            # Clear and enter search query
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)
            
            # Wait for search results to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "contents"))
            )
            
            self.speak(f"Searching YouTube for {query}")
            logger.info(f"Searched YouTube for: {query}")
            
            # Wait a moment for results to fully load
            time.sleep(2)
            
            # Parse the search results
            self._parse_search_results()
            
            # Announce how many videos were found
            if self.current_videos:
                self.speak(f"I found {len(self.current_videos)} videos. You can say 'Tell me about video number X' or 'Play video number X'.")
                return True
            else:
                self.speak("I couldn't find any videos for your search.")
                return False
                
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            self.speak("I had trouble searching YouTube.")
            return False
    
    def _parse_search_results(self):
        """
        Parse the YouTube search results page and extract video information
        """
        # Clear previous results
        self.current_videos = []
        
        try:
            # Get page content
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find video elements - YouTube structure can change, so try different selectors
            video_elements = soup.select("ytd-video-renderer") or soup.select("#contents ytd-item-section-renderer ytd-video-renderer")
            
            for i, video in enumerate(video_elements[:10]):  # Limit to first 10 videos
                try:
                    # Extract video information
                    video_info = {
                        "position": i + 1,
                        "title": self._extract_text(video.select_one("#video-title, .title-and-badge a")),
                        "channel": self._extract_text(video.select_one("#channel-name, .ytd-channel-name")),
                        "views": self._extract_text(video.select_one(".metadata-stats .style-scope, .ytd-video-meta-block .ytd-video-meta-block")),
                        "time": self._extract_text(video.select_one(".ytd-thumbnail-overlay-time-status-renderer, span.ytd-thumbnail-overlay-time-status-renderer")),
                        "description": self._extract_text(video.select_one("#description-text, .description-text")),
                        "url": video.select_one("#video-title, .title-and-badge a")["href"] if video.select_one("#video-title, .title-and-badge a") else None
                    }
                    
                    # Clean up the URL to be absolute
                    if video_info["url"] and video_info["url"].startswith("/watch"):
                        video_info["url"] = f"https://www.youtube.com{video_info['url']}"
                        
                    self.current_videos.append(video_info)
                    
                except Exception as e:
                    logger.error(f"Error parsing video {i+1}: {e}")
                    continue
                    
            logger.info(f"Parsed {len(self.current_videos)} videos from YouTube search results")
            
        except Exception as e:
            logger.error(f"Error parsing YouTube search results: {e}")
            self.speak("I had trouble reading the search results.")
    
    def _extract_text(self, element):
        """Safely extract text from an element that might be None"""
        if element:
            return element.get_text(strip=True)
        return None
    
    def describe_video(self, position):
        """
        Describe the video at the specified position
        
        Args:
            position: The position (1-based) of the video in the search results
            
        Returns:
            True if description was successful, False otherwise
        """
        if not self.current_videos:
            self.speak("I don't have any videos to describe. Try searching first.")
            return False
            
        # Validate position
        if position < 1 or position > len(self.current_videos):
            self.speak(f"Please specify a video between 1 and {len(self.current_videos)}.")
            return False
            
        try:
            # Get the specified video
            video = self.current_videos[position - 1]
            
            # Build description
            description = f"Video {position}: {video['title']}"
            
            if video['channel']:
                description += f", by {video['channel']}"
                
            if video['time']:
                description += f", {video['time']} long"
                
            if video['views']:
                description += f", {video['views']}"
                
            if video['description']:
                description += f". Description: {video['description']}"
                
            logger.info(f"Describing video {position}: {video['title']}")
            self.speak(description)
            
            # Ask if user wants to play
            self.speak("Would you like to play this video?")
            return True
            
        except Exception as e:
            logger.error(f"Error describing video {position}: {e}")
            self.speak(f"I had trouble describing video {position}.")
            return False
    
    def play_video(self, position):
        """
        Play the video at the specified position
        
        Args:
            position: The position (1-based) of the video in the search results
            
        Returns:
            True if playback was successful, False otherwise
        """
        if not self.current_videos:
            self.speak("I don't have any videos to play. Try searching first.")
            return False
            
        # Validate position
        if position < 1 or position > len(self.current_videos):
            self.speak(f"Please specify a video between 1 and {len(self.current_videos)}.")
            return False
            
        try:
            # Get the specified video
            video = self.current_videos[position - 1]
            
            # Navigate to the video URL
            if video["url"]:
                self.driver.get(video["url"])
                self.speak(f"Playing video: {video['title']}")
                logger.info(f"Playing video {position}: {video['title']}")
                return True
            else:
                # Fallback: try to click on the video title
                video_elements = self.driver.find_elements(By.ID, "video-title")
                if len(video_elements) >= position:
                    video_elements[position - 1].click()
                    self.speak(f"Playing video: {video['title']}")
                    logger.info(f"Playing video {position} by clicking: {video['title']}")
                    return True
                else:
                    self.speak("I couldn't find a way to play this video.")
                    return False
                
        except Exception as e:
            logger.error(f"Error playing video {position}: {e}")
            self.speak(f"I had trouble playing video {position}.")
            return False
    
    def summarize_search_results(self):
        """
        Provide a summary of the current search results
        
        Returns:
            True if summary was provided, False otherwise
        """
        if not self.current_videos:
            self.speak("I don't have any videos to summarize. Try searching first.")
            return False
        
        try:
            # Build summary
            summary = f"I found {len(self.current_videos)} videos. "
            
            # Describe the first few videos
            for i, video in enumerate(self.current_videos[:5]):
                summary += f"Video {i+1}: {video['title']}. "
            
            if len(self.current_videos) > 5:
                summary += f"And {len(self.current_videos) - 5} more videos."
                
            self.speak(summary)
            self.speak("You can say 'Tell me about video number X' or 'Play video number X'.")
            return True
            
        except Exception as e:
            logger.error(f"Error summarizing search results: {e}")
            self.speak("I had trouble summarizing the search results.")
            return False 