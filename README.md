# trust.scottstcgbinder.com

Public legal and support pages for **Scott’s TCG Binder** (also referred to as Bindovo).

## Public pages

| Page | Path | URL |
|------|------|-----|
| Home | `dist/index.html` | https://trust.scottstcgbinder.com/ |
| End User License Agreement | `dist/terms/index.html` | https://trust.scottstcgbinder.com/terms/ |
| Privacy Policy | `dist/privacy/index.html` | https://trust.scottstcgbinder.com/privacy/ |
| Support | `dist/support/index.html` | https://trust.scottstcgbinder.com/support/ |

## Repository layout

```text
scotts-tcg-trust/
├── README.md
├── .gitignore
├── wrangler.jsonc
└── dist/
    ├── index.html                      # Site home / page index
    ├── assets/
    │   ├── mobile_header.png           # Banner used on every HTML page
    │   └── scottstcgbinder.png         # Brand artwork
    ├── privacy/
    │   └── index.html                  # Privacy Policy
    ├── support/
    │   └── index.html                  # Support
    └── terms/
        └── index.html                  # Apple Standard EULA
```

## Assets

| File | Use |
|------|-----|
| `dist/assets/mobile_header.png` | Top banner on every HTML page |
| `dist/assets/scottstcgbinder.png` | Brand artwork |

## Notes

- Published HTML lives under `dist/`.
- The terms page reproduces Apple’s Standard Licensed Application End User License Agreement. Official Apple source: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
- Enter `https://trust.scottstcgbinder.com/privacy/` as the App Store Connect Privacy Policy URL.
