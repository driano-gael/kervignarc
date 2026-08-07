// Panneau de routage (E04US018) — « où tire-t-on ensuite ? ».
//
// **Canal n°1 des quatre canaux de routage** (`D-09`) : celui qui attrape l'archer avant qu'il ne
// parte. Il valide, range ses flèches et s'en va — l'information doit le suivre. Le même panneau
// sert les deux surfaces de saisie, parce que c'est la même question :
//
// - **qualification** (E04US002) : la tablette bascule quand les quatre séries de la cible sont
//   validées, et envoie chacun vers son duel de 1ᵉʳ tour ;
// - **duels** (E04US013) : elle bascule dès le duel tranché, et route vainqueur et battu.
//
// `D-08` — l'affichage est **instantané** : rien n'est calculé à cet instant. Les cibles sont
// attribuées aux **matchs** (E03US009), donc la destination existe avant même le duel.
//
// **Ce qui n'est pas encore connu est écrit**, jamais laissé en blanc (arbitrage de cadrage du
// 30/07/2026) : « cible attribuée au lancement du tour », « en attente du duel n°2 », « rang publié
// en fin de phase ». Les phrases viennent du **serveur** — les quatre canaux doivent dire la même
// chose, et c'est lui qui sait pourquoi la donnée manque.

import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { RoutageArcher } from './api'
import { useDeparts } from '../departs/hooks'
import { departDeSalle } from '../salle/rotation'
import { useRoutage } from './hooks'
import { alerte, detail, titre } from './presentation'

export function PanneauRoutage({
  tournoiId,
  archerIds,
  phaseId = null,
  titrePanneau,
  onRetour,
  libelleRetour = 'Retour à la grille',
}: {
  tournoiId: number
  archerIds: number[]
  phaseId?: number | null
  titrePanneau: string
  onRetour: () => void
  libelleRetour?: string
}) {
  // ⚠️ **Le routage entre par le créneau** (E01US025, ADR-0075) : « le tableau qui vient » n'a de
  // sens que dans une séquence, et un tournoi en compte autant qu'il a de départs. La tablette
  // connaît déjà « sa cible et son départ » — mais elle ne le passe pas encore explicitement, faute
  // de le porter dans son état de poste. On résout donc le **créneau qu'on est en train de tirer**,
  // par le même helper pur que le classement, le plan de cibles et l'écran de salle. C'est la
  // même hypothèse qu'eux, tenue au même endroit ; un poste qui saisirait pour un créneau clos
  // recevrait un 404 plutôt qu'un routage d'un autre départ, ce qui est le bon échec.
  const departs = useDeparts(tournoiId)
  const departId = departDeSalle(departs.data ?? [])?.id ?? null
  const routage = useRoutage(departId, archerIds, phaseId)
  const lignes = routage.data?.archers ?? []

  return (
    <section className="routage" aria-label={titrePanneau}>
      <div className="routage__entete">
        <strong>{titrePanneau}</strong>
        <button type="button" className="bouton--discret" onClick={onRetour}>
          {libelleRetour}
        </button>
      </div>

      {routage.isError && <MessageErreur erreur={routage.error} />}

      {/* Un blanc se lit comme une panne — c'est la règle que tout cet écran applique, elle vaut
          aussi pour la seconde qui suit la bascule, avant l'arrivée des données. */}
      {routage.isLoading && (
        <p className="routage__vide" role="status">
          Recherche des destinations…
        </p>
      )}

      {!routage.isLoading && !routage.isError && lignes.length === 0 && (
        <p className="routage__vide" role="status">
          Aucun archer à router.
        </p>
      )}

      <ul className="routage__liste">
        {lignes.map((ligne) => (
          <LigneRoutage key={ligne.archer_id} ligne={ligne} />
        ))}
      </ul>
    </section>
  )
}

// Une ligne : le nom, la **destination en grand** (ce qu'on vient chercher), le contexte en dessous.
// Un archer qui n'a plus de duel, ou qu'on ne sait pas router, est visuellement distinct — mais
// jamais traité comme une erreur : c'est une information, pas un incident (`P-3`).
function LigneRoutage({ ligne }: { ligne: RoutageArcher }) {
  const secondaire = detail(ligne)
  const avertissement = alerte(ligne)
  const modificateur = ligne.issue === 'prochain_duel' ? '' : ` routage__ligne--${ligne.issue}`

  return (
    <li className={`routage__ligne${modificateur}`}>
      <span className="routage__archer">
        {ligne.nom} <span className="routage__prenom">{ligne.prenom}</span>
      </span>
      <span className="routage__destination">{titre(ligne)}</span>
      {secondaire !== null && <span className="routage__detail">{secondaire}</span>}
      {/* Ambre, jamais rouge (DV-03) : la cible reste bonne, c'est le voisinage qui cloche. */}
      {avertissement !== null && (
        <span className="routage__alerte" role="status">
          {avertissement}
        </span>
      )}
    </li>
  )
}
