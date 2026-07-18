# ADR-0025 — Mode d'identité « scoreur » : entité de domaine, code individuel, session nominative

- **Statut** : Accepté
- **Date** : 2026-07-18
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E10-acces-roles.md`](../../stories/E10-acces-roles.md) (E10US003) ;
  [`docs/glossaire.md`](../glossaire.md) (`Scoreur`) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md)
  (table `SCOREUR` ; abandon du modèle prospectif `UTILISATEUR/SESSION`) ;
  [`docs/dette.md`](../dette.md) (DETTE-001, FK `scoreur.tournoi_id`).
- **Introduit par** : E10US003 (scoreurs : définition & session).
- **S'appuie sur** : [ADR-0007](0007-erreurs-par-couche.md) (erreurs typées par couche, mapping à la
  frontière). Il complète le **modèle d'identité** du projet, dont le premier maillon — l'accès admin
  (E10US002, identifiants `.env`) — n'a **pas** d'ADR dédié (son choix stdlib relève d'ADR-0009,
  gouvernance des dépendances). Cet ADR est donc le **premier** à formaliser un mode d'identité, et
  la **base d'autorisation** pour E04US002 (validation) et le voisin du troisième mode, E10US007
  (poste de cible = le lieu).

## Contexte et problème

La refonte `D-13` (14/07/2026, CDC UX §5) remplace le modèle à quatre rôles par **trois modes
d'identité proportionnés au risque**, dont **aucun n'est un compte utilisateur** : le **poste de
cible** (identité = le *lieu*, sans auth, E10US007), le **scoreur** (identité = la *personne*) et
l'**admin** (identité = un *secret*, ADR-0009). Le scoreur **valide** des scores — un acte qui
verrouille des données —, donc la traçabilité « qui a validé » l'exige (`D-12`) : il **doit** être
identifié, là où le poste de cible ne l'est pas.

E10US003 doit donc matérialiser ce deuxième mode. Plusieurs choix structurants que le CA ne trance
pas seul (arbitrés le 18/07/2026), et qui deviennent **précédent** pour deux US aval (E04US002
autorisera la validation à l'admin **ou** au scoreur ; E10US007 posera le troisième mode) — d'où cet
ADR, au même titre qu'ADR-0009 pour l'admin.

## Décision

**1. Le scoreur est une entité de domaine — à la différence de l'admin.** Table `scoreur`
(`tournoi_id`, `nom`, `code`), agrégat `domain.scoreur.Scoreur`, port `ScoreurRepository`, adapter
SQL. **Asymétrie assumée avec l'admin**, qui, lui, n'a **pas** d'entité (secret dans `.env`,
ADR-0009) : l'admin est **un** secret unique de configuration ; les scoreurs sont **multiples**,
créés/modifiés/supprimés **au runtime**, **nominatifs** et rattachés à un tournoi — c'est de la
**donnée métier persistée**, comme `Depart`, pas un paramètre d'accès. Entité **du tournoi** (FK
`tournoi_id`, dans le périmètre DETTE-001), redéfinissable même tournoi en cours (`D-14`, aucune
garde de statut).

**2. Code individuel généré par le serveur, unique dans toute la base.** L'admin déclare un scoreur
par son **nom** ; le système **génère** son `code` (comme `Depart.numero` est attribué par le
service). Le code est un **secret d'usage** distribué sur papier et **retapé** par le scoreur : d'où
un alphabet **sans caractères confondables** (`ABCDEFGHJKLMNPQRSTUVWXYZ23456789` — ni `I O 0 1`),
6 caractères (~10⁹ combinaisons), tiré par `secrets`. Unicité **globale** (pas par tournoi) parce que
la connexion est `POST /api/v1/scoreurs/session {code}` **sans contexte tournoi** : le code seul doit
désigner un scoreur sans ambiguïté. Génération avec **ré-essai sur collision** (pré-contrôle
`par_code`, comme `ServiceClubs` pour le nom) + contrainte `UNIQUE(code)` en garde-fou ultime. Forme
**canonique** (`normaliser_code` : `strip().upper()`) au stockage et à la comparaison, pour tolérer la
casse à la saisie. Génération **injectée** dans le service (déterminisme des tests, règle 9).

**3. Session nominative en mémoire, sans expiration.** Un jeton opaque (`secrets.token_urlsafe`) est
lié à l'**identité** du scoreur (`jeton → scoreur_id`, `ScoreurSessionStore`) — nominatif, à la
différence du `SessionStore` admin (ensemble anonyme) —, ce qui permettra de tracer « qui a validé »
(E10US005) et de **purger** les jetons d'un scoreur **supprimé** (sa session cesse aussitôt d'être
valable). Store **en mémoire**, non persisté (invalidé au redémarrage serveur). **Pas d'expiration**,
et ce **contre** le fléchage de la docstring du `SessionStore` admin (E10US002 : « l'expiration
relève d'E10US003 ») : le CA veut un jeton qui **survit à la fermeture de l'onglet** le temps d'une journée (persisté en
`localStorage` côté client) ; l'admin, **plus** puissant, n'expire pas — le scoreur ne le ferait pas
davantage ; et une expiration imposerait une **horloge injectée** (déterminisme des tests, règle 9)
pour un gain marginal sur un événement d'un jour (règle 12, simplicité hors domaine). La docstring
d'E10US002 a été **actualisée** en conséquence.

**4. En-tête dédié `X-Jeton-Scoreur`, orthogonal au Bearer admin.** Le jeton scoreur voyage dans un
en-tête **distinct** de l'`Authorization: Bearer` de l'admin (dépendance API `exiger_scoreur`,
symétrique d'`exiger_admin`). Les deux modes sont **indépendants** : un admin (sur son PC) et un
scoreur (sur son téléphone) peuvent coexister sans que l'un masque l'autre, et **E04US002** protégera
les endpoints de **validation** en acceptant l'un **ou** l'autre, sans qu'un jeton chasse l'autre.
Côté front, chaque requête n'engage **qu'une** identité (portée `'admin' | 'scoreur' | 'aucune'` de
`fetchJson`), pour qu'un 401 ne purge que la session réellement concernée.

## Conséquences

- **+** Traçabilité de la validation **rendue possible** (E10US005) sans re-conception : le jeton
  porte l'identité, la trace portera le **nom** (survivant à la suppression du scoreur).
- **+** Symétrie claire avec l'admin (ADR-0009) tout en respectant la vraie différence de nature
  (secret de config unique vs données métier multiples) — le lecteur d'E04US002/E10US007 trouve **ici**
  le contrat d'identité, pas éparpillé dans un corps de commit.
- **+** Un seul code à taper, sans tournoi à choisir : friction minimale le jour J (`D-14`, 3-4 codes).
- **−** Unicité **globale** du code : deux tournois ne peuvent pas réutiliser un même code — sans
  conséquence pratique (l'espace 10⁹ est immense), mais à savoir.
- **−** **Pas de rate-limit** ni d'expiration : accepté par le modèle de menace (LAN mono-club, une
  journée) ; à revoir seulement si le contexte de déploiement change.
- **−** Sessions **en mémoire** : un redémarrage serveur déconnecte les scoreurs (ils retapent leur
  code). Volontaire (cohérent avec la session admin), pas une perte de données.
- **Périmètre** : E10US003 livre la **définition** (CRUD admin) et la **session** (login/déconnexion).
  L'autorisation des endpoints de **validation** et la **trace** nominative sont E04US002 / E10US005 —
  `exiger_scoreur` et le store nominatif sont **prêts**, rien à élargir tant que ces endpoints n'existent pas.
