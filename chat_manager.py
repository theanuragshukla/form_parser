import google.generativeai as genai

API_KEY = ""

genai.configure(api_key=API_KEY)

class ChatManager:
    _instance = None
    _model = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ChatManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            cls._instance.chat = cls._instance.initialize_chat()
        return cls._instance

    def initialize_chat(self):
        default_prompt = (
            "Given a string of comma seperated strings, return a new comma seperated string which only contains the strings which have a high probaility of being a part of a form. Don't include any strings which are very unlikely to be a part of a form like headings, descriptions , large paragraphs, etc. Only give the response asked for and not anything else. Remove any thing resembling the heading, description, etc."
        )
        return self._model.start_chat(history=[{"role": "user", "parts": default_prompt}, {
            "role": "model", "parts": "Okay, I'm ready to help you. What do you need help with?"
        }])

    def send_message(self, message):
        response = self.chat.send_message(message)
        return response.text
