import os
from dotenv import load_dotenv
from google import genai

# 1. Load the secret key from our .env file
load_dotenv()

client = None

if __name__ == "__main__":
    # 2. Initialize the official Google GenAI client
    try:
        client = genai.Client()
    except Exception as e:
        print(f"Gemini client initialization failed: {e}")
    # 3. Send a test message using the recommended Interactions API
    print("Sending test message to Gemini via Interactions API...")
    try:
        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input="Hello, Gemini! Confirm you are ready to help me build my allergen-safe meal-planning agent.",
        )
        # 4. Print out Gemini's response
        print("\n--- Gemini Response ---")
        print(interaction.output_text)
    except Exception as e:
        print(f"Gemini test call failed (expected if rate limited/offline): {e}")