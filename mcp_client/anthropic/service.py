import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

class AnthropicService:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 1000

    def generate_response(self, messages, tools=None):
        return self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
            tools=tools if tools else None,
        ) 