"""
Instagram Send Message Script
Simple script to send Instagram direct messages

Usage:
    python send_message.py

Requirements:
    - Instagram session must be saved first (run save_session.py)
"""

from instagram_scraper import MessageManager


def main():
    """Send a direct message to an Instagram user"""
    print("=" * 70)
    print("📨 Instagram Send Message Script")
    print("=" * 70)
    print()

    # Get username from user
    username = input("Enter Instagram username to message (without @): ").strip().lstrip('@')

    if not username:
        print("❌ No username provided!")
        return

    # Get message
    print()
    message = input("Enter your message: ").strip()

    if not message:
        print("❌ No message provided!")
        return

    # Initialize MessageManager
    print("\n📂 Loading session...")
    messenger = MessageManager()

    try:
        # Load session and setup browser
        session_data = messenger.load_session()
        messenger.setup_browser(session_data)

        print(f"✅ Session loaded!\n")

        # Send the message
        print(f"📨 Sending message to @{username}...")
        result = messenger.send_message(username, message)

        # Print result
        print()
        print("=" * 70)
        if result['success']:
            print(f"✅ SUCCESS! Message sent to @{username}")
            print(f"Message: {message}")
        else:
            print(f"❌ ERROR: {result['message']}")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        messenger.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Program stopped!")
    except Exception:
        pass
