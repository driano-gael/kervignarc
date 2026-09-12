# ADR-0107 — Une écriture concurrente est arbitrée par le rôle de qui écrit

- **Statut** : Accepté *(et **porté** depuis le 12/09/2026 — cf. § « Porté dans le code par ». ⚠️ **Portée réelle : la volée de qualification seule** ; les autres formats gardent le *dernier écrit gagne*)*
- **Date** : 2026-09-10 *(décision)* · 2026-09-12 *(mise en œuvre)*
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

**2. Le rôle est celui de la garde, jamais celui du message.** `Volee.saisie_par` **existe** mais sa
propre docstring le qualifie de **déclaratif** : c'est un nom libre, issu du corps de la requête.
L'employer comme source d'autorité livrerait une hiérarchie qu'un poste contourne en se déclarant
admin. Le rôle se lit sur l'identité **résolue par la garde** — jeton de poste, session scoreur,
session admin. ⚠️ **Ne pas lire « authentifiée »** : le rôle le plus bas ne l'est justement pas, il
est identifié par le lieu (ADR-0030), et c'est ce qui rend l'ordre nécessaire.

**3. À rôles égaux, la règle n'arbitre rien** — et c'est assumé. Deux tablettes de cibles
différentes portent le **même** rôle : entre elles, le dernier écrit gagne, exactement comme
aujourd'hui.

⚠️ **C'est un renoncement déclaré, pas déguisé, et il porte sur le cas le plus fréquent en salle.**
Il se prouve par un test **négatif** (« deux postes écrivent successivement : le second gagne, `200`,
aucun `409` »), qui épingle le comportement actuel. **Critère de réouverture** : on reprend
l'alternative écartée si un tournoi réel remonte **au moins une saisie perdue entre deux postes**.

**4. La préséance ne survit pas au conflit — et une annulation de validation la remet à zéro.** Le
rôle de la dernière écriture ne verrouille pas la volée pour toujours contre les rôles inférieurs.
Sans cette borne, un admin — ou un scoreur, le cas majoritaire — qui annule une validation rendrait
la volée inaccessible à ceux qui doivent la corriger, ce qui **contredirait** le CA d'annulation qui
exige qu'elle reste écrivable par le poste de cible.

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
- **La discrimination des trois rôles à la frontière n'est pas acquise sur la route concernée.** Sur
  `POST /saisie/volees`, seul `autoriser_saisie` est monté, et il ne distingue que deux états
  (admin = `None`, poste). Composer une troisième identité y suppose une dépendance neuve.
- Si la règle vaut pour tous les formats, elle atterrit sur les **sept sites** de `DETTE-065` (le
  garde d'autorisation des routeurs d'écriture, recopié sept fois). Elle doit alors vivre en **un**
  endroit — service ou domaine —, jamais recopiée dans chaque routeur.

## Porté dans le code par

*(Section remplie le 12/09/2026 par `E16US020`, **en relisant le code livré** et non en déduisant de
la décision — l'avertissement de `CLAUDE.md` § « Décision structurante ⇒ ADR ». La rédaction
précédente disait « rien à ce jour, et c'est écrit exprès » ; elle est reproduite sous la table, car
c'est elle qui a évité le défaut d'ADR-0017.)*

| Décision | Portée par | Épinglée par |
|---|---|---|
| **1** — l'ordre `poste < scoreur < admin` | `backend/domain/role.py` (`Role`, `IntEnum`) ; la comparaison elle-même est dans `_refuser_role_inferieur`, `backend/application/saisie.py` | `test_l_ordre_des_roles_est_poste_puis_scoreur_puis_admin`, `test_un_role_inferieur_est_refuse`, `test_un_role_superieur_ecrase` |
| **1** — le `409` et sa phrase | `EcritureDeRoleInferieur` (`backend/application/erreurs/tir.py`) → `else: status = 409` d'`backend/api/erreurs.py` ; l'écran par `MessageErreurSaisie` (`frontend/src/features/saisie/Saisie.tsx`) | `test_un_poste_ne_peut_pas_ecraser_la_saisie_de_l_organisateur` ; `Saisie.test.tsx` |
| **2** — le rôle vient de la garde | `_role_de_saisie(contexte)`, `backend/application/saisie.py` — dérivé de `ContexteSaisie`, que seule `autoriser_saisie` construit | `test_un_poste_ne_gagne_aucune_autorite_en_se_declarant_admin`, `test_le_marqueur_declare_ne_confere_pas_la_preseance_retenue` |
| **3** — à rôles égaux, rien n'est arbitré | **Aucun module** : c'est l'absence de branche dans `_refuser_role_inferieur` (`role < existante.role_de_saisie`, strict) | `test_a_roles_egaux_le_second_gagne_sans_conflit` — le test **négatif** exigé par la décision |
| **4** — l'annulation remet la préséance à zéro | `Serie.annuler_validation`, `backend/domain/serie.py` (`role_de_saisie=None` sur le lot rouvert) | `test_annuler_une_validation_efface_la_preseance_du_lot`, `test_apres_annulation_le_poste_peut_ressaisir_ce_qu_un_admin_avait_ecrit` |
| **L'état persisté** que les *Conséquences* déclaraient requis | `Volee.role_de_saisie` (domaine) ↔ colonne `volee.role_de_saisie` (migration `0055`), traduite par `_vers_role` dans `backend/infrastructure/db/repositories/tir.py` | `test_la_volee_retient_le_role_de_qui_l_a_ecrite`, `test_le_role_persiste_est_le_nom_jamais_le_numero` |

⚠️ **Ce que cette section ne doit PAS laisser croire — la règle ne vaut que pour la volée de
qualification.** Arbitré le 12/09/2026 : duels, poules, système suisse, colline et Big Shoot Off
gardent le *dernier écrit gagne*. Ce n'est pas un cas particulier écrit dans le code — la préséance
est portée par la **donnée**, et une surface qui ne revendique aucun rôle (`role_de_saisie` à `None`)
n'oppose rien. Conséquence directe : les **sept sites de `DETTE-065`** annoncés au paragraphe
précédent **ne sont pas touchés**, et cette ligne de dette n'est ni élargie ni résorbée par `E16US020`.

⚠️ **La discrimination des trois rôles à la frontière n'a PAS été acquise, et le rang du milieu n'est
porté par aucune route.** `_role_de_saisie` lit `contexte is None` comme « admin » parce
qu'`autoriser_saisie` n'admet que deux identités ; aucun scoreur n'écrit de volée de qualification.
L'ordre à trois rangs n'est donc prouvé que par les tests de domaine. Ouvrir cette route au scoreur
**sans** faire porter son rôle par `ContexteSaisie` lui donnerait en silence la préséance de
l'organisateur — `test_un_scoreur_n_est_pas_une_identite_de_saisie_de_qualification` rougira ce
jour-là, et c'est son unique office.

<details><summary>Rédaction d'origine (10/09/2026), conservée — c'est elle qui a évité le défaut d'ADR-0017</summary>

> ⚠️ **Rien à ce jour, et c'est écrit exprès.**
>
> La décision est prise ; l'US qui la porte n'est pas prise. Nommer ici `backend/api/dependances.py`
> ou `backend/domain/serie.py` ferait exactement ce qu'ADR-0017 a fait pendant treize mois : désigner
> un module qui ne porte pas la décision, et rendre la vérification impossible en la faisant croire
> faite.

</details>
