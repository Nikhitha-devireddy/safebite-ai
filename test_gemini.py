import os
from dotenv import load_dotenv
from google import genai

# 1. Load the secret key from our .env file
load_dotenv()

# 2. Initialize the official Google GenAI client
client = genai.Client()

# 3. Send a test message using the recommended Interactions API
print("Sending test message to Gemini via Interactions API...")
interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input="Hello, Gemini! Confirm you are ready to help me build my allergen-safe meal-planning agent.",
)

# 4. Print out Gemini's response
print("\n--- Gemini Response ---")
print(interaction.output_text)