import streamlit as st
import time
import os
import sys

# Ensure the root directory is in the path to import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.ocr_processor import OCRProcessor

# Page Layout
st.set_page_config(page_title="Manga Scraper & OCR", page_icon="📚", layout="wide")

# Custom Styles
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #ff4b4b;
        color: white;
    }
    .status-box {
        padding: 10px
        border-radius: 5px;
        background-color: #f0f2f6;
        border: 1px solid #d6d6d6;
    }
</style>
""", unsafe_allow_html=True)

st.title("Manga Scraper & OCR tool")
st.markdown("Use this tool to scrape manga chapters and perform OCR.")

# Split layout: Inputs (Left) & Logs (Right)
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Settings")
    
    # Operation Mode
    mode = st.radio("Operation Mode", ["Scrape Only", "Scrape & OCR", "Manual OCR Input"], horizontal=True)
    
    # Scraper Settings
    if mode in ["Scrape Only", "Scrape & OCR"]:
        st.subheader("Scraper Settings")
        url = st.text_input("Target URL", placeholder="https://example.com/manga-chapter-1")
        
        with st.expander("Advanced Scraper Options", expanded=False):
            headless = st.checkbox("Headless Mode (Hide Browser)", value=False)
            scroll_pause = st.number_input("Scroll Pause Time (s)", min_value=1, value=5)
            before_scroll_wait = st.number_input("Wait Before Scroll (s)", min_value=0, value=5)
            scroll_step = st.number_input("Scroll Step (px)", min_value=100, value=5000, step=100)
            css_selector = st.text_input("CSS Selector", value=".space-y-2 img")

    # OCR Settings
    ocr_folder_path = None
    if mode == "Manual OCR Input":
        st.subheader("Manual OCR Settings")
        ocr_folder_path = st.text_input("Folder Path (containing images)", placeholder="path/to/downloaded/images")

    if mode in ["Scrape & OCR", "Manual OCR Input"]:
        st.subheader("OCR Configuration")
        ocr_lang = st.text_input("Language", value="en", help="Language code for OCR.")
        # use_angle_cls = st.checkbox("Use Angle Classification", value=True, help="Detect text orientation.") # User said "only necessary"

    start_btn = st.button("Start Process", type="primary")

with col2:
    st.header("Status Log")
    status_container = st.empty()
    log_area = st.empty()

    if "logs" not in st.session_state:
        st.session_state.logs = []

    def log_callback(message):
        """Append message to session state logs and update UI."""
        st.session_state.logs.append(message)
        # Update the log area immediately to show only the latest message
        log_area.info(message) 

def perform_ocr_on_folder(folder_path, lang='en'):
    """Helper to run OCR on all images in a folder."""
    if not os.path.exists(folder_path):
        log_callback(f"Folder not found: {folder_path}")
        return

    log_callback(f"Initializing OCR Processor (Lang: {lang})...")
    # Initialize OCR
    try:
        processor = OCRProcessor(lang=lang, use_angle_cls=True)
    except Exception as e:
        log_callback(f"Failed to initialize OCR: {e}")
        return

    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
    
    if not files:
        log_callback("No valid images found in folder.")
        return

    log_callback(f"Found {len(files)} images. Starting OCR...")
    
    for filename in sorted(files):
        image_path = os.path.join(folder_path, filename)
        log_callback(f"Processing: {filename}")
        try:
            grouped_boxes, grouped_texts = processor.perform_ocr(image_path)
            # Just logging success for now, or could save to a file
            # log_callback(f"OCR finished for {filename}. Found {len(grouped_texts)} text blocks.")
        except Exception as e:
            log_callback(f"Error processing {filename}: {e}")
    
    log_callback("OCR Process Completed.")

if start_btn:
    st.session_state.logs = [] # Clear previous logs
    
    # ------------------ SCRAPER LOGIC ------------------
    if mode in ["Scrape Only", "Scrape & OCR"]:
        if not url:
            st.error("Please enter a valid URL.")
        else:
            status_container.info("Initializing Scraper...")
            downloaded_folder = None
            
            try:
                scraper = MangaScraper(headless=headless, log_callback=log_callback)
                log_callback(f"Navigating to {url}...")
                scraper.navigate_to_url(url)
                
                log_callback("Scrolling page...")
                scraper.scroll_to_bottom(
                    scroll_pause_time=scroll_pause, 
                    before_scroll_wait_time=before_scroll_wait, 
                    scroll_step=scroll_step
                )
                
                log_callback("Extracting image URLs...")
                image_urls = scraper.get_image_urls(css_selector=css_selector)
                
                if image_urls:
                    log_callback(f"Downloading {len(image_urls)} images...")
                    downloaded_folder = scraper.download_images(image_urls)
                    status_container.success("Scraping Completed Successfully!")
                else:
                    status_container.warning("No images found using the provided selector.")
                
            except Exception as e:
                status_container.error(f"An error occurred during scraping: {e}")
                st.exception(e)
                
            finally:
                if 'scraper' in locals():
                    scraper.close_driver()
                    log_callback("Driver closed.")
            
            # ------------------ AUTO OCR LOGIC ------------------
            if mode == "Scrape & OCR" and downloaded_folder:
                status_container.info("Starting OCR on downloaded images...")
                perform_ocr_on_folder(downloaded_folder, lang=ocr_lang)
                status_container.success("All processes finished.")

    # ------------------ MANUAL OCR LOGIC ------------------
    elif mode == "Manual OCR Input":
        if not ocr_folder_path:
            st.error("Please enter a valid folder path.")
        else:
            status_container.info(f"Starting Manual OCR on {ocr_folder_path}...")
            perform_ocr_on_folder(ocr_folder_path, lang=ocr_lang)
            status_container.success("Manual OCR Completed.")
