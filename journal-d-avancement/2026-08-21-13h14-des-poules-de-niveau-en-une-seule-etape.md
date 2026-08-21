# 21 août 2026, 13 h 14 — des poules de niveau en une seule étape

**Ce qui est nouveau.** Un tournoi club « en cascade » se monte maintenant sans corvée de saisie :
36 archers, une première phase de 6 poules de 6 pour estimer les niveaux, puis une seconde phase de
6 poules **composées par niveau** — les rangs 1-6 ensemble, puis les 7-12, et ainsi de suite. Le
classement de cette seconde phase est le classement final du tournoi, exact de 1 à 36. Tout le monde
tire jusqu'au bout ; personne n'est éliminé, et le classement est bien plus juste qu'après une seule
phase.

**Pour qui.** L'organisateur qui compose le déroulé. Jusqu'ici ce format était déjà réalisable, mais
il fallait écrire **six étapes à la main**, une par groupe de niveau, chacune avec sa tranche de
rangs — et tout refaire si l'effectif changeait. Désormais il coche « Par niveau » dans la fiche de
réglages, et l'outil découpe.

**Ce que ça change concrètement.**

- L'aperçu ne dit plus seulement combien de groupes, il dit **lesquels** : « 6 poules de niveau :
  rangs 1-6, 7-12, 13-18, 19-24, 25-30, 31-36 ».
- Le vainqueur du groupe des 31ᵉ-36ᵉ ressort **31ᵉ** au classement, jamais 1ᵉʳ. C'est le point le
  plus important : sans lui, le classement serait bien formé, plausible — et faux.
- Quand l'effectif ne tombe pas juste, ce sont les **groupes du bas** qui grossissent : 34 archers en
  poules de 6 donnent un groupe de 6 puis quatre de 7. On n'ajoute pas un adversaire à ceux qui
  jouent le podium.
- L'application **refuse** une deuxième phase de poules laissée « à l'équilibre » alors qu'elle est
  nourrie par des poules — le réglage par défaut y est presque toujours le mauvais. Une case permet
  de passer outre quand c'est voulu.

**Ce qui ne change pas.** Le réglage par défaut reste « à l'équilibre », et aucune phase déjà
enregistrée ne compose différemment. La façon de tirer, de compter les points et de départager est
strictement la même : « par niveau » est un réglage de la phase de poules, pas un format nouveau.

**Une bonne surprise en chemin.** La fiche d'US annonçait qu'il faudrait apprendre à chaque groupe
« quelle tranche du tournoi il dispute » — un mécanisme de plus, sur une notion délicate. En
vérifiant dans le code, il s'est avéré qu'il suffisait de **lire le classement de la phase groupe par
groupe** : chaque poule occupe alors naturellement sa tranche. Moins de mécanique, et surtout une
seule façon de situer un archer plutôt que deux.
