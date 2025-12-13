import ollama
from ollama import Client

class OllamaTranslator:
    def __init__(self, host="http://localhost:11434", default_model="llama3"):
        """
        Initialize the OllamaTranslator.
        
        Args:
            host (str): The URL of the Ollama server.
            default_model (str): The default model to use if none is specified.
        """
        self.host = host
        self.default_model = default_model
        self.client = Client(host=host)

    def connect(self):
        """
        Checks connection to the Ollama server by attempting to list models.
        
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            self.client.list()
            return True
        except Exception as e:
            print(f"Error connecting to Ollama server at {self.host}: {e}")
            return False

    def list_models(self):
        """
        Lists available models from the Ollama server.
        
        Returns:
            list: A list of model names available on the server.
        """
        print("Listing models...")
        try:
            response = self.client.list()
            models_list = response.get('models', [])
            # Extract model names from the response
            if models_list:
                return [model.get('model') for model in models_list]
            return []
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    def translate_text(self, text, model, prompt):
        """
        Translates text using the specified model and prompt.
        
        Args:
            text (str): The text to translate.
            model (str): The name of the model to use.
            prompt (str): The prompt template containing '{text}' placeholder.
            
        Returns:
            str: The translated text, or None if an error occurs.
        """
        if not model:
            model = self.default_model

        try:
            # Format the prompt with the text
            formatted_prompt = prompt.format(text=text)
            
            # Send request to Ollama
            response = self.client.chat(model=model, messages=[
                {
                    'role': 'user',
                    'content': formatted_prompt,
                },
            ])
            
            # Extract and return the content
            if 'message' in response and 'content' in response['message']:
                return response['message']['content']
            else:
                print("Unexpected response format from Ollama.")
                return None
                
        except Exception as e:
            print(f"Error during translation: {e}")
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
