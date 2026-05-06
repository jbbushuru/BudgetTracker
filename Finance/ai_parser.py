import os
import json
import logging
import re
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
#added logic for precategorization and batch proceesing handling
class KeywordCategorizer:
    """
    Fast-track categorization for known Kenyan entities.
    Avoids AI calls for common, predictable transactions.
    """
    RULES = {
        # Format: "Keyword": "Category Name"
        "NAIVAS": "Shopping",
        "CARREFOUR": "Shopping",
        "QUICKMART": "Shopping",
        "CHANDARANA": "Shopping",
        "SAFARICOM": "Utilities",
        "AIRTEL": "Utilities",
        "KPLC": "Utilities",
        "ZUKU": "Utilities",
        "FAIBA": "Utilities",
        "UBER": "Transportation",
        "BOLT": "Transportation",
        "LITTLE CAB": "Transportation",
        "ZUCCHINI": "Food & Dining",
        "KFC": "Food & Dining",
        "JAVA HOUSE": "Food & Dining",
        "PIZZA INN": "Food & Dining",
        "CHICKEN INN": "Food & Dining",
        "TOTAL": "Transportation",
        "SHELL": "Transportation",
        "RUBIS": "Transportation",
        "STIMA": "Utilities",
        "NHIF": "Healthcare",
        "NSSF": "Other Expense",
        "DATA BUNDLES": "Utilities",
        "AIRTIME": "Utilities",
    }

    def get_category(self, text: str):
        text_upper = text.upper()
        for keyword, category in self.RULES.items():
            if keyword in text_upper:
                return category
        return None

    def extract_basic_info(self, text: str):
        """
        Regex-based extraction for standard M-Pesa patterns to avoid AI.
        """
        # Pattern 1: Sent to ... KES 1,000.00
        # Pattern 2: Paid to ... KES 500.00
        amount_match = re.search(r"KES\s?([\d,]+\.?\d*)", text)
        if not amount_match:
            return None
        
        amount = float(amount_match.group(1).replace(",", ""))

        # Very basic recipient extraction for 'Sent to' or 'Paid to'
        recipient = "Unknown"
        rec_match = re.search(r"(?:Sent to|Paid to|Received from)\s+([^.]+?)\s+on", text, re.IGNORECASE)
        if rec_match:
            recipient = rec_match.group(1).strip()

        # Determine type
        t_type = "OUT"
        if "received" in text.lower():
            t_type = "IN"

        return {
            "amount": amount,
            "fee": 0.0,
            "recipient": recipient,
            "transaction_type": t_type
        }

class SMSParserService:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        #calls the categorizer
        self.keyword_categorizer = KeywordCategorizer()
        # Using the 2026 Flash model for cost-effective, high-speed parsing
        self.model_id = "gemini-3-flash-preview"

    def parse_mpesa_sms(self, raw_text: str):
        """Single SMS parsing."""
        results = self.parse_mpesa_batch([raw_text])
        return results[0] if results else None

    def parse_mpesa_batch(self, sms_list: list[str]):
        """
        Parses multiple SMS messages in a single AI call to optimize quota usage.
        """
        if not sms_list:
            return []

        # Batching multiple messages into one prompt reduces API calls significantly
        prompt = "Parse the following M-Pesa SMS messages and return an array of objects:\n\n"
        for i, sms in enumerate(sms_list):
            prompt += f"SMS {i+1}: {sms}\n---\n"

        system_instruction = """
        ROLE: Expert M-Pesa Financial Auditor for the Kenyan market.
        TASK: Extract transaction data and assign the most appropriate category from the list below.

        VALID CATEGORIES:
        - "Education" (School fees, books, courses)
        - "Entertainment" (Netflix, movies, betting, gaming)
        - "Food & Dining" (Groceries, restaurants, fast food, Zucchini, KFC, Java)
        - "Healthcare" (Pharmacy, hospital bills, NHIF)
        - "Shopping" (Supermarkets, Naivas, Carrefour, clothing, electronics)
        - "Transportation" (Fuel, Shell, Total, Uber, Bolt, Matatu, airfare)
        - "Utilities" (Safaricom, KPLC, Stima, Water, Internet, Zuku)
        - "Other Expense" (Anything that doesn't fit the above)

        REQUIRED JSON OUTPUT:
        [
            {
                "amount": float,
                "fee": float,
                "recipient": "string",
                "transaction_type": "IN" | "OUT",
                "suggested_category": "string" (Must match one of the VALID CATEGORIES exactly)
            },
            ...
        ]

        RULES:
        1. "IN": Look for phrases like "You have received", "from", or "into your M-PESA account".
        2. "OUT": Look for "sent to", "Paid to", or "Give to".
        3. For "IN" transactions, put the Sender's name in the "recipient" field.
        4. Default fee to 0.00 if it is a "Received" message.
        5. Return an empty object {} for any SMS that is not a valid transaction.
        6. Choose the suggested_category based on the recipient or the context of the SMS.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"AI Auditor Batch Failure: {e}")
            # If batch fails, we return a list of Nones to allow individual retry or failure handling
            return [None] * len(sms_list)