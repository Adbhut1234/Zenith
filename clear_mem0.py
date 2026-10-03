"""One-time script to delete ALL mem0 memories for the configured user."""
import os
from dotenv import load_dotenv
from mem0 import MemoryClient

load_dotenv()

raw_user_name = os.getenv('Zenith_USER_ID') or os.getenv('J.A.R.V.I.S._USER_ID') or 'Admin'
user_name = raw_user_name.strip() if raw_user_name and raw_user_name.strip() else 'Admin'

client = MemoryClient()

print(f"Deleting ALL memories for user: '{user_name}'...")
try:
    result = client.delete_all(user_id=user_name)
except Exception as e:
    try:
        result = client.delete_all(filters={'user_id': user_name})
    except Exception as e2:
        result = f"Error: {e2}"
print(f"Result: {result}")
print("All memories cleared!")

