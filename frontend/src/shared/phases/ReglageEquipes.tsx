// Le réglage « qui s'oppose » d'une élimination directe (E13US004, ADR-0120) — partagé par l'écran
// du tournoi et l'atelier de formats. Aucun état interne, même convention que ses voisins.

export type TypeEquipe = 'standard' | 'mixte'

const VALEUR_INDIVIDUELLE = 'individuel'

export function ReglageEquipes({
  valeur,
  surChangement,
}: {
  valeur: TypeEquipe | null
  surChangement: (valeur: TypeEquipe | null) => void
}) {
  return (
    <label className="formulaire__libelle">
      Participants
      <select
        className="formulaire__champ"
        value={valeur ?? VALEUR_INDIVIDUELLE}
        onChange={(e) =>
          surChangement(
            e.target.value === VALEUR_INDIVIDUELLE ? null : (e.target.value as TypeEquipe),
          )
        }
      >
        <option value={VALEUR_INDIVIDUELLE}>Archers (individuel)</option>
        <option value="standard">Équipes de trois</option>
        <option value="mixte">Équipes mixtes</option>
      </select>
      <span className="carte__aide">
        {valeur === null
          ? 'Chaque duel oppose deux archers.'
          : 'Chaque duel oppose deux équipes, rangées par la somme des qualifications de leurs membres. Une équipe incomplète ou non conforme n’entre pas, et l’écran des duels dit pourquoi.'}
      </span>
    </label>
  )
}
