# Security Policy

## Supported versions

| Version | Status |
| ------- | ------ |
| 2.x     | Active. Security patches accepted. |
| < 2.0   | Unsupported. |

The latest release is on [PyPI](https://pypi.org/project/instaharvest/).
We do not maintain a long list of patched minor versions; users should
update to the most recent 2.x release to receive fixes.

## Reporting a vulnerability

Please **do not** file a public GitHub issue for security problems.
Instead, email <kelajak054@gmail.com> with:

- a clear description of the issue,
- steps (or a minimal proof of concept) to reproduce,
- the version/commit you tested against,
- whatever impact assessment you have,
- whether you would like to be credited and how.

We aim to acknowledge reports within 5 business days. Coordinated
disclosure timelines are negotiable; we will not credit you without
your consent.

## Threat model — what this library exposes

InstaHarvest drives a real Instagram session through a browser. Anyone
who can read your filesystem while it is running can read your session.
You are responsible for the operational hygiene around it. In
particular:

### Session data is sensitive

`instagram_session.json` (and any encrypted variant) contains live
Instagram authentication cookies. Anyone with that file can act as you
on Instagram until the session is invalidated. Treat it like a
password file:

- never commit it to a repository (it is in `.gitignore`; keep it
  there);
- restrict its filesystem permissions on shared hosts;
- delete it when you are done.

### Temporary cookie files

Older releases (≤ 2.16) wrote a Netscape-format cookie file under
`/tmp` for `yt-dlp` and never removed it. That bug is fixed in
the v3 infrastructure (`FileSessionStore.temp_cookie_file()` always
unlinks on context-manager exit, including on exception) and in the
legacy `downloader.py` path (try/finally cleanup). If you have older
output directories from earlier runs, audit them for leftover
`ig_cookies_*.txt` files and remove them.

### Proxy lists and `proxy.load_from_url`

The legacy `ProxyManager.load_from_url(url)` fetches a proxy list from
an arbitrary URL with no validation. If the URL is attacker-controlled,
your traffic can be silently routed through their infrastructure. Only
load proxy lists from sources you trust.

### Anti-detection capabilities

The legacy tree contains modules whose explicit purpose is to evade
Instagram's automated abuse detection: `stealth.py` (fingerprint
masking, humanised input), `captcha_solver.py` (paid third-party
CAPTCHA bypass), `proxy.py` (rotating proxies), and `session_manager.py`
(multi-account rotation). These features are off by default in v3 and
must be opted into. Using them is your decision and your legal risk;
we accept security reports about *implementation flaws* in these
modules, but a report whose only finding is "this library can scrape
Instagram" is not a vulnerability.

### Debug snapshots

Both legacy and v3 may write HTML snapshots of pages they could not
parse, to help you diagnose breakage. Those snapshots can contain
content you were logged in to view (DM previews, private posts, etc.).
The default snapshot directory is in `.gitignore`; if you change it,
make sure your new path is also ignored.

## Operational guidance

- **Use a dedicated Instagram account.** Automation increases the
  chance of bans. Don't risk your personal or business primary
  account.
- **Use realistic pacing.** The defaults in v3 (`RateLimitConfig`)
  err on the conservative side. Lowering them aggressively is the
  single most reliable way to get rate-limited or banned.
- **Update regularly.** Instagram changes its DOM and JSON shapes
  often. We patch selectors and parsers in response; running an old
  release is the most common source of user-visible breakage.
- **Pin a known-good version in production.** v3 is the supported
  API surface; legacy v2 is kept for backwards compatibility but
  is not the path forward.

## Disclosure policy

- We ask that you do not publicly disclose a vulnerability before we
  have had a chance to address it.
- Once a fix is released, we will reference your report in the
  release notes (with credit, if you accept it).
- We do not currently offer monetary rewards for security reports.

Thank you for helping keep InstaHarvest safer for everyone who uses it.
