// Bandeau de contexte de l'administration — retour maquettes du 04/08/2026 (A02).
//
// *« Un bandeau en haut doit permettre de savoir sur quel tournoi on est et quel départ, et suit
// tout le cycle de cette section. »*
//
// **Ce qui manquait.** Le tournoi courant n'était visible que dans le sélecteur de la sidebar — un
// `<select>`, donc un *contrôle*, que l'œil lit comme « ce que je peux changer » et non comme « où je
// suis ». Passée la première seconde, l'organisateur travaillait sans repère : rien, dans la zone
// principale, ne disait sur quelle édition il agissait. Sur une machine où deux tournois peuvent être
// `en_cours` en même temps (capacité voulue, intérieur + extérieur), c'est une **erreur de saisie qui
// attend** — pas une gêne esthétique.
//
// **Ce que le bandeau dit, et pas plus.** Le sujet (tournoi, statut, date), le moment (départ
// courant, en pilotage seulement) et la position (axe › écran). Il n'offre **aucune action** : le
// sélecteur reste dans la sidebar. Un bandeau qui agit redevient un contrôle, et l'on perd
// exactement ce qu'on venait chercher — un repère stable qui ne bouge pas quand on travaille.

import type { Tournoi } from '../competition/api'
import { BadgeStatut } from '../competition/BadgeStatut'
import { useDeparts } from '../departs/hooks'
import { departCourant, libelleEtatDepart } from '../departs/courant'

export function BandeauContexte({
  tournoi,
  axeLibelle,
  ecranLibelle,
  avecDepart,
}: {
  tournoi: Tournoi
  axeLibelle: string
  ecranLibelle: string
  // Le départ n'est demandé qu'en **pilotage** : c'est là qu'on « suit le cycle de cette section ».
  // En gestion, une inscription ou un paiement ne se rattachent pas au créneau qui se tire à
  // l'instant — l'afficher y serait un repère faux, ce qui est pire qu'un repère absent.
  avecDepart: boolean
}) {
  const departs = useDeparts(tournoi.id, avecDepart)
  const depart = departCourant(departs.data ?? [])

  return (
    <header className="bandeau-contexte">
      <span className="bandeau-contexte__tournoi">{tournoi.nom}</span>
      <BadgeStatut statut={tournoi.statut} />
      <span className="bandeau-contexte__date">
        {tournoi.date}
        {tournoi.lieu === null ? '' : ` · ${tournoi.lieu}`}
      </span>

      {avecDepart && (
        <span className="bandeau-contexte__depart">
          {depart === null
            ? // Ni « départ 0 » ni case vide : les deux se lisent comme une panne. On dit l'état.
              (departs.data ?? []).length === 0
              ? 'Aucun départ configuré'
              : 'Tous les départs sont clos'
            : `Départ ${depart.numero} · ${depart.horaire} — ${libelleEtatDepart(depart)}`}
        </span>
      )}

      {/* Le fil : où l'on est dans l'axe. Il double la sidebar **volontairement** — la sidebar est à
          gauche, le regard travaille au centre, et le titre de l'écran n'y est jamais répété. */}
      <span className="bandeau-contexte__fil">
        {axeLibelle} <span aria-hidden="true">›</span> {ecranLibelle}
      </span>
    </header>
  )
}
