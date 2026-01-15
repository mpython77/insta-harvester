import json
import pandas as pd
from typing import List
from .models import Comment
import os

class CommentExporter:
    def save_json(self, comments: List[Comment], filename: str):
        data = [c.to_dict() for c in comments]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(comments)} comments to {filename}")

    def save_excel(self, comments: List[Comment], filename: str):
        # Flatten for Excel
        rows = []
        for c in comments:
            row = {
                'id': c.id,
                'username': c.author.username,
                'text': c.text,
                'date': c.timestamp_iso,
                'likes': c.likes_count,
                'replies': c.reply_count,
                'url': c.permalink,
                'is_reply': c.is_reply,
                'parent_id': c.parent_id
            }
            rows.append(row)
            for r in c.replies:
                row_r = {
                    'id': r.id,
                    'username': r.author.username,
                    'text': r.text,
                    'date': r.timestamp_iso,
                    'likes': r.likes_count,
                    'replies': r.reply_count,
                    'url': r.permalink,
                    'is_reply': True,
                    'parent_id': c.id
                }
                rows.append(row_r)
        
        df = pd.DataFrame(rows)
        df.to_excel(filename, index=False)
        print(f"Saved {len(rows)} rows to {filename}")
