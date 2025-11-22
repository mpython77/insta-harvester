"""
Shared Browser - Example Usage
Demonstrates using single browser for multiple operations
"""

from instagram_scraper import SharedBrowser


def example_basic_usage():
    """Example 1: Basic usage with context manager"""
    print("=" * 70)
    print("Example 1: Basic Usage - Single Browser for All")
    print("=" * 70)

    # Context manager - browser opens and closes automatically
    with SharedBrowser() as browser:
        print("\n✅ Browser opened once!\n")

        # Operation 1: Follow a user
        username1 = input("Enter username to follow: ").strip()
        result = browser.follow(username1)
        print(f"Follow: {result['status']}")

        # Operation 2: Send message to same user
        message = input(f"\nEnter message for @{username1}: ").strip()
        result = browser.send_message(username1, message)
        print(f"Message: {result['status']}")

        # Operation 3: Check if following
        result = browser.is_following(username1)
        print(f"Following: {result['following']}")

        print("\n✅ All operations completed in SINGLE browser!")

    print("\n✅ Browser closed automatically")


def example_manual_control():
    """Example 2: Manual browser control"""
    print("=" * 70)
    print("Example 2: Manual Control - Advanced Usage")
    print("=" * 70)

    # Manual control - you manage browser lifetime
    browser = SharedBrowser()

    try:
        # Start browser manually
        browser.start(headless=False)
        print("\n✅ Browser started!\n")

        # Get usernames
        user1 = input("Enter first username: ").strip()
        user2 = input("Enter second username: ").strip()

        # Follow both users
        print(f"\n🔄 Following @{user1}...")
        browser.follow(user1)

        print(f"🔄 Following @{user2}...")
        browser.follow(user2)

        # Send message to both
        msg = input("\nEnter message to send to both: ").strip()

        print(f"\n📨 Sending to @{user1}...")
        browser.send_message(user1, msg)

        print(f"📨 Sending to @{user2}...")
        browser.send_message(user2, msg)

        print("\n✅ All done!")

    finally:
        # Always close browser
        browser.close()


def example_batch_operations():
    """Example 3: Batch operations in single browser"""
    print("=" * 70)
    print("Example 3: Batch Operations - Multiple Users")
    print("=" * 70)

    with SharedBrowser() as browser:
        print("\n✅ Browser opened!\n")

        # Get list of users
        print("Enter usernames (one per line, empty to finish):")
        usernames = []
        while True:
            user = input(f"  Username {len(usernames) + 1}: ").strip()
            if not user:
                break
            usernames.append(user)

        if not usernames:
            print("❌ No usernames provided")
            return

        # Batch follow
        print(f"\n🔄 Following {len(usernames)} users...")
        result = browser.batch_follow(usernames)

        print(f"\n✅ Follow complete:")
        print(f"  Succeeded: {result['succeeded']}")
        print(f"  Already following: {result['already_following']}")
        print(f"  Failed: {result['failed']}")

        # Batch message
        msg = input("\nEnter message to send to all: ").strip()
        if msg:
            print(f"\n📨 Sending message to {len(usernames)} users...")
            result = browser.batch_send(usernames, msg)

            print(f"\n✅ Message sending complete:")
            print(f"  Succeeded: {result['succeeded']}")
            print(f"  Failed: {result['failed']}")


def example_workflow():
    """Example 4: Complete workflow"""
    print("=" * 70)
    print("Example 4: Complete Workflow - Real Use Case")
    print("=" * 70)

    with SharedBrowser() as browser:
        print("\n✅ Browser ready!\n")

        username = input("Enter target username: ").strip()

        # Step 1: Check if already following
        print(f"\n🔍 Checking if following @{username}...")
        status = browser.is_following(username)

        if not status['following']:
            # Step 2: Follow if not following
            print(f"🔄 Following @{username}...")
            browser.follow(username)

        # Step 3: Send a message
        msg = input(f"\nEnter message for @{username}: ").strip()
        if msg:
            print(f"📨 Sending message...")
            browser.send_message(username, msg)

        # Step 4: Get profile info
        print(f"\n🔍 Getting profile info...")
        try:
            data = browser.scrape_profile(username)
            print(f"\nProfile @{username}:")
            print(f"  Posts: {data.get('posts', 'N/A')}")
            print(f"  Followers: {data.get('followers', 'N/A')}")
            print(f"  Following: {data.get('following', 'N/A')}")
        except Exception as e:
            print(f"  ⚠️ Could not get profile info: {e}")

        print("\n✅ Workflow complete!")


def main():
    """Main function - choose example"""
    print("\n" + "=" * 70)
    print("🚀 Shared Browser - Examples")
    print("=" * 70)
    print()
    print("Choose an example:")
    print("  1. Basic usage (context manager)")
    print("  2. Manual control (advanced)")
    print("  3. Batch operations (multiple users)")
    print("  4. Complete workflow (real use case)")
    print()

    choice = input("Enter choice (1-4): ").strip()

    if choice == '1':
        example_basic_usage()
    elif choice == '2':
        example_manual_control()
    elif choice == '3':
        example_batch_operations()
    elif choice == '4':
        example_workflow()
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
