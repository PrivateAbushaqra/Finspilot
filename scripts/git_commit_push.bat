@echo off
git add -A
git commit -m "chore(i18n): add translations; fix templates; remove temporary translation-check helpers" || echo no changes to commit
git push origin main || echo push failed