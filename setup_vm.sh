#!/usr/bin/env bash
# Transforme une VM Ubuntu vierge en collecteur IRVE permanent.
# A lancer UNE SEULE FOIS, depuis le dossier du depot cloné :
#   git clone https://github.com/Valentinafry/irve-collecte.git
#   cd irve-collecte && bash setup_vm.sh
set -e

echo "== 1/4  dependances (python, pandas, git) =="
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pandas python3-requests git

echo "== 2/4  identite git =="
git config user.name "collecteur-vm"
git config user.email "collecte@vm.local"

echo "== 3/4  cle de deploiement pour pousser sur GitHub =="
if [ ! -f ~/.ssh/id_ed25519 ]; then
    ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -q
fi
git remote set-url origin git@github.com:Valentinafry/irve-collecte.git
mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null

echo "== 4/4  minuteur (cron) toutes les 10 minutes =="
chmod +x collecte_vm.sh
REPO="$(pwd)"
( crontab -l 2>/dev/null | grep -v collecte_vm.sh ; \
  echo "*/10 * * * * $REPO/collecte_vm.sh" ) | crontab -

echo
echo "=================================================================="
echo ">>> DERNIERE ETAPE MANUELLE (une seule fois) :"
echo ">>> copie la cle ci-dessous, va sur"
echo ">>> https://github.com/Valentinafry/irve-collecte/settings/keys"
echo ">>> clique 'Add deploy key', colle-la, COCHE 'Allow write access',"
echo ">>> puis valide."
echo "------------------------------------------------------------------"
cat ~/.ssh/id_ed25519.pub
echo "------------------------------------------------------------------"
echo ">>> Ensuite teste tout de suite avec :   ./collecte_vm.sh ; tail collecte_vm.log"
echo ">>> Si tu vois 'points ; N changements', c'est bon : la VM collecte"
echo ">>> desormais toute seule, 24h/24."
echo "=================================================================="
