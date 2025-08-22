# Captain Spire - Teams App Package

## Files Needed
1. ✅ `manifest.json` - Configuration file (created)
2. ⏳ `color.png` - 192x192px color icon (you'll add this)
3. ⏳ `outline.png` - 32x32px outline icon (you'll add this)

## Image Requirements

### color.png (192x192 pixels)
- Full color version of Captain Spire logo/icon
- PNG format with transparent background preferred
- Will be shown in app listings and cards

### outline.png (32x32 pixels)
- Simplified outline version
- Should work on light and dark backgrounds
- Used in app bars and smaller UI elements

## How to Create the Package

Once you have your images:

```bash
# 1. Add your images to this folder
cp /path/to/your/captain-spire-color-192.png ./color.png
cp /path/to/your/captain-spire-outline-32.png ./outline.png

# 2. Create the zip package
zip -r captain-spire.zip manifest.json color.png outline.png

# 3. Verify the package
unzip -l captain-spire.zip
# Should show:
# - manifest.json
# - color.png
# - outline.png
```

## Submitting to IT Admin

Send them:
1. The `captain-spire.zip` file
2. The setup documentation (see CAPTAIN_SPIRE_IT_DOCS.md)
3. Any security/compliance requirements

## Testing Locally First

Before submitting, you can test in Teams Developer Portal:
1. Go to https://dev.teams.microsoft.com/apps
2. Import an app → Import an existing app
3. Select your captain-spire.zip
4. Test in your personal Teams account

## Questions for IT Admin

They'll need to know:
- Where will the bot be hosted? (Azure, on-premises, external)
- What data does it access? (Google Drive documents)
- Authentication method? (API key, Azure AD, etc.)
- Which teams/users should have access?