// Le champ de **titre** d'une étape de déroulé (E16US002).
//
// Partagé par les **deux** écrans qui composent des phases, plus la fiche de la qualification. ⚠️
// **Extrait en revue, sur constat et non sur pronostic** : la première livraison écrivait ce
// contrôle **trois fois**, et les trois copies **divergeaient déjà** dans le commit qui les créait
// — libellé, `className`, `placeholder`, et surtout `maxLength={80}`, miroir manuel du serveur
// recopié trois fois. Ce n'est **pas** un remède structurel : c'est le 8ᵉ exemplaire d'un pattern
// établi. ⚠️ **Aucun état interne**, même convention que ses voisins.

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
