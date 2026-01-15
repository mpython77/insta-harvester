from instaharvest.parser import CommentParser
import os
import sys

def debug_container():
    sys.stdout.reconfigure(encoding='utf-8')
    cwd = os.getcwd()
    file_path = "reply_open.html" # Use existing file
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()

    parser = CommentParser()
    comments = parser.parse_html(html)
    
    print(f"Total parsed: {len(comments)}")
    for i, c in enumerate(comments[:3]):
        print(f"[{i}] {c.author.username}")
        print(f"    Text: '{c.text}'")
        print(f"    Likes: {c.likes_count}")
        print(f"    Replies: {len(c.replies)}")

if __name__ == "__main__":
    debug_container()
