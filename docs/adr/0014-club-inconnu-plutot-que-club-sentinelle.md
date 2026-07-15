# ADR-0014 — Le club d'un archer est facultatif : `NULL` = *inconnu*, jamais un club

- **Statut** : Accepté
- **Date** : 2026-07-15
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E02-inscriptions.md`](../../stories/E02-inscriptions.md) (E02US002 : le CA
  disait « club obligatoire ») ; [`modele-de-donnees.md`](../modele-de-donnees.md) (`ARCHER`)
- **Introduit par** : E02US002 (créer un archer) ; **lie** E03US006 (mixité club), E08US004 /
  E09US004 (sommes par club), E12US005 (complétude), E02US005 (doublons)

## Contexte et problème

E02US002 devait rendre `archer.club_id` **NOT NULL** (« nom, prénom, club, catégorie
obligatoires »). Trois faits se contredisaient :

1. **En FFTA, tout licencié a un club** — le club n'est jamais réellement absent ;
2. **le jour J, on ne le connaît pas toujours** — l'archer se présente au guichet, sa licence est
   restée dans la voiture. Refuser l'inscription pour cette raison est inacceptable : c'est le
   moment où l'outil doit aller vite ;
3. **les archers déjà en base n'ont pas de club**, et la migration `0014` avait explicitement refusé
   d'en inventer un pour les rétro-remplir.

Le problème n'est donc pas « le club est-il obligatoire ? » (il l'est, réglementairement) mais
**« que dit la base quand on ne sait pas encore ? »**.

## Options

1. **`NOT NULL` + club sentinelle « Sans club »** — la contrainte tient, la migration passe, rien
   n'est perdu. Mais le référentiel des clubs est **global** (E02US001, pas de `tournoi_id`) : le
   sentinelle apparaîtrait dans tous les tournois, pour toujours, et deviendrait non supprimable dès
   le premier archer qui le référence (`ClubReference` → 409, livré en E02US001).
2. **`NOT NULL` strict** — le plus honnête vis-à-vis du CA, mais interdit l'inscription au guichet
   dans le cas 2 ci-dessus, et exige un rétro-remplissage impossible.
3. **`NULL` = club inconnu** — l'inscription passe, l'information manquante reste *marquée comme
   manquante*, et l'écran la signale.

## Décision

Retenir l'option 3. **`archer.club_id` est nullable, et `NULL` signifie « club encore inconnu » —
jamais « aucun club », jamais un club.**

- **Un `NULL` est une anomalie, pas un état légitime.** Le classement marque « Club inconnu » sur la
  ligne de l'archer concerné, et E12US005 le comptera parmi ce qui manque avant de lancer le
  tournoi. On ne s'en accommode pas : on le rend visible pour qu'il soit résorbé. **La liste
  déroulante de saisie n'est pas ce signalement** — elle est l'entrée du formulaire ; le signal
  porte sur les archers **déjà inscrits**, ceux qu'on ne regarde plus.
- **Aucun club sentinelle, jamais.** C'est l'interdit central de cet ADR : il **détruirait**
  l'information au lieu de la porter (voir Conséquences).
- **La catégorie, elle, reste `NOT NULL`** — asymétrie délibérée. La catégorie se lit sur l'archer
  présent (âge, arme) ; elle n'est pas une donnée externe. Sans elle il n'est ni classable, ni
  plaçable, ni facturable : c'est un état **inexploitable**, pas une inconnue temporaire.
- **Supprimer un club référencé reste refusé** (409, `ClubReference`) alors même que le modèle le
  permettrait désormais : `NULL` doit dire « pas encore su », pas « effacé par mégarde ». Une
  suppression forçante, si elle se justifie un jour, est une US à part.
- **Deux inconnus ne sont pas égaux — pour *affirmer* quoi que ce soit.** Deux archers sans club
  **peuvent** partager une cible : rien ne prouve qu'ils sont du même club, et le placement
  (E03US006, RG-3) doit donc traiter le cas comme **indécidable** — jamais comme « même club ».
  **Ne pas dériver ce prédicat de `domain.archer.cle_identite`** : cette clé sert au **signalement
  d'un doublon de saisie**, une question différente, et elle rapproche délibérément deux archers
  sans club (un signalement réversible peut se permettre d'être conservateur ; une décision de
  placement, non). Les deux sémantiques de `NULL` coexistent à dessein — `NULL = NULL` pour
  *suggérer*, `NULL ≠ NULL` pour *décider*. Ce que `cle_identite` garantit en revanche, et qui vaut
  ici : elle ne rapproche **jamais** un archer sans club d'un archer rattaché.

## Conséquences

- **+** L'inscription au guichet n'est jamais bloquée par une information administrative absente.
- **+** **L'ignorance reste dite.** C'est le vrai gain, et il se voit en E03US006 : RG-3 exige « ≥ 2
  clubs par cible **lorsque c'est possible** ». Avec un sentinelle, deux archers au club inconnu
  porteraient le **même** `club_id` — le moteur les croirait du même club et refuserait de les
  réunir, sur la foi d'une donnée que personne n'a saisie. Avec `NULL`, le cas reste *indécidable*,
  ce qu'il est réellement, et le placement peut le signaler (« mixité non garantie ») au lieu de se
  tromper en silence. **Un sentinelle transforme une inconnue en affirmation fausse.**
- **+** Le référentiel des clubs ne contient que de vrais clubs — donc les sommes par club
  (E08US004, E09US004) restent lisibles, et les `NULL` s'agrègent naturellement en « club inconnu »
  au lieu de se cacher derrière un faux club.
- **+** La migration `0015` n'a aucun club à rétro-remplir : la position de `0014` est tenue.
- **−** Le CA d'E02US002 était **faux** et a été corrigé dans `stories/` : « club obligatoire »
  décrivait la règle FFTA, pas ce que la base peut affirmer. Laisser les deux se contredire aurait
  fait de `stories/` un document ambigu (mécanisme de [DETTE-003](../dette.md)).
- **−** Tout consommateur de `club_id` doit gérer le `None` (placement, exports, paiements). C'est
  le prix de l'honnêteté : le sentinelle l'aurait masqué en le rendant faux.
- **−** **Rien ne force la complétion.** Le signalement livré par E02US002 est *passif* : le
  classement marque « Club inconnu » sur la ligne de l'archer (seule surface où un archer inscrit
  apparaît tant qu'E02US003 n'existe pas), et rien d'autre. Aucun écran ne totalise les incomplets,
  aucune action n'est bloquée : un archer sans club peut traverser tout le tournoi. C'est E12US005
  (« afficher la complétude ») qui fermera ce trou. **Ne pas confondre les deux** — un marqueur sur
  une ligne n'est pas un garde-fou, c'est un rappel.

## Alternative écartée — un numéro de licence FFTA

Ajouter `archer.licence` (identifiant national, unique par archer) distinguerait deux homonymes du
même club et permettrait un dédoublonnage **entre tournois**. Écartée **pour l'instant**, pour trois
raisons : (a) elle ne résout rien si elle est nullable — `NULL ≠ NULL` dans un index SQL, on
retombe sur le cas du club ; (b) obligatoire, elle impose la saisie d'un numéro à 7 chiffres au
guichet, exactement le blocage qu'on refuse ici ; (c) elle n'existe dans aucun CA ni dans le modèle
de données. Elle arrivera naturellement avec **E02US007** (import inscript'arc), où le fichier
fédéral la porte déjà — c'est là qu'elle aura un usage réel plutôt qu'une saisie manuelle.

## Liens

ADR-0006 (vocabulaire) ; ADR-0007 (erreurs par couche : `CategorieHorsTournoi` → 409) ;
[`modele-de-donnees.md`](../modele-de-donnees.md) (`ARCHER`) ;
[`referentiel-ffta.md`](../referentiel-ffta.md) ; [`dette.md`](../dette.md) DETTE-001 ;
CDC fonctionnel RG-3, EF-4.5 ; `backend/domain/archer.py` ;
`backend/migrations/versions/0015_archer_inscription.py`.
