import ollama
from ollama import Client

class OllamaTranslator:
    def __init__(self, host="http://localhost:11434", default_model="llama3", log_callback=None):
        """
        Initialize the OllamaTranslator.
        
        Args:
            host (str): The URL of the Ollama server.
            default_model (str): The default model to use if none is specified.
            log_callback (callable): A function to log messages.
        """
        self.host = host
        self.default_model = default_model
        self.client = Client(host=host)
        self.log_callback = log_callback

    def log(self, message):
        """Log a message using the callback or print."""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def connect(self) -> bool:
        """
        Checks connection to the Ollama server by attempting to list models.
        
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            self.client.list()
            return True
        except Exception as e:
            self.log(f"Error connecting to Ollama server at {self.host}: {e}")
            return False

    def list_models(self) -> list[str]:
        """
        Lists available models from the Ollama server.
        
        Returns:
            list: A list of model names available on the server.
        """
        self.log("Listing models...")
        try:
            response = self.client.list()
            models_list = response.get('models', [])
            # Extract model names from the response
            if models_list:
                return [model.get('model') for model in models_list]
            return []
        except Exception as e:
            self.log(f"Error listing models: {e}")
            return []

    def translate_text(self, text, model, prompt) -> str | None:
        """
        Translates text using the specified model and prompt.
        
        Args:
            text (str): The text to translate (comma separated sentences).
            model (str): The name of the model to use.
            prompt (str): The start prompt template.
            
        Returns:
            str: The translated text (JSON string), or None if an error occurs.
        """
        if not model:
            model = self.default_model

        try:
            # Combine prompt and text as requested
            full_prompt = f"{prompt}\n\n{text}"
            
            # Send request to Ollama
            response = self.client.chat(
                model=model, 
                messages=[
                    {
                        'role': 'user',
                        'content': full_prompt,
                    },
                ],
                format='json'
            )
            
            # Extract and return the content
            if 'message' in response and 'content' in response['message']:
                return response['message']['content']
            else:
                self.log("Unexpected response format from Ollama.")
                return None
                
        except Exception as e:
            self.log(f"Error during translation: {e}")
            return None

if __name__ == "__main__":
    # Test utilization
    translator = OllamaTranslator()
    
    # Check connection
    if translator.connect():
        print("Connected to Ollama server.")
        
        # List models
        models = translator.list_models()
        print(f"Available Models: {models}")
        
        if models:
            # Select a model (e.g., the first one available or a specific one like 'llama3')
            # You can change 'llama3' to any model you have pulled, like 'gemma2' or 'mistral'
            test_model = input(f"Enter the model you want to use (default: {models[0]}): ").strip() or models[0]
            print(f"Testing with model: {test_model}")
            
            # List of texts to translate
            test_messages = [
                "こんにちは、元気ですか？",
                "昨日は何をしましたか？",
                "この本はとても面白いです。",
                "助けてくれてありがとう。"
            ]
            
            # Prompt for translation (Japanese to Thai as per project context)
            test_prompt = "You are a professional translator. Translate the following Japanese text to Thai, ensuring natural phrasing: '{text}'"
            
            print("\n--- Translation Test Results ---")
            for msg in test_messages:
                print(f"Original: {msg}")
                translated = translator.translate_text(msg, test_model, test_prompt)
                if translated:
                    print(f"Translated: {translated}")
                else:
                    print("Translation failed.")
                print("-" * 30)
        else:
            print("No models found. Please use 'ollama pull <model>' to download a model.")
    else:
        print("Failed to connect to Ollama. Please ensure the Ollama server is running (usually on port 11434).")
