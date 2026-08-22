// Le champ de **titre** d'une étape de déroulé (E16US002).
//
// Partagé par les **deux** écrans qui composent des phases — « Composer un format » (un modèle
// d'étape de bibliothèque) et « Phases du tournoi » (une étape du déroulé d'un tournoi) — plus la
// fiche de la qualification, qui n'ouvre aucun formulaire et règle ses champs un par un.
//
// ⚠️ **Extrait en revue, sur constat et non sur pronostic.** La première livraison écrivait ce
// contrôle **trois fois**, et les trois copies **divergeaient déjà** dans le commit qui les créait :
// libellé (« phase » / « étape »), `className` (présente deux fois sur trois), `placeholder`
// (absent à l'atelier). Surtout, `maxLength={80}` — miroir manuel du `Field(max_length=80)` des deux
// DTO — était recopié trois fois : desserrer la borne serveur demandait trois éditions front, et
// rien n'aurait rougi si l'on n'en faisait que deux.
//
// Ce n'est **pas** un remède structurel au sens de la règle 16 : `shared/phases/` porte déjà **sept**
// contrôles partagés (six `Reglage*` plus `ChoixProfondeur`) dont les en-têtes disent tous « partagée par les deux écrans qui composent des
// phases ». C'est le 8ᵉ exemplaire d'un pattern établi, donc de la conformité à une convention —
// pas l'introduction d'un pattern, qui demanderait un ADR et une US dédiée.
//
// ⚠️ **Ce composant ne détient AUCUN état** — même convention que `ReglageDecoupage` et ses
// voisins : les deux formulaires le montent sous condition, une copie interne divergerait de la
// leur au premier aller-retour de type.

/** La borne de saisie, **miroir unique** du `max_length=80` des deux DTO serveur.
 *
 * Exportée pour qu'un test puisse la confronter au serveur plutôt que de la recopier une 4ᵉ fois.
 * Le domaine, lui, n'a aucune règle de longueur : inventer un maximum sportif serait faux — c'est
 * l'**entrée** qu'on borne, parce qu'une chaîne non bornée gonfle le `config` JSON (règle 6). */
export const LONGUEUR_MAX_TITRE = 80

export function ChampTitre({
  valeur,
  surChangement,
  /** « phase » côté tournoi, « étape » côté atelier : chaque écran garde le mot qu'il emploie déjà
   * partout (règle 3 — la pluralité est légitime **à l'écran**, cf. ADR-0090). Le glossaire tranche
   * pour « étape » côté modèle, ce que les deux écrans respectent dans leur propre registre. */
  libelle,
  /** Le libellé du type, montré en filigrane : il dit ce que devient la ligne si l'on n'écrit rien. */
  placeholder,
}: {
  valeur: string
  surChangement: (valeur: string) => void
  libelle: string
  placeholder?: string
}) {
  return (
    <label className="formulaire__libelle">
      {libelle}
      <input
        className="formulaire__champ"
        value={valeur}
        maxLength={LONGUEUR_MAX_TITRE}
        placeholder={placeholder}
        onChange={(e) => surChangement(e.target.value)}
      />
    </label>
  )
}
