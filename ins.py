import sys
import os
sys.path.insert(0, os.getcwd())

from instaharvest import CommentScraper
from instaharvest.comments_export import export_comments_to_json, export_comments_to_excel

scraper = CommentScraper()
session_data = scraper.load_session()
scraper.setup_browser(session_data)

# Scrape comments from a single post
post_url = 'https://www.instagram.com/p/DTLHDJpDAbO/'
comments = scraper.scrape(
    post_url,
    max_comments=100,
    include_replies=True
)

# Access comment data
print(f"Found {len(comments.comments)} top-level comments.")
print("---")

for comment in comments.comments:
    print(f"ID: {comment.id}")
    print(f"User: {comment.author.username}")
    print(f"Text: '{comment.text}'")
    print(f"Time: {comment.timestamp_iso}")
    print(f"Likes: {comment.likes_count}")
    print(f"Reply Count (Extracted): {comment.reply_count}")
    print(f"Nested Replies: {len(comment.replies)}")
    
    if comment.replies:
        for reply in comment.replies:
             print(f"    > Reply ID: {reply.id} | User: {reply.author.username} | Text: '{reply.text}'")
    print("-" * 20)

# Export Options
save_json = True
save_excel = True

print("\n--- Exporting Data ---")
if save_json:
    json_filename = f"comments_{comments.post_id}.json"
    if export_comments_to_json(comments, json_filename):
        print(f"[+] Saved JSON to {json_filename}")
    else:
        print(f"[-] Failed to save JSON")

if save_excel:
    xlsx_filename = f"comments_{comments.post_id}.xlsx"
    if export_comments_to_excel(comments, xlsx_filename):
        print(f"[+] Saved Excel to {xlsx_filename}")
    else:
        print(f"[-] Failed to save Excel")

scraper.close()
