# Security Policy

## Supported Versions

InstaHarvest is currently supporting the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 2.5.x   | :white_check_mark: |
| 2.4.x   | :white_check_mark: |
| < 2.4   | :x:                |

We recommend always using the latest version available on [PyPI](https://pypi.org/project/instaharvest/).

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in InstaHarvest, please report it responsibly.

### How to Report

1. **Email**: Send details to [kelajak054@gmail.com](mailto:kelajak054@gmail.com)
2. **GitHub Issues**: For non-critical issues, you can also [open an issue](https://github.com/mpython77/insta-harvester/issues)

### What to Include

When reporting a vulnerability, please include:

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if available)
- Your contact information

### What to Expect

- **Initial Response**: Within 48 hours of your report
- **Status Updates**: We'll keep you informed as we investigate and address the issue
- **Resolution Timeline**: We aim to resolve critical vulnerabilities within 7 days
- **Credit**: If you wish, we'll acknowledge your contribution in the fix release notes

### Security Best Practices

When using InstaHarvest:

1. **Session Files**: Keep your `instagram_session.json` file secure and never commit it to version control
2. **Rate Limiting**: Always use `ScraperConfig` with appropriate delays to avoid Instagram rate limiting
3. **Account Safety**: Use dedicated accounts for automation, not your personal account
4. **Updates**: Regularly update to the latest version to get security patches
5. **Terms of Service**: Follow Instagram's Terms of Service and use responsibly

## Disclosure Policy

- We request that you do not publicly disclose the vulnerability until we've had a chance to address it
- Once fixed, we'll coordinate with you on the disclosure timeline
- We'll credit researchers who responsibly disclose vulnerabilities (unless you prefer to remain anonymous)

Thank you for helping keep InstaHarvest and its users safe!
