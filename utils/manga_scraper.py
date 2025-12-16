import undetected_chromedriver as uc
import time
import requests
import os
import re
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class MangaScraper:
    def format_class_names(self, class_string):
        """
        Converts a space-separated string of class names into a joined CSS selector.
        Example: "foo bar" -> ".foo.bar"
        """
        if not class_string:
            return ""
        return "." + ".".join(class_string.strip().split())

    def __init__(self, headless=False, driver_type="chrome_driver_manager", log_callback=None):
        """
        Initializes the Selenium WebDriver.
        driver_type: "chrome_driver_manager" (default) or "undetected_chromedriver"
        log_callback: Optional callable for logging (e.g., st.write). default is print.
        """
        self.log_callback = log_callback if log_callback else print

        if driver_type == "undetected_chromedriver":
            options = uc.ChromeOptions()
            if headless:
                options.add_argument('--headless')
            self.driver = uc.Chrome(options=options)
        else:
            self.driver = self._setup_chrome_driver_manager(headless)

    def log(self, message):
        """Logs message using the registered callback."""
        if self.log_callback:
            self.log_callback(message)

    def _setup_chrome_driver_manager(self, headless):
        """Sets up the driver with ChromeDriverManager and prevents pop-ups."""
        options = Options()
        
        # --- 1. Prevent pop-ups and notifications ---
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        
        # Advanced preferences
        prefs = {
            "profile.default_content_setting_values.notifications": 2, # Block notifications
            "profile.managed_default_content_settings.popups": 2,      # Block popups
            "profile.default_content_setting_values.automatic_downloads": 1 
        }
        options.add_experimental_option("prefs", prefs)

        if headless:
            options.add_argument("--headless")

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def navigate_to_url(self, url):
        """
        Navigates to the specific URL using the driver.
        """
        self.log(f"Navigating to {url}...")
        self.driver.get(url)

    def scroll_to_bottom(self, scroll_pause_time=5, before_scroll_wait_time=5, scroll_step=10000):
        """
        Repeatedly scrolls down the page until no new content is loaded.
        before_scroll_wait_time: Time to wait before starting to scroll (seconds).
        scroll_step: Amount of pixels to scroll in each step (default 500).
        """
        if before_scroll_wait_time > 0:
            self.log(f"Waiting {before_scroll_wait_time} seconds before scrolling...")
            time.sleep(before_scroll_wait_time)
            
        self.log("Starting to scroll...")
        # Get scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        self.log(f"Initial scroll height: {last_height}")

        while True:
            # Scroll down by step
            self.driver.execute_script(f"window.scrollBy(0, {scroll_step});")

            # Wait to load page
            time.sleep(scroll_pause_time)

            # Calculate new scroll height and check position
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            current_scroll_y = self.driver.execute_script("return window.scrollY")
            inner_height = self.driver.execute_script("return window.innerHeight")
            
            # Check if we have reached the bottom of the page
            # (current_scroll_y + inner_height) >= new_height (with small buffer)
            if (current_scroll_y + inner_height) >= (new_height - 10):
                if new_height == last_height:
                    self.log("Reached bottom of the page.")
                    break
                self.log(f"Page expanded. New scroll height: {new_height}")
                last_height = new_height
            else:
                # Still scrolling down, height might have changed or not, 
                # but we haven't hit the bottom bound yet.
                # Update last_height in case it changed while we were scrolling
                last_height = new_height

    def get_image_urls(self, css_selector="img"):
        """
        Extracts image URLs from the page based on the given CSS selector.
        Handles lazy loading by checking 'src' and 'data-src'.
        """
        self.log(f"Extracting image URLs using selector: {css_selector}")
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
            self.log(f"Error extracting image URLs: {e}")
            
        self.log(f"Found {len(image_urls)} unique images.")
        return image_urls

    def click_button(self, selector_type, selector_value):
        """
        Clicks a button based on the provided selector type and value.
        selector_type: e.g., By.CSS_SELECTOR, By.XPATH
        selector_value: The string value for the selector.
        """
        self.log(f"Attempting to click button: {selector_type} = {selector_value}")
        try:
            button = self.driver.find_element(selector_type, selector_value)
            button.click()
            self.log("Button clicked successfully.")
            return True
        except Exception as e:
            self.log(f"Failed to click button: {e}")
            return False

    def download_images(self, image_urls):
        """
        Downloads images from the list of URLs to output_scraper/{driver.title}.
        Handles retry logic for specific error codes:
        - 521: Retry 2-3 times, wait 30s.
        - 522/503: Exponential backoff (5s, 10s, 20s).
        """
        # Base folder
        base_folder = "output_scraper"
        
        # Get and sanitize title
        title = self.driver.title
        # Remove invalid characters for Windows filenames: < > : " / \ | ? *
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title).strip()
        
        # Construct full path
        destination_folder = os.path.join(base_folder, safe_title)

        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
            self.log(f"Created directory: {destination_folder}")
            
        self.log(f"Downloading {len(image_urls)} images to {destination_folder}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for i, url in enumerate(image_urls):
            # Basic extension guessing
            ext = 'jpg'
            if 'png' in url.lower(): ext = 'png'
            elif 'jpeg' in url.lower(): ext = 'jpeg'
            elif 'webp' in url.lower(): ext = 'webp'
            
            filename = f"image_{i+1:03d}.{ext}"
            filepath = os.path.join(destination_folder, filename)
            
            # Retry counters
            retries_521 = 0
            max_retries_521 = 3
            
            retries_backoff = 0
            max_retries_backoff = 3
            
            success = False
            
            while not success:
                try:
                    response = requests.get(url, headers=headers, stream=True)
                    
                    if response.status_code == 200:
                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        success = True
                        
                    elif response.status_code == 521:
                        if retries_521 < max_retries_521:
                            retries_521 += 1
                            self.log(f"Status 521 (Web Server Down) for {url}. Retrying in 10 seconds... ({retries_521}/{max_retries_521})")
                            time.sleep(10)
                        else:
                            self.log(f"Failed to download {url}: Status 521 after {max_retries_521} attempts.")
                            break
                            
                    elif response.status_code in [522, 503]:
                        if retries_backoff < max_retries_backoff:
                            wait_time = 5 * (2 ** retries_backoff) # 5, 10, 20
                            retries_backoff += 1
                            self.log(f"Status {response.status_code} for {url}. Retrying in {wait_time} seconds... ({retries_backoff}/{max_retries_backoff})")
                            time.sleep(wait_time)
                        else:
                            self.log(f"Failed to download {url}: Status {response.status_code} after {max_retries_backoff} attempts.")
                            break
                    else:
                        self.log(f"Failed to download {url}: Status code {response.status_code}")
                        break
                        
                except Exception as e:
                    self.log(f"Error downloading {url}: {e}")
                    break
                    
        self.log("Download complete.")
        return destination_folder
        
    def close_driver(self):
        """
        Closes the WebDriver.
        """
        if self.driver:
            self.driver.quit()