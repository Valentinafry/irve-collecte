#!/usr/bin/env bash
# Collecte IRVE sur VM (appele par cron toutes les 10 min). Meme logique que
# collecte.py, avec commit + push vers GitHub. L'etat courant persiste sur le
# disque de la VM (etat/), donc pas besoin du cache GitHub Actions.
set -uo pipefail
cd "$(dirname "$0")" || exit 1
export GIT_TERMINAL_PROMPT=0

git pull --rebase --quiet origin main 2>/dev/null || true
python3 collecte.py >> collecte_vm.log 2>&1

git add donnees
if ! git diff --cached --quiet; then
    git commit --quiet -m "collecte vm $(date -u +'%Y-%m-%d %H:%M')"
    git pull --rebase --quiet origin main 2>/dev/null || true
    git push --quiet origin main 2>/dev/null || true
fi
