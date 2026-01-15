try:
    from instaharvest import (
        CommentScraper, 
        ScraperConfig, 
        CommentData, 
        Comment, 
        CommentAuthor, 
        PostCommentsData, 
        Collaborator
    )
    print("Imports successful!")
except Exception as e:
    print(f"Import failed: {e}")
