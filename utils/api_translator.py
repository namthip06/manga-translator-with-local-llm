import os
from openai import OpenAI

class APITranslator:
    # Mapping of popular models to their API base URLs
    MODEL_BASE_URL_MAP = {
        # OpenAI
        "gpt-4o": "https://api.openai.com/v1",
        "gpt-4o-mini": "https://api.openai.com/v1",
        "gpt-3.5-turbo": "https://api.openai.com/v1",
        
        # Google Gemini (OpenAI Compatible)
        "gemini-2.0-flash": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.0-flash-lite": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.5-pro": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.5-flash": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.5-flash-lite": "https://generativelanguage.googleapis.com/v1beta/openai/",
        
        # Groq
        "llama3-8b-8192": "https://api.groq.com/openai/v1",
        "llama3-70b-8192": "https://api.groq.com/openai/v1",
    }

    def __init__(self, base_url="https://api.openai.com/v1", api_key=None, default_model="gpt-3.5-turbo", log_callback=None):
        """
        Initialize the APITranslator.
        
        Args:
            base_url (str): The base URL of the API.
            api_key (str): The API key for authentication.
            default_model (str): The default model to use.
            log_callback (callable): A function to log messages.
        """
        self.base_url = base_url
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "EMPTY")
        self.default_model = default_model
        self.log_callback = log_callback
        
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def get_supported_models(self) -> list[str]:
        """Returns a list of supported/pre-configured model names."""
        return list(self.MODEL_BASE_URL_MAP.keys())

    def configure_for_model(self, model_name: str) -> bool:
        """
        Updates the base_url and default_model based on the provided model name.
        If the model is known in MODEL_BASE_URL_MAP, it sets the corresponding base_url.
        
        Args:
            model_name (str): The name of the model to configure for.
            
        Returns:
            bool: True if the model was found in the preset map, False otherwise.
        """
        self.default_model = model_name
        
        if model_name in self.MODEL_BASE_URL_MAP:
            new_base_url = self.MODEL_BASE_URL_MAP[model_name]
            if new_base_url != self.base_url:
                self.base_url = new_base_url
                # Re-initialize client with the new base_url
                self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
                self.log(f"Switched base_url to {self.base_url} for model '{model_name}'")
            return True
        else:
            self.log(f"Model '{model_name}' not found in presets. Keeping current base_url: {self.base_url}")
            return False

    def log(self, message):
        """Log a message using the callback or print."""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def translate_text(self, text, model, prompt, api_key=None, base_url=None, json_format=False) -> str | None:
        """
        Translates text using the specified model and prompt via OpenAI-compatible API.
        
        Args:
            text (str): The text to translate.
            model (str): The name of the model to use.
            prompt (str): The system prompt or instruction.
            api_key (str): Optional API key to use for this request.
            base_url (str): Optional Base URL to use for this request.
            json_format (bool): Whether to enforce JSON output.
            
        Returns:
            str: The translated text, or None if an error occurs.
        """
        if not model:
            model = self.default_model

        # Prepare messages
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ]

        try:
            # If explicit api_key or base_url is provided, we use them. 
            # If not provided, we fall back to instance defaults for the temporary client creation 
            # OR we just use self.client if NOTHING is overridden.
            
            if api_key or base_url:
                target_api_key = api_key or self.api_key
                target_base_url = base_url or self.base_url
                client = OpenAI(api_key=target_api_key, base_url=target_base_url)
            else:
                client = self.client

            chat_args = {
                "model": model,
                "messages": messages,
            }
            
            if json_format:
                chat_args["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**chat_args)
            
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                self.log("Received empty response from API.")
                return None

        except Exception as e:
            self.log(f"Error during API translation: {e}")
            return None