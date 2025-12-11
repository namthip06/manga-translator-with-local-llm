import undetected_chromedriver as uc
import time
import requests
import os
from selenium.webdriver.common.by import By

class MangaScraper:
    def format_class_names(self, class_string):
        """
        Converts a space-separated string of class names into a joined CSS selector.
        Example: "foo bar" -> ".foo.bar"
        """
        if not class_string:
            return ""
        return "." + ".".join(class_string.strip().split())

    def __init__(self, headless=False):
        """
        Initializes the Selenium WebDriver (undetected_chromedriver).
        """
        options = uc.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        # Initialize the driver
        self.driver = uc.Chrome(options=options)

    def navigate_to_url(self, url):
        """
        Navigates to the specific URL using the driver.
        """
        print(f"Navigating to {url}...")
        self.driver.get(url)

    def scroll_to_bottom(self, scroll_pause_time=2):
        """
        Repeatedly scrolls down the page until no new content is loaded.
        """
        print("Starting to scroll...")
        # Get scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load page
            time.sleep(scroll_pause_time)

            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Reached bottom of the page.")
                break
            last_height = new_height

    def get_image_urls(self, css_selector="img"):
        """
        Extracts image URLs from the page based on the given CSS selector.
        Handles lazy loading by checking 'src' and 'data-src'.
        """
        print(f"Extracting image URLs using selector: {css_selector}")
        image_urls = []
        try:
            images = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
            for img in images:
                # Try to get the source from various common attributes
                src = img.get_attribute('src')
                if not src:
                    src = img.get_attribute('data-src')
                if not src:
                    src = img.get_attribute('data-original')
                
                if src and src.strip():
                    if src not in image_urls: # unique
                        image_urls.append(src)
        except Exception as e:
            print(f"Error extracting image URLs: {e}")
            
        print(f"Found {len(image_urls)} unique images.")
        return image_urls

    def click_button(self, selector_type, selector_value):
        """
        Clicks a button based on the provided selector type and value.
        selector_type: e.g., By.CSS_SELECTOR, By.XPATH
        selector_value: The string value for the selector.
        """
        print(f"Attempting to click button: {selector_type} = {selector_value}")
        try:
            button = self.driver.find_element(selector_type, selector_value)
            button.click()
            print("Button clicked successfully.")
            return True
        except Exception as e:
            print(f"Failed to click button: {e}")
            return False

    def download_images(self, image_urls, destination_folder):
        """
        Downloads images from the list of URLs to the specified destination folder.
        """
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
            print(f"Created directory: {destination_folder}")
            
        print(f"Downloading {len(image_urls)} images to {destination_folder}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for i, url in enumerate(image_urls):
            try:
                response = requests.get(url, headers=headers, stream=True)
                if response.status_code == 200:
                    # Basic extension guessing
                    ext = 'jpg'
                    if 'png' in url.lower(): ext = 'png'
                    elif 'jpeg' in url.lower(): ext = 'jpeg'
                    elif 'webp' in url.lower(): ext = 'webp'
                    
                    filename = f"image_{i+1:03d}.{ext}"
                    filepath = os.path.join(destination_folder, filename)
                    
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                else:
                    print(f"Failed to download {url}: Status code {response.status_code}")
            except Exception as e:
                print(f"Error downloading {url}: {e}")
        print("Download complete.")

    def close_driver(self):
        """
        Closes the WebDriver.
        """
        if self.driver:
            self.driver.quit()

# Example usage (commented out or active):
if __name__ == "__main__":
    # Create an instance of MangaScraper
    scraper = MangaScraper()
    
    try:
        # Navigate to a URL
        scraper.navigate_to_url("https://battwo.com/chapter/3988665") # Replace with a manga URL
        
        # Scroll to load all images
        scraper.scroll_to_bottom()
        
        # Extract image URLs
        # Use helper to format the complex class string
        # class_names = "md--page ls limit-width limit-height mx-auto"
        # selector = scraper.format_class_names(class_names) + " > img"
        # image_urls = scraper.get_image_urls(css_selector=selector)
        image_urls = scraper.get_image_urls(css_selector='img') 
        
        # Download images (only if we found any)
        if image_urls:
            page_title = scraper.driver.title
            scraper.download_images(image_urls, f"downloaded : {page_title}")

        # Keep the browser open for a bit to see the result
        time.sleep(5)
        
    finally:
        # Close the driver
        scraper.close_driver()