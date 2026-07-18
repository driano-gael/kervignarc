# Fichiers d'import d'inscriptions — échantillons de format

Deux **exports réels** d'inscriptions d'archers pour le *Challenge des Champions de Kervignac*,
produits par **deux logiciels externes différents**. Ils servent de **référence de format** pour
[E02US007](../../../stories/E02-inscriptions.md) (« Importer un fichier inscript'arc »), qui était
**bloquée faute du format exact** (QT1) : ces fichiers la débloquent.

| Fichier | Logiciel source | Format |
|---|---|---|
| `Export_Ianseo_challenge-des-champions-de-kervignac.csv` | **Ianseo** | CSV **séparé par `;`**, **sans ligne d'en-tête**, encodage Latin-1 (accents `VALÉRIE`, `CÉLIA`). Colonnes observées : n° de licence, codes, sexe (`F`/`H`), nom, prénom, code club, nom du club, date de naissance (`AAAA-MM-JJ`), puis colonnes vides. |
| `Resultarc_challenge-des-champions-de-kervignac.xls` | **Résult'Arc** | Classeur Excel **binaire hérité (`.xls`, OLE2)**, code page Windows-1252 — **pas** un `.xlsx`. |

## Points de vigilance pour E02US007 (l'US qui les consommera)

- **Deux formats hétérogènes** à mapper vers le même modèle (`Archer`, `Club`, `Depart`) : le
  parsing doit être **paramétré par source**, pas câblé sur un seul.
- **`.xls` (OLE2), pas `.xlsx`** : `openpyxl` (envisagé dans les Notes d'E02US007) **ne lit que le
  `.xlsx`**. Lire ce Résult'Arc-là demande `xlrd` (ou une conversion préalable). À trancher au
  cadrage de l'US (dépendance → règle 11).
- **Données personnelles réelles** (noms, n° de licence, dates de naissance de licenciés) : ces
  échantillons sont versionnés à des fins de **référence de format** pour un outil interne mono-club.
  À ne pas rediffuser hors de ce cadre.
- **Le n° de licence est présent** dans l'export Ianseo : c'est la donnée que les Notes d'E02US007
  évoquent pour rendre le doublon *décidable* (y compris entre tournois). L'échantillon confirme sa
  disponibilité.
