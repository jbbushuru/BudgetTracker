import os
import json
import logging
import re
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
class KeywordCategorizer:

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
        "DATA BUNDLES": "Data & Airtime",
        "AIRTIME": "Data & Airtime",
        "M-SHWARI": "Savings",
        "KCB M-PESA": "Savings",
        "Reversal":"MPesa Reversal",
        "Withdraw":"MPesa Withdrawal",
        "Give cash to":"MPesa Deposit"
    }

    def get_rules_string(self):
        return "\n".join([f"- {k}: {v}" for k, v in self.RULES.items()])
# removed the functions that extracted information and let the AI do the parsing and categorization
class SMSParserService:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-3-flash-preview"
#added user parameter to help with the fetching of specific user-created categories
    def parse_mpesa_sms(self, raw_text: str, user=None):
        """Single SMS parsing."""
        results = self.parse_mpesa_batch([raw_text], user=user)
        return results[0] if results else None

    def parse_mpesa_batch(self, sms_list: list[str], user=None):
        """
        Parses multiple SMS messages in a single AI call to optimize quota usage.
        """
        if not sms_list:
            return []

        # Dynamically fetch categories from the database (System + User specific)
        from .models import Category
        from django.db.models import Q
        
        if user and user.is_authenticated:
            categories = Category.objects.filter(
                Q(owner=user) | Q(owner__isnull=True)
            ).values_list('name', flat=True).distinct()
        else:
            categories = Category.objects.filter(owner__isnull=True).values_list('name', flat=True)
        
        categories_list = list(categories)
        if "Other Expense" not in categories_list:
            categories_list.append("Other Expense")
        
        categories_str = ", ".join([f'"{c}"' for c in categories_list])

        # Batching multiple messages into one prompt reduces API calls significantly
        prompt = "Parse the following M-Pesa SMS messages and return an array of objects:\n\n"
        for i, sms in enumerate(sms_list):
            prompt += f"SMS {i+1}: {sms}\n---\n"

    #adjusted the instructions for better categorization and timestamp extraction
        system_instruction = f"""
        ROLE: Expert M-Pesa Financial Auditor for the Kenyan market.
        TASK: Extract transaction data and assign the most appropriate category.

        CATEGORIZATION HINTS (Use these keywords to identify categories):
        {KeywordCategorizer().get_rules_string()}

        VALID CATEGORIES (Only use these EXACT names):
        {categories_str}

        TIMESTAMP EXTRACTION:
        Strictly extract the date and time from the SMS and format as an ISO 8601 string: YYYY-MM-DDTHH:MM:SS.
        Example: "on 5/5/26 at 12:45 PM" -> "2026-05-05T12:45:00"
        Note: Year '26' refers to 2026.

        REQUIRED JSON OUTPUT:
        [
            {{
                "amount": float,
                "fee": float,
                "recipient": "string",
                "transaction_type": "IN" | "OUT",
                "suggested_category": "string",
                "timestamp": "YYYY-MM-DDTHH:MM:SS"
            }},
            ...
        ]

        RULES:
        1. "IN": Look for "received", "from", "Give cash to", or "into your M-PESA".
        2. "OUT": Look for "sent to", "Paid to" or "Withdraw"
        3. For "IN" transactions, put the Sender's name in the "recipient" field.
        4. Default fee to 0.00 if it is a "Received" transaction.
        5. Return an empty object {{}} for any SMS that is not a valid transaction.
        6. Choose the suggested_category based on the recipient or the context of the SMS.
        7. If unsure of category, return null for suggested_category.
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