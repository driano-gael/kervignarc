# Suivi des US — état d'avancement

> **Ce fichier est le point de reprise.** Quand l'utilisateur dit « **reprend les US** », l'assistant
> lit ce tableau : il y trouve ce qui est **fait** (mergé sur `main`), et **la prochaine US** à
> prendre. La séquence de référence est celle de [`stories/README.md`](../stories/README.md) (jalons
> de valeur J0→J4). Le détail de chaque US est dans `stories/Exx-*.md`.
>
> **Règle de mise à jour** : une US passe à ✅ **dans son propre dernier commit, la revue
> (`/revue-us`) faite et poussée** — sans attendre la confirmation « c'est mergé ». C'est sûr parce
> que cette mise à jour **voyage avec le diff de l'US** : elle n'atteint `main` qu'**au merge de la
> PR**. Donc sur `main` ce tableau reste **toujours vrai** (le ✅ y apparaît pile au merge) ; sur la
> branche, il est optimiste d'un cran — c'est le livrable. Le même commit pointe la 🎯 suivante. En
> cas de doute au moment de reprendre, recouper avec `git log main --first-parent` / `git branch -r`.

**Dernière mise à jour : 20/07/2026** · **50 US livrées** · dernière : `E07US006`.

---

## 🎯 Prochaine US

> **`E07US009` — Suivre le déroulé du tour en direct** *(J1, tranche 2 — backend + ADR)*
>
> `E07US006` (tranche 1 : suivre des archers — recherche, liste mémorisée en `localStorage`, carte
> cible/position/départ, live) est **terminée et poussée** (revue faite). La suite directe est
> `E07US009`, la **tranche 2** : exposer publiquement le **déroulé du tour** — un endpoint public de
> suivi + DTO restreint (volées, valeurs, statut **en attente / validé**, E01US015) + événement
> WebSocket typé, et l'affichage de la feuille de marque live dans la carte. **Décision structurante ⇒
> ADR** (elle expose au public des scores provisoires non validés). Dépend d'E07US006, E04US002,
> E01US015. Détail : [`stories/E07-affichage-public.md`](../stories/E07-affichage-public.md).

---

## J0 — Walking skeleton — ✅ **terminé (12/12)**

| US | Titre | État |
|---|---|---|
| E00US001 | Initialiser le monorepo | ✅ |
| E00US002 | Configurer la qualité (ruff, mypy, ESLint…) | ✅ |
| E00US003 | CI bloquante | ✅ |
| E00US004 | Squelette de couches + garde-fou d'imports | ✅ |
| E00US005 | Composition root minimale | ✅ |
| E00US006 | SQLite (WAL) + migration initiale | ✅ |
| E00US007 | File d'écriture + writer unique | ✅ |
| E00US008 | WebSocket + diffusion post-commit | ✅ |
| E00US009 | Repository + endpoint bout-en-bout | ✅ |
| E00US010 | Shell React | ✅ |
| E00US011 | Tranche verticale démontrable | ✅ |
| E00US012 | Exécutable de dev (FastAPI sert le front) | ✅ |

## J1 — Tournoi de qualification de bout en bout — 🔶 **en cours (37/46)**

| Seq | US | Titre | État |
|---|---|---|---|
| 13 | E01US001 | Créer un tournoi | ✅ |
| 14 | E10US002 | Accès administrateur protégé | ✅ |
| 15 | E10US001 | Consultation publique ouverte | ✅ |
| 16 | E01US002 | Éditer / lister les tournois | ✅ |
| 17 | E01US003 | Gérer les catégories (CRUD) | ✅ |
| 18 | E01US004 | Pré-charger les catégories FFTA salle | ✅ |
| 19 | E01US013 | Catégorie : éligibilité multi-âges | ✅ |
| 20 | E01US005 | Gérer les blasons | ✅ |
| 21 | E01US014 | Blason : valeurs de score admises | ✅ |
| 22 | E01US006 | Associer catégorie ↔ blason | ✅ |
| 23 | E01US007 | Définir un gabarit de salle | ✅ |
| 24 | E01US008 | Réutiliser / ajuster un gabarit | ✅ |
| 25 | E01US009 | Définir un barème de qualification | ✅ |
| 26 | E01US015 | Grain de validation d'une phase | ✅ |
| 27 | E01US010 | Définir le tarif par départ | ✅ |
| 28 | E02US001 | Gérer le référentiel clubs | ✅ |
| 29 | E02US002 | Créer un archer | ✅ |
| 30 | E02US003 | Éditer / supprimer un archer | ✅ |
| 31 | E02US004 | Configurer les départs (créneaux) | ✅ |
| 32 | E02US009 | Inscrire un archer sur des départs | ✅ |
| 33 | E00US014 | Outiller les tests du front | ✅ |
| 34 | E08US001 | Calculer le montant dû | ✅ |
| 35 | E03US001 | Placement automatique & plan de cibles | ✅ |
| 36 | E03US004 | Ajuster le placement (glisser-déposer) | ✅ |
| 37 | E10US003 | Scoreurs : définition & session | ✅ |
| 38 | E09US008 | Imprimer QR de cible & codes scoreurs | ✅ |
| 39 | E04US001 | Rattacher une tablette à sa cible (QR) | ✅ |
| 40 | E10US007 | Poste de cible : saisir sans s'identifier | ✅ |
| 41 | E04US002 | Saisie de qualification en temps réel | ✅ |
| 42 | E04US009 | Diffusion live & résilience réseau | ✅ |
| 43 | E12US001 | Superviser les postes de saisie | ✅ |
| 44 | E06US001 | Classement de qualification | ✅ |
| 45 | E07US001 | Vues publiques : classements, plans, live | ✅ |
| 46 | E07US006 | Suivre des archers : ma journée *(tranche 1, front)* | ✅ |
| **46b** | **E07US009** | **Suivre le déroulé du tour en direct** *(tranche 2, backend + ADR)* | 🎯 **suivante** |
| 47 | E10US005 | Journal d'audit métier | ✅ *(fait en avance)* |
| 48 | E12US007 | Alerter par calcul d'impact | ⬜ |
| 49 | E08US002 | Suivi des paiements | ⬜ |
| 50 | E12US005 | Afficher la complétude du tournoi | ⬜ |
| 51 | E12US006 | Rechercher un archer depuis n'importe où | ⬜ |
| 52 | E02US005 | Détecter et fusionner les doublons | ⬜ |
| 53 | E02US006 | Contrôler les quotas | ✅ *(fait en avance)* |
| 54 | E09US001 | Socle PDF & feuille de marque | ✅ *(fait en avance)* |
| 55 | E09US003 | Listes imprimables (placement, club, paiement) | ⬜ |
| 56 | E11US001 | Release, base et mise en réseau | ⬜ |
| 57 | E11US003 | Sauvegarde & archive | ⬜ |

## J2 — Duels simples + bascule de tour — ⬜ **non commencé (0/15)**

| Seq | US | Titre | État |
|---|---|---|---|
| 58 | E05US001 | Séquence de phases | ⬜ |
| 59 | E05US003 | Politiques injectables & assemblage | ⬜ |
| 60 | E05US005 | Arbre d'élimination directe | ⬜ |
| 61 | E03US006 | Contrainte ≥ 2 clubs par cible | ⬜ |
| 62 | E03US009 | Placer les duellistes côte à côte | ⬜ |
| 63 | E04US013 | Saisie en duels | ⬜ |
| 64 | E04US015 | Gérer abandon / disqualification | ⬜ |
| 65 | E12US004 | Tracer un forfait | ⬜ |
| 66 | E12US008 | Cycle de vie d'un départ | ⬜ |
| 67 | E08US005 | Rembourser une inscription payée annulée | ⬜ |
| 68 | E12US002 | Lancer un tour (feu vert + lancement) | ⬜ |
| 69 | E04US018 | Afficher la prochaine cible après validation | ⬜ |
| 70 | E07US008 | Vue publique des affectations du prochain tour | ⬜ |
| 71 | E06US003 | Barrage de tir pour places décisives | ⬜ |
| 72 | E06US004 | Podium des duels & agrégation des rangs | ⬜ |

## J3 — Placement intégral 1→N + écran de salle — ⬜ **non commencé (1/11)**

| Seq | US | Titre | État |
|---|---|---|---|
| 73 | E05US010 | Placement intégral 1→N | ⬜ |
| 74 | E05US015 | Big Shoot Off | ⬜ |
| 75 | E05US018 | Oracle 120 (rejeu + comparaison) | ⬜ |
| 76 | E06US006 | Classement intégral 1→N & profondeur | ⬜ |
| 77 | E03US007 | Contrainte séparation catégorie/blason | ⬜ |
| 78 | E09US005 | Classements PDF | ⬜ |
| 79 | E00US013 | Factoriser les briques d'UI partagées | ⬜ |
| 80 | E01US016 | Définir l'identité visuelle du tournoi | ⬜ |
| 81 | E07US004 | Écran de salle : déroulé auto & pilotage | ⬜ |
| 82 | E07US005 | Vue tableaux/arbres live | ⬜ |
| 83 | E05US019 | Enregistrer une séquence comme modèle | ⬜ |
| — | E00US015 | Ossature de navigation admin (coquille) | ✅ *(fait en avance — ajout 18/07)* |

## J4 — Confort, richesse & robustesse — ⬜ **non commencé (0/8)**

| Seq | US | Titre | État |
|---|---|---|---|
| 84 | E02US007 | Importer un fichier inscript'arc | ⬜ |
| 85 | E01US011 | Presets de barèmes multi-phases | ⬜ |
| 86 | E01US012 | Gérer plusieurs gabarits | ⬜ |
| 87 | E03US010 | Générer / éditer le déroulé horaire | ⬜ |
| 88 | E09US007 | Déroulé horaire imprimable | ⬜ |
| 89 | E05US016 | Routing repêchage-réintégration (WA) | ⬜ |
| 90 | E11US006 | Restauration & arrêt propre | ⬜ |
| 91 | E10US006 | Modifier le mot de passe admin | ⬜ |

## Ajouts de l'entretien du 18/07/2026 — ⬜ **à planifier (1/10)**

> Non renumérotés dans les jalons ci-dessus (séquence indicative, à insérer au bon rang). Cf.
> [`stories/README.md`](../stories/README.md) § « Ajouts » et ADR-0026/0027/0028.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US015 | Coquille de navigation admin | J3 | ✅ |
| E00US016 | Écrans admin : liste/fiche & référentiels | J3 | ⬜ *(définie en `stories/`, non implémentée)* |
| E01US017 | Cycle de vie enrichi (7 statuts) | J1 | ⬜ *(idem)* |
| E01US018 | Vocabulaire de score configurable | J1 | ⬜ *(idem)* |
| E01US019 | Capacité de cible non bornée | J1→J3 | ⬜ *(idem)* |
| E02US010 | Horaire de départ HH:MM obligatoire | J1 | ⬜ *(idem)* |
| E13US001 | Abstraction participant | J2 | ⬜ |
| E13US002 | Composer les équipes d'un tournoi | J2 | ⬜ |
| E13US003 | Scoring d'équipe (politique injectable) | J2 | ⬜ |
| E13US004 | Placement, saisie & classement par équipe | J2→J3 | ⬜ |

## Ajout du 20/07/2026 — ⬜ **à planifier (0/1)**

> Issu de l'échange sur le modèle d'entrée de l'appli (une seule SPA, trois expériences). Cf.
> [`stories/E00-socle.md`](../stories/E00-socle.md) § E00US017.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US017 | Écran d'accueil : choisir son appareil / rôle | J3 | ⬜ *(définie en `stories/`, non implémentée — ADR à l'implémentation)* |

## US caduque

| US | Titre | Motif |
|---|---|---|
| E10US004 | ~~Habiliter un scoreur sur plusieurs cibles~~ | Sans objet depuis `D-12`/`D-13` (scoreur itinérant). Conservée comme trace. |

---

## Légende

- ✅ mergé sur `main` · 🎯 prochaine US à prendre · 🔶 jalon en cours · ⬜ à faire
- *« fait en avance »* : US traitée avant son rang de séquence (dépendance ou opportunité).
- *« définie en `stories/`, non implémentée »* : le fichier de spec existe (créé à l'entretien du
  18/07) mais aucun code n'est livré — ne pas confondre présence en `stories/` et US faite.
