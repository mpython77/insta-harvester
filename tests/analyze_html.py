from bs4 import BeautifulSoup
import json
import re

def analyze_comments():
    with open("comments_dom.html", "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    time_tags = soup.find_all("time")
    
    with open("debug_output2.txt", "w", encoding="utf-8") as out:
        out.write(f"Found {len(time_tags)} <time> tags\n")
        
        for i, time_tag in enumerate(time_tags[:3]):
            out.write(f"\n======== Comment Node {i+1} ========\n")
            
            node = time_tag
            depth = 0
            while node and node.name != 'body' and depth < 10:
                out.write(f"\n--- Parent Depth {depth} ({node.name}) ---\n")
                if node.name:
                    cls = ".".join(node.get('class', []))
                    out.write(f"Class: {cls}\n")
                
                texts = [t.strip() for t in node.find_all(text=True) if t.strip()]
                out.write("Text: " + repr(texts) + "\n")
                
                # Stop if we hit a node that has multiple time tags, meaning we've gone too far up
                if len(node.find_all("time")) > 1:
                    out.write(">>> STOPPING: Found multiple time tags in this parent (it's a container of multiple comments)\n")
                    break
                    
                node = node.parent
                depth += 1

if __name__ == "__main__":
    analyze_comments()
