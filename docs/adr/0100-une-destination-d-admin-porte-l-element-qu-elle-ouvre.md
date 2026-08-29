# ADR-0100 — Une destination d'admin porte, dans son adresse, l'élément qu'elle ouvre

- **Statut** : Accepté
- **Date** : 2026-08-29
- **US** : E16US010
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0059](0059-routage-par-role-dans-l-url-routeur-maison.md) — le routeur maison, et le principe
    qu'il **ignore** la structure interne de l'admin : c'est `axes.ts` qui interprète les segments
  - [ADR-0058](0058-decoupage-de-l-admin-en-trois-axes-d-activite.md) — les trois axes ; l'élément
    ouvert ne déplace aucune activité, il désigne une ligne **là où elle vit déjà**

> ⚠️ **Cet ADR ne figure pas à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md), et c'est volontaire.**
> Il est de **navigation et d'IHM** : aucun moteur sportif ne lit une adresse, aucune portée ne
> change, aucune politique injectable n'est en jeu. Le critère de `CLAUDE.md` exclut nommément les
> ADR d'UI ; les précédents existent (`0095`, `0096`, `0098`). Il porte en revanche sa section
> « Porté dans le code par », exigée de **tout ADR neuf**.

## Contexte

Le CA d'E16US010 demande qu'un résultat de recherche permette « **d'ouvrir la fiche en
modification** ». En allant voir le code, on découvre que **rien ne peut le faire** :

- l'état d'édition d'une ligne est un `useState(false)` **local à la ligne** — `Archers.tsx`,
  `Clubs.tsx`, `Tournois.tsx` portent le même patron. Aucun appelant extérieur ne peut l'atteindre ;
- l'adresse d'admin n'a que trois segments : `/admin/<tournoi?>/<axe?>/<destination?>`. Elle sait
  dire « quel écran », jamais « quelle ligne » ;
- et le projet a **délibérément** mis tout l'état de navigation dans l'URL (ADR-0059,
  `useChemin`) : il n'existe pas de store Zustand de navigation où glisser l'information.

Trois issues étaient possibles. **(a)** Un store de navigation : contredit le principe de l'URL
comme source unique, et un F5 reperdrait la fiche. **(b)** Un `useState` synchronisé sur l'adresse
par un effet : deux sources — dès qu'on referme la fiche, l'adresse continue de la désigner et le
même lien cesse de la rouvrir. **(c)** Étendre l'adresse. C'est (c).

## Décision

**1. L'élément qu'un écran ouvre fait partie de son adresse.** Le contrat d'adresse d'admin devient
`/admin/<tournoi?>/<axe?>/<destination?>/<élément?>`. Le 4ᵉ segment est numérique ; il n'est jamais
confondu avec le tournoi, qui est en tête.

**2. Ouvrir n'est pas sélectionner.** `selectionneId` désigne le tournoi **sur lequel on travaille**
et se reconduit d'écran en écran ; l'élément ouvert **déplie un formulaire** et ne concerne que
l'écran courant. Les confondre ferait s'ouvrir une fiche à chaque changement de tournoi courant.

**3. Deux formes d'adresse, un seul sens.** La liste des tournois vit sur **l'accueil**, qui n'a ni
axe ni destination : un 4ᵉ segment ne l'atteint pas. Le segment littéral `fiche` demande donc
l'ouverture — `/admin/12` dit « c'est celle-là », `/admin/12/fiche` dit « ouvre-la », et
`/admin/12/fiche/7` dit « ouvre la fiche du 7 **sans quitter** le 12 ». C'est une seconde forme,
pas un second mécanisme : les deux alimentent le **même** champ `elementDemande`, et les trois
listes consomment la **même** prop.

> ⚠️ **Corrigé en revue le 29/08/2026, et la correction touche le §2.** La 1ʳᵉ rédaction faisait de
> l'élément **le tournoi courant lui-même** (`segmentsAdmin(id, null, null, id)`). Cela contredisait
> le §2 dans les faits : ouvrir la fiche du tournoi 7 depuis le 12 **changeait le tournoi de
> travail**, et refermer la fiche renvoyait sur `/admin` nu, désélectionnant tout. Deux slots
> distincts dans l'adresse, deux sens — c'est ce que le §2 promettait, et ce que la forme longue
> tient enfin.

**4. L'ouverture est l'adresse, pas un état qui la copie.** Le hook `useOuvertureParAdresse` dérive
l'ouverture de la prop et **remonte** la fermeture par un `onOuvrir(null)` qui réécrit l'adresse.
Un repli en état local subsiste pour les points de montage qui ne routent pas (tests, écrans
autonomes) : c'est la seule concession, et elle est explicite.

**5. Un élément sans écran pour l'ouvrir est ignoré.** `/admin/12/gestion/57` ne porte pas
d'élément : sans destination, personne ne le consommerait et l'adresse porterait un état mort.

## Conséquences

**Acquis.** Une fiche devient **adressable** : le lien se copie, se met en favori, survit au F5 et
au bouton *Précédent*. C'est un bénéfice que le CA ne demandait pas et qui tombe gratuitement.
La recherche transverse peut tenir sa promesse sur les trois entités.

**Coût.** `analyserSegmentsAdmin` et `segmentsAdmin` gagnent un champ et un paramètre ; les trois
composants de liste gagnent deux props. `RouteAdmin` ayant un champ de plus, les attentes
exhaustives d'`axes.test.ts` ont dû être complétées — c'est le prix d'un contrat testé, et il est
juste : un champ ajouté en silence n'aurait fait tomber aucun test.

**Piège à connaître.** La réciprocité `segmentsAdmin` ↔ `analyserSegmentsAdmin` est ce qui garantit
qu'un lien rouvre la même vue. Elle est **testée dans les deux formes** ; une troisième forme
d'adresse devra l'être aussi, sans quoi une fiche s'ouvrirait à l'aller et pas au retour.

**Ce que cet ADR ne tranche pas.** Le 4ᵉ segment désigne un élément **par son identifiant** : il ne
dit pas *ce qu'on lui fait*. « Ouvrir en modification » (hors pilotage) et « ouvrir en consultation
puis agir » (en pilotage) sont deux lectures du même segment, portées par les écrans. Si un jour un
écran devait offrir les deux, il faudrait un mot de plus dans l'adresse — pas un second mécanisme.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 — l'élément entre dans l'adresse | `frontend/src/features/admin/axes.ts` (`RouteAdmin.elementDemande`, `analyserSegmentsAdmin`, `segmentsAdmin`) | oui |
| §1 — le routeur reste ignorant de la structure admin (ADR-0059) | `frontend/src/shared/navigation/routeur.ts` — **inchangé** : il ne connaît que `segments` | oui — aucune ligne touchée |
| §2 — ouvrir ≠ sélectionner | `frontend/src/features/tournois/Tournois.tsx` (`GestionTournois` reçoit `selectionneId` **et** `ouvrir`, deux props distinctes) | oui |
| §3 — la seconde forme, sur l'accueil, **sans écraser le tournoi courant** | `frontend/src/features/admin/axes.ts` (`SEGMENT_FICHE`, `elementOuvert`, `segmentsAdmin`) · `frontend/src/features/admin/CoquilleAdmin.tsx` (`ouvrirFicheTournoi` passe `tournoiId` **et** `id`) — gardé par `axes.test.ts` (`['12','fiche','7']` → tournoi 12, élément 7 ; fermer rend `['12']`) | oui — ⚠️ corrigé en revue, cf. l'encadré du §3 |
| §3 — un seul champ, une seule prop | `axes.ts` (`elementDemande`) consommé par les trois listes via `ouvrir` | oui |
| §4 — l'ouverture **est** l'adresse | `frontend/src/shared/navigation/useOuvertureParAdresse.ts` — gardé par `frontend/src/shared/navigation/useOuvertureParAdresse.test.tsx` (l'écran monté avec `ouvrir`/`onOuvrir` : la fiche désignée est ouverte, elle seule, et la fermeture remonte `onOuvrir(null)`) | oui — ⚠️ **corrigé en revue** : cette cellule citait `axes.test.ts`, qui garde la réciprocité du **parseur** et ne touche jamais le hook. Nommer un module qui n'applique pas ce qu'on lui prête est le défaut qu'ADR-0075 documente (ADR-0028, ADR-0049) — il s'est reproduit ici, dans l'ADR qui l'annonçait |
| §4 — le repli local est explicite | `useOuvertureParAdresse` (branche `onOuvrir === undefined`) | oui |
| §1 — l'adresse **canonique** conserve l'élément | `frontend/src/features/admin/axes.ts` (`segmentsCanoniques`) · `frontend/src/features/admin/CoquilleAdmin.tsx` (l'effet de correction d'adresse l'appelle) — gardé par `axes.test.ts` **et** par `frontend/src/features/admin/AdresseElement.test.tsx`, qui monte la coquille | oui — ⚠️ **c'était le bloquant de la revue** : la correction d'adresse rappelait `segmentsAdmin` sans son 4ᵉ argument et effaçait l'élément par `replaceState`, si bien qu'aucune fiche ne s'ouvrait hors de l'accueil. Trois axes l'ont trouvé ; aucun test ne pouvait le voir, tous portant sur des fonctions pures |
| §5 — un élément orphelin est ignoré | `axes.ts` (`elementOuvert`, garde `destination !== null`) — gardé par `axes.test.ts` (`un élément SANS destination pour l'ouvrir est ignoré`) | oui |
| §1 — l'axe d'une destination n'est jamais réécrit à la main | `CoquilleAdmin.tsx` (`ouvreurDe` lit `AXE_PAR_DESTINATION`) | oui |
