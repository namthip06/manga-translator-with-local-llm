import streamlit as st
import time
import os
import sys
import json

# Ensure the root directory is in the path to import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.manga_scraper import MangaScraper
from utils.ocr_processor import OCRProcessor
from utils.ollama_translator import OllamaTranslator

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
            scroll_step = st.number_input("Scroll Step (px)", min_value=1000, value=5000, step=1000)
            css_selector = st.text_input("CSS Selector", value="img")

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
        # Update the log area to show the latest message
        log_area.info(message) 

    # ------------------ INITIALIZATION ------------------
    if 'processor' not in st.session_state:
        log_callback("First-time Initialization...")
        
        # Initialize OCR
        try:
            log_callback("Initializing OCR Processor...")
            st.session_state.processor = OCRProcessor(lang='en', use_angle_cls=True)
            log_callback("OCR Processor Ready.")
        except Exception as e:
            log_callback(f"Failed to initialize OCR: {e}")

        # Initialize Translator
        try:
            log_callback("Initializing Ollama Translator...")
            st.session_state.translator = OllamaTranslator(log_callback=log_callback)
            log_callback("Ollama Translator Ready.")
            
            # Auto-Connect during Initialization
            log_callback("Connecting to Ollama...")
            if st.session_state.translator.connect():
                st.session_state.ollama_connected = True
                log_callback("Connected to Ollama.")
                st.session_state.ollama_models = st.session_state.translator.list_models()
            else:
                st.session_state.ollama_connected = False
                log_callback("Failed to connect to Ollama.")
                
        except Exception as e:
            log_callback(f"Failed to initialize Translator: {e}")
            st.session_state.ollama_connected = False
            
    # Retrieve objects from session state
    processor = st.session_state.get('processor')
    translator = st.session_state.get('translator')

def perform_ocr_on_folder(folder_path, lang='en'):
    """Helper to run OCR on all images in a folder."""
    if not os.path.exists(folder_path):
        log_callback(f"Folder not found: {folder_path}")
        return []

    if not processor:
        log_callback("OCR Processor not initialized.")
        return []

    # Re-configure language if needed (optional, assuming English for now or reusing instance)
    # processor.ocr.lang = lang # PaddleOCR lang switch is complex, usually requires reload. 
    # For now, we use the initialized one.

    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
    
    if not files:
        log_callback("No valid images found in folder.")
        return []

    log_callback(f"Found {len(files)} images. Starting OCR...")
    
    ocr_results = []
    total_files = len(files)
    
    for i, filename in enumerate(sorted(files)):
        image_path = os.path.join(folder_path, filename)
        remaining = total_files - (i + 1)
        log_callback(f"Processing: {filename} (Remaining: {remaining})")
        try:
            grouped_boxes, grouped_texts = processor.perform_ocr(image_path)
            ocr_results.append({
                "filename": filename,
                "grouped_boxes": grouped_boxes,
                "grouped_texts": grouped_texts
            })
        except Exception as e:
            log_callback(f"Error processing {filename}: {e}")
            ocr_results.append({
                "filename": filename,
                "error": str(e)
            })
    
    log_callback("OCR Process Completed.")
    return ocr_results

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
                st.session_state.ocr_results = ocr_results
                st.write("Debug Result:", ocr_results)
                status_container.success("All processes finished. Proceeding to Translation Setup...")

    # ------------------ MANUAL OCR LOGIC ------------------
    elif mode == "Manual OCR Input":
        if not ocr_folder_path:
            st.error("Please enter a valid folder path.")
        else:
            status_container.info(f"Starting Manual OCR on {ocr_folder_path}...")
            ocr_results = perform_ocr_on_folder(ocr_folder_path, lang=ocr_lang)
            st.session_state.ocr_results = ocr_results
            st.write("Debug Result:", ocr_results)
            status_container.success("Manual OCR Completed. Proceeding to Translation Setup...")


# ------------------ LLM TRANSLATION LOGIC ------------------

# ------------------ LLM TRANSLATION LOGIC ------------------
# Triggered if ocr_results exist
if 'ocr_results' in st.session_state and st.session_state.ocr_results:
    with col1:
        st.markdown("---")
        st.header("LLM Translation (Ollama)")
        
        # Check Connection Status
        if not st.session_state.get('ollama_connected'):
             st.warning("Ollama not connected. Trying to connect...")
             if st.button("Retry Connection"):
                 if translator and translator.connect():
                     st.session_state.ollama_connected = True
                     st.session_state.ollama_models = translator.list_models()
                     st.experimental_rerun()
        
        if st.session_state.get('ollama_connected'):
            col_model, col_prompt = st.columns([1, 2])
            
            # Model Selection
            with col_model:
                models = st.session_state.get('ollama_models', [])
                if models:
                    selected_model = st.selectbox("Select Model", models)
                else:
                    st.warning("No models found.")
                    selected_model = None
            
            # Prompt Editing
            with col_prompt:
                 default_prompt = (
                    "You are a professional manga translator. Translate the following English text to Thai. "
                    "Return the result strictly as a valid JSON object where the keys are the original text "
                    "and the values are the translated Thai text."
                )
                 user_prompt = st.text_area("Prompt Template", value=default_prompt, height=250)
            
            # Prepare Payload Preview
            all_sentences = []
            for res in st.session_state.ocr_results:
                if 'grouped_texts' in res:
                    for group in res['grouped_texts']:
                        if isinstance(group, list):
                            # Join with space and convert to sentence case (assuming English based on prompt)
                            sentence = " ".join(group).capitalize()
                        else:
                            sentence = str(group).capitalize()
                        all_sentences.append(sentence)
            
            # Use JSON format instead of comma separation
            text_payload = json.dumps(all_sentences, ensure_ascii=False, indent=2)
            
            st.subheader("Translation Preview")
            st.text_area("Content to be sent to LLM", value=text_payload, height=100, disabled=True)
            st.info(f"Total Sentences: {len(all_sentences)}")

            # Translate Button
            if st.button("Start Translation", type="primary"):
                if not selected_model:
                    st.error("Please select a model.")
                else:
                    st.info("Translating...")
                    
                    # Call Translate
                    translation_result = translator.translate_text(
                        text=text_payload, 
                        model=selected_model, 
                        prompt=user_prompt
                    )
                    
                    if translation_result:
                        st.success("Translation Completed!")
                        st.subheader("Translation Result (JSON)")
                        st.json(translation_result)
                        with col2:
                             st.write("Debug Result (Raw):", translation_result)
                    else:
                        st.error("Translation returned empty or failed.")
