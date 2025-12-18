# Manga Translator with Local LLM

This application provides a comprehensive workflow for translating manga chapters. It integrates web scraping, Optical Character Recognition (OCR), machine translation via local Large Language Models (LLMs) or external APIs, and automated typesetting (text removal and replacement). It is designed to run locally, prioritizing user privacy and control over the translation pipeline.

## Technical Details

The project relies on a modular architecture to handle different stages of the translation process:

- **Frontend Interface**: Built with [Streamlit](https://streamlit.io/), providing an interactive web-based UI.
- **Web Scraping**: Utilizes [Selenium](https://www.selenium.dev/) with the Chrome WebDriver to extract images from manga websites.
- **OCR Engine**: Implements an OCR processor (powered by PaddleOCR) to detect and extract text coordinates and content from images.
- **Translation**:
  - **Local**: Integrates with [Ollama](https://ollama.com/) to run open-weights models (like Llama 3, Mistral) locally.
  - **Cloud**: Supports external APIs compatible with OpenAI, Gemini, and Groq.
- **Image Processing**: Uses [OpenCV](https://opencv.org/) for text removal (inpainting) and image manipulation.

## Prerequisites

Before running the application, ensure the following software is installed on your system:

- **Python**: Version 3.10 or higher.
- **Google Chrome**: Required for the scraping module.
- **Ollama**: Required if you intend to use local LLMs for translation.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/namthip06/manga-translator-with-local-llm.git
    cd manga-translator-with-local-llm
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If you encounter encoding errors with requirements.txt, ensure your pip version is up to date.*

## Configuration

### Local LLM (Ollama)
If using the local translation mode:
1.  Install [Ollama](https://ollama.com/download).
2.  Start the Ollama server:
    ```bash
    ollama serve
    ```
3.  Pull the models you wish to use (e.g., Llama 3):
    ```bash
    ollama pull llama3
    ```

### External APIs
If using cloud-based translation (OpenAI, Gemini, Groq):
-   You will need valid API keys for the respective services.
-   These can be entered directly into the application interface during runtime.

## Usage

1.  **Launch the Application**:
    ```bash
    streamlit run app.py
    ```
    The interface will open in your default browser at `http://localhost:8501`.

2.  **Select Operation Mode**:
    -   **Scrape Only**: Downloads images from a target URL.
    -   **Scrape & OCR**: Downloads images and immediately runs OCR on them.
    -   **Manual OCR Input**: Runs OCR on an existing local folder of images.

3.  **Translation**:
    -   After OCR is complete, configure the translation settings.
    -   Choose between **Local LLM (Ollama)** or **API**.
    -   Select your model and customize the system prompt if needed.
    -   Click "Start Translation".

4.  **Typesetting**:
    -   Once translation is confirmed, proceed to the "Typesetting & Rendering" section.
    -   Select a font and adjust the font size.
    -   Click "Confirm & Render Images" to generate the final pages with the original text removed and translated text overlaid.

## Acknowledgements

-   **[Streamlit](https://streamlit.io/)** for the rapid application development framework.
-   **[Selenium](https://www.selenium.dev/)** for robust browser automation.
-   **[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)** for the optical character recognition capabilities.
-   **[Ollama](https://ollama.com/)** for simplifying local LLM inference.