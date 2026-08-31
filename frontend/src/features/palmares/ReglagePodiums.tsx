// Réglage des podiums du **tournoi** (E16US014, A16) : ce que le club récompense, et sur combien
// de places.
//
// ⚠️ **Rendu par l'admin seulement**, jamais par `VuePalmares` — ce composant-là sert aussi l'appli
// publique et l'écran de salle (`interactif` ne distingue que le projeté).
//
// Aucun état local : ce qui est coché est **ce que le serveur a accepté**. Un état local recalé par
// `useEffect` afficherait un réglage non encore retenu (défaut relevé en revue d'E06US006).

import type { PorteePodium } from './api'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useReglagePodiums, useReglerPodiums } from './hooks'

const PORTEES: { valeur: PorteePodium; libelle: string; aide: string }[] = [
  {
    valeur: 'scratch',
    libelle: 'Scratch',
    aide: 'Le podium du tournoi, toutes catégories mêlées.',
  },
  { valeur: 'categorie', libelle: 'Par catégorie', aide: 'Un podium par catégorie présente.' },
  { valeur: 'club', libelle: 'Par club', aide: 'Les archers de chaque club, classés entre eux.' },
]

export function ReglagePodiums({ tournoiId }: { tournoiId: number }) {
  const reglage = useReglagePodiums(tournoiId)
  const regler = useReglerPodiums(tournoiId)
  const portees = reglage.data?.portees ?? []
  const profondeur = reglage.data?.profondeur ?? 4
  // Verrouillé tant que le serveur n'a pas répondu : sans cela, deux clics rapides enverraient le
  // second réglage calculé sur une liste que le premier a déjà changée.
  const fige = reglage.isPending || reglage.isError || regler.isPending

  const basculer = (portee: PorteePodium) => {
    const retenues = portees.includes(portee)
      ? portees.filter((p) => p !== portee)
      : [...portees, portee]
    regler.mutate({ portees: retenues, profondeur })
  }

  return (
    <section className="palmares-reglage" aria-label="Réglage des podiums">
      <h4 className="palmares-section">Ce que ce tournoi récompense</h4>
      <fieldset className="palmares-reglage__portees" disabled={fige}>
        <legend className="palmares-reglage__legende">Podiums affichés</legend>
        {PORTEES.map((portee) => (
          <label key={portee.valeur} className="palmares-reglage__portee">
            <input
              type="checkbox"
              checked={portees.includes(portee.valeur)}
              onChange={() => basculer(portee.valeur)}
            />
            <span className="palmares-reglage__portee-libelle">{portee.libelle}</span>
            <span className="palmares-reglage__portee-aide">{portee.aide}</span>
          </label>
        ))}
      </fieldset>

      <label className="palmares-reglage__profondeur" htmlFor="profondeur-podium">
        Places récompensées
      </label>
      {/* ⚠️ Champ **non contrôlé**, seule exception au principe ci-dessus, et il n'y en a pas
          d'autre : une case à cocher se valide au clic, un nombre se tape — « 12 » passe par « 1 ».
          Un `value` sans `onChange` rend le champ impossible à saisir en React ; un état local
          recalé par `useEffect` rouvrirait la divergence. Le `key` remonte le champ sur la valeur
          **du serveur** dès qu'elle change : la frappe vit dans le DOM, la vérité reste au-dessus. */}
      <input
        key={profondeur}
        id="profondeur-podium"
        className="formulaire__champ"
        type="number"
        min={1}
        defaultValue={profondeur}
        disabled={fige}
        onBlur={(e) => {
          const saisie = Number(e.target.value)
          if (Number.isInteger(saisie) && saisie >= 1 && saisie !== profondeur) {
            regler.mutate({ portees, profondeur: saisie })
            return
          }
          // Saisie vide, nulle ou inchangée : on **ramène** l'affichage au réglage retenu plutôt
          // que de laisser à l'écran un nombre que le serveur ignore.
          e.target.value = String(profondeur)
        }}
      />

      <p className="carte__etat">
        {portees.length === 0
          ? 'Aucun podium affiché — le palmarès ne montrera que le classement complet.'
          : 'Les podiums réglés ici sont ceux de l’écran, de l’affichage public et du PDF.'}{' '}
        Changer ce réglage <strong>ne modifie aucun résultat</strong> : le palmarès se recalcule à
        chaque lecture, seul ce qu’il affiche change.
      </p>
      <MessageErreur erreur={reglage.error} />
      <MessageErreur erreur={regler.error} />
    </section>
  )
}
