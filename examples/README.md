# InstaHarvest Examples

## Quick Start (v4.0)

```python
from instaharvest import InstaHarvest, Settings

with InstaHarvest(Settings.default()) as ih:
    profile = ih.profile.scrape("instagram")
    print(profile.followers, profile.is_verified)
```

See the main README.md and ARCHITECTURE.md for the full API reference.
