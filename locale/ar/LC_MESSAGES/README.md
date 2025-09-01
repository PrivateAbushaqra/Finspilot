# Arabic Translation Files

This directory contains the Arabic translation files for FinsPilot.

## Files:
- `django.po` - Source translation file with Arabic translations
- `django.mo` - Compiled translation file (binary format)

## Important Notes:
- The `.mo` file is pre-compiled and included in the repository
- This avoids issues with Django's `compilemessages` command on deployment platforms
- The translations are ready to use without additional compilation

## If you need to update translations:
1. Edit `django.po` with new translations
2. Compile locally: `msgfmt -o django.mo django.po`
3. Commit both `.po` and `.mo` files

## Translation Status:
✅ 400+ Arabic terms translated
✅ Complete UI coverage
✅ Ready for production deployment
