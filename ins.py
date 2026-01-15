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
    results = orchestrator.scrape_complete_profile_advanced(
        'anoshka._.__',
        parallel=3,
        save_excel=True,
        scrape_comments=True,          # Enable comment scraping
        max_comments_per_post=100,     # Limit per post (None = all)
        include_replies=True           # Include reply threads
    )

    print(f"Total comments: {results.get('comments_data', 'N/A')}")

if __name__ == '__main__':
    # On Windows, multiprocessing requires this protection
    main()
