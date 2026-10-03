// Le champ de **durée prévue** d'une étape (E03US010) — partagé, comme `ChampTitre`, par l'écran
// du tournoi et l'atelier de formats. Aucun état interne, même convention que ses voisins.

import { decrireDuree, DUREE_PREVUE_MAX, dureeSaisieValide, versDureePrevue } from './horaires'

export function ChampDureePrevue({
  valeur,
  surChangement,
}: {
  valeur: string
  surChangement: (valeur: string) => void
}) {
  const duree = versDureePrevue(valeur)
  return (
    <label className="formulaire__libelle">
      Durée prévue, en minutes (facultatif)
      <input
        className="formulaire__champ"
        type="number"
        inputMode="numeric"
        min={1}
        max={DUREE_PREVUE_MAX}
        step={1}
        value={valeur}
        onChange={(e) => surChangement(e.target.value)}
      />
      <span className="carte__aide">
        {!dureeSaisieValide(valeur)
          ? `Un nombre entier de minutes, de 1 à ${DUREE_PREVUE_MAX}.`
          : duree !== null
            ? `Soit ${decrireDuree(duree)}, pauses comprises.`
            : 'Pauses comprises. Vide = horaire inconnu pour cette phase et celles qui en dépendent.'}
      </span>
    </label>
  )
}
