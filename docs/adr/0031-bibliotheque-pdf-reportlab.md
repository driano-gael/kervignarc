# ADR-0031 — Bibliothèque PDF : ReportLab (QT3)

- **Statut** : Accepté
- **Date** : 2026-07-18
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`cahier-des-charges-technique.md`](../../cahier-des-charges-technique.md) (QT3 tranchée,
  risque R4 réévalué) ; [`docs/dependances.md`](../dependances.md) (ajout de `reportlab`) ;
  [`stories/E09-exports.md`](../../stories/E09-exports.md) (E09US001 — CA « socle PDF »).
- **Introduit par** : E09US001 (socle PDF & feuille de marque).
- **Réfs** : [ADR-0002](0002-stack-et-topologie.md) (packaging PyInstaller, risque R4),
  [ADR-0009](0009-gouvernance-dependances.md) (gouvernance des dépendances).

## Contexte et problème

Le CDC technique laisse **QT3** ouverte : quelle bibliothèque pour générer les documents PDF
(feuilles de marque, classements, déroulé, QR) — **WeasyPrint** ou **ReportLab** ? E09US001, premier
document imprimable, doit trancher.

La contrainte dominante n'est pas la qualité de rendu mais le **packaging**. Le déploiement cible est
un **binaire unique PyInstaller**, **hors ligne**, sur des postes **Windows** (cf.
[ADR-0002](0002-stack-et-topologie.md)). Le risque **R4** du CDC technique nomme explicitement le
danger : *« valider WeasyPrint / dépendances **natives** dans le binaire »*.

- **WeasyPrint** rend du HTML/CSS — mise en page riche et agréable (templates Jinja2, CSS
  réutilisable). Mais il s'appuie sur des bibliothèques **natives** (Pango, cairo, GDK-PixBuf,
  fontconfig via GObject). Sous Windows, elles exigent le **runtime GTK+ installé au niveau système** —
  précisément ce que PyInstaller embarque mal. C'est le cœur du risque R4.
- **ReportLab** compose le PDF par une API Python (Platypus : *flowables*, tables). Ses roues (wheels)
  sont **autoportantes** : aucune bibliothèque système à installer. Il s'embarque proprement dans
  PyInstaller et est éprouvé dans ce contexte. Contrepartie : la mise en page est **impérative**
  (plus verbeuse que du HTML/CSS), et le rendu libre y est plus coûteux.

## Décision

**1. La bibliothèque PDF du projet est `reportlab`.** QT3 est tranchée en sa faveur sur le seul
critère qui domine ici : l'**embarquabilité dans le binaire PyInstaller hors ligne sous Windows**
(règle 12 — la rigueur va au moteur métier, l'infra reste **simple** ; règle 11 — parcimonie). Les
documents du projet (feuille de marque, classements, déroulé, papiers QR) sont **tabulaires et
structurés**, pas des maquettes libres : le point faible de ReportLab (mise en page riche) ne mord
quasiment pas, et son point fort (tables, grilles) sert directement.

**2. La validation « fonctionne dans l'exécutable packagé » (CA socle) est déférée à EPIC-11.**
Aucun build PyInstaller n'existe encore (E00US012 ne produit qu'un exécutable de **dev** qui sert le
front statique ; le packaging complet est EPIC-11). E09US001 **choisit la lib et génère le PDF dans
l'application qui tourne** ; la preuve dans le binaire est un jalon d'EPIC-11. Ce choix de ReportLab
**rend cette validation quasi acquise** (aucune bibliothèque native **de niveau système** à installer
à part — `pillow` et `reportlab` embarquent bien du code compilé, mais dans leurs *wheels*, ce que
PyInstaller sait reprendre, au contraire du runtime GTK de WeasyPrint) — le report est donc à
**faible risque résiduel**. Ce n'est pas une **dette** (aucun raccourci dans le code d'aujourd'hui,
qui fonctionne) mais un **volet du risque R4** suivi contre EPIC-11 ; l'arbitrage de périmètre est
reversé dans `stories/E09-exports.md` (E09US001).

## Conséquences

- **+** R4 est largement **désamorcé** : plus de bibliothèque native **de niveau système** à installer
  hors du binaire.
  Le report de la validation PyInstaller à EPIC-11 devient un contrôle de confirmation, pas un pari.
- **+** Une seule dépendance runtime ajoutée (`reportlab`), licence permissive (BSD), sans runtime
  système à installer à part — cohérent avec la sobriété du socle (règle 11,
  [ADR-0009](0009-gouvernance-dependances.md)).
- **−** La mise en page est du **code Python impératif** : chaque document se construit à la main
  (positions, tables, styles). Acceptable pour des documents tabulaires ; à surveiller si un futur
  document réclame une maquette vraiment libre (on ne reviendra pas sur QT3 pour autant sans preuve).
- **−** Le rendu des **QR** (E09US008) exigera une **lib QR** distincte (`reportlab` ne les dessine
  pas nativement) — arbitrage de dépendance à part entière, à trancher dans cette US-là.
- **Risque résiduel (R4, non-dette)** : « fonctionne packagé » n'est **pas** prouvé tant qu'EPIC-11
  n'a pas monté le build PyInstaller. Suivi dans la table des risques (R4), à confirmer au premier
  build d'EPIC-11 — pas au registre de dette (le code d'aujourd'hui n'a pas de raccourci ; c'est une
  étape de séquence, or « le registre n'est pas une liste de tâches »).
