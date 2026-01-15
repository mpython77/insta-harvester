import sys
import os
import time
sys.path.insert(0, os.getcwd())

from instaharvest import InstagramOrchestrator
from instaharvest.config import ScraperConfig
from instaharvest.comment_scraper import CommentScraper
from instaharvest.exporters import StreamingExcelExporter, StreamingJSONExporter

def main():
    # Create config
    config = ScraperConfig()
    
    # 🛡️ SECURITY: PROXY TESTING
    # Proxies disabled by user request
    # config.proxies = [
    #    "socks5://..."
    # ]
    
    orchestrator = InstagramOrchestrator(config)

    print("Starting orchestrator...")

    # Option 1: Profile Scraper (Legacy)
    # See documentation for usage.

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
        # Load Session & Setup Browser (CRITICAL FIX)
        print("🌍 Setting up browser session...")
        session_data = scraper.load_session()
        scraper.setup_browser(session_data)
        
        count = 0
        print("⏳ Starting stream... (Press Ctrl+C to stop safely)")
        
        # Consume Generator
        valid_photo_comment = None
        
        for comment in scraper.scrape_stream(url, max_comments=limit, include_replies=True):
            count += 1
            if comment.author.profile_picture_url:
                valid_photo_comment = comment
            
            # Prepare Row
            row = [
                url, comment.id, comment.author.username, comment.text,
                comment.likes_count, comment.reply_count, comment.timestamp,
                "Yes" if comment.is_reply else "No", comment.parent_id or ""
            ]
            
            # Write Immediately
            excel.append_row(row)
            json_export.append_item(comment.model_dump())
            
            # Print Progress
            print(f"\r[{count}] {comment.author.username}: {comment.text[:30]}...", end="", flush=True)
        
        print(f"\n\n✅ Done! Scraped {count} comments.")
        
        # --- HYBRID MODE DEMO ---
        print("\n" + "="*50)
        print("⚡ HYBRID MODE: Fast Media Download (curl_cffi)")
        print("="*50)
        
        if count > 0 and 'valid_photo_comment' in locals() and valid_photo_comment:
            target_url = valid_photo_comment.author.profile_picture_url
            print(f"🎯 Target Media: {valid_photo_comment.author.username}'s Profile Pic")
            print(f"🔗 URL: {target_url[:60]}...")
            
            # 1. Sync Cookies
            scraper.sync_network_client()
            
            # 2. Download
            filename = f"profile_pic_{valid_photo_comment.author.username}.jpg"
            print(f"⬇️ Downloading to {filename}...")
            
            start_t = time.time()
            success = scraper.network_client.download_media(target_url, filename)
            duration = time.time() - start_t
            
            if success:
                print(f"✅ Downloaded in {duration:.2f}s using Hybrid Client!")
            else:
                print("❌ Download failed.")
        else:
             print("⚠️ No comments with profile pictures found to test download.")
             
        # ------------------------
        
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
