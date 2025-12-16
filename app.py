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
from utils.api_translator import APITranslator
from utils.text_remover import TextRemover
from utils.typesetter import Typesetter
import cv2
import logging

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

st.title("Manga Translator with Local LLM")
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
        col_ocr_1, col_ocr_2, col_ocr_3 = st.columns(3)
        with col_ocr_1:
            ocr_lang = st.text_input("Language", value="en", help="Language code for OCR.")
        with col_ocr_2:
            x_threshold = st.number_input("X Threshold", value=20, help="Maximum horizontal gap for text grouping.")
        with col_ocr_3:
            y_threshold = st.number_input("Y Threshold", value=20, help="Maximum vertical gap for text grouping.")
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

def perform_ocr_on_folder(folder_path, lang='en', x_threshold=20, y_threshold=20):
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
            grouped_boxes, grouped_texts = processor.perform_ocr(image_path, x_threshold=x_threshold, y_threshold=y_threshold)
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
                ocr_results = perform_ocr_on_folder(downloaded_folder, lang=ocr_lang, x_threshold=x_threshold, y_threshold=y_threshold)
                st.session_state.ocr_results = ocr_results
                st.session_state.current_image_folder = downloaded_folder
                status_container.success("All processes finished. Proceeding to Translation Setup...")

    # ------------------ MANUAL OCR LOGIC ------------------
    elif mode == "Manual OCR Input":
        if not ocr_folder_path:
            st.error("Please enter a valid folder path.")
        else:
            status_container.info(f"Starting Manual OCR on {ocr_folder_path}...")
            ocr_results = perform_ocr_on_folder(ocr_folder_path, lang=ocr_lang, x_threshold=x_threshold, y_threshold=y_threshold)
            st.session_state.ocr_results = ocr_results
            st.session_state.current_image_folder = ocr_folder_path
            status_container.success("Manual OCR Completed. Proceeding to Translation Setup...")

# ------------------ LLM TRANSLATION LOGIC ------------------
# Triggered if ocr_results exist
if 'ocr_results' in st.session_state and st.session_state.ocr_results:
    with col1:
        st.markdown("---")
        st.header("LLM Translation")
        
        # Provider Selection
        provider_option = st.radio("LLM Provider", ["Local LLM (Ollama)", "API (OpenAI/Gemini/Groq)"], horizontal=True)

        selected_model = None
        api_key_input = None
        current_translator = None

        # --- Configuration Phase (Specific to Provider) ---
        if provider_option == "Local LLM (Ollama)":
            current_translator = translator # Use the pre-initialized Ollama translator
            
            # Check Connection Status
            if not st.session_state.get('ollama_connected'):
                 st.warning("Ollama not connected. Trying to connect...")
                 if st.button("Retry Connection"):
                     if translator and translator.connect():
                         st.session_state.ollama_connected = True
                         st.session_state.ollama_models = translator.list_models()
                         st.rerun()
            
            if st.session_state.get('ollama_connected'):
                col_model, col_prompt_layout = st.columns([1, 2])
                with col_model:
                    models = st.session_state.get('ollama_models', [])
                    if models:
                        selected_model = st.selectbox("Select Model", models)
                    else:
                        st.warning("No models found.")
        
        else: # API Mode
            # Initialize API Translator if needed
            if 'api_translator' not in st.session_state:
                st.session_state.api_translator = APITranslator(log_callback=log_callback)
            
            current_translator = st.session_state.api_translator
            
            col_model, col_prompt_layout = st.columns([1, 2])
            with col_model:
                # Get supported models
                api_models = current_translator.get_supported_models()
                selected_model = st.selectbox("Select Model", api_models)
                
                # Configure when model changes
                if selected_model:
                    current_translator.configure_for_model(selected_model)
                
                # API Key Input
                api_key_input = st.text_input("API Key", type="password", help="Leave empty if set in Environment Variables")

        # --- Shared Logic Phase (Prompt, Payload, Execution) ---
        if current_translator and selected_model:
            # Note: col_prompt_layout is defined in both branches above to keep layout consistent
            
            # Translation Options
            st.subheader("Translation Options")
            translation_mode = st.radio("Output Format", ["JSON", "Text (Line-by-Line)"], horizontal=True)
            
            # Prompt Editing
            # We use the second column from the layout defined above for the prompt to save space? 
            # Or distinct row? The previous design had models and prompt side-by-side.
            # Let's keep the side-by-side layout using the col_prompt_layout object.
            
            with col_prompt_layout:
                 if translation_mode == "JSON":
                     default_prompt = (
                        "You are a professional manga translator. Translate the following English text to Thai. "
                        "Return the result strictly as a valid JSON object where the keys are the original text "
                        "and the values are the translated Thai text."
                    )
                 else:
                     default_prompt = (
                        "You are a professional manga translator. Translate the following English text to Thai. "
                        "Return only the translated lines, one per line, corresponding to the input. "
                        "Do not include any other text or explanations."
                     )
                 
                 user_prompt = st.text_area("Prompt Template", value=default_prompt, height=200)
            
            # Prepare Payload Preview
            all_sentences = []
            for res in st.session_state.ocr_results:
                if 'grouped_texts' in res:
                    for group in res['grouped_texts']:
                        if isinstance(group, list):
                            # Logic to handle hyphenated words across lines
                            processed_words = []
                            i = 0
                            while i < len(group):
                                word = group[i]
                                # Check if current word ends with hyphen and there is a next word
                                if word.endswith("-") and i < len(group) - 1:
                                    # Remove hyphen and join with next word without space
                                    next_word = group[i+1]
                                    combined = word[:-1] + next_word
                                    processed_words.append(combined)
                                    i += 2 # Skip next word as it is merged
                                    continue
                                
                                processed_words.append(word)
                                i += 1
                                
                            # Join with space and convert to sentence case
                            sentence = " ".join(processed_words).capitalize()
                        else:
                            sentence = str(group).capitalize()
                        all_sentences.append(sentence)
            
            if translation_mode == "JSON":
                 # Use JSON format
                 text_payload = json.dumps(all_sentences, ensure_ascii=False, indent=2)
            else:
                 # Use Line-by-Line format
                 text_payload = "\n".join(all_sentences)
            
            st.text_area("Content to be sent to LLM", value=text_payload, height=300)
            st.text(f"Total Sentences: {len(all_sentences)}")

            # Translate Button
            if st.button("Start Translation", type="primary"):
                with col2:
                    st.info(f"Translating with {selected_model}...")
                
                # Prepare arguments dynamically
                translate_kwargs = {
                    "text": text_payload,
                    "model": selected_model,
                    "prompt": user_prompt,
                    "json_format": (translation_mode == "JSON")
                }
                
                # Add API key if in API mode
                if provider_option == "API (OpenAI/Gemini/Groq)":
                    translate_kwargs["api_key"] = api_key_input

                # Call Translate
                translation_result = current_translator.translate_text(**translate_kwargs)
                
                if translation_result:
                    with col2:
                        st.success("Translation Completed!")
                    
                    st.subheader("Translation Result")
                    
                    translated_lines = []
                    
                    try:
                        if translation_mode == "JSON":
                            # Parse JSON if it's a string
                            data = translation_result
                            if isinstance(data, str):
                                # Clean potential markdown code blocks if present
                                clean_data = data.replace("```json", "").replace("```", "").strip()
                                data = json.loads(clean_data)
                                
                            if isinstance(data, dict):
                                # Map back to original sentences using keys
                                for sent in all_sentences:
                                    translated_lines.append(data.get(sent, sent)) 
                            elif isinstance(data, list):
                                # Assume it's a direct list of translations
                                translated_lines = data
                            else:
                                st.error("Unexpected JSON structure. Expected Dict or List.")
                                
                        else:
                            # Text Mode: Split by lines
                            if isinstance(translation_result, str):
                                translated_lines = [line.strip() for line in translation_result.strip().split('\n') if line.strip()]
                            else:
                                st.error("Expected string output for Text mode.")
                        
                        st.write("Translation Result:", translated_lines)

                        if len(translated_lines) != len(all_sentences):
                            st.warning(f"⚠️ Mismatch detected! Input: {len(all_sentences)} vs Output: {len(translated_lines)}")
                        else:
                            st.success("✅ Count Matches.")
                            
                        # Save to session state for next step
                        st.session_state.translated_lines = translated_lines
                        
                    except Exception as e:
                        st.error(f"Error processing translation result: {e}")
                        st.text(translation_result)
                    
                else:
                    st.error("Translation returned empty or failed.")

# ------------------ TYPESETTING & RENDERING LOGIC ------------------
if 'translated_lines' in st.session_state and st.session_state.translated_lines:
    st.markdown("---")
    st.header("Typesetting & Rendering")
    st.info("Translation confirmed. You can now generate the final images.")
    
    # Initialize Typesetter for UI options
    if 'typesetter' not in st.session_state:
        st.session_state.typesetter = Typesetter()
    
    typesetter = st.session_state.typesetter
    available_fonts = typesetter.get_available_fonts()
    
    col_settings_1, col_settings_2, col_settings_3 = st.columns(3)
    
    with col_settings_1:
        selected_font = st.selectbox("Select Font", available_fonts if available_fonts else ["Default"])
    
    with col_settings_2:
        font_size = st.number_input("Font Size", min_value=10, max_value=200, value=30)
    
    with col_settings_3:
        text_padding = st.number_input("Text Padding (px)", min_value=0, max_value=50, value=0)
    
    if st.button("Confirm & Render Images", type="primary"):
        if 'current_image_folder' not in st.session_state:
            st.error("Image folder path is missing. Please restart the process.")
        else:
            image_folder = st.session_state.current_image_folder
            translated_lines = st.session_state.translated_lines
            ocr_results = st.session_state.ocr_results
            
            # Setup Output
            output_folder = os.path.join(image_folder, "translated")
            os.makedirs(output_folder, exist_ok=True)
            
            # Initialize Tools
            try:
                remover = TextRemover(log_level=logging.ERROR)
                # typesetter is already initialized
                
                status_bar = st.progress(0)
                status_text = st.empty()
                
                curr_translation_idx = 0
                total_images = len(ocr_results)
                
                for i, res in enumerate(ocr_results):
                    filename = res['filename']
                    original_path = os.path.join(image_folder, filename)
                    
                    status_text.text(f"Processing {filename} ({i+1}/{total_images})...")
                    
                    # Get corresponding translations for this image
                    # We assume 1-to-1 mapping logic used in payload generation holds true
                    if 'grouped_texts' in res:
                        num_lines = len(res['grouped_texts'])
                        
                        # Extract subset of translations
                        img_translations = translated_lines[curr_translation_idx : curr_translation_idx + num_lines]
                        curr_translation_idx += num_lines
                        
                        # 1. Remove Text
                        # Note: remover.remove_text returns a cv2 image (numpy array)
                        cleaned_image_cv = remover.remove_text(original_path, res['grouped_boxes'])
                        
                        if cleaned_image_cv is not None:
                            # Save cleaned image temporarily (Typesetter currently expects a path)
                            # We can stick to saving it in output folder
                            cleaned_path = os.path.join(output_folder, f"cleaned_{filename}")
                            cv2.imwrite(cleaned_path, cleaned_image_cv)
                            
                            # 2. Overlay Text
                            final_path = os.path.join(output_folder, f"final_{filename}")
                            
                            typesetter.overlay_text(
                                image_path=cleaned_path,
                                grouped_boxes=res['grouped_boxes'], 
                                grouped_texts=img_translations,
                                output_path=final_path,
                                font_name=selected_font if selected_font != "Default" else None,
                                font_size=font_size,
                                padding=text_padding
                            )
                            
                            # Display result
                            with st.expander(f"Result: {filename}", expanded=True):
                                col_orig, col_final = st.columns(2)
                                col_orig.image(original_path, caption="Original")
                                col_final.image(final_path, caption="Translated")
                        else:
                            st.error(f"Failed to remove text from {filename}")
                    
                    # Update Progress
                    status_bar.progress((i + 1) / total_images)
                
                status_text.text("Processing Complete!")
                st.success(f"All images saved to: {output_folder}")
                st.balloons()
                
            except Exception as e:
                st.error(f"An error occurred during rendering: {e}")
                st.exception(e)
