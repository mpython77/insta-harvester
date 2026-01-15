from instaharvest.parser import CommentParser
import sys
sys.stdout.reconfigure(encoding='utf-8')

def test_parsing():
    try:
        with open(r'c:\Users\TROLL\Desktop\Test\insta-harvester\reply_open.html', 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print("Test file not found. Please ensure 'full_comment_html_code.html' is in the correct directory.")
        return
    
    parser = CommentParser()
    comments = parser.parse_html(html)
    
    print(f"Found {len(comments)} top-level comments.")
    
    for c in comments[:10]: # Check first 10
        print(f"---")
        print(f"ID: {c.id}")
        print(f"User: {c.author.username}")
        print(f"Text: {repr(c.text)}") # Use repr to see invisible chars
        print(f"Time: {c.timestamp_iso}")
        print(f"Likes: {c.likes_count}")
        print(f"Reply Count (Extracted): {c.reply_count}")
        print(f"Nested Replies: {len(c.replies)}")
        
        for r in c.replies:
             print(f"    > Reply ID: {r.id} | User: {r.author.username} | Text: {repr(r.text)}")

if __name__ == "__main__":
    test_parsing()
