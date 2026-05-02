import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime
from google import genai
from google.genai import types
from django.conf import settings

# Direct imports for Type Hinting and IDE navigation
from Users.models import Profile  
from Advisor.models import ChatMessage

logger = logging.getLogger(__name__)

@dataclass
class ChatNudge:
    type: str 
    message: str 
    impact_on_goal: str 
    suggested_action: str 

@dataclass
class FinancialInstrument:
    name: str
    expected_returns: str
    ussd_code: str
    suitability: str 

@dataclass
class AdvisorResponse:
    ai_message: str
    nudges: List[ChatNudge]
    suggested_questions: List[str]
    relevant_instruments: List[FinancialInstrument]
    timestamp: str

class AdvisorService:
    def __init__(self):
        # Using Gemini 2.5 Flash for the core advisor logic
        self.flash_model = "gemini-2.5-flash"
        self.pro_model = "gemini-3-pro" # Fallback for complex ROI/calculations

    def _get_client(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found!")
            raise ValueError("API Key missing")
        return genai.Client(api_key=api_key)

    def _get_model(self, is_complex: bool):
        return self.pro_model if is_complex else self.flash_model

    def _build_system_instruction(self, profile: Profile, snapshot: Dict, triggers: List[str], history: List[ChatMessage]):
        """
        Uses Dot Notation to allow IDE navigation (Ctrl+Click) 
        and provide full autocomplete for Profile fields.
        """
        chat_history_str = "\n".join([
            f"{'AI' if m.role == 'ai' else 'User'}: {m.content}" 
            for m in history
        ])

        return f"""
        ROLE: You are "Finn," a savvy Kenyan Financial Advisor. 
        
        CONTEXT: 
        User Goal: {profile.financial_goal or 'Financial Stability'}.
        User Income: {profile.monthly_income or '40,000'} KES.
        User Age: {profile.age or 'Unknown'}.

        FINANCIAL SNAPSHOT (MONTHLY):
        {json.dumps(snapshot)}
        
        BEHAVIORAL TRIGGERS:
        {", ".join(triggers) if triggers else "NONE"}
        
        CHAT HISTORY:
        {chat_history_str}

        STRICT RULES:
        1. PERSISTENCE: Refer to the CHAT HISTORY for continuity.
        2. LOCALIZATION: Mention M-Pesa, SACCOs, M-Shwari, and Ruai land costs.
        3. FORMAT: Return ONLY valid JSON using the schema below.

        JSON SCHEMA:
        {{
            "ai_message": "Your advice string here",
            "nudges": [
                {{
                    "type": "WARNING",
                    "message": "text",
                    "impact_on_goal": "text",
                    "suggested_action": "text"
                }}
            ],
            "suggested_questions": ["question 1"],
            "relevant_instruments": [
                {{
                    "name": "instrument name",
                    "expected_returns": "percentage",
                    "ussd_code": "*123#",
                    "suitability": "explanation"
                }}
            ]
        }}
        """

    def get_advisor_response(self, user_query: str, profile: Profile, 
                             spending_snapshot: Dict, triggers: List[str], 
                             history: List[ChatMessage]) -> AdvisorResponse:
        """
        Takes the actual Profile model instance instead of a dictionary.
        """
        is_complex = any(word in user_query.lower() for word in ['calculate', 'compare', 'roi', 'investment', 'sacco', 'interest'])
        
        try:
            client = self._get_client()
            model_id = self._get_model(is_complex)
            
            # Passing the profile object directly to the instruction builder
            system_instr = self._build_system_instruction(profile, spending_snapshot, triggers, history)

            config = types.GenerateContentConfig(
                system_instruction=system_instr,
                response_mime_type="application/json",
                temperature=0.7
            )

            response = client.models.generate_content(
                model=model_id,
                contents=user_query,
                config=config
            )
            
            raw_data = json.loads(response.text)

            return AdvisorResponse(
                ai_message=raw_data.get('ai_message', "Sawa! Let's talk about your money."),
                nudges=[ChatNudge(**n) for n in raw_data.get('nudges', []) if isinstance(n, dict)],
                suggested_questions=raw_data.get('suggested_questions', []),
                relevant_instruments=[FinancialInstrument(**i) for i in raw_data.get('relevant_instruments', []) if isinstance(i, dict)],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Advisor Service Error: {e}")
            return AdvisorResponse(
                ai_message="Pole sana! My connection is a bit shaky. Can you repeat that?",
                nudges=[],
                suggested_questions=["Try again?"],
                relevant_instruments=[],
                timestamp=datetime.now().isoformat()
            )