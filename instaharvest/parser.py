from bs4 import BeautifulSoup, NavigableString
import re
from typing import List, Optional, Set, Any, Tuple
from .models import Comment, CommentAuthor

class CommentParser:
    def parse_html(self, html_content: str) -> List[Comment]:
        """
        Parses the full page HTML and returns a list of top-level Comment objects.
        Nested replies are included in the 'replies' field of their parent.
        """
        soup = BeautifulSoup(html_content, 'lxml')
        all_nodes: List[Tuple[Comment, Any]] = []
        processed_ids: Set[str] = set()

        # 1. Broad Search for Comments
        # We rely on permanent links (/c/ID/) as the most reliable anchor
        comment_links = soup.find_all('a', href=re.compile(r'/c/\d+'))
        
        for link in comment_links:
            # Find the semantic row container for this comment
            container = self._find_comment_container(link)
            if container:
                data = self._extract_data_from_node(container)
                if data and data.id not in processed_ids:
                    all_nodes.append((data, container))
                    processed_ids.add(data.id)

        # 2. Reconstruct Hierarchy
        # Map ID -> Comment object
        comment_map = {c.id: c for c, _ in all_nodes}
        top_level_comments: List[Comment] = []
        
        # We need to preserve order to correctly link parents
        # Replies appear visually below parents. In DOM, they are often in a UL following the parent.
        
        for comment, node in all_nodes:
            is_nested = False
            
            # Check if inside a UL (Reply List)
            parent_ul = node.find_parent('ul')
            if parent_ul:
                # This is a reply. We need to find the parent comment.
                # Strategy: Traverse up from UL to find the closest preceding comment container.
                # The hierarchy is typically:
                # [Parent Comment Block]
                #   [Content Div]
                #   [Toggle Replies Div]
                #   [UL (Replies)]
                #     [Reply 1]
                #     [Reply 2]
                
                # So the parent is NOT inside the UL, but is a sibling (or cousin) of the UL.
                
                parent_candidate = self._find_parent_for_ul(parent_ul, comment_map)
                
                if parent_candidate:
                    comment.is_reply = True
                    comment.parent_id = parent_candidate.id
                    parent_candidate.replies.append(comment)
                    is_nested = True
            
            if not is_nested:
                top_level_comments.append(comment)

        return top_level_comments

    def _find_parent_for_ul(self, ul_node, comment_map) -> Optional[Comment]:
        """
        Finds the parent comment for a given UL.
        Traverses ancestors. For each ancestor, looks backwards at siblings.
        """
        curr = ul_node
        # Traverse up the DOM tree from the UL
        for _ in range(10): # Limit levels up
            if not curr: break
            
            # Check previous siblings of current node
            sib = curr.previous_sibling
            while sib:
                if isinstance(sib, NavigableString):
                    sib = sib.previous_sibling
                    continue
                
                # Check for comment link in this sibling
                # We need to be careful not to find a link that is part of the current thread's Reply Toggle (e.g. "View replies") 
                # but valid comments usually have the permalink structure.
                links = sib.find_all('a', href=re.compile(r'/c/(\d+)'))
                for Link in links:
                    # Match ID
                    match = re.search(r'/c/(\d+)', Link['href'])
                    if match:
                        cid = match.group(1)
                        if cid in comment_map:
                            return comment_map[cid]
                
                sib = sib.previous_sibling
            
            curr = curr.parent
            if not curr or curr.name == 'body': break
            
        return None

    def _find_comment_container(self, link_node) -> Optional[Any]:
        current = link_node
        for _ in range(15): 
            current = current.parent
            if not current: break
            if current.name == 'div':
                # We need the full row container (User + Text + Actions).
                # Timestamp alone is often just in the header, so it's NOT sufficient.
                # The "Like" button (heart) or "Reply" action are effectively always present at the bottom of the row.
                
                has_reply = current.find(string=re.compile(r'Reply', re.IGNORECASE))
                has_like = current.find('svg', attrs={'aria-label': 'Like'}) or current.find('svg', attrs={'aria-label': 'Unlike'})
                
                # If we have the Like button or Reply text, we definitely have the full row.
                if has_like or has_reply:
                    return current
        return None

    def _extract_data_from_node(self, node) -> Optional[Comment]:
        try:
            # 1. ID & Permalink
            link_tag = node.find('a', href=re.compile(r'/c/\d+'))
            if not link_tag: return None
            
            href = link_tag['href']
            match = re.search(r'/c/(\d+)', href)
            if not match: return None
            comment_id = match.group(1)
            permalink = f"https://www.instagram.com{href}"

            # 2. Timestamp
            time_tag = node.find('time')
            iso_time = time_tag.get('datetime', '') if time_tag else ''
            display_time = time_tag.get_text(strip=True) if time_tag else ''

            # 3. Author
            user_link = node.find('a', href=re.compile(r'^/([\w\._]+)/?$'))
            username = "Unknown"
            profile_url = ""
            pic_url = ""
            
            if user_link:
                # Extract clean username from href
                # href is like /username/
                parts = [p for p in user_link['href'].split('/') if p]
                if parts:
                    username = parts[0]
                profile_url = f"https://www.instagram.com/{username}/"
                
                # Robust Profile Picture Extraction
                # 1. Try finding img with alt containing "profile picture" (Standard Instagram)
                img_tag = node.find('img', alt=re.compile(r'profile picture|change profile', re.IGNORECASE))
                
                # 2. Fallback: Check inside user link
                if not img_tag and user_link:
                    img_tag = user_link.find('img')
                
                # 3. Extract best URL from tag
                if img_tag:
                    # Prefer standard src
                    pic_url = img_tag.get('src', '')
                    
                    # If empty or data-uri, try srcset (often contains high-res)
                    if not pic_url or pic_url.startswith('data:'):
                        srcset = img_tag.get('srcset', '')
                        if srcset:
                            # srcset format: "url 150w, url 300w"
                            # We take the last one (highest res)
                            parts = srcset.split(',')
                            if parts:
                                last_part = parts[-1].strip().split(' ')[0]
                                pic_url = last_part
                else:
                    pic_url = ""
                    
                # Clean URL
                if pic_url:
                    pic_url = pic_url.replace('&amp;', '&')

            is_verified = bool(node.find('svg', attrs={'aria-label': 'Verified'}))

            # 4. Likes
            likes_count = 0
            like_node = node.find(string=re.compile(r'^\d+(?:,\d+)*\s+likes?$'))
            if like_node:
                 num_match = re.search(r'([\d,]+)', like_node)
                 if num_match:
                     likes_count = int(num_match.group(1).replace(',', ''))

            # 5. Text Extraction (Cleaned)
            text_parts = []
            
            for string in node.stripped_strings:
                # Normalize whitespace
                s_text = " ".join(str(string).split())
                if not s_text: continue
                
                # Check for bad parents
                if hasattr(string, 'parent') and string.parent:
                    parent = string.parent
                    if parent.find_parent('div', role='button'): continue
                    
                    # Username Skip: Check if this string belongs to the user link
                    if parent.name == 'a' and parent == user_link: continue
                    # Also check spans inside the user link
                    if user_link and (string in user_link.stripped_strings): continue
                    
                    if parent.name == 'time' or string == display_time: continue

                # Fallback filters
                if s_text in ['Reply', 'See translation', 'Hidden', 'Hide all replies']: continue
                if s_text == 'Verified': continue
                if s_text == username: continue 
                if re.match(r'^\d+[wmhd]$', s_text): continue 
                if re.match(r'^\d+(?:,\d+)*\s+likes?$', s_text): continue
                if "View" in s_text and "replies" in s_text: continue
                
                text_parts.append(s_text)
            
            text = " ".join(text_parts).strip()
            
            if not text:
                # Fallback: sometimes text is empty or emoji only?
                # If truly empty, it might be an issue.
                pass

            # 6. Reply Count
            reply_count = 0
            # Look for "View X replies" in the node or siblings
            for s in node.stripped_strings:
                 s_norm = " ".join(str(s).split())
                 if "View" in s_norm and "replies" in s_norm:
                     match = re.search(r'View\s+(?:all\s+)?(\d+)\s+replies', s_norm, re.IGNORECASE)
                     if match:
                         reply_count = int(match.group(1))
            
            # Also check siblings if not found inside (button might be outside container)
            if reply_count == 0:
                 pass # Logic preserved from before? Or rely on parents for nested counts?
                 # Actually, usually "View replies" is a SIBLING of the node.
                 # Since we capture a larger container now (User+Replies toggle?), it might be inside stripping.
                 # If we don't find it, we check siblings.
                 curr = node.next_sibling
                 for _ in range(3):
                     if not curr: break
                     if hasattr(curr, 'stripped_strings'):
                        for s in curr.stripped_strings:
                            s_norm = " ".join(str(s).split())
                            if "View" in s_norm and "replies" in s_norm:
                                match = re.search(r'View\s+(?:all\s+)?(\d+)\s+replies', s_norm, re.IGNORECASE)
                                if match:
                                    reply_count = int(match.group(1))
                                    break
                     if reply_count > 0: break
                     curr = curr.next_sibling

            author = CommentAuthor(
                username=username,
                profile_url=profile_url,
                profile_picture_url=pic_url,
                is_verified=is_verified
            )

            return Comment(
                id=comment_id,
                text=text,
                author=author,
                timestamp=display_time,
                timestamp_iso=iso_time,
                likes_count=likes_count,
                reply_count=reply_count,
                permalink=permalink
            )

        except Exception as e:
            print(f"Error extracting comment: {e}")
            return None
