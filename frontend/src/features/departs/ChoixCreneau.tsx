// Le sélecteur de créneau, partagé par les surfaces qui lisent une donnée **de départ**.
//
// Depuis ADR-0075, le départ est la portée sportive : classement, tableaux et forfaits
// appartiennent à un créneau, pas au tournoi. Plusieurs écrans doivent en désigner un, et **de la
// même façon** — sinon l'organisateur ne sait plus s'il regarde le même. Hissé ici à la **3ᵉ
// occurrence réelle** (`Placement.tsx` portait déjà le même sélecteur depuis E03US004), seuil que
// le projet se fixe. `Placement` n'est pas migré : son sélecteur porte un état « aucun départ
// choisi » que les deux autres n'ont pas.

import { libelleCreneau, type CreneauChoisissable } from './libelle'

export function ChoixCreneau({
  departs,
  valeur,
  surChangement,
  etiquette = 'Départ',
}: {
  departs: readonly CreneauChoisissable[]
  valeur: number | null
  surChangement: (departId: number) => void
  /** Le mot devant le `<select>`. Par défaut « Départ ». */
  etiquette?: string
}) {
  // Aucun créneau : pas de `<select>` vide. L'appelant dit lui-même ce qu'il faut faire (créer un
  // départ) — c'est son écran qui a le contexte, pas ce composant.
  if (departs.length === 0) return null
  return (
    <label className="classement-filtre">
      {etiquette}{' '}
      <select value={valeur ?? ''} onChange={(e) => surChangement(Number(e.target.value))}>
        {departs.map((depart) => (
          <option key={depart.id} value={depart.id}>
            {libelleCreneau(depart)}
          </option>
        ))}
      </select>
    </label>
  )
}
