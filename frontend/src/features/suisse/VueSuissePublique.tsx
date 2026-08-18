// La vue **publique** d'une phase au système suisse (E05US031, ADR-0089).
//
// Un seul composant pour trois surfaces, comme `VueTableaux` : l'appli publique, l'écran de salle
// (`interactif=false`) et l'écran d'organisation.
//
// **C'est le seul des trois formats sans arbre qui réclame une navigation d'historique.** Une poule
// tient tous ses tours à l'écran (round-robin sur un plateau), un Big Shoot Off met ses manches en
// colonnes ; un suisse, lui, ré-apparie **tout le plateau** à chaque ronde, donc les afficher toutes
// donnerait une page interminable où la ronde en cours — la seule que la salle regarde — serait
// noyée. D'où l'atterrissage sur la ronde courante et des boutons pour remonter.

import { useState } from 'react'
import { LigneRencontre } from '../../shared/duels/LigneRencontre'
import { participants } from '../../shared/duels/rencontre'
import { decrirePlaces } from '../../shared/salle/place'
import { type ModeAffichage } from '../../shared/suivis/focus'
import type { RondePublique } from './api'
import { ClassementSuisse } from './ClassementSuisse'
import { useEtatSuisse } from './hooks'
import { motDeLaFin } from './presentation'

export function VueSuissePublique({
  tournoiId,
  phaseId,
  interactif = true,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  phaseId: number
  /** `false` sur l'écran projeté : aucune interaction (CA E07US004), donc pas de choix de ronde. */
  interactif?: boolean
  mode?: ModeAffichage
  suivis?: number[]
}) {
  const [rondeChoisie, setRondeChoisie] = useState<number | null>(null)
  const etat = useEtatSuisse(tournoiId, phaseId)
  const donnees = etat.data

  if (donnees === undefined) {
    return (
      <p className="carte__etat">
        {etat.isError ? 'Connexion momentanément perdue — mise à jour au retour.' : 'Chargement…'}
      </p>
    )
  }
  if (donnees.rondes.length === 0) {
    return <p className="carte__etat">La première ronde n’est pas encore appariée.</p>
  }

  // La ronde **qui se joue** : la première non close, sinon la dernière (à 17 h, c'est celle dont
  // on veut voir le résultat). Même règle que le tableau qui se joue dans `VueTableaux`.
  //
  // ⚠️ Le `?? null` n'est pas décoratif : `noUncheckedIndexedAccess` type `.at(-1)` en
  // `| undefined`, et le garde de liste vide ci-dessus ne le lui apprend pas. Écrire un `!` ici
  // affirmerait au compilateur quelque chose qu'il ne peut pas vérifier, pour une liste qui vient
  // du réseau.
  const courante = donnees.rondes.find((r) => !r.close) ?? donnees.rondes.at(-1) ?? null
  const ronde =
    (interactif && rondeChoisie !== null
      ? donnees.rondes.find((r) => r.numero === rondeChoisie)
      : undefined) ?? courante
  if (ronde === null || courante === null) {
    return <p className="carte__etat">La première ronde n’est pas encore appariée.</p>
  }
  const fin = motDeLaFin(donnees.rondes, donnees.nb_rondes)

  return (
    <div className="encours">
      <p className="encours__entete">
        Ronde {ronde.numero} sur {donnees.nb_rondes} · {donnees.effectif} archers
        {ronde.close ? ' · close' : ''}
      </p>

      {/* Le choix n'apparaît que s'il y a un choix à faire : une phase à une seule ronde n'a pas à
          afficher une barre d'un bouton. */}
      {interactif && donnees.rondes.length > 1 && (
        <nav className="encours__rondes" aria-label="Rondes jouées">
          {donnees.rondes.map((r) => (
            <button
              key={r.numero}
              type="button"
              className={r.numero === ronde.numero ? 'onglet onglet--actif' : 'onglet'}
              onClick={() => setRondeChoisie(r.numero)}
            >
              Ronde {r.numero}
            </button>
          ))}
        </nav>
      )}

      <BlocRonde ronde={ronde} mode={mode} suivis={suivis} />

      {/* Le mot de la fin ne vaut que pour la ronde **courante** : affiché en remontant
          l'historique, il dirait « en attente de la ronde 4 » sous la ronde 1, ce qui est vrai mais
          incompréhensible à cet endroit. */}
      {ronde.numero === courante.numero && fin !== null && (
        <p className="carte__etat">
          {fin.etat === 'fini'
            ? 'Toutes les rondes sont jouées — le classement est définitif.'
            : `Ronde ${fin.courante} en cours : la ronde ${fin.suivante} sera appariée une fois toutes ses rencontres validées.`}
        </p>
      )}

      <ClassementSuisse classement={donnees.classement} rondes={donnees.rondes} />
    </div>
  )
}

function BlocRonde({
  ronde,
  mode,
  suivis,
}: {
  ronde: RondePublique
  mode: ModeAffichage
  suivis: readonly number[]
}) {
  const retenues =
    mode === 'suivis'
      ? ronde.rencontres.filter((r) => participants(r).some((id) => suivis.includes(id)))
      : ronde.rencontres
  const byeSuivi = ronde.bye !== null && suivis.includes(ronde.bye.archer_id)

  if (retenues.length === 0 && !(mode === 'suivis' && byeSuivi)) {
    if (mode === 'suivis') {
      // ⚠️ **Aucun de vos archers ici ≠ ronde vide** (ADR-0079) : un archer suivi peut fort bien
      // tirer dans une autre phase, ou porter le bye — cas traité juste au-dessus.
      return (
        <p className="carte__etat">
          Aucun des archers que vous suivez ne tire dans cette ronde. Passez à « Tout le tournoi »
          pour la voir en entier.
        </p>
      )
    }
    return <p className="carte__etat">Cette ronde n’a aucune rencontre.</p>
  }

  return (
    <>
      <ul className="encours__lignes">
        {retenues.map((r) => (
          <LigneRencontre
            key={r.numero}
            rencontre={r}
            places={r.couloirs === null ? null : decrirePlaces(r.couloirs)}
            souligne={participants(r).some((id) => suivis.includes(id))}
          />
        ))}
      </ul>
      {/* Le porteur du bye ne tire pas et **marque quand même** : le taire ferait chercher son nom
          dans une liste où il ne peut pas être, et croire à un oubli d'appariement. */}
      {ronde.bye !== null && (
        <p className={byeSuivi ? 'encours__bye encours__bye--suivi' : 'encours__bye'}>
          {`${ronde.bye.prenom} ${ronde.bye.nom}`.trim()} ne tire pas cette ronde (bye) et marque la
          victoire.
        </p>
      )}
    </>
  )
}
