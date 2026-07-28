# 28 juillet 2026, 11h04 — Un accueil qui « raconte l'histoire » du tournoi

**Pour l'organisateur.** Jusqu'ici, choisir un tournoi ouvrait sur un écran ou un autre, sans vue
d'ensemble : rien ne disait d'un coup d'œil « où en est ce tournoi, qu'est-ce que je fais
maintenant ». C'était l'un des retours de la démo du 27/07 (« l'interface doit me raconter une
histoire claire »).

Désormais, choisir un tournoi ouvre son **Accueil-tableau de bord** :

- une **frise** montre les **sept étapes** de la vie du tournoi (brouillon → prêt → en cours →
  terminé → archivé, plus « en pause » et « annulé »), l'étape **courante surlignée** ;
- sous la frise, les **boutons d'action** possibles à ce stade — marquer prêt, démarrer, mettre en
  pause / reprendre, terminer, archiver, annuler — au bon endroit, au bon moment ;
- un bandeau de **chiffres-clés** (inscrits, réglés, postes en ligne) ;
- une liste **« à faire »** (ce qui manque pour finir, reprise de l'écran Complétude) et les
  **alertes** du moment (ce qui est à finir, les postes hors ligne).

**Un bug corrigé au passage.** Le pilotage du cycle de vie ne connaissait en réalité que **trois**
états côté écran (brouillon, en cours, terminé), alors que le tournoi en a **sept** depuis le mois
dernier. Résultat : dès qu'un tournoi passait « prêt » ou « en pause », les boutons **disparaissaient**
et on ne pouvait plus le piloter. C'est réglé : la frise couvre les sept états partout.

**Ce que ça ne fait pas.** L'accueil ne fait qu'**assembler** des informations déjà présentes
ailleurs — il ne calcule aucune nouvelle règle. Terminer un tournoi demande toujours sa **confirmation
chiffrée** (« il reste X à régler… »). L'**aide écran par écran** (« ce qui est saisissable et
pourquoi ») viendra dans une prochaine étape.

*Recette détaillée : [`docs/fonctionnel/E14US001.md`](../docs/fonctionnel/E14US001.md). Décisions :
[`docs/adr/0052-accueil-admin-contextualise-par-statut.md`](../docs/adr/0052-accueil-admin-contextualise-par-statut.md).*
