# ADR-0056 — Le lancement d'un tour est un acte audité et diffusé, pas un statut sur le tableau

- **Statut** : Accepté
- **Date** : 2026-07-28
- **Décideurs** : Organisateur / Architecte
- **Portée** : E12US002 (lancer un tour — feu vert + lancement)
- **Lie** : [ADR-0049](0049-saisie-et-scoring-des-duels.md) (le tableau **non persisté**, reconstruit
  du classement et rejoué des duels validés — la raison structurelle pour laquelle il n'y a « rien à
  lancer » au sens état), [ADR-0005](0005-async-et-sqlite.md) / règle 7 (writer unique + **diffusion
  post-commit** — le mécanisme sur lequel s'appuie l'émission), [ADR-0040](0040-alerte-par-calcul-d-impact.md)
  (« chiffrer ce qu'on déclenche », recalcul dans la file jamais cru sur parole — précédent réutilisé),
  [ADR-0035](0035-atomicite-acte-trace-session-partagee.md) (la trace d'audit comme acte de première classe),
  [ADR-0048](0048-cote-a-cote-des-duellistes-par-reordonnancement.md) (le plan de duels d'où sort la cible d'un duelliste).

## Contexte

E12US002 livre **le geste central du jour J** : voir en continu ce qui est prêt à faire tirer, puis
**lancer** le tour suivant d'un geste. La story pose l'invariant `D-23` (« l'unité lançable est
l'événement, le duel — pas le tour ») et `D-09` (« les 4 canaux servis ensemble : tablettes
E04US018, téléphones E07US008, écran de salle E07US004, table d'organisation E12US006 »).

Trois faits du code d'aujourd'hui cadrent la décision :

1. **Le tableau n'est pas un état persistant.** Il est **reconstruit** du classement et **rejoué**
   des duels validés à chaque lecture (ADR-0049). Un `Duel`/`Match` n'a donc **aucun** statut « lancé
   » où l'on pourrait écrire — seulement `validee_par` (le tir validé). Il n'existe littéralement
   « rien à lancer » au sens d'une transition d'état d'agrégat.
2. **La diffusion temps réel est post-commit.** Toute écriture qui passe par la file (writer unique,
   règle 7 / ADR-0005) notifie les listeners après commit ; un listener publie le `LiveEvent` que la
   commande renvoie (sinon un générique `donnees_modifiees`). **Rien ne diffuse sans écriture.**
3. **3 des 4 canaux récepteurs n'existent pas encore** : E04US018 (tablette), E07US008 (public) et
   E07US004 (écran de salle) sont à venir ; seule la recherche (E12US006) est livrée, et elle
   n'affiche pas encore les affectations de duel. « Servir les 4 canaux ensemble » n'est donc
   **pas** entièrement réalisable aujourd'hui.

Le **périmètre** a été tranché au cadrage avec l'organisateur : livrer **le feu vert (lecture)** et
**le geste de lancement** dès maintenant, en actant que la matérialisation dans les 3 canaux sortants
est **séquencée** vers leurs US — même motif que E12US005/E12US006 face à EPIC-05. La question
restait : *comment* le geste part, sans statut où l'écrire et sans récepteur ciblé à ce jour.

## Décision

**Le lancement d'un tour est un acte d'audit qui déclenche la diffusion d'un événement typé — il ne
pose aucun statut sur le tableau.**

1. **Nouvelle nature d'acte auditée `LANCEMENT`** (`domain.entree_audit.ActionAuditee`). Lancer, c'est
   un acte de pilotage sensible du jour J : **daté, attribué** (rôle admin, un secret — pas un nom,
   comme la trace `REPLACEMENT`), consultable. C'est le seul « écrit » du geste, et il est
   **justifié en soi** (traçabilité `D-15` / E10US005). Il est aussi la **seule écriture minimale**
   qui, passant par la file, permet à la diffusion post-commit de partir sans violer la règle 7.
2. **La commande de lancement renvoie un `LiveEvent("tour_lance", …)` typé.** Le listener post-commit
   le diffuse tel quel : c'est le **point de branchement** unique des 4 canaux. Les récepteurs ciblés
   (E04US018/E07US008/E07US004) s'abonneront à ce type quand ils existeront ; jusque-là le signal
   **part** mais n'est écouté de façon ciblée par personne — assumé, séquencé.
3. **Aucun statut « lancé » sur le duel ni le tableau.** Le tableau reste reconstruit (ADR-0049) ;
   le feu vert est une **lecture pure** sur ce tableau + le plan de duels persisté. Le service de
   pilotage (`application.pilotage_tour.ServicePilotageTour`) **compose** `ServiceSaisieDuels`
   (reconstruction + noms), `ServicePlacementDuels` (la cible de chaque duelliste) et `ServiceAudit`
   (la trace) — service→service, sur le précédent de `ServiceClassement`. Aucun repository neuf.
4. **Le lancement est recalculé dans la file, jamais cru sur parole** (précédent ADR-0040) : au
   moment d'agir, le feu vert est reconstruit et **seuls les duels réellement prêts** (jouables **et**
   placés) partent ; un duel demandé qui n'est plus prêt est écarté ; s'il ne reste rien, l'acte est
   un conflit d'état (`AucunDuelALancer`, 409 — rien à émettre, aucune trace). L'unité lançable est le
   **duel** (`D-23`) : le lancement global fait partir tous les prêts, un sous-ensemble est accepté.
5. **`Q-UX6` reste partiellement ouverte.** Le feu vert livre le **socle minimal** du CA — par duel :
   *participants connus ?*, *cible attribuée ?*, *source amont validée ?* (avec le blocage **nommé**,
   « en attente du duel n°3 »). Les métriques d'exploitation supplémentaires (poste en ligne, scoreur
   disponible, conflit de placement) restent à arrêter devant l'écran avec l'organisateur.

## Conséquences

**Positives**

- **Fidèle à l'architecture** : réutilise le patron « écriture → audit co-écrit → `LiveEvent`
  post-commit » (ADR-0040/0035) sans rien inventer ; la règle 7 est intacte.
- **Pas de dette d'état** : aucun statut « lancé » à maintenir cohérent avec un tableau qui, lui, se
  reconstruit — on n'introduit pas un second système de vérité sur la progression.
- **Traçable** : chaque lancement laisse *qui / quand / quoi* dans le journal d'audit, exploitable
  dès aujourd'hui (l'endpoint admin d'audit existe).
- **Point de branchement prêt** : le jour où un canal récepteur naît, il s'abonne au type
  `tour_lance` — aucune reprise du geste de lancement.

**Négatives / limites assumées (séquencées, règle 9)**

- **Signal sans récepteur ciblé aujourd'hui.** 3 des 4 canaux n'existent pas : le lancement émet,
  mais seul un futur écran le matérialisera pour l'archer. Le feu vert (lecture) porte donc l'essentiel
  de la valeur livrée maintenant ; le geste est câblé et prêt.
- **Cible des tours ≥ 2 non attribuée.** Le placement 1→N est E05US010 (non livré) : un duel de tour
  ≥ 2, même jouable, ressort « cible non attribuée » tant que ce placement n'existe pas — le feu vert
  n'est **pleinement** vert que pour le premier tour du tableau. Honnête, séquencé.
- **Sans statut, « prêt » ne se distingue pas de « en cours de saisie ».** Un duel dont un scoreur a
  commencé (mais non validé) la saisie a toujours `vainqueur = None` : il réapparaît « prêt » au feu
  vert. Relancer ne fait que réémettre le signal (inoffensif — les archers sont déjà là). C'est le
  prix direct du choix « lancement = événement, pas état » ; un marqueur « lancé » le raffinerait, au
  prix d'une dette d'état qu'on refuse pour l'instant.

## Alternatives écartées

- **Un statut persistant « lancé » sur le duel/tour.** Donnerait « déjà parti vs à lancer » et
  survivrait aux reconnexions — mais introduit un état à tenir cohérent avec un tableau reconstruit
  (deux vérités sur la progression), pour un bénéfice nul tant qu'aucun récepteur ne l'exploite.
  Rejeté : de la dette d'état sans usage. Réexaminable si un besoin concret émerge.
- **Une diffusion directe hors file** (publier le `LiveEvent` sans écrire). Contournerait la règle 7
  et son invariant « on diffuse ce qui est committé » ; le signal ne laisserait aucune trace. Rejeté :
  moins idiomatique et non traçable, pour ne rien gagner (l'audit est de toute façon justifié).
- **Réduire E12US002 à la transition de statut `pret → en_cours` du tournoi** (`demarrer`). Confond le
  cycle de vie du *tournoi* (E01US017) avec le lancement d'un *tour de duels* : raterait le feu vert
  par duel et le chiffrage — tout le sujet de l'US. Rejeté.
