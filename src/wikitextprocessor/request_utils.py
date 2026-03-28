import os

def get_user_agent():
  return os.getenv("CUSTOM_USER_AGENT", "Custom UA")
