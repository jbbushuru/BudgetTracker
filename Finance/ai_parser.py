import os
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class SMSParserService:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        # Using the 2026 Flash model for cost-effective, high-speed parsing
        self.model_id = "gemini-3-flash-preview"

    def parse_mpesa_sms(self, raw_text: str):
        system_instruction = """
        ROLE: Expert M-Pesa Financial Auditor.
        TASK: Extract transaction data and determine if it is "IN" (Received) or "OUT" (Sent).

        REQUIRED JSON SCHEMA:
        {
            "amount": float,
            "fee": float,
            "recipient": "string",
            "transaction_type": "IN" | "OUT"
        }

        RULES:
        1. "IN": Look for phrases like "You have received", "from", or "into your M-PESA account".
        2. "OUT": Look for "sent to", "Paid to", or "Give to".
        3. For "IN" transactions, put the Sender's name in the "recipient" field.
        4. Default fee to 0.00 if it is a "Received" message.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=f"Parse this SMS: {raw_text}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"AI Auditor Failure: {e}")
            return None