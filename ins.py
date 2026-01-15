import sys
import os
sys.path.insert(0, os.getcwd())

from instaharvest import InstagramOrchestrator
from instaharvest.config import ScraperConfig

def main():
    # Create config
    config = ScraperConfig()
    orchestrator = InstagramOrchestrator(config)

    print("Starting orchestrator...")

    # Option 1: Scrape profile with comments included
    # The following block is replaced by the streaming comment scraper logic
    # results = orchestrator.scrape_complete_profile_advanced(
    #     'anoshka._.__',
    #     parallel=3,
    #     save_excel=True,
    #     scrape_comments=True,          # Enable comment scraping
    #     max_comments_per_post=100,     # Limit per post (None = all)
    #     include_replies=True           # Include reply threads
    # )

    # print(f"Total comments: {results.get('comments_data', 'N/A')}")

    print("\n" + "="*50)
    print("🚀 STREAMING COMMENT SCRAPER (MEMORY SAFE)")
    print("="*50)
    print("INFO: Data will be saved in real-time to avoid data loss.")
    
    url = input("Enter Post/Reel URL: ").strip()
    limit_input = input("Limit (Enter for None): ").strip()
    limit = int(limit_input) if limit_input.isdigit() else None
    
    # Setup Streaming Exporter
    
    # Create filenames
    short_code = url.split("/")[4] if len(url.split("/")) > 4 else "unknown"
    timestamp = int(time.time())
    excel_file = f"comments_{short_code}_{timestamp}.xlsx"
    json_file = f"comments_{short_code}_{timestamp}.jsonl"
    
    # Define Columns
    columns = [
        'Post URL', 'Comment ID', 'Username', 'Text', 
        'Likes', 'Replies', 'Date', 'Is Reply', 'Parent ID'
    ]
    
    excel = StreamingExcelExporter(excel_file, columns)
    json_export = StreamingJSONExporter(json_file)
    
    print(f"\n📂 Saving to:\n  - {excel_file}\n  - {json_file}\n")
    
    scraper = CommentScraper(config)
    
    try:
        count = 0
        print("⏳ Starting stream... (Press Ctrl+C to stop safely)")
        
        # Consume Generator
        for comment in scraper.scrape_stream(url, max_comments=limit, include_replies=True):
            count += 1
            
            # Prepare Row
            row = [
                url, comment.id, comment.author.username, comment.text,
                comment.likes_count, comment.reply_count, comment.timestamp,
                "Yes" if comment.is_reply else "No", comment.parent_id or ""
            ]
            
            # Write Immediately
            excel.append_row(row)
            json_export.append_item(comment.to_dict())
            
            # Print Progress
            print(f"\r[{count}] {comment.author.username}: {comment.text[:30]}...", end="", flush=True)
        
        print(f"\n\n✅ Done! Scraped {count} comments.")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user. Data is verified safe on disk.")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
    finally:
        scraper.close()
        input("\nPress Enter to return...")

if __name__ == '__main__':
    # On Windows, multiprocessing requires this protection
    main()
