from instaharvest.parser import CommentParser

def test_parser():
    with open("comments_dom.html", "r", encoding="utf-8") as f:
        html = f.read()

    parser = CommentParser()
    comments = parser.parse_html(html)
    
    print(f"Parsed {len(comments)} top-level comments.")
    for c in comments:
        print(f"[{c.id}] {c.author.username} ({c.timestamp}): {c.text}")
        for r in c.replies:
            print(f"  -> [{r.id}] {r.author.username} ({r.timestamp}): {r.text}")

if __name__ == "__main__":
    test_parser()
