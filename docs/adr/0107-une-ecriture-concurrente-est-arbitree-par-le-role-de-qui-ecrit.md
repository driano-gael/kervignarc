# ADR-0107 — Une écriture concurrente est arbitrée par le rôle de qui écrit

- **Statut** : Accepté *(et **porté** depuis le 12/09/2026 — cf. § « Porté dans le code par ». ⚠️ **Portée réelle : la volée de qualification seule** ; les autres formats gardent le *dernier écrit gagne*)*
- **Date** : 2026-09-10
- **US** : `E16US011` *(carte de découpage)* · **`E16US020`** *(mise en œuvre)*
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0030](0030-saisie-autorisee-au-poste-de-cible-403-hors-cible.md) — la saisie est autorisée
    **au poste de cible**, sans authentification de personne. C'est lui qui fixe l'identité du rôle
    le plus bas, et donc ce que cet ADR peut ordonner
  - [ADR-0035](0035-atomicite-acte-trace-session-partagee.md) — l'acte tracé et la session partagée :
    le contexte dans lequel deux écritures se croisent
  - [ADR-0102](0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) — la **forme** de cet
    ADR : décision prise, section « Porté dans le code par » qui dit franchement qu'elle ne porte
    rien encore
  - [ADR-0037](0037-file-de-saisie-hors-ligne-et-rejeu.md) — la file hors-ligne et son tri des
    refus, que cet ADR **amende** (cf. Conséquences)

> **Portée de la règle « décision structurante ⇒ ADR »** : cet ADR est inscrit à la liste **hors
> critère** d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md), qui
> **fait foi** — c'est cette liste, et non un plaidoyer chez soi, qui borne ce qu'une revue a le
> droit de relever. *(La 1ʳᵉ rédaction argumentait son exclusion ici même : c'était la 6ᵉ occurrence
> du mode de panne que ce paragraphe d'ADR-0075 existe pour empêcher — relevé en 2ᵉ passe de revue.)*

## Contexte

Le questionnaire de maquettes S09 (04/08/2026) demandait qui doit trancher un conflit de
modification concurrente. **La question compte autant que la réponse**, parce qu'elle nomme les
options :

> **« qui doit trancher : la tablette, le scoreur, ou toi ? »**
> — « hiérarchie → archer < scoreur < admin »

⚠️ **« archer » y désigne littéralement l'option « la tablette »**, et c'est ce qui autorise à lire
la réponse sur les identités réelles du dépôt : il n'y a **pas de rôle archer**, il y a **un poste
ouvert**, dont l'identité est le **lieu** et non la personne (`D-13` du 14/07/2026, opérationnalisé
par ADR-0030). Le glossaire porte d'ailleurs une section **« Rôles »** dont le tableau liste
exactement les identités à ordonner — d'où le mot retenu ici. *(« Rang » a été essayé et écarté en
revue : le glossaire le définit déjà comme la **position finale d'un archer**.)*

Trois constats, tous vérifiés dans le code du 10/09/2026, cadrent la décision :

1. **Il n'existe aujourd'hui aucun mécanisme de conflit.** `RegistreIdempotence` ne dédoublonne qu'un
   **rejeu du même client** (`identifiant_saisie` identique). Deux écritures d'identifiants
   différents sur la même volée non validée : `Serie.saisir_volee` écrase la première **en silence**,
   sans version, sans horodatage comparé, sans `409`.
2. **La file d'écriture ne protège de rien ici.** Le writer unique (règle 7) **sérialise** les
   écritures — il n'y a donc pas de course en base. Mais *sérialiser n'est pas arbitrer*, et c'est
   précisément ce qui rend le défaut invisible : tout se passe bien, et une saisie disparaît.
3. **Les rôles n'ont aucun ordre.** `backend/api/dependances.py` porte cinq gardes qui rendent une
   identité sur une écriture — `exiger_admin`, `exiger_scoreur`, `exiger_poste_de_cible`,
   `autoriser_saisie`, `autoriser_forfait` — plus `exiger_poste`, qui ne garde que la session et le
   *heartbeat* et que `exiger_poste_de_cible` **compose**. Aucune n'en compare deux : cet ADR
   introduit le **premier** ordre entre rôles du dépôt.

## Décision

**1. L'ordre est `poste de cible < scoreur < admin`.** Une écriture d'un rôle **supérieur** à celui
qui a déjà écrit **écrase**. Une écriture d'un rôle **inférieur** est **refusée** (`409`), et l'écran
dit pourquoi — un refus muet serait pire que l'écrasement qu'il remplace.

⚠️ **Une EXCEPTION, et elle n'est pas un détail : le verrou prime la préséance.** Sur une volée
**verrouillée**, toute correction habilitée passe, quel que soit le rang inscrit — le rang stocké
peut donc *redescendre*. C'est voulu : l'organisateur n'a **aucune** route de correction (`/volees`
lève `VoleeVerrouillee`, `/corrections` est réservée au scoreur), et refuser fermerait le seul
chemin de réparation d'une feuille signée. La préséance ne protège donc que la volée **non
verrouillée**. *(Relevé en 3ᵉ passe de revue : le code portait cette exception, la décision
l'énonçait « sans exception » et la garde affirmait un refus qui n'avait pas lieu. Épinglée par
`test_corriger_une_volee_verrouillee_passe_meme_par_dessus_un_rang_superieur`.)*

**2. Le rôle est celui de la garde, jamais celui du message.** `Volee.saisie_par` **existe** mais sa
propre docstring le qualifie de **déclaratif** : c'est un nom libre, issu du corps de la requête.
L'employer comme source d'autorité livrerait une hiérarchie qu'un poste contourne en se déclarant
admin. Le rôle se lit sur l'identité **résolue par la garde** — jeton de poste, session scoreur,
session admin. ⚠️ **Ne pas lire « authentifiée »** : le rôle le plus bas ne l'est justement pas, il
est identifié par le lieu (ADR-0030), et c'est ce qui rend l'ordre nécessaire.

**3. À rôles égaux, la règle n'arbitre rien** — et c'est assumé. Deux tablettes rattachées à la
**même** cible portent le même rôle : entre elles, le dernier écrit gagne, exactement comme
aujourd'hui. *(Rédaction corrigée le 12/09/2026 : « deux cibles **différentes** » décrivait un cas
**impossible** — un poste qui écrit hors de sa cible est refusé en amont, `SaisieHorsCible`,
ADR-0033 §3. Le CA disait la même chose et a été corrigé au même moment.)*

⚠️ **C'est un renoncement déclaré, pas déguisé, et il porte sur le cas le plus fréquent en salle.**
Il se prouve par un test **négatif** (« deux postes écrivent successivement : le second gagne, `200`,
aucun `409` »), qui épingle le comportement actuel. **Critère de réouverture** : on reprend
l'alternative écartée si un tournoi réel remonte **au moins une saisie perdue entre deux postes**.

**4. La préséance ne survit pas au conflit — et une annulation de validation la remet à zéro.** Le
rôle de la dernière écriture ne verrouille pas la volée pour toujours contre les rôles inférieurs.

Sans cette borne, un admin — ou un scoreur, le cas majoritaire — qui annule une validation rendrait
la volée inaccessible à ceux qui doivent la corriger, ce qui **contredirait** le CA d'annulation qui
exige qu'elle reste écrivable par le poste de cible.

⚠️ **Mais le geste de remise à zéro n'est PAS toujours disponible là où le blocage se produit**, et
c'est la nuance qui manquait *(relevée en 2ᵉ passe de revue, axe D, le 12/09/2026)*. Si un scoreur
**corrige** une volée déjà rouverte, la tablette est refusée — et `annuler_validation` refuse à son
tour, la volée étant *déjà en correction*. **La sortie tient alors en DEUX gestes**, tous deux
offerts par l'écran du scoreur : **refermer** la correction, puis **annuler** la validation. Épinglée
par `test_la_sortie_du_blocage_existe_et_tient_en_deux_gestes`.

⚠️ **Et pendant une PAUSE de phase, il n'y a pas de sortie du tout** : les deux gestes sont gelés
(E05US033) alors que `corriger_volee` ne l'est pas. Une écriture de rang supérieur sur une volée
rouverte y ferme donc la ressaisie de la tablette **jusqu'à la reprise**. Assumé plutôt qu'ignoré :
lever la garde rouvrirait le contournement par le choix de l'endpoint. Épinglé par
`test_pendant_une_pause_une_ecriture_d_admin_ferme_la_reparation_jusqu_a_la_reprise`.
*(Troisième état, relevé en 3ᵉ passe par C1 et D.)*

**5. La règle ne vaut que pour la volée de QUALIFICATION.** *(Arbitrage du commanditaire, 12/09/2026,
à la mise en œuvre.)* Duels, poules, système suisse, colline et Big Shoot Off gardent le **dernier
écrit gagne**. Ce n'est pas un cas particulier dans le code : la préséance est portée par la
**donnée** (`Volee.role_de_saisie`), et une surface qui n'en revendique aucune (`None`) n'oppose
rien — la règle y est **inerte par construction**.

⚠️ **Conséquence directe sur la puce de `DETTE-065` ci-dessous** : la règle ne vit qu'au service de
saisie, elle n'atterrit **pas** sur les sept routeurs d'écriture. La question revient si un autre
format l'adopte — ce serait une US à part entière.

## Alternative écartée — le refus explicite symétrique

Refuser **tout** second écrivain (`409` + rafraîchir, indépendamment du rôle) et lui montrer la
saisie de l'autre. Recommandée par l'assistant, **écartée par le commanditaire** le 10/09/2026, qui a
retenu la lettre du questionnaire.

⚠️ **Elle est écartée, pas oubliée, et son avantage est réel** : elle traite le cas que la hiérarchie
ne peut pas traiter — deux postes de même rôle, qui est **le cas le plus fréquent en salle**. Le
critère de réouverture est écrit à la décision 3.

## Conséquences

- Une hiérarchie **tranche sans prévenir** : celui qui est écrasé ne l'apprend pas. C'est le revers,
  il a été exposé avant la décision et accepté.
- ⚠️ **Un état persisté est REQUIS — ce n'est pas une option.** La règle compare le rôle entrant à
  celui **qui a déjà écrit**, et la garde ne fournit jamais que le premier. Le second n'existe
  aujourd'hui **nulle part** : `Volee.saisie_par` est un nom déclaratif, que la décision 2 interdit
  d'employer comme autorité, et `validee_par` n'existe qu'une fois la volée validée — or le cas visé
  est précisément la volée **non validée**. Deux voies, à trancher avec la fenêtre de préséance :
  **une colonne** (durable, donc une migration) ou **un registre en mémoire** à la manière de
  `RegistreIdempotence` (volatile — la préséance est perdue au redémarrage, ce qui doit être assumé
  et inscrit au registre de dette). *(La 1ʳᵉ rédaction proposait de « dériver le rôle de la garde
  sans aucune colonne » : quatre axes de revue ont montré indépendamment que cette voie n'existe
  pas.)*
- ⚠️ **Cet ADR AMENDE la décision 4 d'[ADR-0037](0037-file-de-saisie-hors-ligne-et-rejeu.md).**
  Celle-ci discriminait les refus au rejeu **par le seul statut**, et rangeait **tout** `409` parmi
  les transitoires « gardés en file ». `ecriture_de_role_inferieur` est le **premier refus définitif
  au statut 409** du produit : la classification devient « fenêtre 4xx **d'abord**, liste de codes
  **ensuite** ». Le renoncement est assumé — la volée du poste est **perdue**, avec le seul
  `console.error` que personne ne lit sur tablette — parce que le rang du poste ne montera jamais et
  que la garder **gèle la tête de file**, donc toutes les volées enfilées derrière.
  *(Relevé en 3ᵉ passe de revue : la décision était prise dans le code et écrite nulle part, sur un
  garde-fou de perte de score — le mode de panne d'ADR-0017.)*
- **Critère de remède structurel, écrit pour ne pas être redécouvert.** La préséance est aujourd'hui
  tenue par **deux** appels manuels à `_refuser_role_inferieur`, alors que la donnée et sa remise à
  zéro vivent dans le domaine. On duplique sciemment (règle 16 : 2 sites, pas 3). **Au 3ᵉ chemin
  d'écriture qui pose une préséance**, la comparaison descend dans `Serie` — l'agrégat devient
  inviolable quel que soit l'appelant — et le service ne garde que la phrase du refus.
- **La discrimination des trois rôles à la frontière n'est pas acquise sur la route concernée.** Sur
  `POST /saisie/volees`, seul `autoriser_saisie` est monté, et il ne distingue que deux états
  (admin = `None`, poste). Composer une troisième identité y suppose une dépendance neuve.
- ~~Si la règle vaut pour tous les formats, elle atterrit sur les **sept sites** de `DETTE-065`~~ →
  **tranché à la décision 5 : elle n'y atterrit pas.** Elle ne vaut que pour la qualification et vit
  en **un** endroit — le service de saisie. `DETTE-065` n'est ni élargie ni résorbée. Si un autre
  format l'adopte un jour, c'est **alors** que la règle devra sortir du service, et jamais être
  recopiée dans chaque routeur.

## Porté dans le code par

*(Section remplie le 12/09/2026 par `E16US020`, **en relisant le code livré**. ⚠️ **Et RÉÉCRITE en
2ᵉ passe** : la 1ʳᵉ rédaction était une table `décision | module | test`, qui a produit **sept
faux signaux `portage-symbole-absent`** — l'atlas rapporte tous les identifiants d'une ligne à
chaque fichier de cette ligne, donc les noms de tests étaient réclamés dans les modules de
production. Noyer le seul contrôle mécanique capable d'attraper un ADR-0017 bis, sous des faux
positifs portant son propre numéro, est pire que de ne rien écrire. Format à puces, comme
[ADR-0109](0109-une-volee-en-correction-reste-comptee.md), qui n'en produit aucun.)*

- `backend/domain/role.py` — `Role`, l'ordre de la **décision 1** (`POSTE_DE_CIBLE < SCOREUR <
  ADMIN`). ⚠️ C'est un `IntEnum` : l'ordre **est** la donnée, et sa renumérotation ne réinterprète
  pas les lignes existantes parce que la persistance écrit le **nom**.
- `backend/application/saisie.py` — `_refuser_role_inferieur` (la comparaison elle-même) et
  `_libelle_role` (la phrase du refus). ⚠️ La **décision 2** n'est plus portée ici : le rang est un
  paramètre **sans défaut** des deux chemins d'écriture, et se calcule dans `api/v1/saisie.py`, là
  où la garde a parlé. *(3ᵉ passe de revue : le déduire de `contexte is None` accordait le rang le
  plus haut par omission — un défaut `fail-open`. mypy tient désormais ce qu'un commentaire disait.)* ⚠️ La **décision 3** n'est portée par aucun code : c'est l'**absence** de branche, la
  comparaison étant `<` stricte. Elle ne se lit donc que dans son test négatif — c'est pour cela
  que la décision l'exigeait.
- `backend/domain/serie.py` — `Serie.annuler_validation` remet `role_de_saisie` à `None` sur le lot
  rouvert (**décision 4**) ; `Serie.saisir_volee` **et** `Serie.corriger_volee` reposent une
  préséance. ⚠️ **`corriger_volee` manquait à la 1ʳᵉ rédaction**, et c'est exactement le défaut
  d'ADR-0017 : le scoreur corrigeait sans revendiquer, la tablette écrasait en silence.
- `backend/api/v1/saisie.py` — `POST /saisie/volees` (rang dérivé d'`autoriser_saisie`) et
  `POST /saisie/corrections` (rang `SCOREUR`, dérivé d'`exiger_scoreur`). ⚠️ **Ce second est le seul
  site où `Role.SCOREUR` s'inscrit en base** : la route de saisie n'admet que l'admin et le poste.
- `backend/application/erreurs/tir.py` — `EcritureDeRoleInferieur` (`409`), mappée par le `else`
  final d'`backend/api/erreurs.py` : 409 **est** la branche par défaut des conflits d'état, aucune
  erreur 409 du dépôt n'ayant d'entrée nominative.
- `backend/infrastructure/db/models.py` (`VoleeORM.role_de_saisie`),
  `backend/migrations/versions/0055_volee_role_de_saisie.py` (la colonne, sans reprise) et
  `backend/infrastructure/db/repositories/tir.py` (`_vers_role`, l'aller-retour par le **nom**).
  ⚠️ `_vers_role` **dégrade** sur un nom inconnu au lieu de lever : il est sur le chemin de
  `par_phase`, donc du classement entier d'un départ.
- `frontend/src/features/saisie/Saisie.tsx` (`MessageErreurSaisie`, le refus expliqué),
  `frontend/src/features/saisie/hooks.ts` (`onError`, qui relit la vérité serveur) et
  `frontend/src/features/saisie/horsLigne.ts` (`CODES_DEFINITIFS` : ce `409` est le **premier refus
  définitif du produit**, et le classer transitoire gelait la file du poste).

**Épinglé par** — `backend/tests/test_preseance_de_role.py` (l'ordre, les deux sens du refus, le
rang du milieu par sa route de correction, la remise à zéro, le marqueur déclaratif sans autorité,
le libellé du refus, et le **test négatif** de la décision 3) ·
`backend/tests/test_serie_repository.py` (l'aller-retour **réel** de la colonne sur base migrée, et
la dégradation sur nom inconnu) · `backend/tests/test_saisie_api.py` (le `409` et sa phrase bout en
bout, le `200` à rangs égaux, et le garde-fou du rang du milieu sur la route de saisie) ·
`frontend/src/features/saisie/Saisie.test.tsx`, `frontend/src/features/saisie/hooks.test.tsx` et
`frontend/src/features/saisie/rejeu.test.ts`.

⚠️ **Ce que cette section ne doit PAS laisser croire.** La règle ne vaut que pour la volée de
qualification (décision 5) : `DETTE-065` n'est pas touchée. Et **aucun des deux croisements n'est
joignable depuis les écrans livrés** (`DETTE-100`) — ni admin → poste (pas d'écran d'administration
qui saisisse), ni scoreur → poste (`POST /saisie/corrections` n'a aucun appelant front). Les deux
routes sont gardées et testées ; c'est la surface qui manque, des deux côtés.

<details><summary>Rédaction d'origine (10/09/2026), conservée — c'est elle qui a évité le défaut d'ADR-0017</summary>

> ⚠️ **Rien à ce jour, et c'est écrit exprès.**
>
> La décision est prise ; l'US qui la porte n'est pas prise. Nommer ici `backend/api/dependances.py`
> ou `backend/domain/serie.py` ferait exactement ce qu'ADR-0017 a fait pendant treize mois : désigner
> un module qui ne porte pas la décision, et rendre la vérification impossible en la faisant croire
> faite.

</details>
