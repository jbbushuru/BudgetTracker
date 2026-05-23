import time
from django.contrib.auth import get_user_model
from Finance.views import process_single_transaction
from Finance.ai_parser import SMSParserService

def process_sms_batch_task(user_id, transactions_data):
    """
    Background task to process a batch of M-Pesa SMS messages using the AI parser.
    """
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"error": "User not found"}

    parser = SMSParserService()
    processed_count = 0
    errors = []

    # Extract all SMS bodies
    all_sms = [item.get('body') for item in transactions_data if item.get('body')]
    
    if all_sms:
        CHUNK_SIZE = 30
        for i in range(0, len(all_sms), CHUNK_SIZE):
            if i > 0:
                # RPM limit safety
                time.sleep(1) 

            chunk_texts = all_sms[i:i + CHUNK_SIZE]
            audit_results = parser.parse_mpesa_batch(chunk_texts, user=user)

            for raw_sms, audit_result in zip(chunk_texts, audit_results):
                if not audit_result or not audit_result.get('recipient'):
                    errors.append(f"Failed to parse: {raw_sms[:20]}...")
                    continue

                try:
                    process_single_transaction(user, raw_sms, audit_result)
                    processed_count += 1
                except Exception as e:
                    errors.append(str(e))

    return {
        "processed_count": processed_count,
        "fast_tracked": processed_count - len([e for e in errors if "Failed to parse" in e]),
        "errors": errors
    }
