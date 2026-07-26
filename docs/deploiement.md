# Déploiement du jour J — build, base et mise en réseau

> **US : E11US001** — « Release, base et mise en réseau ». Objectif : déployer et démarrer
> l'application le jour du tournoi **sans installation ni internet**, sur un réseau local avec
> ~30 tablettes. Ce document est le CA « procédure réseau » de l'US.

L'application se déploie comme **un seul exécutable auto-contenu** : il embarque le front React,
les migrations de base de données et la génération PDF. Aucun Python, Node ni dépendance à
installer sur la machine du jour J.

---

## 1. Fabriquer le binaire (poste de préparation)

Sur un poste **de développement** (Python 3.13 + Node ≥ 20, venv dev installé), depuis `backend/` :

```bash
python build_release.py            # build front (npm run build) puis PyInstaller
python build_release.py --no-build # réutilise frontend/dist/ si déjà à jour
```

Sortie : **`backend/dist/kervignarc.exe`** (Windows) — un unique fichier. C'est lui, et lui seul,
qu'on copie sur la machine du jour J (clé USB, partage réseau…).

> **Ce que le binaire embarque** (via `kervignarc.spec`) : `frontend/dist/` (SPA), `migrations/`
> (schéma Alembic), les ressources ReportLab (PDF) et la pile mDNS `zeroconf`. Le détail des
> inclusions est commenté dans la spec.

## 2. Premier lancement (machine du jour J)

Double-cliquer `kervignarc.exe` (ou le lancer en console pour voir les adresses affichées). Au
**premier lancement** :

- le fichier de base **`kervignarc.db`** est créé **à côté de l'exécutable** (pas dans un dossier
  temporaire) et **toutes les migrations** sont appliquées — la base est prête, vide ;
- le serveur écoute sur le **port fixe `8000`**, sur **toutes les interfaces** réseau ;
- la console affiche les deux adresses d'accès, p. ex. :

  ```
  -> Serveur prêt sur http://192.168.1.10:8000  et  http://kervignarc.local:8000
  ```

Aux lancements suivants, la base existante est **conservée** (les migrations non appliquées le
seraient si le binaire était mis à jour). Pour repartir d'une base neuve : fermer l'appli et
supprimer/déplacer `kervignarc.db`.

> **Où placer l'exe ?** Dans un dossier **inscriptible** (ex. `C:\kervignarc\`), **jamais** dans
> `C:\Program Files\` (droits en lecture seule) : la base s'écrit à côté de l'exe.

## 3. Mettre en réseau les tablettes

Le jour J, **pas d'internet** : on isole un réseau local dédié.

1. **Routeur / point d'accès dédié.** Brancher un routeur Wi-Fi (ou point d'accès) autonome.
   Y connecter la machine serveur **en filaire** de préférence (stabilité), et les ~30 tablettes
   en Wi-Fi. Aucune box internet n'est nécessaire.
2. **Machine serveur.** Lancer `kervignarc.exe` dessus. Noter l'**IP locale** affichée
   (ex. `192.168.1.10`). Idéalement, réserver cette IP dans le routeur (bail DHCP fixe) pour
   qu'elle ne change pas d'un jour à l'autre.

   > ⚠️ **Une seule connexion réseau active sur la machine serveur.** Le serveur détecte son
   > IP via l'**interface de la route par défaut**. Si la machine a, en plus du routeur dédié,
   > une **autre** connexion active (Wi-Fi maison, partage 4G, VPN), l'IP affichée — et le nom
   > `kervignarc.local` annoncé — peut pointer vers la **mauvaise** interface, injoignable par les
   > tablettes. **Désactiver le Wi-Fi et tout VPN** sur la machine serveur si elle est branchée en
   > filaire au routeur dédié. En cas de doute, vérifier que l'IP affichée est bien dans la plage
   > du routeur (ex. `192.168.1.x`).
3. **Tablettes.** Ouvrir le navigateur et saisir **l'une** des deux adresses :
   - par IP : `http://192.168.1.10:8000` — **toujours** fonctionnel ;
   - par nom : `http://kervignarc.local:8000` — plus simple à dicter, publié par le serveur en
     **mDNS** (voir ci-dessous).

### Accès par nom `kervignarc.local` (mDNS)

Le serveur s'**annonce lui-même** sur le réseau local sous le nom `kervignarc.local` via le
protocole **mDNS** (« Bonjour » d'Apple, « Avahi » sous Linux) — rien à configurer sur le routeur.
La résolution de ce nom est native sur **iOS/iPadOS et macOS**, et sur **Android récent** ; la
plupart des tablettes le résolvent donc sans réglage.

> ⚠️ **L'accès par IP reste la référence.** Si une tablette ne résout pas `kervignarc.local`
> (Android ancien, pare-feu du routeur bloquant le multicast, réseau capricieux), utiliser
> **l'adresse IP** — elle marche partout. L'annonce mDNS est un confort **best-effort** : si la
> pile réseau la refuse, le serveur démarre quand même et reste joignable par IP (aucun blocage).

## 4. Pièges connus

- **`http://`, pas `https://`.** Le déploiement local est en clair (pas de certificat). Certaines
  API navigateur « *secure-context only* » sont indisponibles hors `https`/`localhost` — le front
  en tient déjà compte (repli sans WebCrypto), mais rester en `http://…:8000`.
- **Port `8000` occupé.** Si une autre application le tient, fermer celle-ci : le port est fixe
  (le front et les tablettes le visent).
- **Pare-feu Windows.** Au premier lancement, Windows peut demander d'autoriser l'accès réseau de
  `kervignarc.exe` : **accepter** (réseaux privés), sinon les tablettes ne joignent pas le serveur.
- **Dossier en lecture seule.** Si l'exe est dans un dossier non inscriptible, la création de
  `kervignarc.db` échoue au démarrage — le placer dans un dossier inscriptible (cf. §2).
