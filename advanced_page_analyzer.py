import json
import logging
import groq
from bs4 import BeautifulSoup
import os

# Set up logging
logger = logging.getLogger(__name__)

class AdvancedPageAnalyzer:
    """
    Advanced page analyzer that uses LLM to provide detailed description of web page content.
    Takes parsed HTML elements and extracts structured information about products, videos, etc.
    """
    
    def __init__(self, groq_api_key=None):
        """Initialize the analyzer with the API key for LLM service"""
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if self.groq_api_key:
            self.llm_client = groq.Client(api_key=self.groq_api_key)
            logger.info("Advanced Page Analyzer initialized with Groq API key")
        else:
            self.llm_client = None
            logger.warning("No Groq API key provided. Advanced analysis will be limited.")
    
    def analyze_with_llm(self, page_info):
        """
        Send the parsed page information to the LLM for detailed analysis
        
        Args:
            page_info: Dictionary containing parsed page elements and content
            
        Returns:
            Dictionary with enhanced page analysis
        """
        if not self.llm_client:
            logger.warning("LLM client not available. Using basic analysis only.")
            return self._fallback_analysis(page_info)
        
        try:
            # Create a prompt for the LLM with the page structure information
            system_prompt = """
            You are a specialized web page analyzer that can identify and categorize content on websites.
            Analyze the provided website content and identify the following elements:
            
            1. Products - with details about name, price, seller, ratings
            2. Videos - with details about title, creator, duration
            3. Music/Audio tracks - with details about title, artist, album
            4. Articles/Blog posts - with title, author, date
            5. Images - with description of what they show (from alt text)
            6. Interactive elements - buttons, forms, etc.
            
            For each category, provide structured information in a conversational format that describes what's on the page.
            If you detect a specific type of website (e-commerce, video platform, news site, etc.), mention that.
            
            Return your analysis in a JSON format with a 'description' field containing a conversational summary,
            and a 'structured_data' field containing categorized elements.
            """
            
            # Format the page_info as part of the user prompt
            user_prompt = f"""
            Website: {page_info['url']}
            Title: {page_info['title']}
            
            Here's what I've detected so far:
            
            Products ({len(page_info['products'])}): 
            {json.dumps(page_info['products'][:5], indent=2)}
            
            Videos ({len(page_info['videos'])}): 
            {json.dumps(page_info['videos'][:5], indent=2)}
            
            Articles/Cards ({len(page_info['cards'])}): 
            {json.dumps(page_info['cards'][:5], indent=2)}
            
            Music ({len(page_info['music'])}): 
            {json.dumps(page_info['music'][:5], indent=2)}
            
            Images ({len(page_info['images'])}): 
            {json.dumps(page_info['images'][:5], indent=2)}
            
            Links ({len(page_info['links'])}): 
            {json.dumps(page_info['links'][:5], indent=2)}
            
            Based on this information, provide an enhanced analysis of what's on this page.
            Add any insights about the type of website, what it's selling or offering, and the main content.
            For e-commerce sites, describe the products in more detail.
            For video platforms, identify the main themes of videos.
            For music sites, describe the music collection.
            For news/blog sites, summarize the article topics.
            """
            
            # Send request to LLM
            response = self.llm_client.chat.completions.create(
                model="llama3-70b-8192",  # Fast, economical model with good understanding
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Low temperature for consistent results
                max_tokens=1024,
            )
            
            # Extract the response
            result = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                # First try to extract JSON if it's embedded in text
                json_match = result.strip('`').strip()
                if json_match.startswith('json'):
                    json_match = json_match[4:].strip()
                
                enhanced_analysis = json.loads(json_match)
                return enhanced_analysis
            except json.JSONDecodeError:
                # If not valid JSON, use the text as a description
                logger.warning("LLM response was not valid JSON. Using as plain text.")
                return {
                    "description": result,
                    "structured_data": self._organize_page_info(page_info)
                }
                
        except Exception as e:
            logger.error(f"Error during LLM page analysis: {str(e)}")
            return self._fallback_analysis(page_info)
    
    def _fallback_analysis(self, page_info):
        """Provide basic analysis without LLM"""
        # Determine website type
        website_type = self._determine_website_type(page_info)
        
        # Create a basic description
        description = f"This appears to be a {website_type} website titled '{page_info['title']}'. "
        
        # Add content summary
        content_types = []
        if page_info['products']:
            content_types.append(f"{len(page_info['products'])} products")
        if page_info['videos']:
            content_types.append(f"{len(page_info['videos'])} videos")
        if page_info['cards']:
            content_types.append(f"{len(page_info['cards'])} articles/posts")
        if page_info['music']:
            content_types.append(f"{len(page_info['music'])} music tracks")
        if page_info['images']:
            content_types.append(f"{len(page_info['images'])} images")
            
        if content_types:
            description += f"It contains {', '.join(content_types)}. "
        
        return {
            "description": description,
            "structured_data": self._organize_page_info(page_info)
        }
    
    def _determine_website_type(self, page_info):
        """Determine the type of website based on content"""
        url = page_info['url'].lower()
        title = page_info['title'].lower() if page_info['title'] else ""
        
        # Check URL patterns
        if any(shop in url for shop in ['amazon', 'ebay', 'shop', 'store', 'product']):
            return "e-commerce"
        elif any(video in url for video in ['youtube', 'vimeo', 'netflix', 'video']):
            return "video sharing"
        elif any(music in url for music in ['spotify', 'soundcloud', 'music', 'audio']):
            return "music streaming"
        elif any(news in url for news in ['news', 'blog', 'article']):
            return "news or blog"
        elif any(social in url for social in ['facebook', 'twitter', 'instagram', 'social']):
            return "social media"
        
        # Check content patterns
        if len(page_info['products']) > 0:
            return "e-commerce"
        elif len(page_info['videos']) > 0:
            return "video content"
        elif len(page_info['music']) > 0:
            return "music content"
        elif len(page_info['cards']) > 0:
            return "article or blog"
        
        # Default
        return "general content"
    
    def _organize_page_info(self, page_info):
        """Organize page info into a clean structure for analysis"""
        return {
            "products": [p for p in page_info['products'] if any(p.values())],
            "videos": [v for v in page_info['videos'] if any(v.values())],
            "articles": [c for c in page_info['cards'] if any(c.values())],
            "music": [m for m in page_info['music'] if any(m.values())],
            "images": [i for i in page_info['images'] if i.get('alt')],
        }
    
    def generate_human_friendly_description(self, analysis):
        """Generate a human-friendly description from the analysis results"""
        if 'description' in analysis:
            return analysis['description']
        
        # Fallback to creating a description from structured data
        structured_data = analysis.get('structured_data', {})
        description = f"This page contains: "
        
        content_parts = []
        
        # Add product information
        products = structured_data.get('products', [])
        if products:
            product_part = f"{len(products)} products"
            if len(products) <= 3:
                product_names = [p.get('name', 'Unnamed product') for p in products if p.get('name')]
                if product_names:
                    product_part += f" ({', '.join(product_names)})"
            content_parts.append(product_part)
        
        # Add video information
        videos = structured_data.get('videos', [])
        if videos:
            video_part = f"{len(videos)} videos"
            if len(videos) <= 3:
                video_titles = [v.get('title', 'Untitled video') for v in videos if v.get('title')]
                if video_titles:
                    video_part += f" ({', '.join(video_titles)})"
            content_parts.append(video_part)
        
        # Add article information
        articles = structured_data.get('articles', [])
        if articles:
            article_part = f"{len(articles)} articles"
            if len(articles) <= 3:
                article_titles = [a.get('title', 'Untitled article') for a in articles if a.get('title')]
                if article_titles:
                    article_part += f" ({', '.join(article_titles)})"
            content_parts.append(article_part)
        
        # Add music information
        music = structured_data.get('music', [])
        if music:
            music_part = f"{len(music)} music tracks"
            if len(music) <= 3:
                track_titles = [m.get('title', 'Untitled track') for m in music if m.get('title')]
                if track_titles:
                    music_part += f" ({', '.join(track_titles)})"
            content_parts.append(music_part)
        
        # Add image information
        images = structured_data.get('images', [])
        if images:
            content_parts.append(f"{len(images)} images with descriptions")
        
        if content_parts:
            description += ", ".join(content_parts)
        else:
            description = "I couldn't identify specific content elements on this page."
        
        return description 