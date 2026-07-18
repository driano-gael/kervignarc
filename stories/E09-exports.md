# E09 — Exports & documents — User Stories

> EPIC : [EPIC-09](../epics/EPIC-09-exports.md) · Réfs : CDC fonctionnel M9 (QT3 : lib PDF).

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (8 → 5). Les
> anciennes US découpées par document/étape technique (lib PDF / feuille de marque / placement /
> club & paiement / classement catégorie / classement intégral) sont devenues des **critères
> d'acceptation** de l'US de capacité qui les porte. **Aucun comportement n'est perdu** (règle 9 —
> chaque ancien titre = une puce CA identifiée). Correspondance ancien → nouveau en fin de fichier.

---

### E09US001 — Socle PDF & feuille de marque
*En tant que* développeur (le socle) et organisateur (le document), *je veux* un socle de génération
PDF qui fonctionne dans l'exécutable packagé et produise la feuille de marque, *afin de* disposer du
premier document imprimable pour la saisie/l'archivage papier.
- **CA — socle PDF (ex-001)** : lib PDF choisie (**ReportLab** — QT3 tranchée, [ADR-0031](../docs/adr/0031-bibliotheque-pdf-reportlab.md))
  intégrée ; un document de test se génère ; ~~fonctionne dans l'exécutable packagé~~ → **volet
  packaging déféré à EPIC-11** (voir Notes).
- **CA — feuille de marque (ex-002)** : feuille par cible/archer avec zones de scores ; conforme aux
  données.
- **Notes** : **QT3 tranchée en ReportLab** ([ADR-0031](../docs/adr/0031-bibliotheque-pdf-reportlab.md)) —
  wheels autoportantes, aucune dépendance native, embarquable dans PyInstaller. **Arbitrage de
  périmètre (18/07/2026)** : aucun build PyInstaller n'existe encore (E00US012 = exécutable de *dev*
  seul ; le packaging complet est EPIC-11), donc la clause « fonctionne packagé » est **déférée à
  EPIC-11** — E09US001 choisit la lib et génère le PDF dans l'app qui tourne. Risque **R4** résiduel
  (validation dans le binaire) suivi dans la table des risques, à confirmer au 1ᵉʳ build d'EPIC-11 —
  **pas** au registre de dette (pas de raccourci dans le code livré ; « le registre n'est pas une
  liste de tâches »).
- **Absorbe** : ex-E09US001, E09US002. **Dépend de** : E00US012, E03US001 · **Jalon** : J1

### E09US003 — Listes imprimables (placement, club & paiement)
*En tant qu'*organisateur, *je veux* imprimer la liste de placement et la liste club/paiement, *afin
de* afficher l'accueil des archers et gérer l'administratif.
- **CA — placement (ex-003)** : liste archer → cible/position/départ ; triable par cible ou par nom.
- **CA — club & paiement (ex-004)** : par club/archer : nom/prénom, n° départ, nb départs, dû,
  payé/non ; totaux par club.
- **Absorbe** : ex-E09US003, E09US004. **Dépend de** : E09US001, E03US001, E08US002 · **Jalon** : J1

### E09US005 — Classements PDF (par catégorie, intégral 1→N)
*En tant qu'*organisateur, *je veux* exporter les classements par catégorie et le classement complet,
*afin de* les diffuser/afficher et publier le résultat final.
- **CA — par catégorie (ex-005)** : PDF par catégorie (qualif et duels) ; en-tête tournoi ;
  imprimable.
- **CA — intégral 1→N (ex-006)** : PDF listant les rangs 1→N ; cohérent avec E06US006.
- **Absorbe** : ex-E09US005, E09US006. **Dépend de** : E09US001, E06US001, E06US006 · **Jalon** : J3

### E09US007 — Déroulé horaire imprimable
*En tant qu'*organisateur, *je veux* imprimer le déroulé, *afin de* le communiquer.
- **CA** : PDF du déroulé (phases, tours, horaires) issu d'E03US010.
- **Dépend de** : E09US001, E03US010 · **Jalon** : J4

### E09US008 — Imprimer les QR de cible et les codes scoreurs
*En tant qu'*organisateur, *je veux* imprimer **un QR par cible** et **un code par scoreur**, *afin
de* monter la salle sans avoir **rien à configurer** le jour J.
- **CA** : **un QR par cible**, à poser sur le pied — il encode l'**URL de rattachement** du poste
  (E04US001) et porte **le code lisible en clair** en dessous (recours si le QR est abîmé ou
  l'appareil photo capricieux) ; **un papier par scoreur** avec son code personnel (E10US003) ;
  **régénérable** ; **lié au tournoi** (un nouveau tournoi = de nouveaux QR, cf. `D-07`).
- **Notes** : `D-07` et `P-6` (« tout ce qui s'identifie se prépare à l'avance ; le jour J on
  distribue, on ne configure pas »). **Le QR n'est pas un gadget, c'est un filet** : puisqu'il n'y a
  **pas de mode kiosque** (`D-05`) et que l'onglet **sera** fermé par accident sur 30 postes × 8 h, il
  faut que « l'écran est bizarre → **tu scannes le QR de ta cible → tu es revenu** » — plutôt que
  d'appeler l'admin à l'autre bout du gymnase. **Ne porte pas** le rattachement lui-même (c'est
  E04US001) : le QR n'encode qu'une URL. Nécessite une **lib QR** → inscrire au [registre des
  dépendances](../docs/dependances.md) (ADR-0009).
- **Dépend de** : E09US001, E04US001, E10US003 · **Jalon** : J1

---

## Correspondance ancien → nouveau (maille révisée du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E09US001 | Intégrer la bibliothèque PDF | **E09US001** — CA « socle PDF » |
| E09US002 | Feuille de marque | **E09US001** — CA « feuille de marque » |
| E09US003 | Liste de placement | **E09US003** — CA « placement » |
| E09US004 | Liste club & paiement | **E09US003** — CA « club & paiement » |
| E09US005 | Classement PDF par catégorie | **E09US005** — CA « par catégorie » |
| E09US006 | Classement intégral 1→N (PDF) | **E09US005** — CA « intégral 1→N » |
| E09US007 | Déroulé horaire imprimable | **E09US007** (inchangée) |
| E09US008 | Imprimer les QR de cible et les codes scoreurs | **E09US008** (inchangée) |
