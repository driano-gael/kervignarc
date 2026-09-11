// Panneau de routage (E04US018) — « où tire-t-on ensuite ? ».
//
// **Canal n°1 des quatre canaux de routage** (`D-09`) : celui qui attrape l'archer avant son
// départ. Le même panneau sert les deux surfaces de saisie — qualification (bascule aux quatre
// séries validées) et duels (bascule dès le duel tranché). `D-08` : l'affichage est **instantané**,
// rien n'est calculé là, les cibles étant attribuées aux **matchs** (E03US009). **Ce qui n'est pas
// encore connu est écrit**, jamais laissé en blanc (cadrage du 30/07/2026), et les phrases viennent
// du **serveur** : les quatre canaux doivent dire la même chose.

import { useEffect, useRef, useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useMaintenant } from '../../shared/ui/useMaintenant'
import type { RoutageArcher } from './api'
import { useDeparts } from '../departs/hooks'
import { departDeSalle } from '../salle/rotation'
import { useRoutage } from './hooks'
import { alerte, avanceeFermeture, detail, doitSeRefermer, titre } from './presentation'

// La jauge se lit à la seconde, pas plus fin : un battement plus rapide ne ferait que multiplier
// les re-rendus d'un écran de tablette posé sur une butte.
const BATTEMENT_MS = 1000

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

  // Le retour automatique (E16US018). ⚠️ **Un écriteau ne se referme pas** : « tir suspendu » ou
  // « phase non configurée » valent tant que la situation dure (une pause tient 15 à 20 minutes),
  // alors qu'une annonce de destination se lit une fois. C'est le **serveur** qui les distingue.
  // ⚠️ Le décompte part de l'ouverture, pas de l'arrivée des données : un écran resté trois
  // minutes sur « Recherche des destinations… » n'a plus rien à apprendre à personne.
  const ecriteau = routage.data?.avis_permanent === true
  // ⚠️ **L'ancre est l'instant de MONTAGE, donc tout démontage la remet à zéro.** C'est pourquoi
  // les deux appelants rendent désormais ce panneau **avant** toute sortie `isPending` / `isError` :
  // placé après, un refetch en échec le démontait puis le remontait avec trois minutes neuves, et
  // sur un wifi de salle il pouvait ne **jamais** se refermer. Ne pas déplacer cette branche.
  const [ouvertureMs] = useState(() => Date.now())
  const maintenant = useMaintenant(BATTEMENT_MS)
  const rendu = useRef(false)
  useEffect(() => {
    // ⚠️ Le garde n'est pas décoratif : `onRetour` est une lambda recréée à chaque rendu chez les
    // deux appelants, et le battement continue après l'échéance. Sans lui, la liste des matchs
    // remonterait une fois par seconde.
    if (ecriteau || rendu.current || !doitSeRefermer(ouvertureMs, maintenant)) return
    rendu.current = true
    onRetour()
  }, [ecriteau, ouvertureMs, maintenant, onRetour])
  const avancee = avanceeFermeture(ouvertureMs, maintenant)

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

      {!ecriteau && <JaugeRetour avancee={avancee} />}
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

// Le signal du retour automatique : une jauge et une mention, **jamais un chiffre**. Le compte à
// rebours en secondes est la signature de la variante C du questionnaire S06, écartée au profit de
// la variante A (ADR-0108). La mention existe parce qu'un écran qui disparaît sans prévenir se lit
// comme un plantage.
//
// ⚠️ `role="img"` et non `progressbar` — patron déjà retenu par `Supervision.tsx`. Un
// `progressbar` **publie** `aria-valuenow`, donc annonce « 45 pour cent » : le « jamais un chiffre »
// est un principe, pas une contrainte seulement visuelle.
function JaugeRetour({ avancee }: { avancee: number }) {
  return (
    <div className="routage__retour" role="img" aria-label="Retour automatique à la saisie">
      <span className="routage__retour-mention">Retour automatique</span>
      <div className="routage__retour-piste">
        <span className="routage__retour-jauge" style={{ width: `${avancee * 100}%` }} />
      </div>
    </div>
  )
}
