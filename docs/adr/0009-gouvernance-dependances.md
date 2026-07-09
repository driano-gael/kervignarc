# ADR-0009 — Gouvernance des dépendances externes

- **Statut** : Accepté
- **Date** : 2026-07-09
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

Chaque librairie externe ajoutée est à la fois un **gain** (temps, fiabilité) et un **coût
durable** : surface d'attaque (vulnérabilités, typosquatting, chaîne d'approvisionnement),
poids dans l'exécutable PyInstaller, dette de maintenance (mises à jour, abandon amont),
contraintes de licence. Le projet est un **outil interne mono-club** livré en **binaire
auto-contenu**, maintenu par une équipe réduite : une prolifération de dépendances « plaisir »
(ajoutées par réflexe pour un besoin marginal) fragiliserait la sécurité et l'entretien.

Le `guide-architecture.md` §3 imposait déjà de tenir les manifestes à jour (pas de dépendance
« fantôme »), mais **rien** n'encadrait la *décision d'ajouter* une dépendance : sa
justification, sa sûreté, sa traçabilité.

## Options envisagées

- **Encadrer chaque ajout** par des règles de parcimonie, sécurité et documentation (registre). 
- Laisser au jugement individuel : rapide, mais dérive silencieuse (deps superflues, non auditées).
- Interdiction quasi totale de dépendances : irréaliste (FastAPI, React… sont le socle).

## Décision

Toute dépendance externe (runtime **ou** dev, Python **ou** front, directe) est soumise à :

1. **Parcimonie** — pas de librairie « plaisir ». On privilégie la **bibliothèque standard** ou
   un peu de code maison à une lib pour un besoin marginal. Un ajout doit répondre à un **besoin
   réel** et son **poids/transitivité** est pesé. En cas de doute : **on n'ajoute pas**.
2. **Sécurité** — seules des librairies **sûres** : activement maintenues, largement adoptées,
   **sans vulnérabilité connue** (`pip-audit` / `npm audit` **verts**, bloquant en CI),
   **licence compatible** (permissive MIT/BSD/Apache/ISC ; copyleft à valider explicitement),
   installées depuis les **sources officielles** (PyPI/npm). Vigilance typosquatting (paquets
   récents/peu téléchargés).
3. **Documentation** — chaque dépendance est **inscrite au registre** `docs/dependances.md`
   (nom, version, couche, rôle, justification, licence). Un ajout **non documenté** = échec de revue.
4. **Traçabilité** — l'ajout est un **point de revue de PR** explicite ; une dépendance
   **structurante** (framework, moteur, ORM…) fait l'objet d'un **ADR** dédié.

Ces règles complètent (ne remplacent pas) l'obligation de synchroniser les manifestes (§3).
L'**enforcement automatisé** (`pip-audit`, `npm audit`, contrôle de synchro `requirements.txt`)
est porté par la **CI** (EPIC-00 / E00US003).

## Conséquences

- **+** Surface de risque et poids du binaire maîtrisés ; sécurité vérifiable (audits).
- **+** Le « pourquoi » de chaque lib est tracé et opposable en revue et à l'onboarding.
- **−** Léger frottement à l'ajout (justifier + documenter + vérifier l'audit) — assumé.
- **−** Discipline à tenir : le registre doit rester synchrone des manifestes (contrôlé en revue,
  à terme en CI).

## Liens

`guide-architecture.md` §3 et §12 ; `docs/dependances.md` ; ADR-0002 ; ADR-0008 ;
CDC technique §3 ; EPIC-00 (E00US003 — CI bloquante).
