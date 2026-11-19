import sys
print("Testing interactive input...")
print("If you see this, type 'test' and press Enter:")
try:
    user_input = input(">>> ")
    print(f"You typed: {user_input}")
    print("✅ Interactive input works!")
except EOFError:
    print("❌ EOFError - not in interactive terminal")
    print("Please run this in a real terminal, not in background")
