#!/usr/bin/env bash
# Collecte IRVE sur VM (cron toutes les 10 min) : collecte, commit, push.
# PAS de `git pull` en DÉBUT de script : la VM est seul écrivain, elle n'a
# rien à récupérer, et un pull au début pouvait télécharger une nouvelle
# version de CE script pendant son exécution (script auto-modifié → bash
# corrompu, collecte jamais atteinte). En cas de divergence (rare), on ne
# rebase/retry qu'APRÈS un échec de push, une fois le travail déjà fait.
set -uo pipefail
cd "$(dirname "$0")" || exit 1
export GIT_TERMINAL_PROMPT=0
git config core.fileMode false            # ignore les bits exécutables

python3 collecte.py >> collecte_vm.log 2>&1
python3 collecte_nl.py >> collecte_vm.log 2>&1
python3 collecte_no.py >> collecte_vm.log 2>&1      # dormant sans cle NOBIL
python3 collecte_at.py >> collecte_vm.log 2>&1      # photo quotidienne AT
python3 collecte_de.py >> collecte_vm.log 2>&1      # registre DE par millesime

for d in donnees donnees_nl donnees_no donnees_at donnees_de; do
    [ -d "$d" ] && git add "$d"
done
if ! git diff --cached --quiet; then
    git commit --quiet -m "collecte vm $(date -u +'%Y-%m-%d %H:%M')"
    if ! git push --quiet origin main 2>/dev/null; then
        git rebase --abort 2>/dev/null || true
        git pull --rebase --quiet origin main 2>/dev/null || true
        git push --quiet origin main 2>/dev/null || true
    fi
fi
