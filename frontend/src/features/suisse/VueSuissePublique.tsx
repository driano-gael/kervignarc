// La vue **publique** d'une phase au système suisse (E05US031, ADR-0089).
//
// Un seul composant pour **deux** surfaces, comme `VueTableaux` : l'appli publique et l'écran de
// salle (`interactif=false`). ⚠️ **« Trois » jusqu'à la revue** : la formule recopiée ajoutait
// l'écran d'organisation, qui ne monte pas cette vue — or c'est cette liste qui **justifie** «
// cette vue ne lit pas le store ». **Seul format sans arbre qui réclame une navigation
// d'historique** : un suisse ré-apparie tout le plateau à chaque ronde, d'où l'atterrissage sur la
// ronde courante.

import { useState } from 'react'
import { LigneRencontre } from '../../shared/duels/LigneRencontre'
import { participants } from '../../shared/duels/rencontre'
import { decrirePlaces } from '../../shared/salle/place'
import { messageDeLecture } from '../../shared/api/etatDeLecture'
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
    return <p className="carte__etat">{messageDeLecture(etat)}</p>
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

      {/* Une ronde qu'aucun bloc de couloirs ne porte : plan non posé, ou salle trop petite. On le
          **dit**, sinon les rencontres s'affichent sans cible et le spectateur croit à un oubli.
          ⚠️ Ajouté en revue (axe C1) : `VuePoulesPublique` le faisait déjà, sur le même champ et
          dans le même onglet, et le suisse se taisait — deux comportements pour une même
          situation, à un écran d'écart. */}
      {donnees.conflits.length > 0 && (
        <p className="carte__etat">
          {donnees.conflits.length === 1
            ? 'Une rencontre n’a pas encore de cibles attribuées.'
            : `${donnees.conflits.length} rencontres n’ont pas encore de cibles attribuées.`}
        </p>
      )}

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
          dans une liste où il ne peut pas être, et croire à un oubli d'appariement.
          ⚠️ **Mais il passe par le filtre comme le reste** (correctif de revue, axes B et C1) : il
          était rendu inconditionnellement, si bien qu'en « mes archers » le nom d'un archer non
          suivi s'affichait quand même. Le CA est explicite — l'interrupteur d'ADR-0079 vaut ici
          « sans exception » —, et la fiche de recette promet un filtrage des **lignes**. */}
      {ronde.bye !== null && (mode !== 'suivis' || byeSuivi) && (
        <p className={byeSuivi ? 'encours__bye encours__bye--suivi' : 'encours__bye'}>
          {`${ronde.bye.prenom} ${ronde.bye.nom}`.trim()} ne tire pas cette ronde (bye) et marque la
          victoire.
        </p>
      )}
    </>
  )
}
