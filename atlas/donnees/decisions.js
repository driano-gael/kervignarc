/* GÉNÉRÉ par `cd backend && python -m atlas` — ne pas éditer à la main.
   Toute modification sera écrasée à la régénération et rejetée par la CI. */
window.ATLAS = window.ATLAS || {};
window.ATLAS.decisions = {
 "decisions": [
  {
   "amende_par": [],
   "date": "2026-07-08",
   "date_brute": "2026-07-08",
   "extrait": "Nous adoptons les Architecture Decision Records, stockés dans docs/adr/, au format court (contexte / options / décision / conséquences). Toute décision structurante donne lieu à un ADR ; un ADR accepté est immuable et remplacé par un nouvel ADR en cas d'évolution.",
   "fichier": "docs/adr/0001-adopter-les-adr.md",
   "identifiant": "0001",
   "liens": [],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Adopter les ADR",
   "us": []
  },
  {
   "amende_par": [],
   "date": "2026-07-08",
   "date_brute": "2026-07-08",
   "extrait": "- Backend : Python FastAPI, réutilisant/étendant le domaine existant. - Frontend : React + TypeScript (SPA, Vite), servi en statique par le backend. - Base : SQLite (fichier local). - Topologie : serveur-autoritaire sur LAN ; le serveur tourne sur le PC portable de l'organisateur, connecté à un routeur wifi dédié ; les clients sont en navigateur (BYOD). - Temps réel : WebSocket. - Livraison : exécutable auto-contenu (PyInstaller), lancement double-clic ; outil mono-club. - Tolérance réseau : coupures brèves seulement (file d'attente côté front + reconnexion), pas d'offline-first.",
   "fichier": "docs/adr/0002-stack-et-topologie.md",
   "identifiant": "0002",
   "liens": [],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Stack technique & topologie de déploiement",
   "us": []
  },
  {
   "amende_par": [],
   "date": "2026-07-08",
   "date_brute": "2026-07-08",
   "extrait": "- Architecture hexagonale ciblée sur le domaine : domain/ est pur (aucune dépendance à FastAPI, SQLAlchemy, Pydantic ni aux couches externes). Les dépendances pointent vers le domaine. - Le domaine expose des ports (interfaces : repositories, stores) ; l'infrastructure fournit les adapters. - Composition root explicite : le câblage des adapters et des politiques se fait à la main dans bootstrap/ + main.py, sans conteneur DI. - Les Depends FastAPI restent cantonnés à la couche API. - Pragmatisme assumé hors du domaine (infrastructure simple, pas de sur-abstraction).",
   "fichier": "docs/adr/0003-architecture-hexagonale.md",
   "identifiant": "0003",
   "liens": [],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Architecture hexagonale ciblée + composition root explicite",
   "us": []
  },
  {
   "amende_par": [
    "0011",
    "0027",
    "0045",
    "0046",
    "0066"
   ],
   "date": "2026-07-08",
   "date_brute": "2026-07-08",
   "extrait": "Le moteur manipule une séquence de phases. Chaque phase de tableau reçoit un jeu de politiques injectables, interfaces du domaine avec plusieurs implémentations : | Politique | Rôle | Variantes | |---|---|---| | Routage route(perdant, tour, contexte) | destination du perdant | cascade de placement · repêchage-réintégration · élimination sèche | | Barème | calcul/victoire | cumul · sets 4 pts · finales 6 pts · shoot-off · Big Shoot Off | | Seeding | composition de l'arbre | serpent, arrondi 2^k | | Byes | exempts si effectif ≠ 2^k | aux mieux classés (défaut) | | Départage | égalités | nb de 10/9 · shoot-off plus près du centre | | Profondeur | jusqu'où classer | 1→N (défaut) · top N + […]",
   "fichier": "docs/adr/0004-moteur-de-phases-politiques.md",
   "identifiant": "0004",
   "liens": [],
   "portage": [
    {
     "chemin": "backend/bootstrap/composition.py",
     "existe": true,
     "symboles": [
      "tiebreak",
      "routing"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "TypePhase",
      "config",
      "SourcePhase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/politiques.py",
     "existe": true,
     "symboles": [
      "FamillePolitique",
      "Protocol",
      "Routing",
      "Scoring",
      "Seeding",
      "Byes",
      "Tiebreak",
      "Depth",
      "Aggregation",
      "PolitiquesPhase",
      "RegistrePolitiques",
      "config"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/tableau.py",
     "existe": true,
     "symboles": [
      "Protocol"
     ],
     "symboles_absents": [
      "Protocol"
     ],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Moteur de phases à politiques injectables",
   "us": [
    "E05US003"
   ]
  },
  {
   "amende_par": [
    "0010",
    "0037"
   ],
   "date": "2026-07-08",
   "date_brute": "2026-07-08",
   "extrait": "- Pas d'accès DB asynchrone. FastAPI reste async au niveau I/O réseau / WebSocket / connexions, mais la couche de persistance est synchrone (SQLAlchemy sync). - Écritures via une file (queue) consommée par un unique writer : - les handlers publient une commande d'écriture dans la file et attendent son résultat (future) ; - un seul worker exécute les écritures séquentiellement → sérialisation native, pas de contention, pas de database is locked ; - le point d'écriture unique est l'endroit naturel pour journaliser l'audit et déclencher la diffusion WebSocket après commit. - Lectures : directes/synchrones, exécutées hors de la boucle événementielle (threadpool/executor) pour ne pas la bloquer […]",
   "fichier": "docs/adr/0005-async-et-sqlite.md",
   "identifiant": "0005",
   "liens": [],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Accès SQLite : lectures synchrones + file d'écriture (single-writer)",
   "us": []
  },
  {
   "amende_par": [
    "0073"
   ],
   "date": "2026-07-08",
   "date_brute": "2026-07-08",
   "extrait": "- Concepts métier nommés en français, tels que la FFTA : Archer, Cible, Blason, Volee, Fleche, Duel, Set, Barrage, Depart, Categorie, Placement, Tableau, Phase. - Code technique / infrastructure en anglais : Repository, Adapter, Service, Router, Store, Factory… - Cohérence obligatoire du terme entre domaine, API, UI et documentation. - Un glossaire (docs/glossaire.md) fait référence. - Le prototype est renommé en conséquence (Player → Archer, lettre/idCible → position/cible).",
   "fichier": "docs/adr/0006-ubiquitous-language.md",
   "identifiant": "0006",
   "liens": [],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Vocabulaire : métier en français, technique en anglais",
   "us": []
  },
  {
   "amende_par": [],
   "date": "2026-07-08",
   "date_brute": "2026-07-08",
   "extrait": "Chaque couche définit sa propre famille d'exceptions ; le mapping vers une réponse HTTP normalisée se fait uniquement dans l'adapter API. Le domaine ignore HTTP. | Couche | Famille | Exemple | → HTTP | |---|---|---|---| | Domaine | DomainError | PlacementInvalide, PhaseMalAlimentee | 422 (code métier) | | Application | ApplicationError | TournoiIntrouvable | 404 / 409 | | Infrastructure | InfrastructureError | échec DB / IO | 500 (message générique) | | API | ApiError | validation d'entrée | 400 | - Format d'erreur uniforme côté client : { code, message, details? }. - Les messages internes ne fuient pas : détail technique journalisé côté serveur, message générique renvoyé au client. - Les […]",
   "fichier": "docs/adr/0007-erreurs-par-couche.md",
   "identifiant": "0007",
   "liens": [],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Erreurs typées par couche",
   "us": []
  },
  {
   "amende_par": [
    "0072"
   ],
   "date": "2026-07-09",
   "date_brute": "2026-07-09",
   "extrait": "Pour ce projet, l'outillage est : - Python (backend) : environnement virtuel python -m venv .venv + pip. pyproject.toml reste la source de vérité des dépendances ; requirements.txt est régénéré (jamais édité à la main) via pip freeze (versions épinglées) et versionné. - Frontend : npm + Vite ; package.json + package-lock.json (lockfile) versionnés. Les principes du guide restent valables : source de vérité unique des dépendances, lockfiles versionnés, aucune dépendance « fantôme », versions figées. Seuls les gestionnaires changent. Cette décision est réversible : une migration vers uv/pnpm reste possible ultérieurement (nouvel ADR remplaçant celui-ci) sans impact sur l'architecture […]",
   "fichier": "docs/adr/0008-outillage-npm-venv.md",
   "identifiant": "0008",
   "liens": [],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Outillage : npm + venv/pip au lieu de pnpm + uv",
   "us": [
    "E00US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-09",
   "date_brute": "2026-07-09",
   "extrait": "Toute dépendance externe (runtime ou dev, Python ou front, directe) est soumise à : 1. Parcimonie — pas de librairie « plaisir ». On privilégie la bibliothèque standard ou un peu de code maison à une lib pour un besoin marginal. Un ajout doit répondre à un besoin réel et son poids/transitivité est pesé. En cas de doute : on n'ajoute pas. 2. Sécurité — seules des librairies sûres : activement maintenues, largement adoptées, sans vulnérabilité connue (pip-audit / npm audit verts, bloquant en CI), licence compatible (permissive MIT/BSD/Apache/ISC ; copyleft à valider explicitement), installées depuis les sources officielles (PyPI/npm). Vigilance typosquatting (paquets récents/peu téléchargés). […]",
   "fichier": "docs/adr/0009-gouvernance-dependances.md",
   "identifiant": "0009",
   "liens": [],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Gouvernance des dépendances externes",
   "us": [
    "E00US003"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-12",
   "date_brute": "2026-07-12",
   "extrait": "- Une commande d'écriture = une session = une transaction = une diffusion post-commit. Le writer (WriteQueue) ouvre la session au début de la commande, exécute le callable, puis commit ; toute exception provoque un rollback complet et se propage à la Future de l'appelant (aucune écriture partielle). Les listeners post-commit ne sont notifiés qu'après le commit réussi. - En écriture, les repositories utilisent la session fournie par l'unité de travail (session ambiante de la commande) et n'appellent plus commit() eux-mêmes. Le commit est la responsabilité exclusive de la frontière (le writer). - Les lectures restent inchangées : hors file, elles ouvrent leur session courte autonome (mode […]",
   "fichier": "docs/adr/0010-unite-de-travail-transactionnelle.md",
   "identifiant": "0010",
   "liens": [
    {
     "cible": "0005",
     "libelle": "Précise",
     "sens": "sortant",
     "type": "amende"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Unité de travail : la commande d'écriture est la frontière transactionnelle",
   "us": []
  },
  {
   "amende_par": [
    "0045",
    "0046"
   ],
   "date": "2026-07-14",
   "date_brute": "2026-07-14",
   "extrait": "Retenir l'option 3, bornée au strict nécessaire : introduire une entité Phase minimale et une table phase, dont E01US009 n'exploite qu'une phase de type qualification par tournoi, portant le barème dans config ({\"scoring\": {\"volees\": N, \"fleches\": M, \"mode\": \"cumul\"}}). Dans le périmètre (J1, E01US009) : - agrégat Phase pur (immuable) : tournoi_id, ordre, type (TypePhase), statut (StatutPhase), et un barème de qualification typé (BaremeQualification, value object validé) ; - table phase alignée sur le modèle de données (colonnes ordre, type, config, statut) — pour ne pas créer une table divergente qu'il faudrait ensuite compléter ; - un seul type utilisé (qualification) et un seul statut […]",
   "fichier": "docs/adr/0011-phase-qualification-anticipee.md",
   "identifiant": "0011",
   "liens": [
    {
     "cible": "0004",
     "libelle": "Précise / anticipe",
     "sens": "sortant",
     "type": "amende"
    }
   ],
   "portage": [
    {
     "chemin": "backend/domain/bareme.py",
     "existe": true,
     "symboles": [
      "BaremeQualification"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "Phase",
      "TypePhase",
      "StatutPhase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/moteur.py",
     "existe": true,
     "symboles": [
      "phase",
      "config"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté (forme de `config` **amendée** par [ADR-0046](0046-config-policies-politiques-nommees-parametrees.md), E05US003)",
   "titre": "Introduire une `Phase` minimale dès J1 pour héberger le barème de qualification",
   "us": [
    "E01US009",
    "E05US003"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-15",
   "date_brute": "2026-07-15",
   "extrait": "Retenir l'option 3. Tout montant du projet est un entier de centimes, et cette règle vaut pour le domaine, la base, l'API et le front. - L'unité est dans le nom : tout champ monétaire porte le suffixe _centimes (tarif_depart_centimes, montant_du_centimes…). C'est la défense la moins chère contre la confusion euros/centimes — la classe de bug que ce choix rouvrirait s'il restait implicite. Elle remplace un type dédié : l'invariant se réduit à >= 0, un value object serait de l'abstraction sans emploi (ADR-0003, parcimonie). - Les euros n'existent qu'à l'affichage. L'API transporte des centimes ; la conversion vit dans un seul module côté client (aujourd'hui […]",
   "fichier": "docs/adr/0012-argent-en-centimes-entiers.md",
   "identifiant": "0012",
   "liens": [
    {
     "cible": "E01US010",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Compter l'argent en centimes entiers, jamais en flottants",
   "us": [
    "E01US010",
    "E02US004",
    "E08US001",
    "E08US002",
    "E09US003"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-15",
   "date_brute": "2026-07-15",
   "extrait": "1. Porte mécanique avant la revue (étape 0). Les vérifications outillées passent au vert avant de dépenser une passe. Elles déchargent les relecteurs de ce qu'elles prouvent : faire relire à l'œil ce que test_domain_isolation.py établit par AST est plus lent et plus faible qu'une preuve machine. Les commandes sont identiques à celles de ci.yml, l'autorité bloquante — options comprises : une commande approchante n'est pas la même mesure. La porte en est un sous-ensemble volontaire : une seule étape est sciemment omise (la synchro requirements.txt↔pyproject.toml) ; toute autre divergence est un bug de la procédure. 2. Quatre axes disjoints, relus en parallèle, à modèle fort — A (architecture […]",
   "fichier": "docs/adr/0013-conduite-de-la-revue-d-us.md",
   "identifiant": "0013",
   "liens": [],
   "portage": [
    {
     "chemin": ".github/workflows/ci.yml",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/pyproject.toml",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_agents_de_revue.py",
     "existe": true,
     "symboles": [
      "Edit",
      "Write"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_isolation.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "docs/metriques-revue.md",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Conduite de la revue d'US : axes parallèles + porte mécanique",
   "us": [
    "E01US001",
    "E02US001",
    "E05US028"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-15",
   "date_brute": "2026-07-15",
   "extrait": "Retenir l'option 3. archer.club_id est nullable, et NULL signifie « club encore inconnu » — jamais « aucun club », jamais un club. - Un NULL est une anomalie, pas un état légitime. Le classement marque « Club inconnu » sur la ligne de l'archer concerné, et E12US005 le comptera parmi ce qui manque avant de lancer le tournoi. On ne s'en accommode pas : on le rend visible pour qu'il soit résorbé. La liste déroulante de saisie n'est pas ce signalement — elle est l'entrée du formulaire ; le signal porte sur les archers déjà inscrits, ceux qu'on ne regarde plus. - Aucun club sentinelle, jamais. C'est l'interdit central de cet ADR : il détruirait l'information au lieu de la porter (voir […]",
   "fichier": "docs/adr/0014-club-inconnu-plutot-que-club-sentinelle.md",
   "identifiant": "0014",
   "liens": [
    {
     "cible": "E02US002",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E03US006",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E08US002",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E09US003",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E12US005",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E02US005",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le club d'un archer est facultatif : `NULL` = *inconnu*, jamais un club",
   "us": [
    "E02US001",
    "E02US002",
    "E02US003",
    "E02US005",
    "E02US007",
    "E03US006",
    "E08US002",
    "E09US003",
    "E12US005"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-15",
   "date_brute": "2026-07-15",
   "extrait": "Retenir l'option 3, sans index UNIQUE. - Le contrôle vit dans le service applicatif, au sens de domain.archer.cle_identite (nom, prénom, club ; casse et accents repliés par domain.club.cle_nom). - Aucune contrainte de base ne le double, contrairement au patron Club (où nom_club_deja_pris est doublé d'un UNIQUE). C'est une rupture assumée : ici, la contrainte rejetterait le fils. - La confirmation est un drapeau du corps de requête : autoriser_homonyme: bool = false sur POST /api/v1/tournois/{id}/archers. Le client qui reçoit le 409 réémet le même corps avec le drapeau à true. - Le 409 est une question, pas un verdict. C'est ce qui le distingue de tous les autres 409 du projet […]",
   "fichier": "docs/adr/0015-signaler-un-doublon-plutot-que-l-interdire.md",
   "identifiant": "0015",
   "liens": [
    {
     "cible": "E02US002",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E02US005",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E02US007",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Signaler un doublon d'archer plutôt que l'interdire : 409 + confirmation",
   "us": [
    "E02US002",
    "E02US003",
    "E02US005",
    "E02US007"
   ]
  },
  {
   "amende_par": [
    "0050"
   ],
   "date": "2026-07-16",
   "date_brute": "2026-07-16",
   "extrait": "Retenir l'option 3, et séparer explicitement forfait et suppression dans le vocabulaire du projet (glossaire.md : Engagé, Placé, Forfait). - ArcherEngage est un signalement, 3ᵉ de la famille ADR-0015 : 409, drapeau de confirmation, False par défaut, route admin. Il se déclenche si l'archer est placé (cible renseignée) ou engagé (au moins un score). - Sa confirmation détruit — et c'est le premier du projet dans ce cas. Les deux autres signalements créent (HomonymeArcher) ou déplacent (ChangementCategorieArcherEngage). Rupture assumée avec « on refuse plutôt que de cascader en silence » : on cascade, mais pas en silence — c'est toute la différence, et c'est ce que le message porte. - Le […]",
   "fichier": "docs/adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md",
   "identifiant": "0016",
   "liens": [
    {
     "cible": "0015",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "E02US003",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E04US015",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E12US004",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E10US005",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Supprimer un archer engagé : confirmer et détruire, plutôt que refuser — et ne pas confondre avec le forfait",
   "us": [
    "E00US011",
    "E02US003",
    "E04US015",
    "E10US005",
    "E12US004"
   ]
  },
  {
   "amende_par": [
    "0075"
   ],
   "date": "2026-07-16",
   "date_brute": "2026-07-16",
   "extrait": "- DEPART change de parent : enfant de TOURNOI (tournoi_id NOT NULL), non plus d'ARCHER. Champs : numero (unique par tournoi), horaire (libellé de créneau, optionnel), tarif_centimes (NOT NULL, ≥ 0, centimes — ADR-0012). - Le prix vit sur le départ ; TOURNOI.tarif_depart_centimes est retiré. E01US010 est retravaillé : il posait « le tarif d'un départ » sur le tournoi faute de départs modélisés ; maintenant qu'ils existent, le prix va sur eux. L'état « non défini » (NULL) que l'ADR-0012 distinguait de « gratuit » (0) disparaît pour le tarif : on ne crée pas un départ sans prix, donc l'inquiétude « annoncer 0 € à une compétition dont le tarif a été oublié » n'a plus d'objet. 0 = gratuit reste […]",
   "fichier": "docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md",
   "identifiant": "0017",
   "liens": [
    {
     "cible": "0012",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "E02US004",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E02US009",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E08US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E02US006",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0075",
     "libelle": "Prolongé par",
     "sens": "entrant",
     "type": "complete"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/departs.py",
     "existe": true,
     "symboles": [
      "DEPART"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/departs.py",
     "existe": true,
     "symboles": [
      "DEPART"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/depart.py",
     "existe": true,
     "symboles": [
      "DEPART"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/",
     "existe": true,
     "symboles": [
      "DEPART"
     ],
     "symboles_absents": [],
     "verifiable": false
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le départ est un créneau du tournoi, pas une participation de l'archer",
   "us": [
    "E01US010",
    "E02US004",
    "E02US006",
    "E02US009",
    "E03US001",
    "E07US004",
    "E08US001"
   ]
  },
  {
   "amende_par": [
    "0051",
    "0057"
   ],
   "date": "2026-07-16",
   "date_brute": "2026-07-16",
   "extrait": "1. Confirmable (patron ArcherEngage, non ClubReference). Supprimer un départ à inscriptions lève DepartAvecInscriptions (409 depart_avec_inscriptions), franchissable en rejouant l'appel avec autoriser_suppression_inscrits=true (paramètre de requête sur le DELETE, comme autoriser_suppression_engage — un DELETE n'a pas de corps, cf. ADR-0016). La suppression confirmée cascade sur les inscriptions du créneau (cascade applicative maîtrisée, dans la transaction de l'adapter — DETTE-001, jamais ON DELETE). Pourquoi confirmable et non refus dur : un créneau est une configuration locale du tournoi, comme un archer — pas un référentiel global comme le club. Un créneau annulé (trop peu d'inscrits, […]",
   "fichier": "docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md",
   "identifiant": "0018",
   "liens": [
    {
     "cible": "E02US009",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0016",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0017",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Supprimer un départ à inscriptions : confirmable, effets monétaires déportés",
   "us": [
    "E02US001",
    "E02US003",
    "E02US004",
    "E02US009",
    "E08US005",
    "E12US008"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-16",
   "date_brute": "2026-07-16",
   "extrait": "- Categorie.ages: tuple[TrancheAge, ...] remplace tranche_age. TrancheAge est un enum fermé des huit tranches FFTA (U11, U13, U15, U18, U21, S1, S2, S3, §2). ages est un ensemble d'éligibilité : dédoublonné et ordonné canoniquement (U11 → S3) à la construction, pour que deux catégories aux mêmes tranches soient égales. Vide = aucune contrainte d'âge (pendant de l'ancien None), permis pour une catégorie créée à la main, jamais pour le preset. - Les regroupements sont des libellés, pas des tranches. Le référentiel encode « U18 » (arc nu) → ages = (U15, U18) et « Scratch » → ages = (U21, S1, S2, S3) ; le libellé affiché est découplé de la liste d'âges. « Scratch » disparaît des valeurs de […]",
   "fichier": "docs/adr/0019-categorie-eligibilite-multi-tranches.md",
   "identifiant": "0019",
   "liens": [
    {
     "cible": "E01US013",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E01US003",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E01US004",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "La catégorie porte un ensemble de tranches d'âge, pas une tranche unique",
   "us": [
    "E01US003",
    "E01US004",
    "E01US013"
   ]
  },
  {
   "amende_par": [
    "0027"
   ],
   "date": "2026-07-17",
   "date_brute": "2026-07-17",
   "extrait": "1. Vocabulaire fermé, validé à la frontière — même régime qu'ADR-0019. Les onze valeurs du §4.2 deviennent l'énuméré ZoneScore(str, Enum) du domaine (10…1, M), exposé tel quel par les DTO. Une valeur hors vocabulaire est rejetée en 400 par Pydantic, avant que le domaine ne la voie (règle 6) — comme TrancheAge pour Categorie.ages. Les règles structurelles restent au domaine et sortent en 422. La mouche (X) n'est pas une zone : le §4.3 la donne comme un diamètre (le « 10 intérieur » des poulies), pas comme une valeur de score, et aucun consommateur ne la demande — E06US001 départage au nombre de 10 puis de 9. Si EPIC-06 la réclame, c'est là qu'elle naîtra. 2. Trois règles structurelles, et […]",
   "fichier": "docs/adr/0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md",
   "identifiant": "0020",
   "liens": [
    {
     "cible": "E01US014",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E01US005",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0019",
     "libelle": "Suit",
     "sens": "sortant",
     "type": "complete"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le blason porte ses valeurs de score admises ; défaut = blason simple complet",
   "us": [
    "E01US005",
    "E01US014",
    "E06US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-17",
   "date_brute": "2026-07-17",
   "extrait": "- Grain « capacité ». Une US regroupe les comportements d'une même surface métier livrés ensemble. Les frontières de jalon (J0→J4) ne se franchissent jamais : deux US de jalons différents ne fusionnent pas (sinon on ne livre plus par jalon de valeur). - Patron de regroupement. L'US survivante garde l'ID le plus bas du groupe ; chaque US absorbée devient une puce de critère d'acceptation étiquetée CA — \u003caspect> (ex-USxxx) — aucun comportement n'est perdu (règle 9 : le CA reste l'oracle de test). La survivante porte une ligne Absorbe : … et une table ## Correspondance ancien → nouveau clôt le fichier d'epic. - Le livré est gelé. Une US déjà livrée (code + tests dérivés du CA + […]",
   "fichier": "docs/adr/0021-maille-des-us-au-grain-capacite.md",
   "identifiant": "0021",
   "liens": [],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Maille des US au grain « capacité », pas « comportement testable »",
   "us": [
    "E04US002",
    "E04US007",
    "E04US015",
    "E10US004"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-17",
   "date_brute": "2026-07-17",
   "extrait": "1. Categorie porte hauteur_cm: int (hauteur du centre de l'or, en cm), défaut 130. Champ obligatoire en base, un entier strictement positif (HauteurCentreInvalide sinon). La chaîne existante Archer.categorie_id → Categorie donne au moteur la hauteur de chaque archer sans nouvelle jointure. 2. Le pré-chargement FFTA renseigne la hauteur. categories_salle_18m() marque les catégories U11 à 110 cm, toutes les autres à 130 (la constante _HAUTEUR_CENTRE_U11 vit dans le référentiel, pas dans le domaine : c'est une donnée FFTA, docs/referentiel-ffta.md §5). Une catégorie créée à la main part du défaut 130 et reste éditable. 3. La compatibilité de hauteur est une contrainte de placement de 1er rang, […]",
   "fichier": "docs/adr/0022-hauteur-de-centre-sur-la-categorie.md",
   "identifiant": "0022",
   "liens": [
    {
     "cible": "E03US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0020",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "La hauteur du centre de l'or vit sur la catégorie ; contrainte de placement de 1er rang",
   "us": [
    "E01US003",
    "E03US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-17",
   "date_brute": "2026-07-17",
   "extrait": "1. Glouton déterministe, mono-passe, sans retour arrière. Les archers sont triés par (hauteur, blason, id) — ce qui rend contigus les tireurs d'une même hauteur puis d'un même blason — et l'on remplit cible par cible, en passant à la suivante dès qu'un archer n'entre plus. Un archer qui n'entre sur aucune cible restante ressort en conflit (NON_PLACE), jamais en échec silencieux. Propriétés retenues, dans l'ordre : - Déterminisme avant optimalité. Le jour J, un placement reproductible et explicable (« cet archer est ici parce que sa butte est à sa hauteur, les autres étaient pleines ») vaut mieux qu'un optimum opaque que l'organisateur ne peut pas justifier à un club. C'est aussi une […]",
   "fichier": "docs/adr/0023-moteur-de-placement-glouton-deterministe.md",
   "identifiant": "0023",
   "liens": [
    {
     "cible": "E03US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0004",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0022",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Moteur de placement : glouton déterministe, contraintes câblées, recalcul à la demande",
   "us": [
    "E03US001",
    "E03US004",
    "E03US006",
    "E03US007"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-18",
   "date_brute": "2026-07-18",
   "extrait": "1. Plan matérialisé, source de vérité — pas une surcouche. Une table placement porte, par inscription (l'archer sur ce départ), la case occupée : (inscription_id, depart_id, cible_index, position). Un inscrit sans ligne est en réserve. La lecture (plan_de_cibles) ne recalcule plus : elle lit l'état persisté (les gardes 404 d'ADR-0023 demeurent). Motif du choix contre la surcouche : le geste « réserve » (mettre N archers de côté puis les reposer un à un pour valider le plan final) décrit une session d'édition sur un plan, pas des écarts sur un calcul vivant. Faire tourner l'auto « par-dessus » des archers épinglés reviendrait à un placement sous contraintes fixes — plus de code, sémantique […]",
   "fichier": "docs/adr/0024-plan-de-cibles-materialise-ajustable.md",
   "identifiant": "0024",
   "liens": [
    {
     "cible": "E03US004",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0023",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Plan de cibles matérialisé et ajustable : persistance, modèle transactionnel, réserve",
   "us": [
    "E03US001",
    "E03US004"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-18",
   "date_brute": "2026-07-18",
   "extrait": "1. Le scoreur est une entité de domaine — à la différence de l'admin. Table scoreur (tournoi_id, nom, code), agrégat domain.scoreur.Scoreur, port ScoreurRepository, adapter SQL. Asymétrie assumée avec l'admin, qui, lui, n'a pas d'entité (secret dans .env, ADR-0009) : l'admin est un secret unique de configuration ; les scoreurs sont multiples, créés/modifiés/supprimés au runtime, nominatifs et rattachés à un tournoi — c'est de la donnée métier persistée, comme Depart, pas un paramètre d'accès. Entité du tournoi (FK tournoi_id, dans le périmètre DETTE-001), redéfinissable même tournoi en cours (D-14, aucune garde de statut). 2. Code individuel généré par le serveur, unique dans toute la base. […]",
   "fichier": "docs/adr/0025-mode-d-identite-scoreur-par-code-individuel.md",
   "identifiant": "0025",
   "liens": [
    {
     "cible": "E10US003",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0007",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0009",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Mode d'identité « scoreur » : entité de domaine, code individuel, session nominative",
   "us": [
    "E04US002",
    "E10US002",
    "E10US003",
    "E10US005",
    "E10US007"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-18",
   "date_brute": "2026-07-18",
   "extrait": "1. Sept statuts, chacun porteur d'un comportement distinct. | Statut | Ce qu'il change concrètement | |---|---| | brouillon | Config libre, tout éditable ; suppression libre. État initial. | | prêt | Déclare la config complète et validée ; suppression encore libre ; sert de « feu vert » au démarrage. | | en_cours | Compétition lancée ; suppression interdite ; le structurel (catégories, gabarit, barème) se fige, les métadonnées restent éditables. | | en_pause | Gèle la saisie de tout le tournoi (aucune validation de score acceptée) sans le terminer ; reprend en en_cours. | | terminé | Résultats sportifs figés (seule action irréversible côté sportif) ; la complétude hors-sportif reste […]",
   "fichier": "docs/adr/0026-cycle-de-vie-du-tournoi-sept-statuts.md",
   "identifiant": "0026",
   "liens": [
    {
     "cible": "E01US017",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/tournois.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/tournois.py",
     "existe": true,
     "symboles": [
      "TransitionStatutInvalide"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/tournoi.py",
     "existe": true,
     "symboles": [
      "StatutTournoi",
      "TransitionTournoi"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/accueil/FriseCycleDeVie.tsx",
     "existe": true,
     "symboles": [
      "CycleDeVie"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Cycle de vie du tournoi : sept statuts explicites",
   "us": [
    "E01US002",
    "E01US017",
    "E12US005",
    "E14US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-18",
   "date_brute": "2026-07-18",
   "extrait": "1. Le vocabulaire de score devient une donnée du tournoi, injectée, défaut FFTA. Les valeurs admissibles (10 → 1 + M en FFTA salle) ne sont plus un énuméré gravé mais un jeu configuré, rattaché au tournoi (résolu par la politique scoring, ADR-0004). À la création d'un tournoi, il est pré-rempli avec le vocabulaire FFTA — exactement comme les catégories et barèmes (référentiel §10, template modifiable). L'admin peut le surcharger. 2. Le maximum de flèche se dérive du vocabulaire, il ne se déclare plus. score_max d'un barème = nb_flèches_total × max(valeurs marquantes du vocabulaire). La constante VALEUR_FLECHE_MAX = 10 disparaît au profit de ce calcul ; « 10 » n'est plus qu'une valeur par […]",
   "fichier": "docs/adr/0027-vocabulaire-de-score-injectable-defaut-ffta.md",
   "identifiant": "0027",
   "liens": [
    {
     "cible": "E01US018",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0020",
     "libelle": "Révise",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0004",
     "libelle": "Révise",
     "sens": "sortant",
     "type": "amende"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le vocabulaire de score est injectable par tournoi ; défaut FFTA",
   "us": [
    "E01US014",
    "E01US018"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-18",
   "date_brute": "2026-07-18",
   "extrait": "1. Le match oppose des participants, jamais des archers en dur. Le domaine du moteur (EPIC-05) manipule un Participant — soit un archer individuel, soit une équipe. Le modèle porte MATCH.participant_A/B (CDC technique §5), pas archer_a/archer_b. Un tournoi individuel est le cas où chaque participant est un archer : l'abstraction ne complique pas le cas simple, elle le contient. 2. L'équipe est une entité du tournoi, nommée, composée d'archers. Equipe (tournoi_id, nom, membres) + table MEMBRE_EQUIPE. Composition selon la règle FFTA (§6.3/§7 : typiquement 3 archers, ou équipe mixte 2 archers H/F). Le nombre et la contrainte de composition sont de la configuration (vocabulaire fermé FFTA en […]",
   "fichier": "docs/adr/0028-epreuves-par-equipes-participant.md",
   "identifiant": "0028",
   "liens": [
    {
     "cible": "E13US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0004",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [
    {
     "chemin": "backend/domain/duel.py",
     "existe": true,
     "symboles": [
      "Participant"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/participant.py",
     "existe": true,
     "symboles": [
      "Participant",
      "genre",
      "ref_id",
      "frozen",
      "GenreParticipant"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/tableau.py",
     "existe": true,
     "symboles": [
      "Participant"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Épreuves par équipes dans le périmètre : le match oppose des *participants*",
   "us": [
    "E05US005",
    "E13US001",
    "E13US002",
    "E13US003",
    "E13US004"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-18",
   "date_brute": "2026-07-18",
   "extrait": "1. Le poste de cible est une donnée métier persistée — le code de cible naît ici. Table poste (tournoi_id, cible_index, code), agrégat domain.poste.Poste, port PosteRepository, adapter SQL — sur le patron Scoreur (ADR-0025), avec la même asymétrie assumée avec l'admin. Un Poste matérialise le credential d'une cible (tournoi_id, cible_index) : la Cible elle-même reste un value object dérivé du GabaritSalle (elle n'a pas d'identité propre) ; le Poste lui ajoute un code distribuable. E09US008 (imprimer les QR) ne fera qu'imprimer ces codes — le contrat (forme du code, URL de rattachement) est fixé ici, puisque E04US001 précède E09US008 malgré la dépendance inverse de la séquence (défaut de […]",
   "fichier": "docs/adr/0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md",
   "identifiant": "0029",
   "liens": [
    {
     "cible": "E04US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0025",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0007",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0009",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Mode d'identité « poste de cible » : code de cible régénérable, jeton de poste lié au tournoi",
   "us": [
    "E01US017",
    "E04US001",
    "E04US002",
    "E09US008",
    "E10US007",
    "E12US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-18",
   "date_brute": "2026-07-18",
   "extrait": "1. Une dépendance combinée autoriser_saisie(request) -> Poste | None. Elle renvoie None si une session admin est valide (l'admin saisit sans contrainte), le Poste si un jeton de poste (X-Jeton-Poste) est valide, et lève NonAuthentifie (→ 401) sinon. On élargit l'endpoint existant (on remplace dependencies=[Depends(exiger_admin)] par la valeur rendue par autoriser_saisie) plutôt que d'ajouter une route « poste » distincte — même principe qu'ADR-0025 (élargissement endpoint par endpoint, l'admin reste autorisé). L'admin est essayé en premier : mode le plus large, purement en mémoire, alors que résoudre un poste relit la base (statut du tournoi, ADR-0029). C'est le premier endpoint du projet […]",
   "fichier": "docs/adr/0030-saisie-autorisee-au-poste-de-cible-403-hors-cible.md",
   "identifiant": "0030",
   "liens": [
    {
     "cible": "E10US007",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0029",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0025",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0007",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Saisie de score autorisée au poste de cible, bornée par le lieu (403 hors-cible)",
   "us": [
    "E00US011",
    "E04US001",
    "E04US002",
    "E10US001",
    "E10US003",
    "E10US007"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-18",
   "date_brute": "2026-07-18",
   "extrait": "1. La bibliothèque PDF du projet est reportlab. QT3 est tranchée en sa faveur sur le seul critère qui domine ici : l'embarquabilité dans le binaire PyInstaller hors ligne sous Windows (règle 12 — la rigueur va au moteur métier, l'infra reste simple ; règle 11 — parcimonie). Les documents du projet (feuille de marque, classements, déroulé, papiers QR) sont tabulaires et structurés, pas des maquettes libres : le point faible de ReportLab (mise en page riche) ne mord quasiment pas, et son point fort (tables, grilles) sert directement. 2. La validation « fonctionne dans l'exécutable packagé » (CA socle) est déférée à EPIC-11. Aucun build PyInstaller n'existe encore (E00US012 ne produit qu'un […]",
   "fichier": "docs/adr/0031-bibliotheque-pdf-reportlab.md",
   "identifiant": "0031",
   "liens": [
    {
     "cible": "E09US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0002",
     "libelle": "Réfs",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0009",
     "libelle": "Réfs",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Bibliothèque PDF : ReportLab (QT3)",
   "us": [
    "E00US012",
    "E09US001",
    "E09US008"
   ]
  },
  {
   "amende_par": [
    "0059"
   ],
   "date": "2026-07-19",
   "date_brute": "2026-07-19",
   "extrait": "La navigation de la coquille admin se fait par état local useState, sans react-router. La destination active, le tournoi courant et le groupe déplié sont des useState dans le composant CoquilleAdmin ; changer de destination met à jour cet état, la zone principale rend la feature correspondante. Aucune dépendance de routage n'est ajoutée (le manifeste package.json est inchangé par l'US). Ce choix vaut pour l'appli admin. Il ne préjuge pas de l'app poste de cible (déjà pilotée par le marqueur ?poste=\u003ccode> en query-string, E04US001) ni d'une éventuelle vitrine publique, qui répondent à d'autres besoins. Mise à jour E07US001 (2026-07-20). La vitrine publique (vues classement + plan de cibles) […]",
   "fichier": "docs/adr/0032-navigation-admin-par-etat-local.md",
   "identifiant": "0032",
   "liens": [
    {
     "cible": "E00US015",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0009",
     "libelle": "Réfs",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "0059",
   "statut": "remplace",
   "statut_brut": "**Remplacé par [ADR-0059](0059-routage-par-role-dans-l-url-routeur-maison.md)** (30/07/2026)",
   "titre": "Navigation de l'appli admin par état local plutôt que react-router",
   "us": [
    "E00US015",
    "E00US016",
    "E04US001",
    "E07US001",
    "E07US006",
    "E14US003"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-19",
   "date_brute": "2026-07-19",
   "extrait": "1. La source des archers d'une saisie est le modèle Affectation, pas Archer.cible. Un poste reconstitue ses archers par Affectation filtrées sur cible_index, avec leur position A–D. Le champ Archer.cible n'est plus une source de saisie : il reste, pour l'instant, la donnée du seul chemin de démo saisir_score (walking skeleton), remplacé par la nouvelle surface volée-par-volée. Son retrait a été différé (arbitrage tranché en tranche exposition PR2b, reversé dans stories/E04-saisie-scores.md) : /scores est le véhicule de test du walking skeleton (E2E, « engagé », diffusion) et son retrait casse ~10 tests — c'est une US de nettoyage dédiée. La démo coexiste sans conflit (tables score vs […]",
   "fichier": "docs/adr/0033-source-de-saisie-affectations-cible-depart.md",
   "identifiant": "0033",
   "liens": [
    {
     "cible": "E04US002",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0024",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0017",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0029",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0030",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Source des archers d'un poste : les affectations `(cible, départ)`, pas `Archer.cible`",
   "us": [
    "E00US011",
    "E03US004",
    "E04US002",
    "E06US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-19",
   "date_brute": "2026-07-19",
   "extrait": "1. La session de poste porte un depart_id courant, posé par un geste explicite. Le poste, une fois rattaché à sa cible (ADR-0029), se met « en mode départ X » : un appel dédié fixe le départ courant de la session. Tant qu'aucun départ n'est fixé, le poste connaît son lieu mais ne peut pas saisir (il ne sait pas qui afficher) — refus explicite, pas un affichage vide ambigu. 2. Le geste est manuel dans cette US ; son automatisation est différée à E12US002. « Lancer un tour » (E12US002, D-25) fera exactement le même geste — fixer le départ courant — mais pour tous les postes à la fois, au feu vert de l'admin. On implémente ici la primitive (un poste, un départ) ; E12US002 en fera […]",
   "fichier": "docs/adr/0034-poste-selectionne-son-depart-courant.md",
   "identifiant": "0034",
   "liens": [
    {
     "cible": "E04US002",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0029",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0033",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le poste sélectionne son départ courant (geste manuel ; automatisation différée)",
   "us": [
    "E04US001",
    "E04US002",
    "E12US002",
    "E12US008"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-19",
   "date_brute": "2026-07-19",
   "extrait": "Option (c) : une couture de session partagée. L'écriture de l'acte de score et la consignation de sa trace se font dans une seule session, un seul commit — donc tout ou rien. 1. L'écriture d'audit accepte une session fournie. Une méthode consigner_dans(session, entree) écrit dans une session existante au lieu d'en ouvrir une, sans commit. Le consigner historique (session propre + commit) est préservé — les appels autonomes d'E10US005 ne changent pas. > Rectification (tranche persistance PR2a, 2026-07-19). La rédaction initiale disait « le port > AuditRepository gagne la capacité… soit un paramètre session, soit consigner_dans ». C'est > impossible en l'état : le port AuditRepository vit […]",
   "fichier": "docs/adr/0035-atomicite-acte-trace-session-partagee.md",
   "identifiant": "0035",
   "liens": [
    {
     "cible": "E04US002",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Atomicité acte↔trace : co-écriture score + audit dans une session partagée",
   "us": [
    "E04US002",
    "E04US015",
    "E10US005",
    "E12US004"
   ]
  },
  {
   "amende_par": [
    "0037"
   ],
   "date": "2026-07-19",
   "date_brute": "2026-07-19",
   "extrait": "1. Le client fournit un identifiant de saisie ; la commande de la file dédoublonne dessus. Chaque écriture de volée (saisie, validation, correction) porte un identifiant opaque généré côté client (un par geste utilisateur). Un RegistreIdempotence mémorise identifiant → résultat : un premier passage exécute l'acte et mémorise son résultat ; tout rejeu du même identifiant renvoie ce résultat sans ré-exécuter. Absence d'identifiant (None/vide) = pas de déduplication. 2. La déduplication est consultée DANS la commande de la file (writer unique, ADR-0005), pas au bord HTTP. C'est ce qui rend le contrôle « déjà vu ? » et l'écriture atomiques : deux rejeux concurrents ne peuvent pas manquer tous […]",
   "fichier": "docs/adr/0036-idempotence-de-la-saisie-par-identifiant-en-memoire.md",
   "identifiant": "0036",
   "liens": [
    {
     "cible": "E04US002",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0005",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0029",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0034",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Idempotence de la saisie par identifiant de saisie (registre en mémoire, borné)",
   "us": [
    "E04US002",
    "E04US009",
    "E10US005",
    "E12US002"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-20",
   "date_brute": "2026-07-20",
   "extrait": "1. Détecter le hors-ligne par la nature de l'échec, pas par navigator.onLine. Le client HTTP (fetchJson) rejette avec une TypeError quand le fetch échoue au niveau réseau (serveur injoignable), et lève une ErreurApi quand le serveur a répondu un refus (403 hors-cible, 404 blason introuvable…). On met en file seulement le premier cas ; une ErreurApi est une vraie erreur, propagée à l'UI. navigator.onLine est écarté : sur un LAN sans internet il vaut souvent true alors que le serveur est injoignable — il mentirait. 2. Ranger la file dans un store Zustand persisté (localStorage). Nouveau shared/stores/fileHorsLigneStore (à côté de sessionPosteStore, même patron persist) : une liste FIFO de […]",
   "fichier": "docs/adr/0037-file-de-saisie-hors-ligne-et-rejeu.md",
   "identifiant": "0037",
   "liens": [
    {
     "cible": "0005",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0036",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "E04US009",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0036",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0029",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "File de saisie hors-ligne côté front : mise en file sur panne, rejeu à la reconnexion",
   "us": [
    "E00US008",
    "E00US010",
    "E04US009"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-20",
   "date_brute": "2026-07-20",
   "extrait": "### 1. Liveness par heartbeat, pas par la connexion WebSocket Le poste envoie périodiquement (~10 s) un POST /api/v1/postes/session/heartbeat authentifié par son jeton (X-Jeton-Poste). Le serveur mémorise, par poste_id, l'instant de la dernière réception et l'IP vue. Un RegistrePresence (port du domaine, adapter en mémoire) porte cet état. Règle d'état (fonction pure du domaine, domain/supervision.py) : à partir de (rattaché ?, secondes depuis le dernier heartbeat, seuil) → - non rattaché : aucune session ouverte pour ce poste (code préparé mais aucune tablette dessus) ; - hors ligne : rattaché mais dernier heartbeat plus vieux que le seuil (30 s = 3 pings manqués) — ou jamais vu ; - en […]",
   "fichier": "docs/adr/0038-presence-des-postes-par-heartbeat.md",
   "identifiant": "0038",
   "liens": [
    {
     "cible": "E12US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0029",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0034",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Présence des postes par heartbeat (état en ligne / hors ligne)",
   "us": [
    "E00US008",
    "E12US001"
   ]
  },
  {
   "amende_par": [
    "0079"
   ],
   "date": "2026-07-21",
   "date_brute": "2026-07-21",
   "extrait": "1. Un endpoint public dédié expose le déroulé par archer. GET /api/v1/tournois/{tournoi_id}/archers/{archer_id}/deroule, sans authentification (comme toute lecture publique, E10US001), lecture seule exécutée hors boucle (run_in_threadpool). Il réutilise le service de lecture existant ServiceSaisie.etat_serie — pas de nouveau modèle ni de nouveau chemin de lecture. Un archer sans rien de saisi (ou un couple (tournoi, archer) inconnu) renvoie un déroulé vide en 200, jamais un 404 : corollaire de la frontière de confidentialité — l'endpoint public ne révèle pas l'existence d'un couple, l'énumération ne distingue rien. 2. Le déroulé inclut les volées NON validées. Chaque volée porte un statut […]",
   "fichier": "docs/adr/0039-exposition-publique-du-deroule-scores-provisoires.md",
   "identifiant": "0039",
   "liens": [
    {
     "cible": "E07US009",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0035",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Exposition publique du déroulé du tour, scores **provisoires** inclus",
   "us": [
    "E01US015",
    "E04US002",
    "E06US001",
    "E07US006",
    "E07US009",
    "E10US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-21",
   "date_brute": "2026-07-21",
   "extrait": "1. Périmètre (arbitrage produit) : le mécanisme réutilisable + la seule action régénérer le plan de cibles. C'est l'action qui correspond mot pour mot à l'exemple du CDC (le cas « REPLACER »). Les autres écritures destructrices existantes (changer le gabarit, modifier un barème/phase, une catégorie/blason) gardent leur comportement actuel ; elles se grefferont sur le mécanisme quand leur propre US les touchera. Aucun comportement perdu (règle 9) : le CA « toutes les écritures » reste l'horizon, il est séquencé, pas rogné — comme l'écran de salle d'E12US001. 2. Fork tranché (arbitrage technique) : (A) endpoint de prévisualisation, avec re-calcul de l'impact au commit. C'est le seul choix […]",
   "fichier": "docs/adr/0040-alerte-par-calcul-d-impact.md",
   "identifiant": "0040",
   "liens": [
    {
     "cible": "E12US007",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0035",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0024",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0016",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0018",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Alerter par **calcul d'impact** : prévisualisation, échelle à trois niveaux, geste délibéré",
   "us": [
    "E03US004",
    "E10US002",
    "E10US005",
    "E12US001",
    "E12US007"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-21",
   "date_brute": "2026-07-21",
   "extrait": "1. La tarification est une propriété de configuration du tournoi. À terme, comment se calcule le montant dû est une politique injectable (règle 2, ADR-0004), choisie à la création/configuration du tournoi — au même rang que scoring ou seeding. Un tournoi porte sa stratégie de tarification ; le service de paiement lit un dû, il ne le code pas. 2. Le sujet de facturation est configuré par tournoi : archer ou club. « Celui qui doit l'argent » est un choix de configuration. Le cas club — le club est l'unité facturée, pas seulement le payeur groupé de ses archers — s'appuie sur le référentiel club (ADR-0014, club_id), et non sur l'abstraction Participant d'ADR-0028. « Sujet de facturation » (qui […]",
   "fichier": "docs/adr/0041-tarification-configuration-du-tournoi.md",
   "identifiant": "0041",
   "liens": [
    {
     "cible": "E08US002",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0004",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0017",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0028",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté *(organisateur, 21/07/2026 — sujet de facturation = unité facturée, joueur ou club)*",
   "titre": "La tarification est une configuration du tournoi, pas du code",
   "us": [
    "E01US010",
    "E01US020",
    "E01US021",
    "E08US001",
    "E08US002",
    "E08US005",
    "E13US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-21",
   "date_brute": "2026-07-21",
   "extrait": "Au 1ᵉʳ lancement, tant qu'aucun rôle n'est posé, l'app présente un écran de choix à quatre portes — Tablette (cible), Public (téléphone), Scoreur, Admin (PC) — et mémorise le choix (localStorage, store sessionRoleStore). Aux ouvertures suivantes l'app va droit au rôle choisi, sans réafficher l'écran : c'est le geste initial explicite, pas un menu récurrent (D-09 — l'archer, le plus nombreux, ne subit pas de friction à chaque ouverture). ### Le rôle effectif : une session en cours prime sur le choix Le routage ne lit pas seulement le marqueur de choix : une session déjà ouverte l'emporte, pour qu'une tablette rattachée ou un admin connecté ne retombe jamais sur l'écran de choix après un […]",
   "fichier": "docs/adr/0042-modele-d-entree-choix-de-role-explicite.md",
   "identifiant": "0042",
   "liens": [
    {
     "cible": "E00US017",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Modèle d'entrée de l'appli : choix de rôle explicite au 1ᵉʳ lancement",
   "us": [
    "E00US015",
    "E00US017",
    "E01US016",
    "E04US001",
    "E07US001",
    "E07US004",
    "E07US006",
    "E10US002",
    "E10US003"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-26",
   "date_brute": "2026-07-26",
   "extrait": "1. On accepte zeroconf (LGPL-2.1) comme dépendance runtime. La LGPL n'impose d'obligation qu'en cas de distribution d'un binaire liant la bibliothèque en refusant à l'utilisateur le re-link vers une version modifiée. Kervignarc est un outil interne mono-club, jamais diffusé publiquement : aucune distribution au sens de la LGPL n'a lieu. Aucune modification de zeroconf n'est faite (simple import). L'obligation copyleft est donc sans objet en pratique. 2. La règle générale reste « permissif par défaut ». Cet ADR n'ouvre pas la porte au copyleft en général : il tranche un cas nommé, sur le critère « outil interne non distribué ». Toute future dépendance copyleft repasse par la même validation […]",
   "fichier": "docs/adr/0043-acceptation-dependance-copyleft-lgpl.md",
   "identifiant": "0043",
   "liens": [
    {
     "cible": "E11US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0009",
     "libelle": "Réfs",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0002",
     "libelle": "Réfs",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Acceptation d'une dépendance copyleft (LGPL) : `zeroconf`",
   "us": [
    "E11US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-26",
   "date_brute": "2026-07-26",
   "extrait": "Une copie de base est une LECTURE ; elle ne passe donc pas par la file d'écriture. On utilise l'API de sauvegarde en ligne de SQLite (sqlite3.Connection.backup()), qui copie page à page au niveau moteur, inclut l'état WAL, et redémarre proprement si la source change pendant la copie. Conformément à la règle 7 (« lectures synchrones hors boucle »), cette opération : - ouvre une connexion sqlite3 brute directe au fichier, en parallèle du writer et hors du moteur SQLAlchemy (helper unique infrastructure/db/snapshot.py) ; - s'exécute hors boucle événementielle, dans un run_in_threadpool (même patron que les endpoints PDF) ; - pose un PRAGMA busy_timeout sur la connexion source pour patienter […]",
   "fichier": "docs/adr/0044-sauvegarde-lecture-concurrente-et-tache-periodique.md",
   "identifiant": "0044",
   "liens": [
    {
     "cible": "E11US003",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0005",
     "libelle": "Réfs",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Sauvegarde/archive : lecture concurrente hors file d'écriture + première tâche périodique",
   "us": [
    "E11US003",
    "E11US006"
   ]
  },
  {
   "amende_par": [
    "0075",
    "0076",
    "0078",
    "0083"
   ],
   "date": "2026-07-26",
   "date_brute": "2026-07-26",
   "extrait": "### 1. Le cycle de vie d'une phase suit le patron du tournoi (ADR-0026 §4) Quatre statuts : a_venir → en_cours → terminee, avec en_cours ⇄ en_pause réversible. L'agrégat ne porte que la valeur et des transitions pures (demarrer, mettre_en_pause, reprendre, terminer) qui renvoient une copie ; c'est le service qui arbitre l'enchaînement (quel état → quel état) et lève TransitionStatutInvalide (→ 409) sur une transition illégale — exactement comme ServiceTournois (règle 2 : la règle vit dans le service/domaine, jamais dans l'API ; aucune horloge injectée, transitions déclenchées par acte admin, déterministes — règle 9). en_pause de phase gèle une phase pendant que le reste du tournoi vit ; il […]",
   "fichier": "docs/adr/0045-sequence-de-phases-cycle-de-vie-typage-source.md",
   "identifiant": "0045",
   "liens": [
    {
     "cible": "E05US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0004",
     "libelle": "Raffine",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0011",
     "libelle": "Raffine",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0026",
     "libelle": "S'articule avec",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/phases.py",
     "existe": true,
     "symboles": [
      "transitions"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/phases.py",
     "existe": true,
     "symboles": [
      "TransitionStatutInvalide",
      "ServiceTournois"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "StatutPhase",
      "demarrer",
      "mettre_en_pause",
      "reprendre",
      "terminer",
      "SourcePhase"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Séquence de phases : cycle de vie, typage et amorce du modèle de source",
   "us": [
    "E01US009",
    "E04US013",
    "E05US001",
    "E05US003",
    "E05US005",
    "E05US010",
    "E05US023"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-26",
   "date_brute": "2026-07-26",
   "extrait": "### 1. Les politiques vivent sous config.policies On adopte la forme cible d'ADR-0004. La config d'une phase distingue désormais explicitement les politiques du moteur (sous policies) du reste de la configuration : json { \"policies\": { \"scoring\": {\"nom\": \"cumul\", \"volees\": 20, \"fleches\": 3} }, \"validation\": {\"grain\": \"fin_de_serie\"}, \"source\": {\"ordre_source\": 1, \"rang_debut\": 1, \"rang_fin\": 16}, \"effectif\": 16 } Pourquoi maintenant : DETTE-003 objectait que policies « n'a de sens que face à plusieurs politiques hétérogènes ». C'est précisément ce qu'E05US003 introduit — six familles. Le regroupement gagne sa place au moment où il cesse d'être une abstraction à clé unique. Il donne au […]",
   "fichier": "docs/adr/0046-config-policies-politiques-nommees-parametrees.md",
   "identifiant": "0046",
   "liens": [
    {
     "cible": "0011",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0004",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    }
   ],
   "portage": [
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "config.policies",
      "validation"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/politiques.py",
     "existe": true,
     "symboles": [
      "PolitiquesPhase",
      "RegistrePolitiques"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/moteur.py",
     "existe": true,
     "symboles": [
      "config"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "`config.policies` : politiques nommées et paramétrées (résorption de DETTE-003)",
   "us": [
    "E01US009",
    "E01US015",
    "E05US003",
    "E05US005",
    "E05US010"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-26",
   "date_brute": "2026-07-26",
   "extrait": "1. Favoriser la mixité = ré-ordonner l'entrée du glouton, pas ajouter une branche dans la boucle. Avant de placer, on remplace le tri (hauteur, blason, id) par un entrelacement des clubs en round-robin à l'intérieur de chaque groupe (hauteur, blason) (les frontières de groupe sont identiques à l'ancien tri). Le glouton (_CibleEnCours.accueille, remplissage cible par cible) reste byte-identique. Trois propriétés le justifient : - Les contraintes de rang supérieur sont préservées par construction. Le moteur n'est pas touché ; la mixité ne peut pas provoquer un dépassement de capacité/espace ni un mélange de hauteurs. - Aucune régression sur le nombre de placés/conflits, ni sur la structure […]",
   "fichier": "docs/adr/0047-mixite-clubs-par-reordonnancement-et-signal-derive.md",
   "identifiant": "0047",
   "liens": [
    {
     "cible": "E03US006",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0023",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0024",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0014",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Mixité ≥ 2 clubs : ré-ordonnancement de l'entrée + signal dérivé, plutôt qu'une contrainte du glouton",
   "us": [
    "E03US001",
    "E03US004",
    "E03US006",
    "E03US007"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-26",
   "date_brute": "2026-07-26",
   "extrait": "### 1. Le tableau est recalculé (déterministe), le placement est matérialisé L'arbre (construire_tableau) est une fonction pure reproductible de (participants ordonnés par rang, seeding, byes) : même régime qu'ADR-0023, recalculable à la demande depuis le classement (ServiceClassement) dont il dérive. On ne persiste pas l'arbre : le figer exigerait une table de matchs + la progression + le routing persistés — le cœur d'E05US010, hors périmètre. Ce qu'on matérialise, comme la qualification (ADR-0024), c'est le placement (qui tire où), pour le rendre ajustable. Séparation nette : l'appariement (qui affronte qui) est recalculé ; la pose (sur quelle cible/position) est persistée et éditable. […]",
   "fichier": "docs/adr/0048-cote-a-cote-des-duellistes-par-reordonnancement.md",
   "identifiant": "0048",
   "liens": [
    {
     "cible": "E03US009",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0023",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0024",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0047",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0028",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0004",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0046",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Duellistes côte à côte : ré-ordonnancement de l'entrée + signal dérivé, plan de duels matérialisé par phase",
   "us": [
    "E03US001",
    "E03US004",
    "E03US006",
    "E03US009",
    "E05US005",
    "E05US010",
    "E06US006",
    "E13US002"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-27",
   "date_brute": "2026-07-27",
   "extrait": "### 1. Un agrégat de domaine Duel distinct, réutilisant Volee/ZoneScore Le scoring d'un duel est un nouvel agrégat pur domain/duel.py, pas une extension de Serie : - MancheDuel(numero, volee_haut: Volee, volee_bas: Volee) — une manche (un « set ») oppose deux volées ; on réutilise Volee/ZoneScore (.points) sans les dupliquer. - Duel(bareme, participant_haut, participant_bas, manches, barrage) — racine d'agrégat immuable (comme Serie/Tableau) : saisir_manche(...), saisir_barrage(...) renvoient un nouveau Duel. La configuration (barème, zones admises du blason) est passée aux opérations par le service, jamais dupliquée dans l'agrégat — patron d'ADR-0027/Serie. - Le résultat (ResultatDuel : […]",
   "fichier": "docs/adr/0049-saisie-et-scoring-des-duels.md",
   "identifiant": "0049",
   "liens": [
    {
     "cible": "E04US013",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0004",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0046",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0028",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0023",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0048",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [
    {
     "chemin": "backend/application/saisie_duels.py",
     "existe": true,
     "symboles": [
      "_decor",
      "_etat_du_match"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/duel.py",
     "existe": true,
     "symboles": [
      "Duel",
      "saisir_manche",
      "saisir_barrage",
      "valider",
      "resultat",
      "vainqueur",
      "verrouille",
      "MancheDuel",
      "ResultatDuel",
      "ModeDuel",
      "Barrage",
      "Duel.barrage",
      "_vainqueur_barrage",
      "BaremeDuel",
      "preset_ffta_classique",
      "preset_ffta_poulies",
      "preset_club",
      "Protocol",
      "ResolveurBaremeDuel",
      "ResolveurBaremeDuelFfta"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/tir.py",
     "existe": true,
     "symboles": [
      "DuelRepositorySQL",
      "_manches_json",
      "_barrage_json"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Saisie et scoring des duels : agrégat `Duel`, barème résolu par (phase, arme), barrage dans l'agrégat, résultats persistés / tableau reconstruit",
   "us": [
    "E01US011",
    "E01US015",
    "E01US017",
    "E01US018",
    "E04US002",
    "E04US009",
    "E04US013",
    "E04US016",
    "E05US003",
    "E05US005",
    "E05US010",
    "E06US003",
    "E06US006",
    "E10US001",
    "E10US005",
    "E12US002"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-27",
   "date_brute": "2026-07-27",
   "extrait": "Un seul concept Forfait, agrégat de domaine immuable, scopé à une phase (phase_id) : - nature ∈ { abandon, disqualification } — porte l'effet sur le classement ; - daté (declare_le, UTC via le port Horloge), attribué (declare_par, un nom, pas une FK — la trace survit à la suppression du scoreur, comme l'audit), motif optionnel ; - réversible : l'annulation supprime la déclaration (les flèches, serie/volee, ne sont jamais touchées) — pas un troisième état ; interdite si le tournoi est terminé (D-15). Un même concept, lu par trois endroits selon la phase où le forfait est déclaré : 1. Classement de qualification (domain.classement) — lit les forfaits de la phase de qualif : un abandon est […]",
   "fichier": "docs/adr/0050-forfait-abandon-et-disqualification.md",
   "identifiant": "0050",
   "liens": [
    {
     "cible": "0016",
     "libelle": "Complète / amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0049",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Forfait unifié (abandon / disqualification), scopé à la phase",
   "us": [
    "E04US002",
    "E04US013",
    "E04US015",
    "E06US001",
    "E10US005",
    "E12US004",
    "E12US005"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-27",
   "date_brute": "2026-07-27",
   "extrait": "1. État dérivé, jamais stocké. Depart reste un agrégat figé (règle 4) sans colonne de statut. L'état est un calcul à la lecture, porté par un value object pur AvancementDepart (domain/cycle_depart.py) qui dérive EtatDepart de trois décomptes — nombre d'archers placés, combien ont tiré, combien ont leur série close — exactement comme domain/impact.py dérive un niveau d'alerte. Règle : - nb_ayant_tire == 0 → ouvert ; - sinon, toutes les séries closes → clos ; sinon → lancé. 2. « lancé » = présence d'un score. Le fait réel retenu est la flèche validée (Serie.nb_fleches_validees > 0), seul fait réel disponible. « heure atteinte » est écarté (horaire non comparable). « clos » = toutes les séries […]",
   "fichier": "docs/adr/0051-cycle-de-vie-d-un-depart.md",
   "identifiant": "0051",
   "liens": [
    {
     "cible": "0018",
     "libelle": "Complète / amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0040",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0050",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Cycle de vie d'un départ : état dérivé, garde-fou confirmable",
   "us": [
    "E02US009",
    "E04US015",
    "E12US005",
    "E12US007",
    "E12US008"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-28",
   "date_brute": "2026-07-28",
   "extrait": "1. L'accueil est un écran dédié qui agrège, il ne recalcule rien. Accueil (feature accueil) compose des sources déjà livrées — complétude (E12US005), supervision (E12US001), paiements (E08US002) — plus la frise du cycle de vie. Aucune règle métier nouvelle : la checklist « à faire » est la complétude, les chiffres-clés sont des lectures existantes, les alertes sont dérivées (lignes de complétude en alerte + postes hors ligne). C'est le cadrage d'E14US001. 2. Le front s'aligne sur les 7 statuts d'ADR-0026. Le type StatutTournoi passe à 7 valeurs ; BadgeStatut devient exhaustif (un statut sans libellé casse la compilation — le badge ne peut plus être muet) ; les classes CSS […]",
   "fichier": "docs/adr/0052-accueil-admin-contextualise-par-statut.md",
   "identifiant": "0052",
   "liens": [
    {
     "cible": "E14US001",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0026",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0032",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Accueil d'admin contextualisé par statut",
   "us": [
    "E00US015",
    "E00US016",
    "E01US016",
    "E01US017",
    "E08US002",
    "E12US001",
    "E12US005",
    "E14US001",
    "E14US002"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-28",
   "date_brute": "2026-07-28",
   "extrait": "1. Adopter Testing Library + jsdom comme socle de test de rendu, en devDependencies : - @testing-library/react — monter/interroger un composant par ce qu'un utilisateur perçoit (rôle, texte accessibles), pas par ses détails d'implémentation ; - @testing-library/user-event — simuler un vrai geste (séquence d'événements d'un tap/clic), fidèle à l'usage tactile visé ; - @testing-library/jest-dom — matchers DOM lisibles (toBeVisible, toHaveAttribute…) et leur typage ; - jsdom — le DOM en mémoire (« faux navigateur ») requis par le rendu. Toutes MIT, npm audit --audit-level=high = 0 vulnérabilité. Standard de fait de l'écosystème React (maintenu, largement adopté) — pas une lib « plaisir » : il […]",
   "fichier": "docs/adr/0053-outillage-test-de-rendu-front.md",
   "identifiant": "0053",
   "liens": [
    {
     "cible": "0009",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Outillage de test de rendu front (Testing Library + jsdom)",
   "us": [
    "E00US014",
    "E14US002"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-28",
   "date_brute": "2026-07-28",
   "extrait": "1. Rebrancher les mêmes services sur des adapters in-memory des ports (Option A). Les services du moteur ne dépendent que de ports (domain/ports.py) et de politiques pures — le spike l'a confirmé : aucun ne touche SQLite ni la write_queue, seule la couche API soumet à la file. Il suffit donc de les instancier sur un jeu d'adapters in-memory (magasins dict) au lieu des adapters SQL. « Ne rien persister » devient une propriété structurelle, pas une discipline à tenir : les écritures du moteur (poser un plan de duels, enregistrer un tir) atterrissent dans des dict jetés à la fin — il n'existe aucun chemin de ces adapters vers la base. 2. Les adapters in-memory sont du code de production, dans […]",
   "fichier": "docs/adr/0054-execution-ephemere-du-moteur-sur-adapters-in-memory.md",
   "identifiant": "0054",
   "liens": [
    {
     "cible": "0003",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0005",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0026",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Exécution éphémère du moteur sur adapters in-memory des ports",
   "us": [
    "E15US001",
    "E15US002",
    "E15US003"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-28",
   "date_brute": "2026-07-28",
   "extrait": "1. Une SessionSimulation mutable, éphémère, en mémoire serveur — hors file d'écriture. On introduit un objet de session qui détient un HarnaisSimulation hydraté (le substrat ADR-0054) plus l'état du pilote (en cours / en pause / terminé), l'étape courante (qualif / duels / terminé), la graine et son générateur pseudo-aléatoire, et le niveau tiré de chaque archer. Un registre en mémoire (dict[SessionId, SessionSimulation], câblé à la composition root, règle 8) garde les sessions vivantes. Rien n'atteint SQLite ni la write_queue : comme le substrat, la non-persistance est structurelle (règle 7 intacte — aucune transaction longue, aucun writer monopolisé). Une session est jetable : arreter la […]",
   "fichier": "docs/adr/0055-session-de-simulation-vivante-pilotee-par-pas.md",
   "identifiant": "0055",
   "liens": [
    {
     "cible": "0054",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0005",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0049",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Session de simulation vivante, pilotée par pas, sur le substrat in-memory",
   "us": [
    "E04US002",
    "E15US001",
    "E15US002",
    "E15US003"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-28",
   "date_brute": "2026-07-28",
   "extrait": "Le lancement d'un tour est un acte d'audit qui déclenche la diffusion d'un événement typé — il ne pose aucun statut sur le tableau. 1. Nouvelle nature d'acte auditée LANCEMENT (domain.entree_audit.ActionAuditee). Lancer, c'est un acte de pilotage sensible du jour J : daté, attribué (rôle admin, un secret — pas un nom, comme la trace REPLACEMENT), consultable. C'est le seul « écrit » du geste, et il est justifié en soi (traçabilité D-15 / E10US005). Il est aussi la seule écriture minimale qui, passant par la file, permet à la diffusion post-commit de partir sans violer la règle 7. 2. La commande de lancement renvoie un LiveEvent(\"tour_lance\", …) typé. Le listener post-commit le diffuse tel […]",
   "fichier": "docs/adr/0056-lancement-d-un-tour-acte-audite-et-diffuse.md",
   "identifiant": "0056",
   "liens": [
    {
     "cible": "0049",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0005",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0040",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0035",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0048",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le lancement d'un tour est un acte audité et diffusé, pas un statut sur le tableau",
   "us": [
    "E01US017",
    "E04US018",
    "E05US010",
    "E07US004",
    "E07US008",
    "E10US005",
    "E12US002",
    "E12US005",
    "E12US006"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-29",
   "date_brute": "2026-07-29",
   "extrait": "1. Un registre à part, sans FK vers ce qui disparaît. Nouvel agrégat Remboursement (domain/remboursement.py) + table remboursement (migration 0033). Il survit à l'effacement de l'inscription (et souvent du départ) : donc aucune FK vers inscription/depart. On fige des instantanés textuels — archer_prenom, archer_nom, creneau — et le montant_centimes encaissé, exactement comme entree_audit/forfait figent le nom de l'auteur plutôt qu'une FK (la trace survit à la suppression du scoreur, E10US003). Seul tournoi_id reste une FK. Cycle de vie à trois états : à_rembourser → remboursé | reporté (transitions terminales). 2. Création = conséquence atomique de l'effacement, non tracée à l'audit. Un […]",
   "fichier": "docs/adr/0057-registre-de-remboursements.md",
   "identifiant": "0057",
   "liens": [
    {
     "cible": "0018",
     "libelle": "Complète / amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0035",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Registre de remboursements : mouvement d'argent né d'un effacement",
   "us": [
    "E02US005",
    "E02US009",
    "E08US002",
    "E08US005",
    "E10US003",
    "E10US005"
   ]
  },
  {
   "amende_par": [
    "0074"
   ],
   "date": "2026-07-30",
   "date_brute": "2026-07-30",
   "extrait": "1. Le critère de découpage n'est plus quand, c'est quelle activité. Trois axes : | Axe | Activité | Durée de vie | Utilisateur · tempo | Travaille sur un tournoi ? | |---|---|---|---|---| | Atelier | Fabriquer : briques du club, salles types, formats de déroulé, modèles réutilisables, banc d'essai | Pluriannuelle | Le concepteur du format · posé, hors urgence | Non | | Pilotage | Le temps réel : lancer, superviser, valider, faire tourner la journée | La journée | La table d'organisation · la seconde, sous pression | Oui | | Gestion | L'administratif : inscriptions, paiements, exports, archives | Semaines avant → après | Secrétaire, trésorier · le jour, la semaine | Oui | Ce qui justifie la […]",
   "fichier": "docs/adr/0058-decoupage-de-l-admin-en-trois-axes-d-activite.md",
   "identifiant": "0058",
   "liens": [
    {
     "cible": "0042",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0026",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Découpage de l'appli admin en trois axes d'activité, plus par temps du tournoi",
   "us": [
    "E00US015",
    "E10US001",
    "E14US001",
    "E14US002",
    "E14US003",
    "E15US003"
   ]
  },
  {
   "amende_par": [
    "0072"
   ],
   "date": "2026-07-30",
   "date_brute": "2026-07-30",
   "extrait": "1. Cinq adresses, une par monde. / (choix des quatre portes), /public, /scoreur, /cible, /admin/\u003ctournoi>/\u003caxe>/\u003cdestination>. Le tournoi est dans l'adresse, pas seulement l'écran. Corrigé en revue : la première version le laissait en état local, si bien que F5 restaurait l'axe et la destination mais pas leur sujet — 21 destinations sur 24 en dépendent, l'utilisateur retombait donc sur « choisissez un tournoi ». Il est placé avant l'axe pour survivre au changement d'axe, et reconnu à sa forme (suite de chiffres) : aucun axe ni aucune destination n'est numérique, la lecture est donc sans ambiguïté. L'adresse dit cible, le code dit tablette. Ce n'est pas une incohérence : l'adresse est lue […]",
   "fichier": "docs/adr/0059-routage-par-role-dans-l-url-routeur-maison.md",
   "identifiant": "0059",
   "liens": [
    {
     "cible": "0032",
     "libelle": "Remplace",
     "sens": "sortant",
     "type": "remplace"
    },
    {
     "cible": "0042",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0058",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Une adresse par rôle, servie par un routeur maison",
   "us": [
    "E07US004",
    "E09US008",
    "E14US003"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-30",
   "date_brute": "2026-07-30",
   "extrait": "Une brique appartient au club ; un tournoi en détient une copie. ### 1. Deux formes distinguées par tournoi_id - tournoi_id is None — modèle de bibliothèque, patrimoine du club, réutilisable d'une année sur l'autre, n'appartenant à aucune édition ; - tournoi_id renseigné — copie d'un tournoi, ajustable sans altérer le modèle. Ce n'est pas un patron neuf : gabarit_salle l'applique depuis E01US007/E01US008 (« appliquer un modèle (copie), lire et ajuster la copie sans altérer le modèle »). E01US023 le généralise. C'est ce qui rend le changement petit — et cet ADR court. Le port gagne une lecture par_bibliotheque() distincte de par_tournoi(), et non un par_tournoi(None) : ce sont deux lectures […]",
   "fichier": "docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md",
   "identifiant": "0060",
   "liens": [
    {
     "cible": "0011",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0045",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0020",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0058",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/application/patrimoine.py",
     "existe": true,
     "symboles": [
      "appliquer_categorie",
      "appliquer_blason",
      "promouvoir_blason",
      "promouvoir_categorie",
      "dupliquer_categorie",
      "dupliquer_blason",
      "precharger_ffta"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/format_tournoi.py",
     "existe": true,
     "symboles": [
      "FormatTournoi"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/patrimoine.py",
     "existe": true,
     "symboles": [
      "tournoi_id"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/ports.py",
     "existe": true,
     "symboles": [
      "CategorieRepository",
      "BlasonRepository"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Les briques de configuration sont le patrimoine du club : bibliothèque, copie, promotion",
   "us": [
    "E01US007",
    "E01US008",
    "E01US023",
    "E14US003",
    "E16US002"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-07-31",
   "date_brute": "2026-07-31",
   "extrait": "### 1. Routing dit où, Depth dit jusqu'où Routing.destination_du_perdant() est ressignée en route(contexte) -> Destination, comme ADR-0004 l'annonçait et comme politiques.py le prévoyait explicitement (« rupture bon marché, un implémenteur, aucun consommateur »). Deux destinations : HorsTableau et VersPlage(plage) ; le repêchage World Archery (E05US015) en ajoutera une troisième sans toucher aux deux premières. La profondeur décide séparément jusqu'où descendre : un sous-tableau n'est engendré que si sa plage contient encore un rang à classer. Cette séparation est ce qui rend le moteur générique — le routing exprime la mécanique du format, la profondeur son ambition. ### 2. L'élimination […]",
   "fichier": "docs/adr/0061-routing-generique-et-placement-en-cascade.md",
   "identifiant": "0061",
   "liens": [
    {
     "cible": "0004",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0045",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0049",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0060",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/domain/plage.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/politiques.py",
     "existe": true,
     "symboles": [
      "HorsTableau",
      "VersPlage",
      "VersRepechage",
      "EliminationSeche",
      "PlacementEnCascade",
      "RoutingRepechage",
      "ContexteRoutage"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/tableau.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/",
     "existe": true,
     "symboles": [
      "podium"
     ],
     "symboles_absents": [],
     "verifiable": false
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le routing devient générique, et l'élimination directe n'est qu'un placement tronqué",
   "us": [
    "E01US023",
    "E01US024",
    "E05US005",
    "E05US010",
    "E05US015",
    "E07US004"
   ]
  },
  {
   "amende_par": [
    "0083"
   ],
   "date": "2026-07-31",
   "date_brute": "2026-07-31",
   "extrait": "### 1. Le critère : une structure propre, pas un réglage Un type de phase se justifie par une structure d'appariement et de progression qui lui est propre. Ce qui ne fait que régler une structure existante est une politique (ADR-0004) ou un paramètre, jamais un type. Appliqué à la liste, le critère la coupe en trois : | Ce que le CDC énumère | Ce que c'est réellement | Où ça vit | |---|---|---| | échauffement, barrage, poules, Big Shoot Off, système suisse, colline | types — structure propre | TypePhase + un moteur de domaine | | repêchage | politique routing — décide où va un perdant | RoutingRepechage | | handicap | politique scoring — décide comment se calcule un score | […]",
   "fichier": "docs/adr/0062-catalogue-de-types-de-phase.md",
   "identifiant": "0062",
   "liens": [
    {
     "cible": "0004",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0045",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0046",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0061",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/domain/barrage.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/big_shoot_off.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/colline.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "TypePhase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/politiques.py",
     "existe": true,
     "symboles": [
      "RoutingRepechage",
      "ScoreAvecHandicap",
      "ContexteScore",
      "elimination_directe"
     ],
     "symboles_absents": [
      "elimination_directe"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/poule.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/suisse.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un type de phase se justifie par une structure, pas par un réglage",
   "us": [
    "E01US024",
    "E02US001",
    "E05US003",
    "E05US015",
    "E05US023",
    "E05US026",
    "E05US027",
    "E05US028",
    "E07US004"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-01",
   "date_brute": "2026-08-01",
   "extrait": "L'invariant quitte l'enregistrement pour l'usage. Ce qui doit être cohérent, ce n'est pas la ligne en base : ce sont les phases produites. ### 1. Un format s'enregistre presque toujours ; il ne s'applique que s'il tient ModelePhase.__post_init__ ne valide plus rien. FormatTournoi.__post_init__ ne garde qu'un invariant : le nom non vide. Il le garde parce que le nom est la clé d'unicité de la bibliothèque — l'assemblage et la promotion dédoublonnent par lui (arbitrage d'E01US023, point 1) : un format sans nom ne serait pas un brouillon, il serait introuvable. Tout le reste — aucune étape, ordres non contigus, source postérieure, qualification sans barème, grain inadmissible — se diagnostique […]",
   "fichier": "docs/adr/0063-brouillon-de-format-invariant-a-l-application.md",
   "identifiant": "0063",
   "liens": [
    {
     "cible": "0060",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0045",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0061",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0062",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0054",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0055",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0026",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un format se compose en brouillon ; l'invariant se vérifie à l'application",
   "us": [
    "E01US023",
    "E01US024",
    "E05US010",
    "E05US015",
    "E14US003"
   ]
  },
  {
   "amende_par": [
    "0089"
   ],
   "date": "2026-08-01",
   "date_brute": "01/08/2026",
   "extrait": "### 1. L'écran de salle est un Poste typé, pas un agrégat parallèle Poste gagne un type (cible | ecran). Un écran porte un libellé de place dans le gymnase au lieu d'un cible_index, et son déroulé de vues (SequenceVues). Le typage rend cible_index facultatif. Plutôt que de laisser chaque appelant décider quoi faire d'un None — et parfois l'oublier —, l'invariant « seul un poste de cible a une cible » est rendu exigible au point d'usage : Poste.cible() lève PosteSansCible. Symétriquement, PosteSansEcran garde deroule_effectif / avec_libelle. L'exclusivité cible_index ↔ libelle n'est pas un CHECK en base : le projet n'en utilise nulle part, et en poser un ferait vivre une règle métier hors du […]",
   "fichier": "docs/adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md",
   "identifiant": "0064",
   "liens": [
    {
     "cible": "E07US004",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0029",
     "libelle": "Liés",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0038",
     "libelle": "Liés",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0063",
     "libelle": "Liés",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0056",
     "libelle": "Liés",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "L'écran de salle est un poste typé, et son pilotage est un état lu",
   "us": [
    "E01US016",
    "E01US024",
    "E05US031",
    "E06US004",
    "E07US004",
    "E07US005",
    "E07US008",
    "E16US009"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-02",
   "date_brute": "02/08/2026",
   "extrait": "### 1. Le rang acquis d'un battu est la moitié basse de la plage du match qu'il a perdu Aucune règle de classement n'est écrite dans le service. Match.plage porte déjà « les rangs encore atteignables avant ce match » (ADR-0061), et Plage.moitie_basse() est la Règle R — « le perdant descend dans la moitié basse de sa plage ». Le battu d'un quart d'un tableau de 8 sort donc de [1..8] vers [5..8] : 5ᵉ-8ᵉ. La conséquence importante est qu'on rend une fourchette, pas un chiffre. Ce n'est pas une approximation faute de mieux : dans un tableau tronqué au podium, aucun match n'a été joué pour départager les quatre battus des quarts. Ils sont ex æquo, et c'est le résultat. Choisir un chiffre dans la […]",
   "fichier": "docs/adr/0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md",
   "identifiant": "0065",
   "liens": [
    {
     "cible": "E07US008",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0061",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0062",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0039",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "Le rang acquis se lit sur la plage du match perdu, et un repêché n'est pas un éliminé",
   "us": [
    "E01US024",
    "E04US018",
    "E05US010",
    "E05US028",
    "E05US030",
    "E06US004",
    "E07US004",
    "E07US006",
    "E07US008",
    "E12US002",
    "E13US002"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-02",
   "date_brute": "2026-08-02",
   "extrait": "### 1. Le seuil est un réglage de format, donc une politique Ce qui fait qu'une place est « à enjeu » dépend du tournoi : la dernière place qualificative d'un tableau de 8 n'est pas celle d'un tableau de 32, et un club peut vouloir ne barrer que le podium. C'est exactement ce qu'ADR-0004 appelle de la configuration, pas du code. La famille concernée est sans ambiguïté tiebreak : le seuil dit jusqu'où on départage, le comparateur dit comment. Nous l'y logeons plutôt que d'ouvrir une septième famille, pour une raison qui n'est pas l'économie : les deux réglages doivent rester cohérents entre eux. Barrer selon §8.1 dans un tournoi qui départage en poule (§10.1, cinq critères) n'a aucun sens, […]",
   "fichier": "docs/adr/0066-seuil-de-barrage-porte-par-la-politique-tiebreak.md",
   "identifiant": "0066",
   "liens": [
    {
     "cible": "E06US003",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0004",
     "libelle": "Révise",
     "sens": "sortant",
     "type": "amende"
    }
   ],
   "portage": [
    {
     "chemin": "backend/domain/barrage.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/politiques.py",
     "existe": true,
     "symboles": [
      "Protocol",
      "Tiebreak",
      "departager",
      "TiebreakAvecBarrage",
      "TiebreakFftaDefaut.barrage_requis",
      "TiebreakPoules.barrage_requis",
      "False"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le seuil de barrage est porté par la politique `tiebreak`",
   "us": [
    "E05US015",
    "E06US001",
    "E06US003"
   ]
  },
  {
   "amende_par": [
    "0085"
   ],
   "date": "2026-08-03",
   "date_brute": "03/08/2026",
   "extrait": "### 1. Le palmarès est une fusion de blocs, la phase la plus tardive l'emportant Chaque archer est situé par la phase la plus tardive qui l'a classé (son ordre dans la séquence), la qualification faisant bloc 0. Les blocs se rangent par ordre décroissant, et à l'intérieur d'un bloc par position acquise croissante ; les rangs sont ensuite renumérotés 1→N sans trou. Deux conséquences qui ne sont pas des détails : - avoir disputé le tableau passe avant tout. Le battu du 1ᵉʳ tour devance tout non-qualifié, quel qu'ait été le rang de qualification de l'un et de l'autre : il a franchi une porte que l'autre n'a pas franchie. C'est l'usage, et c'est ce que « fusionner » veut dire — sans quoi le […]",
   "fichier": "docs/adr/0067-palmares-agregation-des-rangs-de-phases.md",
   "identifiant": "0067",
   "liens": [
    {
     "cible": "E06US004",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0004",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0065",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0046",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0050",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0066",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/application/palmares.py",
     "existe": true,
     "symboles": [
      "ServicePalmares",
      "pour_tournoi",
      "calculer_palmares"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/palmares.py",
     "existe": true,
     "symboles": [
      "ResultatPhase",
      "LignePalmares",
      "Palmares",
      "PositionPhase",
      "OriginePalmares",
      "Phase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/politiques.py",
     "existe": true,
     "symboles": [
      "ClePolitique.AGGREGATION",
      "Protocol",
      "Aggregation",
      "AggregationParQualification",
      "AggregationExAequo"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "Le palmarès agrège les rangs des phases, et une 7ᵉ politique départage les ex æquo",
   "us": [
    "E01US024",
    "E04US018",
    "E05US005",
    "E05US015",
    "E06US001",
    "E06US004",
    "E07US004",
    "E07US008",
    "E12US002"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-03",
   "date_brute": "03/08/2026",
   "extrait": "### 1. Un prélèvement par rangs garde les archers dont le rang tombe dans son intervalle ServiceSaisieDuels._preleves lit phase.sources et ne conserve que les lignes du classement dont le rang_scratch appartient à l'un des intervalles déclarés. Les bornes viennent du domaine (SourcePhase.intervalle), qui sait déjà résoudre une fin ouverte sur l'effectif réel : « les rangs 33 et suivants » vaut 88 archers à 120 classés et 50 à 82. On consomme cette sémantique, on ne la réécrit pas — c'était tout l'objet de la remonter dans le domaine en E05US010. Une phase sans source reste alimentée par les inscriptions : c'est la première de sa séquence (la qualification), et c'est aussi le tableau tant […]",
   "fichier": "docs/adr/0068-le-moteur-consomme-les-prelevements-declares.md",
   "identifiant": "0068",
   "liens": [
    {
     "cible": "E05US020",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0061",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0063",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0050",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0065",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/application/prelevement.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/saisie_duels.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "Le moteur consomme les prélèvements déclarés, et seulement ceux dont la règle est écrite",
   "us": [
    "E01US024",
    "E05US010",
    "E05US020",
    "E05US021",
    "E06US004"
   ]
  },
  {
   "amende_par": [
    "0082"
   ],
   "date": "2026-08-04",
   "date_brute": "04/08/2026",
   "extrait": "### 1. Le plancher se déduit, il ne se saisit pas Le minimum technique est calculé des prélèvements, jamais déclaré seul. Une phase qui oppose des tireurs en exige deux ; un prélèvement « à partir du rang d » n'en trouve deux que lorsque sa phase source en classe d + 1. D'où d - 1 + 2 inscrits — 34 pour « les rangs 33 et suivants ». Entre phases, le plus exigeant l'emporte ; entre prélèvements d'une même phase, le plus bas décide (ils se cumulent). Seuls la qualification et l'échauffement se contentent d'un participant : la liste est énoncée en négatif pour qu'un type ajouté au catalogue hérite du plancher prudent. Pourquoi pas un champ saisi. Un nombre saisi peut contredire le déroulé […]",
   "fichier": "docs/adr/0069-effectif-minimum-deduit-et-exige.md",
   "identifiant": "0069",
   "liens": [
    {
     "cible": "E05US021",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0068",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0063",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0060",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/formats.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/formats.py",
     "existe": true,
     "symboles": [
      "PrelevementVide"
     ],
     "symboles_absents": [
      "PrelevementVide"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/application/tournois.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule.py",
     "existe": true,
     "symboles": [
      "ExigenceEffectif",
      "ProjectionDeroule.effectif_minimum",
      "effectif_minimum",
      "EtapeSequencee",
      "FormatTournoi.effectif_minimum_exige"
     ],
     "symboles_absents": [
      "FormatTournoi.effectif_minimum_exige"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/format_tournoi.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "L'effectif minimum se **déduit** du déroulé, et le club peut exiger plus",
   "us": [
    "E05US020",
    "E05US021",
    "E05US025"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-04",
   "date_brute": "04/08/2026",
   "extrait": "### 1. La phase porte le choix, le registre rend la stratégie Phase et ModelePhase gagnent un champ profondeur: ProfondeurClassement | None — un descripteur sérialisable (nom + jusqu_au), pas la stratégie. La résolution passe par RegistrePolitiques, exactement comme le seuil de barrage d'ADR-0066. Mettre une Depth sur l'agrégat aurait fait entrer un objet non sérialisable dans une donnée persistée et court-circuité le point d'injection : la politique serait devenue une décoration. Persistance : config.policies.depth = {\"nom\": …, \"jusqu_au\": …}, la forme d'ADR-0046. Aucune migration Alembic — la colonne config est un document JSON, comme pour tiebreak. ### 2. Deux modes en façade, trois au […]",
   "fichier": "docs/adr/0070-profondeur-de-classement-reglee-par-phase.md",
   "identifiant": "0070",
   "liens": [
    {
     "cible": "E06US006",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0004",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0011",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0046",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0061",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0066",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    }
   ],
   "portage": [
    {
     "chemin": "backend/application/prelevement.py",
     "existe": true,
     "symboles": [
      "RegistrePolitiques"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/politiques.py",
     "existe": true,
     "symboles": [
      "ProfondeurClassement",
      "nom",
      "jusqu_au",
      "NomProfondeur",
      "ProfondeurUnVersN",
      "ProfondeurPodium",
      "AucunClassement"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "La profondeur de classement se règle par phase, et son absence reste le podium",
   "us": [
    "E01US015",
    "E01US024",
    "E05US003",
    "E05US010",
    "E05US020",
    "E06US003",
    "E06US004",
    "E06US006"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-04",
   "date_brute": "04/08/2026",
   "extrait": "### 1. Un réglage à quatre positions, porté par le tournoi Cloisonnement — aucun (défaut), categorie, blason, blason_et_categorie — est un value object du domaine (domain/cloisonnement.py), stocké sur l'agrégat Tournoi (colonne tournoi. cloisonnement, migration 0041, NOT NULL avec défaut aucun). - Sur le tournoi, pas sur le gabarit : le gabarit de salle est une brique de patrimoine partagée entre tournois (E01US023) ; deux tournois montés sur le même plan de salle doivent pouvoir cloisonner différemment. - Sur le tournoi, pas sur le départ : la règle est sportive, pas logistique — elle ne change pas d'un créneau à l'autre. C'est aussi ce qui permet au plan de duels (E03US009) d'obéir au […]",
   "fichier": "docs/adr/0071-cloisonnement-categorie-blason-active-et-dur.md",
   "identifiant": "0071",
   "liens": [
    {
     "cible": "E03US007",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0023",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0024",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0047",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0048",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0022",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "Le cloisonnement catégorie/blason est un réglage de tournoi, dur quand il est actif",
   "us": [
    "E01US023",
    "E03US001",
    "E03US004",
    "E03US006",
    "E03US007",
    "E03US009",
    "E12US007"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-05",
   "date_brute": "05/08/2026",
   "extrait": "1. window.confirm est proscrit du produit. Toute confirmation passe par deux composants de shared/ui/ : DialogueConfirmation (le primitif) et BoutonConfirme (le cas courant, « un bouton + une question », qui possède son propre état d'ouverture). 2. On n'ajoute pas de librairie de modale. L'élément \u003cdialog> et showModal() fournissent nativement le piège de focus, la fermeture par Échap, l'inertie de l'arrière-plan et le ::backdrop — c'est-à-dire exactement la liste de ce pour quoi on prendrait une dépendance. La règle 11 du projet dit « stdlib ou quelques lignes maison préférées » ; c'est le même arbitrage qu'ADR-0059 a rendu pour le routeur. 3. Le produit assume une baseline navigateur : […]",
   "fichier": "docs/adr/0072-confirmation-destructrice-dialog-natif.md",
   "identifiant": "0072",
   "liens": [
    {
     "cible": "0059",
     "libelle": "Remplace",
     "sens": "sortant",
     "type": "remplace"
    },
    {
     "cible": "0008",
     "libelle": "Remplace",
     "sens": "sortant",
     "type": "remplace"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "Confirmation d'un geste destructeur : `\u003cdialog>` natif, pas de librairie",
   "us": []
  },
  {
   "amende_par": [],
   "date": "2026-08-05",
   "date_brute": "05/08/2026",
   "extrait": "Trois termes, opposables partout — écrans, PDF, messages d'API, maquettes, glossaire : | Terme | Désigne | Ne désigne jamais | |---|---|---| | pas de tir | un groupement de cibles : la rangée tirée depuis la même ligne de tir | la place d'un archer | | couloir de tir | la place d'un archer devant sa cible, repérée par une lettre (A, B, C, D…) | une rangée, une tablette | | poste | une tablette ou un écran rattaché à un lieu (ADR-0064) | la place d'un archer | « Pas de tir » reste une notion de salle : aucune entité ne la porte, elle ne sert qu'à se repérer à l'écran. Le gabarit de salle reste une liste, pas un plan. La salle du club rentre dans une grille régulière : un gabarit est « N […]",
   "fichier": "docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md",
   "identifiant": "0073",
   "liens": [
    {
     "cible": "E16US001",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0006",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0064",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0024",
     "libelle": "Prolonge",
     "sens": "sortant",
     "type": "complete"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "« Pas de tir » = groupement de cibles, « couloir de tir » = place d'un archer",
   "us": [
    "E01US019",
    "E16US001",
    "E16US004",
    "E16US005",
    "E16US010",
    "E16US011"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-05",
   "date_brute": "05/08/2026",
   "extrait": "1. Les planches de maquettes/ deviennent la référence opposable de mise en page du front. Un écart entre l'écran livré et sa planche est un défaut, constatable en revue, et non plus une divergence tolérée. Les CDC restent au-dessus : en cas de conflit planche ↔ charte, la charte mesurée l'emporte (elle porte les ratios de contraste), et la planche est corrigée. Deux réserves, permanentes, à lire avec la règle : - La fidélité porte sur la mise en page, pas sur le balisage. Là où la planche décrit un rendu qu'une structure sémantique rend mieux — un \u003ctable> contre une pile de \u003cdiv> —, le produit garde la structure et n'en prend que l'apparence. Une planche est dessinée, elle n'est pas lue par […]",
   "fichier": "docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md",
   "identifiant": "0074",
   "liens": [
    {
     "cible": "E17US001",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0058",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "Les maquettes font foi, et la charte mesurée est la source des jetons du front",
   "us": [
    "E01US016",
    "E17US001",
    "E17US002"
   ]
  },
  {
   "amende_par": [
    "0076",
    "0079"
   ],
   "date": "2026-08-06",
   "date_brute": "2026-08-06",
   "extrait": "Le départ est la portée sportive du tournoi. Un départ est une exécution complète de la compétition : il a sa séquence de phases, ses classements, ses tableaux, ses duels et son podium. Les archers de deux départs ne sont jamais comparés. 1. Phase appartient au départ (depart_id), plus au tournoi. SequencePhases valide la suite contiguë 1..N d'un départ ; ses invariants sont inchangés, seule leur portée l'est. 2. Le classement se calcule par départ. calculer_classement reste une fonction pure sur un lot d'archers — c'est l'appelant qui ne lui passe plus que les archers d'un départ. Le rang scratch et le rang de catégorie sont donc des rangs dans le départ. 3. Tableaux, duels, barrages et […]",
   "fichier": "docs/adr/0075-le-depart-est-la-portee-sportive.md",
   "identifiant": "0075",
   "liens": [
    {
     "cible": "0017",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0045",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0076",
     "libelle": "Complété et partiellement révisé par",
     "sens": "entrant",
     "type": "amende"
    },
    {
     "cible": "E01US025",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [
    {
     "chemin": "backend/application/classements.py",
     "existe": true,
     "symboles": [
      "pour_depart",
      "pour_tournoi",
      "phase_id"
     ],
     "symboles_absents": [
      "pour_tournoi",
      "phase_id"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/format_tournoi.py",
     "existe": true,
     "symboles": [
      "appliquer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "Phase.depart_id",
      "SequencePhases"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/moteur.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_portee_sportive.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le départ est la portée sportive, pas seulement un créneau logistique",
   "us": [
    "E00US021",
    "E01US025",
    "E05US026",
    "E05US029",
    "E05US032",
    "E05US034",
    "E05US035",
    "E16US002"
   ]
  },
  {
   "amende_par": [
    "0078"
   ],
   "date": "2026-08-07",
   "date_brute": "2026-08-07",
   "extrait": "Le déroulé est défini une fois, au tournoi ; l'avancement est porté par chaque départ. Tournoi ──► Déroulé : suite d'ÉTAPES (définition, une seule fois) ├── Départ 1 ──► PHASES : l'avancement de chaque étape dans ce créneau └── Départ 2 ──► PHASES : idem, indépendant 1. EtapeDeroule — la définition d'une étape, portée par le tournoi : ordre, type, bareme, validation, sources, effectif, profondeur, barrage_jusqu_au. Aucun statut, aucun départ. C'est ModelePhase (le contenu d'un format) doté d'un tournoi et d'une identité. 2. Phase — l'instance d'une étape dans un créneau : depart_id, ordre, statut, id. Elle reste l'objet du moteur : en mémoire, elle porte toujours sa définition, mais […]",
   "fichier": "docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md",
   "identifiant": "0076",
   "liens": [
    {
     "cible": "0075",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0045",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "E01US025",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/phases.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/departs.py",
     "existe": true,
     "symboles": [
      "ServiceDeparts.creer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/grain_validation.py",
     "existe": true,
     "symboles": [
      "PhaseRepository"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/phases.py",
     "existe": true,
     "symboles": [
      "qualification_representative",
      "qualification_du_tournoi"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/portee.py",
     "existe": true,
     "symboles": [
      "qualification_representative",
      "qualification_du_tournoi"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule_etape.py",
     "existe": true,
     "symboles": [
      "EtapeDeroule",
      "Phase",
      "SequencePhases"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/format_tournoi.py",
     "existe": true,
     "symboles": [
      "appliquer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "EtapeDeroule",
      "Phase",
      "SequencePhases"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/models.py",
     "existe": true,
     "symboles": [
      "DerouleEtapeORM",
      "PhaseORM"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_portee_sportive.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un déroulé défini une fois, un avancement par départ",
   "us": [
    "E01US025"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-07",
   "date_brute": "2026-08-07",
   "extrait": "Le tournoi suit le protocole de l'archer engagé (ADR-0016) : on signale, l'admin confirme, puis on détruit — en cascade applicative, jamais par ON DELETE CASCADE en base. 1. Un tournoi vide se supprime sans rien demander. Aucun signalement inutile : la confirmation doit rester rare pour rester lue. 2. Un tournoi peuplé est signalé en 409, avec un décompte chiffré de ce qui partira — archers, inscriptions, scores, séries, duels, forfaits, barrages, remboursements. « Une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection » (D-16) : le message nomme les natures et leurs nombres, il ne dit pas « des données existent ». 3. L'admin confirme explicitement […]",
   "fichier": "docs/adr/0077-supprimer-un-tournoi-signaler-puis-confirmer.md",
   "identifiant": "0077",
   "liens": [
    {
     "cible": "0016",
     "libelle": "Étend",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0015",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "E01US025",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Supprimer un tournoi : signaler sa descendance, puis confirmer — jamais cascader en silence",
   "us": [
    "E01US002",
    "E01US025",
    "E02US003",
    "E02US009",
    "E02US010"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-07",
   "date_brute": "2026-08-07",
   "extrait": "Le lien entre une phase et sa définition, et entre une source et sa phase amont, passe par une identité — le rang ne décrit plus que l'ordre d'affichage. 1. phase.etape_id → deroule_etape.id (clé étrangère). Le rang reste porté par la seule étape ; l'avancement d'un créneau n'a plus besoin d'en connaître un. 2. SourcePhase.ordre_source devient etape_source_id dans les config d'une édition concrète (deroule_etape), avec migration des JSON existants. 3. FormatTournoi garde l'ancrage par ordre — et c'est la partie asymétrique de la décision. Ses ModelePhase n'ont pas d'identité, par construction (ADR-0060 §5) : un format de bibliothèque décrit un déroulé type, réutilisable, dont les étapes […]",
   "fichier": "docs/adr/0078-la-sequence-s-ancre-sur-l-identite-de-l-etape.md",
   "identifiant": "0078",
   "liens": [
    {
     "cible": "0045",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0076",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "La séquence s'ancre sur l'identité de l'étape, pas sur son rang",
   "us": [
    "E05US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-08",
   "date_brute": "08/08/2026",
   "extrait": "### 1. Un interrupteur unique, en tête de l'écran public Le spectateur choisit une fois « je regarde mes archers » et ne le redit pas à chaque onglet. L'alternative — un sélecteur par vue — est écartée : elle obligeait à répéter le même geste six fois, et surtout elle rendait deux interrupteurs simultanément visibles sur l'écran « Tableaux », où le sélecteur local et l'interrupteur global auraient fini par se contredire. Conséquence assumée : la combinaison « mon chemin sur les tableaux et classement complet » n'est plus exprimable. C'est une perte réelle par rapport à E07US005, jugée acceptable — personne ne l'avait demandée, et le coût du doublon contradictoire est certain quand celui de […]",
   "fichier": "docs/adr/0079-un-seul-interrupteur-mes-archers-pour-tout-l-onglet-public.md",
   "identifiant": "0079",
   "liens": [
    {
     "cible": "0039",
     "libelle": "Remplace",
     "sens": "sortant",
     "type": "remplace"
    },
    {
     "cible": "0075",
     "libelle": "Remplace",
     "sens": "sortant",
     "type": "remplace"
    }
   ],
   "portage": [
    {
     "chemin": "frontend/src/features/competition/VueClassement.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/palmares/VuePalmares.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/placement/PlanCiblesPublic.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/public/AccueilPublic.tsx",
     "existe": true,
     "symboles": [
      "BasculeAffichage"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/routage/VueAffectations.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/tableaux/VueTableaux.tsx",
     "existe": true,
     "symboles": [
      "suivis"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/stores/sessionSuivisStore.ts",
     "existe": true,
     "symboles": [
      "centrerSurSuivis"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/suivis/focus.ts",
     "existe": true,
     "symboles": [
      "centrerCibles",
      "modeEffectif"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "Un seul interrupteur « mes archers / tout » pour tout l'onglet public",
   "us": [
    "E06US001",
    "E07US005",
    "E07US006",
    "E16US004"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-08",
   "date_brute": "2026-08-08",
   "extrait": "Chaque prélèvement est résolu dans le classement de la phase qu'il désigne. ### 1. preleves reçoit un résolveur, pas un ordre privilégié La signature passe de preleves(phase, classement, ordre_qualification) à preleves(phase, classement, resoudre_source), où resoudre_source: Callable[[int], Classement | None]. Un résolveur et non une table pré-calculée : résoudre un tableau amont coûte une reconstruction complète, on ne la paie donc que pour les ordres réellement déclarés en source. tranche (ADR-0068 §5) suit la même règle, et pour la même raison : un décalage calculé sur une autre base que celle qui a peuplé le tableau situerait ses positions dans le mauvais espace de rangs — c'était […]",
   "fichier": "docs/adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md",
   "identifiant": "0080",
   "liens": [
    {
     "cible": "0068",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0061",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0065",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0067",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0075",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/application/palmares.py",
     "existe": true,
     "symboles": [
      "tranche"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/placement_duels.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/prelevement.py",
     "existe": true,
     "symboles": [
      "ResolveurClassement",
      "preleves",
      "tranche"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/saisie_duels.py",
     "existe": true,
     "symboles": [
      "resolveur_de_classement",
      "_classement_de_l_ordre",
      "_decor"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/bootstrap/composition.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/classement_de_tableau.py",
     "existe": true,
     "symboles": [
      "classement_de_tableau",
      "aggregation"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule.py",
     "existe": true,
     "symboles": [
      "_TYPES_CLASSANTS_LUS",
      "_source_lisible",
      "_inscrits_pour_classer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_effectif_minimum.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_prelevement_phase_source.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un prélèvement lit le classement de **sa** phase source",
   "us": [
    "E01US024",
    "E05US020",
    "E05US021",
    "E05US023",
    "E05US024",
    "E05US025",
    "E06US004",
    "E16US002"
   ]
  },
  {
   "amende_par": [
    "0085"
   ],
   "date": "2026-08-08",
   "date_brute": "2026-08-08",
   "extrait": "Une fenêtre de prélèvement est honorée si et seulement si elle ne coupe aucun bloc de rangs encore indécis. « Couper », c'est chevaucher sans contenir. 1. domain/classement_de_tableau.py rend un ClassementSource — le classement plus la liste des plages_indecises, blocs de rangs portés par des archers encore en lice. Les rangs provisoires continuent d'être produits : le palmarès en a besoin pour situer tout le monde à chaque instant. Ce qui change, c'est qu'ils sont désormais étiquetés. 2. application/prelevement.py:preleves lève PrelevementEnAttente quand la fenêtre coupe un de ces blocs. Le raisonnement d'ADR-0080 §2 est préservé, pas jeté : une fenêtre qui contient entièrement le bloc […]",
   "fichier": "docs/adr/0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md",
   "identifiant": "0081",
   "liens": [
    {
     "cible": "E05US024",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0080",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0065",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0067",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/tableaux.py",
     "existe": true,
     "symboles": [
      "TableauPublicReponse.en_attente_de"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/colline.py",
     "existe": true,
     "symboles": [
      "_achevee",
      "classement_de_phase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/erreurs/moteur.py",
     "existe": true,
     "symboles": [
      "PrelevementEnAttente",
      "ordre_source",
      "DerouleCyclique"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/palmares.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/placement_duels.py",
     "existe": true,
     "symboles": [
      "_charger"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/prelevement.py",
     "existe": true,
     "symboles": [
      "preleves",
      "PrelevementEnAttente",
      "tranche"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/saisie_duels.py",
     "existe": true,
     "symboles": [
      "_classement_de_l_ordre",
      "ClassementSource",
      "rang_premier"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/simulation.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/tableaux_publics.py",
     "existe": true,
     "symboles": [
      "pour_depart"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/classement_de_colline.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/classement_de_tableau.py",
     "existe": true,
     "symboles": [
      "ClassementSource.plages_indecises",
      "rang_premier"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/tableaux/VueTableaux.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "une phase attend que sa source ait départagé les places qu'elle prélève",
   "us": [
    "E05US020",
    "E05US024",
    "E05US027"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-09",
   "date_brute": "2026-08-09",
   "extrait": "Un déroulé peut porter plusieurs phases de qualification. L'invariant d'unicité est retiré, et les lecteurs qui le supposaient sont réparés — c'était l'ordre des opérations que le pansement avait inversé. ### 1. La feuille de marque pend à sa phase La clé de Serie descend de (tournoi, archer) à (phase, archer). tournoi_id reste comme cadre des vues d'ensemble, mais n'est plus une clé. Cela résorbe DETTE-046 sans détour. Le registre signalait qu'un archer inscrit sur deux créneaux n'avait qu'un emplacement pour ses flèches — la seconde série écrasant la première — et proposait Serie.depart_id. La phase subsume le départ (elle lui appartient depuis ADR-0075) : un seul champ règle les deux […]",
   "fichier": "docs/adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md",
   "identifiant": "0082",
   "liens": [
    {
     "cible": "0069",
     "libelle": "Amende",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0075",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0076",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0080",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0068",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/bareme_qualification.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/bareme_qualification.py",
     "existe": true,
     "symboles": [
      "definir_pour_etape",
      "qualifications"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/classements.py",
     "existe": true,
     "symboles": [
      "pour_phase",
      "_premiere_qualification"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/completude.py",
     "existe": true,
     "symboles": [
      "_jugements_du_creneau",
      "_population",
      "_est_clos"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/feuille_de_marque.py",
     "existe": true,
     "symboles": [
      "_bareme_du_creneau"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/grain_validation.py",
     "existe": true,
     "symboles": [
      "definir_pour_etape",
      "qualifications"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/palmares.py",
     "existe": true,
     "symboles": [
      "_resultat_qualification"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/phases.py",
     "existe": true,
     "symboles": [
      "ajouter"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/portee.py",
     "existe": true,
     "symboles": [
      "qualification_courante",
      "la_plus_courante",
      "qualification_du_tournoi",
      "forfaits",
      "feuille_de_marque"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/prelevement.py",
     "existe": true,
     "symboles": [
      "LecteurPopulationPhase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/saisie.py",
     "existe": true,
     "symboles": [
      "_qualification_de_l_archer",
      "_admet",
      "_phase_qualification_ou_none",
      "_etat_dans",
      "_feuille"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/saisie_duels.py",
     "existe": true,
     "symboles": [
      "_classement_de_l_ordre",
      "QUALIFICATION",
      "preleves",
      "tranche"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/palmares.py",
     "existe": true,
     "symboles": [
      "ResultatPhase.origine",
      "decerne"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "_anomalies_unicite_qualification"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/ports.py",
     "existe": true,
     "symboles": [
      "SerieRepository",
      "par_phase",
      "par_tournoi"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/serie.py",
     "existe": true,
     "symboles": [
      "Serie.phase_id"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/models.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/migrations/versions/0044_serie_par_phase.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_bareme_qualification_api.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_palmares_qualifications_multiples.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_phase.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_migration_0044_serie_par_phase.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/bareme/",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/grain-validation/",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Plusieurs qualifications dans un même déroulé",
   "us": [
    "E05US021",
    "E05US025",
    "E06US004"
   ]
  },
  {
   "amende_par": [
    "0084",
    "0085"
   ],
   "date": "2026-08-09",
   "date_brute": "2026-08-09, **amendé le 2026-08-14** (E05US028 — le contrat cède où le §2 l'annonçait : une capacité renommée, cf. § « Ce que le contrat a appris de sa **deuxième** mise à l'épreuve »)",
   "extrait": "### 1. Un contrat de phase jouable, résolu par type Ce qu'une phase doit savoir répondre pour être jouable tient en six questions — celles que les dix tables ci-dessus posaient chacune dans son coin : > 🔄 Une 7ᵉ question s'est ajoutée le 18/08/2026 — en combien de tours, et sous quel nom ? > (ContratDePhase.unite_de_tour, ADR-0090). > Elle est décrite là-bas et n'est pas reprise ici, mais ce paragraphe ne dit plus six sans le > dire : un lecteur qui arrive par cet ADR pour ajouter un type de phase en oublierait une. C'est > exactement le mode de défaillance que les deux encarts ⚠️ de cet ADR documentent déjà — un > paragraphe qui porte l'affirmation inverse du code livré. Relevé en revue […]",
   "fichier": "docs/adr/0083-le-contrat-de-phase-jouable.md",
   "identifiant": "0083",
   "liens": [
    {
     "cible": "0045",
     "libelle": "Précise",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0062",
     "libelle": "Précise",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0046",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0024",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0048",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0068",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/big_shoot_off.py",
     "existe": true,
     "symboles": [
      "ReglageBigShootOffDTO"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/api/v1/formats.py",
     "existe": true,
     "symboles": [
      "ReglageBigShootOffDTO",
      "ReglagePoulesDTO"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/api/v1/phases.py",
     "existe": true,
     "symboles": [
      "ReglageBigShootOffDTO",
      "ReglagePoulesDTO"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/api/v1/poules.py",
     "existe": true,
     "symboles": [
      "saisie_duels"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/big_shoot_off.py",
     "existe": true,
     "symboles": [
      "ServiceBigShootOff",
      "duel",
      "serie",
      "volee",
      "LecteurEtatBigShootOff",
      "LecteurClassementBigShootOff"
     ],
     "symboles_absents": [
      "LecteurClassementBigShootOff"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/application/palmares.py",
     "existe": true,
     "symboles": [
      "_resultat_big_shoot_off",
      "_resultat",
      "TYPES_RECONSTRUCTIBLES"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/placement_duels.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/poules.py",
     "existe": true,
     "symboles": [
      "ServicePoules",
      "classement_de_phase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/prelevement.py",
     "existe": true,
     "symboles": [
      "LecteurClassementDePhase",
      "ServicePoules",
      "ServiceSaisieDuels",
      "LecteurClassementPoules",
      "LecteurClassementBigShootOff"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/routage.py",
     "existe": true,
     "symboles": [
      "_routage_big_shoot_off",
      "ProchaineManche",
      "IssueRoutage.PROCHAINE_MANCHE",
      "plan_de_cibles",
      "AUCUN"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/saisie_duels.py",
     "existe": true,
     "symboles": [
      "_classement_de_l_ordre",
      "brancher_lecteur",
      "TYPES_DELEGUES",
      "brancher_poules",
      "classement_lisible"
     ],
     "symboles_absents": [
      "brancher_poules"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/application/simulation_format.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/suisse.py",
     "existe": true,
     "symboles": [
      "ServiceSuisse",
      "rondes_maximales",
      "conflits"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/bootstrap/composition.py",
     "existe": true,
     "symboles": [
      "ServicePoules"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/classement_de_poules.py",
     "existe": true,
     "symboles": [
      "RangPoule",
      "LigneClassement",
      "Tiebreak",
      "classement_de_tableau"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/classement_de_suisse.py",
     "existe": true,
     "symboles": [
      "ServiceSuisse",
      "rondes_maximales",
      "conflits"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/contrat_phase.py",
     "existe": true,
     "symboles": [
      "saisie_duels.TYPES_DELEGUES",
      "palmares._TYPES_CLASSANTS_AU_PALMARES",
      "TYPES_EN_TABLEAU",
      "TYPES_DEROULES",
      "TYPES_CLASSANTS_LUS",
      "TYPES_EN_TABLEAU_JOUE",
      "TYPES_JOUES",
      "TYPES_SIGNALES_EN_ECART",
      "deroule_par_un_service",
      "monte_les_oppositions",
      "TYPES_MONTES",
      "BIG_SHOOT_OFF",
      "classement_lisible",
      "route_l_archer",
      "True",
      "route_tout_le_plateau",
      "TYPES_ROUTES_IMPLICITEMENT"
     ],
     "symboles_absents": [
      "saisie_duels.TYPES_DELEGUES",
      "palmares._TYPES_CLASSANTS_AU_PALMARES"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule.py",
     "existe": true,
     "symboles": [
      "_TYPES_DEROULES",
      "_TYPES_CLASSANTS_LUS",
      "_anomalies_choc_de_poule"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule_etape.py",
     "existe": true,
     "symboles": [
      "big_shoot_off",
      "_lire_reglage_big_shoot_off",
      "config",
      "config.poules"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/format_tournoi.py",
     "existe": true,
     "symboles": [
      "big_shoot_off",
      "_lire_reglage_big_shoot_off",
      "config",
      "config.poules"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "Phase.poules",
      "ReglageDePoulesInvalide",
      "big_shoot_off",
      "_lire_reglage_big_shoot_off",
      "config",
      "config.poules"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/placement_par_bloc.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/poule.py",
     "existe": true,
     "symboles": [
      "ReglageDePoules",
      "pour_effectif",
      "produit_un_classement",
      "produit_des_qualifies",
      "nb_poules_pour",
      "couloirs_occupes",
      "ReglageDePoules.departage_inter_poules",
      "config.poules.departage"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/suisse.py",
     "existe": true,
     "symboles": [
      "ServiceSuisse",
      "rondes_maximales",
      "conflits"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/models.py",
     "existe": true,
     "symboles": [
      "PlacementParBlocORM",
      "placement_poule",
      "placement_par_bloc",
      "poule_numero",
      "groupe_numero"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/moteur.py",
     "existe": true,
     "symboles": [
      "big_shoot_off",
      "_lire_reglage_big_shoot_off",
      "config",
      "config.poules",
      "_lire_reglage_poules"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_big_shoot_off.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_contrat_phase.py",
     "existe": true,
     "symboles": [
      "ServiceRoutage._routage_par_rencontres",
      "ProchainDuel",
      "_resultat_classant",
      "_resultat",
      "ScoreAvecHandicap",
      "RoutingRepechage"
     ],
     "symboles_absents": [
      "ProchainDuel",
      "_resultat_classant",
      "ScoreAvecHandicap",
      "RoutingRepechage"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_placement_par_bloc.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/big-shoot-off/SaisieBigShootOff.tsx",
     "existe": true,
     "symboles": [
      "DecorDeSaisie.VOLEE_COLLECTIVE"
     ],
     "symboles_absents": [
      "DecorDeSaisie.VOLEE_COLLECTIVE"
     ],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/poules/SaisiePoules.tsx",
     "existe": true,
     "symboles": [
      "DuelCharge",
      "poule"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/saisie-duels/api.ts",
     "existe": true,
     "symboles": [
      "ROUTES",
      "CLE_DECOR",
      "PHOTO",
      "Record"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/saisie-duels/hooks.ts",
     "existe": true,
     "symboles": [
      "ROUTES",
      "CLE_DECOR",
      "PHOTO",
      "Record"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suisse/ClassementSuisse.tsx",
     "existe": true,
     "symboles": [
      "RONDES_APPARIEES",
      "DuelCharge",
      "suisse"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suisse/SaisieSuisse.tsx",
     "existe": true,
     "symboles": [
      "RONDES_APPARIEES",
      "DuelCharge",
      "suisse"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suisse/presentation.ts",
     "existe": true,
     "symboles": [
      "RONDES_APPARIEES",
      "DuelCharge",
      "suisse"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/ReglageBigShootOff.tsx",
     "existe": true,
     "symboles": [
      "paliers_pour"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/ReglagePoules.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/ReglageSuisse.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/bigShootOff.ts",
     "existe": true,
     "symboles": [
      "paliers_pour"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/catalogue.ts",
     "existe": true,
     "symboles": [
      "TYPES_SIGNALES_EN_ECART"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/poules.ts",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/suisse.ts",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/stores/fileDuelsHorsLigneStore.ts",
     "existe": true,
     "symboles": [
      "FamilleDuel",
      "tableau",
      "poule",
      "suisse"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le contrat de phase jouable, et les poules pour le tailler",
   "us": [
    "E01US024",
    "E04US009",
    "E04US013",
    "E05US015",
    "E05US021",
    "E05US023",
    "E05US024",
    "E05US025",
    "E05US026",
    "E05US028",
    "E05US030",
    "E05US032"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-15",
   "date_brute": "2026-08-15",
   "extrait": "### 1. Un port unique, LecteurClassementDePhase Les deux protocoles sont fondus en un. Il pose une question — « quel classement cette phase a-t-elle produit ? » — et il est réalisé par chaque service de format. ### 2. Le type de phase devient un argument, pas un nom de méthode brancher_poules(...) et brancher_big_shoot_off(...) deviennent brancher_lecteur(TypePhase.POULES, ...). Les slots nommés deviennent un dict[TypePhase, LecteurClassementDePhase], et la cascade de if une recherche. Ajouter un format ne touche plus ni le port, ni le service : seulement une ligne au composition root. ### 3. La liste des types délégués dérive du registre de contrat python TYPES_DELEGUES = […]",
   "fichier": "docs/adr/0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md",
   "identifiant": "0084",
   "liens": [
    {
     "cible": "0083",
     "libelle": "Précise",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0080",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0081",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un seul port de lecture de classement, résolu par type",
   "us": [
    "E05US023",
    "E05US026",
    "E05US027",
    "E05US028"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-16",
   "date_brute": "2026-08-16",
   "extrait": "### 1. Le critère est structurel, pas typologique > Une phase décerne ses rangs — donc peut donner une médaille — si et seulement si aucune > phase avale ne prélève dedans. Le critère se lit sur le graphe des sources du déroulé, pas sur TypePhase. La même phase de poules titre dans un format qui s'arrête là, et ne titre pas dans un format qui enchaîne, sans que l'organisateur ait quoi que ce soit à régler. Il se lit sur ordre et non sur l'identité, parce que c'est ainsi qu'une source désigne sa phase (SourcePhase.ordre_source) : c'est l'ancrage par ordre de DETTE-026, et s'en écarter ici créerait une seconde convention. ### 2. Deux régimes, portés par origine - phase consommée → […]",
   "fichier": "docs/adr/0085-une-phase-decerne-ses-rangs-si-rien-ne-preleve-dedans.md",
   "identifiant": "0085",
   "liens": [
    {
     "cible": "0067",
     "libelle": "Précise",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0081",
     "libelle": "Précise",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0083",
     "libelle": "Précise",
     "sens": "sortant",
     "type": "amende"
    }
   ],
   "portage": [],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Une phase décerne ses rangs si rien ne prélève dedans",
   "us": [
    "E05US025",
    "E05US026",
    "E05US029"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-15",
   "date_brute": "2026-08-15",
   "extrait": "Cinq points. 1. Un site isolé, généré, sans autorité. atlas/ sert un site statique lu depuis CLAUDE.md et docs/adr/. L'atlas ne remplace rien : chaque page nomme sa source, aucun corps de texte n'y est dupliqué, et le supprimer ne perdrait aucune information. Pourquoi ce n'est pas le wiki rejeté par ADR-0001. Le mode de défaillance qu'ADR-0001 redoutait est la désynchronisation. Ici elle est rendue impossible par construction : les données sont régénérées depuis le dépôt et la CI échoue si elles divergent. Un wiki externe se désynchronise parce que personne ne le régénère ; un artefact dérivé sous porte mécanique, non. Sans la porte, cet ADR contredirait ADR-0001 — c'est le point 3 qui rend […]",
   "fichier": "docs/adr/0086-un-atlas-genere-le-depot-cartographie-sans-dependance.md",
   "identifiant": "0086",
   "liens": [
    {
     "cible": "E00US018",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E00US019",
     "libelle": "Introduit par",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0001",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0009",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0063",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0075",
     "libelle": "Lie",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": ".gitattributes",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": ".github/workflows/ci.yml",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": ".pre-commit-config.yaml",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "atlas/code.html",
     "existe": true,
     "symboles": [
      "Pages.carte"
     ],
     "symboles_absents": [],
     "verifiable": false
    },
    {
     "chemin": "atlas/statique/pages.js",
     "existe": true,
     "symboles": [
      "Pages.carte"
     ],
     "symboles_absents": [],
     "verifiable": false
    },
    {
     "chemin": "backend/atlas/avancement.py",
     "existe": true,
     "symboles": [
      "construire"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/atlas/carte.py",
     "existe": true,
     "symboles": [
      "construire",
      "violations"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/atlas/controles.py",
     "existe": true,
     "symboles": [
      "verifier",
      "verifier_avancement",
      "verifier_code"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/atlas/normalisation.py",
     "existe": true,
     "symboles": [
      "_RELATIONS"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/atlas/rendu.py",
     "existe": true,
     "symboles": [
      "serialiser",
      "ecarts"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/atlas/sources/adr.py",
     "existe": true,
     "symboles": [
      "lire_decisions"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/atlas/sources/backlog.py",
     "existe": true,
     "symboles": [
      "lire_epics",
      "lire_dettes",
      "lire_us_specifiees"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/atlas/sources/code.py",
     "existe": true,
     "symboles": [
      "SENS_AUTORISE",
      "autorise",
      "lire_aretes",
      "lire_ports",
      "lire_aretes_front",
      "lister_features",
      "enchevetrements",
      "_fichiers_python"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/atlas/sources/reglement.py",
     "existe": true,
     "symboles": [
      "lire_regles"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/atlas/sources/suivi.py",
     "existe": true,
     "symboles": [
      "lire_sections",
      "compter",
      "lire_entete"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_atlas_avancement.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_atlas_carte.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_atlas_coherence.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_atlas_contrats.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_atlas_corpus.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_atlas_historique.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_atlas_site.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_isolation.py",
     "existe": true,
     "symboles": [
      "atlas"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un atlas généré : le dépôt cartographié en site statique, sans dépendance de rendu",
   "us": [
    "E00US018",
    "E00US019",
    "E00US020",
    "E05US026",
    "E05US028",
    "E05US030"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-16",
   "date_brute": "2026-08-16",
   "extrait": "### 1. EN_ATTENTE est une issue à part entière, pas un INDISPONIBLE motivé Sixième valeur de IssueRoutage, de même nature que REPECHE (ADR-0065 §2) : elle sépare deux situations métier que le champ motif ne pouvait distinguer que pour un lecteur humain. Ce qui la justifie n'est pas la formulation du message, c'est le classement de l'archer : EN_ATTENTE compte parmi ceux qui tirent encore, INDISPONIBLE non. Les trois cas de ServiceRoutage._sans_rencontre sont désormais distincts de bout en bout : | Situation | Issue | Ce que l'écran en fait | |---|---|---| | Il n'est pas dans cette phase | INDISPONIBLE | rangé hors course, motif affiché | | La phase est épuisée, ou il a fini | TERMINE | […]",
   "fichier": "docs/adr/0087-une-attente-n-est-pas-une-indisponibilite.md",
   "identifiant": "0087",
   "liens": [
    {
     "cible": "E05US030",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0065",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0083",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    },
    {
     "cible": "0084",
     "libelle": "Voisins",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/routage.py",
     "existe": true,
     "symboles": [
      "IssueRoutageReponse"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/routage.py",
     "existe": true,
     "symboles": [
      "IssueRoutage.EN_ATTENTE",
      "ServiceRoutage._sans_rencontre"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_routage_api.py",
     "existe": true,
     "symboles": [
      "test_issue_reponse_est_le_miroir_de_l_enumeration",
      "Literal"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_service_routage.py",
     "existe": true,
     "symboles": [
      "_router_sans_rencontre",
      "EN_ATTENTE",
      "TERMINE",
      "INDISPONIBLE"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/routage/api.ts",
     "existe": true,
     "symboles": [
      "IssueRoutage"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/routage/presentation.test.ts",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/routage/presentation.ts",
     "existe": true,
     "symboles": [
      "EN_LICE",
      "partitionner",
      "titre"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "accepté",
   "titre": "Une attente n'est pas une indisponibilité",
   "us": [
    "E05US026",
    "E05US027",
    "E05US030",
    "E05US032"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-16",
   "date_brute": "2026-08-16",
   "extrait": "1. Tout sous-agent réutilisable du dépôt est un fichier versionné de .claude/agents/. Il voyage entre les postes, il se relit, il se diffe, il passe en revue comme le reste du code. Un sous-agent défini à la volée dans un prompt n'est pas reproductible et n'a pas de mémoire d'un poste à l'autre. 2. Son modèle est épinglé au frontmatter, jamais hérité. Le critère est celui de CLAUDE.md : | Ce que fait l'agent | Modèle | Pourquoi | |---|---|---| | Juger — les cinq relecteurs de /revue-us | opus | Barrière qualité. Elle ne s'optimise pas (ADR-0013) | | Localiser — localiser | sonnet | Beaucoup d'entrée, peu de jugement. Pas haiku : 200 K de contexte, et ce dépôt peut le saturer — une […]",
   "fichier": "docs/adr/0088-les-sous-agents-du-depot-sont-versionnes-et-a-modele-epingle.md",
   "identifiant": "0088",
   "liens": [],
   "portage": [
    {
     "chemin": "backend/tests/test_agents_de_revue.py",
     "existe": true,
     "symboles": [
      "Edit",
      "Write"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Les sous-agents du dépôt sont versionnés et à modèle épinglé",
   "us": []
  },
  {
   "amende_par": [],
   "date": "2026-08-18",
   "date_brute": "2026-08-18",
   "extrait": "### 1. La vue s'appelle « En cours » et montre la phase qui se joue, quel que soit son format VueEcran.TABLEAUX devient VueEcran.EN_COURS, et l'onglet public « Tableaux » devient « En cours ». La vue rend l'arbre de duels comme avant, et en plus la poule, la ronde de système suisse et la manche de Big Shoot Off. Pourquoi pas garder « Tableaux ». Le glossaire définit Tableau comme un « arbre de matchs à élimination » : c'est le nom d'un format, pas d'un contenant. Le garder sur une vue qui rend aussi une poule aurait fait dire au code et à la base quelque chose de faux — la règle 3 exige un vocabulaire cohérent entre code, API, UI et doc, et c'est exactement le genre d'écart qui ne se […]",
   "fichier": "docs/adr/0089-le-catalogue-de-vues-porte-des-phases-pas-des-arbres.md",
   "identifiant": "0089",
   "liens": [
    {
     "cible": "0064",
     "libelle": "Révise",
     "sens": "sortant",
     "type": "amende"
    },
    {
     "cible": "0079",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0083",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0076",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/big_shoot_off.py",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/ecran.py",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/migrations/versions/0047_vue_en_cours.py",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/big-shoot-off/VueBigShootOffPublique.tsx",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/ecrans/api.ts",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/en-cours/VueEnCours.tsx",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/en-cours/presentation.ts",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/poules/VuePoulesPublique.tsx",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/public/AccueilPublic.tsx",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/salle/EcranSalle.tsx",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suisse/VueSuissePublique.tsx",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/tableaux/VueTableaux.tsx",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/duels/LigneRencontre.tsx",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/duels/rencontre.ts",
     "existe": true,
     "symboles": [
      "VueEcran.EN_COURS",
      "EtatPubliqueReponse",
      "TireurPubliqueReponse",
      "ManchePubliqueReponse",
      "FormatPubliqueReponse",
      "VueEcran",
      "LIBELLE_VUE",
      "TOUTES_LES_VUES",
      "switch",
      "phaseAAtterrir",
      "phaseId"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le catalogue de vues porte des **phases**, pas des arbres",
   "us": [
    "E05US023",
    "E05US026",
    "E05US027",
    "E05US028",
    "E05US030",
    "E05US032",
    "E16US004"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-18",
   "date_brute": "2026-08-18",
   "extrait": "### 1. Le tour est l'unité d'avancement générique d'une phase Toute phase, quel que soit son type, compte N tours numérotés de 1 à N, et sait dire lequel est en cours. Aucun type n'en est exclu — la qualification et l'échauffement en comptent un, ce qui est vrai (la phase entière est un tour) et non un cas dégénéré à traiter à part. ### 2. Un tour est une unité d'avancement, jamais de classement C'est l'invariant central, et c'est celui que le code viole aujourd'hui. - Certaines phases classent au fil des tours : chaque tour d'une élimination directe attribue une tranche de rangs — le braquet, la Règle R de moteur-placement-lucky-loser.md. - D'autres ne classent qu'à la fin : une […]",
   "fichier": "docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md",
   "identifiant": "0090",
   "liens": [
    {
     "cible": "E05US032",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E05US033",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0083",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0084",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/application/poules.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/suivi_deroule.py",
     "existe": true,
     "symboles": [
      "LecteurAvancementDePhase",
      "ServiceSuiviDeroule"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/bootstrap/composition.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/contrat_phase.py",
     "existe": true,
     "symboles": [
      "UniteDeTour",
      "ContratDePhase.unite_de_tour"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/suivi_deroule.py",
     "existe": true,
     "symboles": [
      "AvancementBloc",
      "TourBraquet"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/tour_de_phase.py",
     "existe": true,
     "symboles": [
      "unite_de_tour",
      "libelle_de_tour",
      "domain.tableau.libelle_tour"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Une phase avance par tours ; un tour n'est pas un braquet",
   "us": [
    "E05US032",
    "E05US033",
    "E07US005"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-19",
   "date_brute": "2026-08-19",
   "extrait": "### 1. Un arrêt se pose après un tour, jamais à une heure ArretProgramme(apres_tour, portee). Le tour est l'unité d'avancement générique posée par ADR-0090 : c'est ce qui rend un arrêt exprimable sur les six formats sans un cas par format. Le planning horaire de journée (« pause repas 12h–13h30 », l'application calculant quel tour tombe avant) est un besoin futur annoncé par le commanditaire le 19/08/2026, hors du besoin d'aujourd'hui. Il n'est pas anticipé : un déclencheur polymorphe posé sur une évolution supposée est exactement ce que le § Dette de CLAUDE.md interdit — un remède structurel se propose sur preuve dans le code du jour, 3ᵉ occurrence réelle, et il y en a une. Cet ADR se […]",
   "fichier": "docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md",
   "identifiant": "0091",
   "liens": [
    {
     "cible": "E05US033",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E05US034",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0090",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0076",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0045",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0056",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/phases.py",
     "existe": true,
     "symboles": [
      "lever",
      "relancer_arret",
      "RelanceDesArrets"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/arrets_programmes.py",
     "existe": true,
     "symboles": [
      "phases_a_arreter",
      "_armer_sur_le_depart",
      "_resoudre_les_arrets_armes",
      "_avancement_connu",
      "lever",
      "relancer_arret",
      "RelanceDesArrets",
      "evaluer",
      "avancement_par_phase",
      "_appliquer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/big_shoot_off.py",
     "existe": true,
     "symboles": [
      "refuser_si_en_pause"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/gel_de_pause.py",
     "existe": true,
     "symboles": [
      "refuser_si_en_pause"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/poules.py",
     "existe": true,
     "symboles": [
      "refuser_si_en_pause"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/routage.py",
     "existe": true,
     "symboles": [
      "_en_pause"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/saisie.py",
     "existe": true,
     "symboles": [
      "refuser_si_en_pause",
      "corriger_volee",
      "saisir_manche",
      "saisir_barrage",
      "projection",
      "etat"
     ],
     "symboles_absents": [
      "saisir_manche",
      "saisir_barrage",
      "projection"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/application/saisie_duels.py",
     "existe": true,
     "symboles": [
      "refuser_si_en_pause"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/suisse.py",
     "existe": true,
     "symboles": [
      "refuser_si_en_pause"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/suivi_deroule.py",
     "existe": true,
     "symboles": [
      "evaluer",
      "avancement_par_phase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/bootstrap/composition.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/arret_programme.py",
     "existe": true,
     "symboles": [
      "ArretProgramme",
      "verifier_arrets",
      "arrets_atteints",
      "FranchissementArret",
      "EtatFranchissement",
      "FranchissementArretORM",
      "phases_a_arreter",
      "_armer_sur_le_depart",
      "_resoudre_les_arrets_armes",
      "_avancement_connu"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule_etape.py",
     "existe": true,
     "symboles": [
      "EtapeDeroule.arrets",
      "_verifier_arrets_applicables",
      "_politiques_json",
      "_lire_arrets",
      "Phase",
      "EtapeDeroule.instancier",
      "TYPES_DEROULES",
      "TYPES_ARRETABLES",
      "ServicePhases.modifier"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/format_tournoi.py",
     "existe": true,
     "symboles": [
      "ModelePhase.arrets",
      "pour_tournoi",
      "d_etape"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/models.py",
     "existe": true,
     "symboles": [
      "FranchissementArret",
      "EtatFranchissement",
      "FranchissementArretORM"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/moteur.py",
     "existe": true,
     "symboles": [
      "EtapeDeroule.arrets",
      "_verifier_arrets_applicables",
      "_politiques_json",
      "_lire_arrets"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/deroule/Deroule.tsx",
     "existe": true,
     "symboles": [
      "ReglageBarrage",
      "PUT"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/phases/Arrets.test.tsx",
     "existe": true,
     "symboles": [
      "_verifier_arrets_applicables",
      "TYPES_DEROULES",
      "TYPES_ARRETABLES",
      "Phase",
      "ServicePhases.modifier",
      "ReglageBarrage",
      "PUT"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/phases/Phases.tsx",
     "existe": true,
     "symboles": [
      "ReglageBarrage",
      "PUT"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suivi-deroule/PilotageCreneau.tsx",
     "existe": true,
     "symboles": [
      "lever",
      "relancer_arret",
      "RelanceDesArrets"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suivi-deroule/hooks.ts",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/ReglageArrets.tsx",
     "existe": true,
     "symboles": [
      "ReglageBarrage",
      "PUT"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/arrets.ts",
     "existe": true,
     "symboles": [
      "ReglageBarrage",
      "PUT"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/catalogue.ts",
     "existe": true,
     "symboles": [
      "_verifier_arrets_applicables",
      "TYPES_DEROULES",
      "TYPES_ARRETABLES",
      "Phase",
      "ServicePhases.modifier"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un arrêt programmé coupe le déroulé à la fin d'un tour",
   "us": [
    "E05US030",
    "E05US032",
    "E05US033",
    "E05US034",
    "E07US008"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-20",
   "date_brute": "20/08/2026",
   "extrait": "Un arrêt décidé pendant que la salle tire est un objet distinct, porté par le départ, et rejoué par personne. Le mécanisme se lit désormais en trois natures, là où ADR-0091 en distinguait deux : Tournoi ──► EtapeDeroule.arrets DÉFINITION — posée à l'atelier, rejouée par TOUS les créneaux Départ ──► ArretDeCirconstance CONDUITE — posée au pilotage, rejouée par PERSONNE Départ ──► FranchissementArret AVANCEMENT — ce qu'un arrêt a coupé, ici, et son relèvement 1. ArretDeCirconstance (domain/arret_programme.py) porte depart_id, phase_id, apres_tour, portee. Il a une table à lui (arret_de_circonstance, migration 0049), et non un document JSON : l'unicité (depart_id, phase_id, apres_tour) doit […]",
   "fichier": "docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md",
   "identifiant": "0092",
   "liens": [
    {
     "cible": "E05US034",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E05US033",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0091",
     "libelle": "Complète",
     "sens": "sortant",
     "type": "complete"
    },
    {
     "cible": "0076",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/phases.py",
     "existe": true,
     "symboles": [
      "tour_d_un_arret_relatif",
      "poser_arret_relatif",
      "PoserArretRelatifRequete",
      "ArretFranchiReponse.arrete_depuis",
      "resumeDeRelance",
      "phraseDeRelance"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/arrets_programmes.py",
     "existe": true,
     "symboles": [
      "tour_d_un_arret_relatif",
      "poser_arret_relatif",
      "PoserArretRelatifRequete",
      "arrets_applicables",
      "_declencher_les_arrets_atteints",
      "_par_phase",
      "_tour_acheve",
      "evaluer",
      "aucun_arret",
      "test_un_arret_relatif_coupe_la_phase_quand_son_tour_s_acheve",
      "verifier_arrets",
      "verifier_type_arretable",
      "_verifier_arrets_applicables",
      "FranchissementArret.arrete_depuis",
      "_horodate",
      "Horloge",
      "HorlogeSysteme"
     ],
     "symboles_absents": [
      "test_un_arret_relatif_coupe_la_phase_quand_son_tour_s_acheve"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/bootstrap/composition.py",
     "existe": true,
     "symboles": [
      "FranchissementArret.arrete_depuis",
      "_horodate",
      "Horloge",
      "HorlogeSysteme"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/arret_programme.py",
     "existe": true,
     "symboles": [
      "ArretDeCirconstance",
      "tour_d_un_arret_relatif",
      "poser_arret_relatif",
      "PoserArretRelatifRequete",
      "arrets_applicables",
      "_declencher_les_arrets_atteints",
      "_par_phase",
      "_tour_acheve",
      "verifier_arrets",
      "verifier_type_arretable",
      "_verifier_arrets_applicables",
      "FranchissementArret.arrete_depuis",
      "_horodate",
      "Horloge",
      "HorlogeSysteme"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule_etape.py",
     "existe": true,
     "symboles": [
      "verifier_type_arretable",
      "_verifier_arrets_applicables",
      "poser_arret_relatif"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/ports.py",
     "existe": true,
     "symboles": [
      "ArretDeCirconstanceRepository",
      "ArretDeCirconstanceRepositorySQL.par_depart"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/models.py",
     "existe": true,
     "symboles": [
      "ArretDeCirconstanceORM",
      "ArretDeCirconstanceRepositorySQL.ajouter",
      "IntegrityError",
      "doublon_d_arret"
     ],
     "symboles_absents": [
      "IntegrityError",
      "doublon_d_arret"
     ],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/moteur.py",
     "existe": true,
     "symboles": [
      "ArretDeCirconstanceRepository",
      "ArretDeCirconstanceRepositorySQL.par_depart"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/migrations/versions/0049_arret_de_circonstance.py",
     "existe": true,
     "symboles": [
      "ArretDeCirconstanceORM",
      "ArretDeCirconstanceRepositorySQL.ajouter",
      "IntegrityError",
      "doublon_d_arret"
     ],
     "symboles_absents": [
      "IntegrityError",
      "doublon_d_arret"
     ],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/accueil/Accueil.tsx",
     "existe": true,
     "symboles": [
      "PastilleDeRelance",
      "useQueries"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/en-cours/VueEnCours.tsx",
     "existe": true,
     "symboles": [
      "MentionDePause",
      "VueEnCours",
      "EN_COURS",
      "SequenceVues.par_defaut"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/salle/EcranSalle.tsx",
     "existe": true,
     "symboles": [
      "MentionDePause",
      "VueEnCours",
      "EN_COURS",
      "SequenceVues.par_defaut"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suisse/presentation.test.ts",
     "existe": true,
     "symboles": [
      "ceQuiManque",
      "CeQuiManqueEncore"
     ],
     "symboles_absents": [
      "CeQuiManqueEncore"
     ],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suisse/presentation.ts",
     "existe": true,
     "symboles": [
      "ceQuiManque",
      "CeQuiManqueEncore"
     ],
     "symboles_absents": [
      "CeQuiManqueEncore"
     ],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suivi-deroule/PilotageCreneau.tsx",
     "existe": true,
     "symboles": [
      "libelleEtatDuTour",
      "EtatDuTour",
      "useSuiviDeroule"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suivi-deroule/api.ts",
     "existe": true,
     "symboles": [
      "poserArretRelatif",
      "usePoserArretRelatif",
      "PoserUnePause",
      "peutPoserUnePause",
      "toursBloquablesRestants"
     ],
     "symboles_absents": [
      "PoserUnePause",
      "peutPoserUnePause",
      "toursBloquablesRestants"
     ],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suivi-deroule/hooks.ts",
     "existe": true,
     "symboles": [
      "poserArretRelatif",
      "usePoserArretRelatif",
      "PoserUnePause",
      "peutPoserUnePause",
      "toursBloquablesRestants"
     ],
     "symboles_absents": [
      "PoserUnePause",
      "peutPoserUnePause",
      "toursBloquablesRestants"
     ],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/relance.test.ts",
     "existe": true,
     "symboles": [
      "ArretFranchiReponse.arrete_depuis",
      "resumeDeRelance",
      "phraseDeRelance"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/relance.ts",
     "existe": true,
     "symboles": [
      "ArretFranchiReponse.arrete_depuis",
      "resumeDeRelance",
      "phraseDeRelance",
      "libelleEtatDuTour",
      "EtatDuTour",
      "useSuiviDeroule"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/ui/BandeauDePause.tsx",
     "existe": true,
     "symboles": [
      "MentionDePause",
      "VueEnCours",
      "EN_COURS",
      "SequenceVues.par_defaut"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/ui/useMaintenant.ts",
     "existe": true,
     "symboles": [
      "PastilleDeRelance",
      "useQueries"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un arrêt posé le jour J appartient au créneau, pas au déroulé",
   "us": [
    "E05US033",
    "E05US034",
    "E05US035"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-20",
   "date_brute": "2026-08-20",
   "extrait": "1. Une qualification se règle en n tours égaux, et le découpage est un réglage de déroulé, pas de barème. L'organisateur saisit un nombre de tours ; le moteur en déduit la longueur et refuse à la composition un nombre qui ne divise pas les volées. 20 volées en 3 tours donneraient 7/7/6, et « après le tour 2 » ne désignerait plus le même instant selon l'archer — donc une pause qui ne tombe pas au même endroit pour tout le monde. Le refus est réparable d'un geste à l'atelier ; le découvrir le jour J ne l'est pas. Le champ vit sur EtapeDeroule (donc au tournoi, ADR-0076) aux côtés de poules, big_shoot_off et suisse, pas sur BaremeQualification. C'était le raccourci naturel — nb_volees y vit […]",
   "fichier": "docs/adr/0093-une-qualification-se-decoupe-en-tours-egaux.md",
   "identifiant": "0093",
   "liens": [
    {
     "cible": "E05US035",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0090",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0091",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0082",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0083",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0076",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/application/saisie.py",
     "existe": true,
     "symboles": [
      "ServiceSaisie.avancement_de_phase",
      "_volees_du_plus_lent",
      "par_phase",
      "_forfaits_qualif",
      "_volees_enchainees"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/bootstrap/composition.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/arret_programme.py",
     "existe": true,
     "symboles": [
      "phases_a_arreter",
      "verifier_type_arretable"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/bareme.py",
     "existe": true,
     "symboles": [
      "BaremeQualification",
      "nb_volees",
      "nb_fleches_par_volee"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/contrat_phase.py",
     "existe": true,
     "symboles": [
      "ContratDePhase.avancement_lisible",
      "TYPES_ARRETABLES"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule_etape.py",
     "existe": true,
     "symboles": [
      "decoupage",
      "__post_init__",
      "instancier",
      "_nb_tours_a_la_composition",
      "verifier_arrets",
      "arretable"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/format_tournoi.py",
     "existe": true,
     "symboles": [
      "ModelePhase.decoupage",
      "pour_tournoi",
      "d_etape"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "decoupage",
      "__post_init__",
      "instancier"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/qualification.py",
     "existe": true,
     "symboles": [
      "DecoupageEnTours",
      "verifier_decoupage",
      "verifier_decoupage_applicable",
      "volees_par_tour"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/suivi_deroule.py",
     "existe": true,
     "symboles": [
      "avancement_de_qualification"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/tour_de_phase.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/moteur.py",
     "existe": true,
     "symboles": [
      "config",
      "_politiques_json",
      "_lire_decoupage"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_arrets_api.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/deroule/Deroule.tsx",
     "existe": true,
     "symboles": [
      "FormulaireEtape"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/phases/Phases.tsx",
     "existe": true,
     "symboles": [
      "ReglageDecoupageDePhase",
      "FormulairePhase",
      "ReglageArrets",
      "motif"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/ReglageArrets.tsx",
     "existe": true,
     "symboles": [
      "ReglageDecoupageDePhase",
      "ReglageArrets",
      "motif"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/ReglageDecoupage.tsx",
     "existe": true,
     "symboles": [
      "ReglageDecoupage"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/catalogue.ts",
     "existe": true,
     "symboles": [
      "TYPES_ARRETABLES"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/decoupage.ts",
     "existe": true,
     "symboles": [
      "versDecoupage",
      "depuisDecoupage",
      "decrireDecoupage"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Une qualification se découpe en tours égaux, et « arrêtable » cesse d'être « déroulé »",
   "us": [
    "E04US009",
    "E05US021",
    "E05US033",
    "E05US034",
    "E05US035",
    "E12US001"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-21",
   "date_brute": "2026-08-21",
   "extrait": "### §1 — Le mode de composition est un réglage, pas un type de phase ReglageDePoules gagne mode: ModeDeComposition — SERPENT (défaut) ou PAR_NIVEAU. TypePhase.POULES ne se dédouble pas : un format de tournoi est de la configuration, pas du code (règle 2). Les deux modes appellent le même moteur — mêmes rencontres, même barème, même départage — et ne diffèrent que sur qui joue avec qui. PAR_NIVEAU découpe le classement source en tranches de rangs contiguës, un groupe par tranche. ### §2 — Le mode commande aussi la lecture du classement de phase, et c'est ce qui remplace le décalage par groupe C'est le cœur de cet ADR. Sous SERPENT, le classement de phase se lit « par rang de poule d'abord » […]",
   "fichier": "docs/adr/0094-le-mode-de-composition-d-une-poule-commande-aussi-la-lecture-de-son-classement.md",
   "identifiant": "0094",
   "liens": [
    {
     "cible": "E05US029",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0083",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0080",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0081",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0068",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0075",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/formats.py",
     "existe": true,
     "symboles": [
      "ReglagePoulesDTO.mode",
      "RepartitionReponse.mode"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/api/v1/phases.py",
     "existe": true,
     "symboles": [
      "ReglagePoulesDTO.mode",
      "RepartitionReponse.mode"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/api/v1/poules.py",
     "existe": true,
     "symboles": [
      "ReglagePoulesDTO.mode",
      "RepartitionReponse.mode"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/poules.py",
     "existe": true,
     "symboles": [
      "ServicePoules.classement_de_phase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/prelevement.py",
     "existe": true,
     "symboles": [
      "rang_premier",
      "ResultatPhase.rang_premier",
      "tranche"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/classement_de_poules.py",
     "existe": true,
     "symboles": [
      "_par_groupe",
      "_en_classement"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/contrat_phase.py",
     "existe": true,
     "symboles": [
      "ModeDeComposition",
      "ReglageDePoules.mode",
      "ConfigurationPoules.mode",
      "pour_effectif"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule.py",
     "existe": true,
     "symboles": [
      "_motif_de_choc",
      "_choc_entre_tranches",
      "ChocDePoulePossible",
      "_anomalies_serpent_apres_poules",
      "_anomalies_structurelles",
      "_ne_donne_qu_un_groupe",
      "SerpentApresDesPoules",
      "ReglageDePoules.serpent_assume"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/erreurs/moteur.py",
     "existe": true,
     "symboles": [
      "_motif_de_choc",
      "_choc_entre_tranches",
      "ChocDePoulePossible",
      "_anomalies_serpent_apres_poules",
      "_anomalies_structurelles",
      "_ne_donne_qu_un_groupe",
      "SerpentApresDesPoules",
      "ReglageDePoules.serpent_assume"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/palmares.py",
     "existe": true,
     "symboles": [
      "rang_premier",
      "ResultatPhase.rang_premier",
      "tranche"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/poule.py",
     "existe": true,
     "symboles": [
      "ModeDeComposition",
      "ReglageDePoules.mode",
      "ConfigurationPoules.mode",
      "pour_effectif",
      "composer_poules",
      "_tranches_de_niveau",
      "_serpent",
      "repartition",
      "nb_qualifies",
      "PAR_NIVEAU",
      "ReglageDePoules.__post_init__",
      "ConfigurationPoules.__post_init__",
      "ConfigurationPouleInvalide",
      "versReglage",
      "tailles_de_niveau",
      "_choc_entre_tranches",
      "_anomalies_serpent_apres_poules",
      "_anomalies_structurelles",
      "_ne_donne_qu_un_groupe",
      "SerpentApresDesPoules",
      "ReglageDePoules.serpent_assume"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/moteur.py",
     "existe": true,
     "symboles": [
      "config",
      "_lire_reglage_poules",
      "_mode_de_composition",
      "_politiques_json"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_service_poules_en_cascade.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/ReglagePoules.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/poules.ts",
     "existe": true,
     "symboles": [
      "_tranches_de_niveau",
      "repartition",
      "nb_qualifies",
      "PAR_NIVEAU",
      "ReglageDePoules.__post_init__",
      "ConfigurationPoules.__post_init__",
      "ConfigurationPouleInvalide",
      "versReglage",
      "ModeDeComposition",
      "tranchesDeRangs",
      "decrireRepartition",
      "depuisReglage"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Le mode de composition d'une poule commande aussi la lecture de son classement",
   "us": [
    "E05US023",
    "E05US026",
    "E05US029",
    "E05US035"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-22",
   "date_brute": "2026-08-22",
   "extrait": "### §1 — Le titre est un libellé, pas une identité EtapeDeroule et ModelePhase gagnent un champ titre: str | None. Ce qu'il n'est pas : - pas une clé — l'identité d'une étape reste son id et son rang dans la séquence 1..N (ADR-0045 §3). Deux étapes du même déroulé peuvent porter le même titre. Imposer l'unicité aurait fait échouer la composition sur une gêne d'affichage, et déplacé dans le domaine une règle qu'aucun besoin métier ne réclame ; - pas obligatoire — None est l'état de tous les déroulés déjà composés. L'exiger aurait invalidé l'existant à la première lecture, c'est-à-dire converti un libellé en migration de données ; - pas propre à un type — à la différence des cinq réglages […]",
   "fichier": "docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md",
   "identifiant": "0095",
   "liens": [
    {
     "cible": "E16US002",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0076",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0060",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0045",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0046",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0073",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/formats.py",
     "existe": true,
     "symboles": [
      "ConfigPhaseRequete.titre",
      "EtapeDTO.titre"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/api/v1/phases.py",
     "existe": true,
     "symboles": [
      "ConfigPhaseRequete.titre",
      "EtapeDTO.titre",
      "Phase",
      "titre",
      "PhaseReponse"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/deroule_etape.py",
     "existe": true,
     "symboles": [
      "titre",
      "titre_normalise",
      "ModelePhase.__post_init__"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/format_tournoi.py",
     "existe": true,
     "symboles": [
      "titre_normalise",
      "ModelePhase.__post_init__",
      "ModelePhase.titre",
      "pour_tournoi",
      "d_etape"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/phase.py",
     "existe": true,
     "symboles": [
      "Phase",
      "titre",
      "PhaseReponse"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/moteur.py",
     "existe": true,
     "symboles": [
      "deroule_etape",
      "_politiques_json",
      "_config_etape",
      "_lire_titre",
      "_vers_etape",
      "config",
      "_config_format",
      "_vers_modele_phase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_titre_de_phase.py",
     "existe": true,
     "symboles": [
      "titre_normalise",
      "ModelePhase.__post_init__"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_patrimoine_api.py",
     "existe": true,
     "symboles": [
      "config",
      "_config_format",
      "_vers_modele_phase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_phase_repository.py",
     "existe": true,
     "symboles": [
      "config",
      "_config_format",
      "_vers_modele_phase"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/admin/CoquilleAdmin.tsx",
     "existe": true,
     "symboles": [
      "phases",
      "deroule"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/deroule/Deroule.tsx",
     "existe": true,
     "symboles": [
      "Etape.titre"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/patrimoine/api.ts",
     "existe": true,
     "symboles": [
      "Etape.titre"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/phases/Phases.tsx",
     "existe": true,
     "symboles": [
      "LignePhase",
      "ficheOuverte",
      "ReglageTitre",
      "ReglageBarrage",
      "ReglageDecoupageDePhase",
      "PlanParBlocs",
      "phase__actions",
      "configInchangee"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/phases/api.ts",
     "existe": true,
     "symboles": [
      "undefined"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/suivi-deroule/PilotageCreneau.tsx",
     "existe": true,
     "symboles": [
      "Phase",
      "usePhases",
      "ordre"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/phases/ChampTitre.tsx",
     "existe": true,
     "symboles": [
      "LONGUEUR_MAX_TITRE"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un titre de phase est un libellé, et chaque écran de composition porte le mot de sa portée",
   "us": [
    "E01US024",
    "E05US023",
    "E05US024",
    "E05US025",
    "E05US026",
    "E05US029",
    "E05US030",
    "E05US035",
    "E16US002"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-23",
   "date_brute": "2026-08-23",
   "extrait": "### §1 — Un jalon est un état consultable, pas une exception Une préparation à un jalon (PreparationJalon) énumère ce que les gardes vérifient, sans les exécuter : une liste d'états (D-17 : jamais une barre de progression) et une réponse binaire. Tout ce qui manque se lit d'un coup. Les gardes ne sont pas réécrites — c'est le CA « sans doublonner ce qui existe ». L'effectif affiché avant le clic sort de ServiceTournois.exigence_effectif, la méthode que la garde exécute elle-même ; les créneaux du même DepartRepository.par_tournoi ; « prêt à terminer » relit ServiceCompletude sans y toucher. Là où le partage mécanique s'arrête — le jalon traduit « aucun créneau » en EN_ATTENTE, la garde le […]",
   "fichier": "docs/adr/0096-un-jalon-enumere-ses-gardes-au-lieu-de-les-lever.md",
   "identifiant": "0096",
   "liens": [
    {
     "cible": "E16US012",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0026",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0058",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0069",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0073",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/erreurs.py",
     "existe": true,
     "symboles": [
      "JalonNonInstruit",
      "isinstance",
      "MancheIntrouvable"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/api/v1/jalons.py",
     "existe": true,
     "symboles": [
      "question",
      "_VERBE",
      "PreparationJalonReponse.question",
      "test_chaque_membre_pose_sa_question_sous_la_meme_forme",
      "LigneCompletudeReponse",
      "question_posee",
      "PreparationJalon.question_posee",
      "questionPosee",
      "tsc",
      "evaluer_terminer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/erreurs/referentiel.py",
     "existe": true,
     "symboles": [
      "JalonNonInstruit",
      "isinstance",
      "MancheIntrouvable"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/jalons.py",
     "existe": true,
     "symboles": [
      "ServiceJalons._demarrer",
      "exigence.suffisant",
      "_exiger_un_effectif_suffisant",
      "inscrits",
      "minimum",
      "test_l_effectif_suit_le_verdict_de_la_garde_et_ne_le_recalcule_pas",
      "exigence_effectif",
      "PreparationJalon.detail",
      "transition_offerte",
      "_TRANSITIONS_DU_JALON",
      "test_le_jalon_terminer_suit_la_table_des_transitions_sur_tous_les_statuts",
      "ARCHIVER",
      "JalonNonInstruit",
      "isinstance",
      "MancheIntrouvable"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/jalon.py",
     "existe": true,
     "symboles": [
      "PreparationJalon",
      "evaluer_demarrer",
      "evaluer_terminer",
      "ServiceJalons._demarrer",
      "exigence.suffisant",
      "_exiger_un_effectif_suffisant",
      "inscrits",
      "minimum",
      "test_l_effectif_suit_le_verdict_de_la_garde_et_ne_le_recalcule_pas",
      "exigence_effectif",
      "question",
      "_VERBE",
      "PreparationJalonReponse.question",
      "test_chaque_membre_pose_sa_question_sous_la_meme_forme",
      "pret",
      "test_un_deroule_vide_est_signale_mais_ne_retient_pas_le_depart",
      "bloquant",
      "False",
      "verdict",
      "_moment_du_refus",
      "test_sans_creneau_le_refus_est_annonce_pour_le_passage_en_pret",
      "PreparationJalon.detail",
      "transition_offerte",
      "_TRANSITIONS_DU_JALON",
      "test_le_jalon_terminer_suit_la_table_des_transitions_sur_tous_les_statuts",
      "ARCHIVER",
      "moment",
      "question_posee",
      "PreparationJalon.question_posee",
      "questionPosee",
      "tsc"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/tournoi.py",
     "existe": true,
     "symboles": [
      "MESSAGE_SANS_DEPART",
      "MESSAGE_TERMINER_HORS_EN_COURS",
      "ServiceTournois",
      "preparation.detail"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_domain_jalon.py",
     "existe": true,
     "symboles": [
      "ServiceJalons._demarrer",
      "exigence.suffisant",
      "_exiger_un_effectif_suffisant",
      "inscrits",
      "minimum",
      "test_l_effectif_suit_le_verdict_de_la_garde_et_ne_le_recalcule_pas",
      "exigence_effectif",
      "question",
      "_VERBE",
      "PreparationJalonReponse.question",
      "test_chaque_membre_pose_sa_question_sous_la_meme_forme",
      "pret",
      "evaluer_demarrer",
      "test_un_deroule_vide_est_signale_mais_ne_retient_pas_le_depart",
      "_moment_du_refus",
      "test_sans_creneau_le_refus_est_annonce_pour_le_passage_en_pret",
      "moment",
      "question_posee",
      "PreparationJalon.question_posee",
      "questionPosee",
      "tsc",
      "evaluer_terminer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_jalons_api.py",
     "existe": true,
     "symboles": [
      "question_posee",
      "PreparationJalon.question_posee",
      "questionPosee",
      "tsc",
      "evaluer_terminer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/tests/test_service_jalons.py",
     "existe": true,
     "symboles": [
      "test_le_jalon_chiffre_l_effectif_du_creneau_le_moins_garni",
      "test_un_tournoi_deja_lance_n_annonce_pas_qu_il_peut_demarrer",
      "test_quand_le_jalon_dit_pret_les_deux_gardes_laissent_passer",
      "transition_offerte",
      "_TRANSITIONS_DU_JALON",
      "test_le_jalon_terminer_suit_la_table_des_transitions_sur_tous_les_statuts",
      "ARCHIVER",
      "MESSAGE_SANS_DEPART",
      "MESSAGE_TERMINER_HORS_EN_COURS",
      "ServiceTournois",
      "preparation.detail",
      "question_posee",
      "PreparationJalon.question_posee",
      "questionPosee",
      "tsc",
      "evaluer_terminer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/admin/axes.ts",
     "existe": true,
     "symboles": [
      "completude"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/completude/Completude.tsx",
     "existe": true,
     "symboles": [
      "questionPosee",
      "pret",
      "complet",
      "detail",
      "enCours",
      "bloquant"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/jalons/PretA.tsx",
     "existe": true,
     "symboles": [
      "questionPosee",
      "pret",
      "complet",
      "PreparationJalon.detail",
      "_moment_du_refus",
      "moment",
      "test_sans_creneau_le_refus_est_annonce_pour_le_passage_en_pret",
      "question_posee",
      "PreparationJalon.question_posee",
      "tsc",
      "evaluer_terminer"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/jalons/PretADemarrer.tsx",
     "existe": true,
     "symboles": [
      "question",
      "_VERBE",
      "PreparationJalonReponse.question",
      "test_chaque_membre_pose_sa_question_sous_la_meme_forme",
      "disabled",
      "useTransitions",
      "VERS_LE_DEPART",
      "_moment_du_refus",
      "test_sans_creneau_le_refus_est_annonce_pour_le_passage_en_pret"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/jalons/presentation.ts",
     "existe": true,
     "symboles": [
      "bloquant",
      "False",
      "verdict",
      "_moment_du_refus",
      "test_sans_creneau_le_refus_est_annonce_pour_le_passage_en_pret"
     ],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un jalon énumère ses gardes au lieu de les lever, et les quatre « prêt à… » partagent une forme",
   "us": [
    "E02US010",
    "E05US021",
    "E12US005",
    "E14US001",
    "E16US003",
    "E16US007",
    "E16US008",
    "E16US012"
   ]
  },
  {
   "amende_par": [],
   "date": "2026-08-25",
   "date_brute": "2026-08-25",
   "extrait": "### 1. Les octets d'un logo vivent en base, dans une table à part Le fichier est stocké en blob dans identite_tournoi, servi par une route dédiée. L'alternative — un répertoire d'actifs sur le disque, chemin en base — a été écartée sur trois conséquences concrètes, pas sur une préférence : - sauvegarder, le jour J, c'est copier le .db. Un logo sur le disque en sortirait, et la sauvegarde deviendrait deux gestes dont l'un s'oublie ; - supprimer un tournoi supprime sa descendance. Un fichier orphelin, non ; - EPIC-11 promet une archive en lecture seule. Un fichier reste remplaçable sous les pieds du tournoi archivé ; une ligne de base, non. Le prix est réel et assumé : des octets passent par […]",
   "fichier": "docs/adr/0097-un-logo-de-tournoi-vit-en-base-avec-lui.md",
   "identifiant": "0097",
   "liens": [
    {
     "cible": "E16US006",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "E01US016",
     "libelle": "US",
     "sens": "sortant",
     "type": "us"
    },
    {
     "cible": "0074",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0026",
     "libelle": "S'appuie sur",
     "sens": "sortant",
     "type": "socle"
    },
    {
     "cible": "0060",
     "libelle": "Voisin",
     "sens": "symetrique",
     "type": "voisin"
    }
   ],
   "portage": [
    {
     "chemin": "backend/api/v1/identite.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/application/identite.py",
     "existe": true,
     "symboles": [
      "decliner"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/domain/identite.py",
     "existe": true,
     "symboles": [
      "IdentiteVisuelle",
      "reglee"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/infrastructure/db/repositories/referentiel.py",
     "existe": true,
     "symboles": [
      "IdentiteVisuelleRepositorySQL"
     ],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "backend/migrations/versions/0050_identite_visuelle_tournoi.py",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/identite/HabillageIdentite.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/identite/jetons.ts",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/public/AccueilPublic.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/features/salle/EcranSalle.tsx",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    },
    {
     "chemin": "frontend/src/shared/charte.test.ts",
     "existe": true,
     "symboles": [],
     "symboles_absents": [],
     "verifiable": true
    }
   ],
   "remplace_par": "",
   "statut": "accepte",
   "statut_brut": "Accepté",
   "titre": "Un logo de tournoi vit en base avec lui, et deux accents suffisent à en dériver le chrome",
   "us": [
    "E01US016",
    "E16US006",
    "E17US001"
   ]
  }
 ]
};
