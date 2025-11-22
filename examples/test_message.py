"""
Instagram Message Manager - Example Usage
Demonstrates how to use the MessageManager class
"""

from instagram_scraper import MessageManager, ScraperConfig


def example_single_message():
    """Example 1: Send message to a single user"""
    print("=" * 70)
    print("Example 1: Send Single Message")
    print("=" * 70)

    # Initialize MessageManager
    messenger = MessageManager()

    try:
        # Load session and setup browser
        session_data = messenger.load_session()
        messenger.setup_browser(session_data)

        # Get username and message
        username = input("Enter username to message (without @): ").strip()
        message = input("Enter your message: ").strip()

        if not username or not message:
            print("❌ Username or message is empty!")
            return

        print(f"\n📨 Sending message to @{username}...")
        result = messenger.send_message(username, message)

        # Print result
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")

        print(f"\nStatus: {result['status']}")

    finally:
        messenger.close()


def example_batch_message():
    """Example 2: Send message to multiple users"""
    print("=" * 70)
    print("Example 2: Batch Send Messages")
    print("=" * 70)

    messenger = MessageManager()

    try:
        # Load session and setup browser
        session_data = messenger.load_session()
        messenger.setup_browser(session_data)

        # Get message
        message = input("Enter message to send to all: ").strip()

        if not message:
            print("❌ Message is empty!")
            return

        # Get list of users
        print("\nEnter usernames (one per line, empty line to finish):")
        usernames = []
        while True:
            username = input(f"  Username {len(usernames) + 1}: ").strip()
            if not username:
                break
            usernames.append(username)

        if not usernames:
            print("❌ No usernames provided!")
            return

        print(f"\n📨 Sending message to {len(usernames)} users...")
        result = messenger.batch_send(
            usernames,
            message,
            delay_between=(3, 5),  # 3-5 seconds between sends
            stop_on_error=False    # Continue even if some fail
        )

        # Print summary
        print("\n" + "=" * 70)
        print("📊 BATCH SEND SUMMARY")
        print("=" * 70)
        print(f"Total users: {result['total']}")
        print(f"Successfully sent: {result['succeeded']}")
        print(f"Failed: {result['failed']}")
        print()

        # Print individual results
        print("Individual results:")
        for r in result['results']:
            status_icon = "✅" if r['success'] else "❌"
            print(f"  {status_icon} @{r['username']}: {r['status']}")

    finally:
        messenger.close()


def example_personalized_messages():
    """Example 3: Send personalized messages to different users"""
    print("=" * 70)
    print("Example 3: Send Personalized Messages")
    print("=" * 70)

    messenger = MessageManager()

    try:
        # Load session and setup browser
        session_data = messenger.load_session()
        messenger.setup_browser(session_data)

        # Get user-message pairs
        print("\nEnter username and message pairs (empty username to finish):")
        messages_to_send = []

        while True:
            username = input(f"\n  Username {len(messages_to_send) + 1}: ").strip()
            if not username:
                break

            message = input(f"  Message for @{username}: ").strip()
            if not message:
                print("  ⚠️ Message is empty, skipping...")
                continue

            messages_to_send.append({'username': username, 'message': message})

        if not messages_to_send:
            print("❌ No messages to send!")
            return

        print(f"\n📨 Sending {len(messages_to_send)} personalized messages...")

        results = []
        for i, item in enumerate(messages_to_send, 1):
            username = item['username']
            message = item['message']

            print(f"[{i}/{len(messages_to_send)}] Sending to @{username}...")

            result = messenger.send_message(username, message)
            results.append(result)

        # Print summary
        succeeded = sum(1 for r in results if r['success'])
        failed = len(results) - succeeded

        print("\n" + "=" * 70)
        print("📊 PERSONALIZED SEND SUMMARY")
        print("=" * 70)
        print(f"Total messages: {len(results)}")
        print(f"Successfully sent: {succeeded}")
        print(f"Failed: {failed}")
        print()

        # Print individual results
        print("Results:")
        for r in results:
            status_icon = "✅" if r['success'] else "❌"
            print(f"  {status_icon} @{r['username']}: {r['status']}")

    finally:
        messenger.close()


def main():
    """Main function - choose example to run"""
    print("\n" + "=" * 70)
    print("📨 Instagram Message Manager - Examples")
    print("=" * 70)
    print()
    print("Choose an example:")
    print("  1. Send single message")
    print("  2. Batch send same message to multiple users")
    print("  3. Send personalized messages to different users")
    print()

    choice = input("Enter choice (1-3): ").strip()

    if choice == '1':
        example_single_message()
    elif choice == '2':
        example_batch_message()
    elif choice == '3':
        example_personalized_messages()
    else:
        print("❌ Invalid choice!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Program stopped!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
