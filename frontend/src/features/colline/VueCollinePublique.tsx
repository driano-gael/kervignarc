// La vue **publique** d'une phase de colline (E05US027, ADR-0089).
//
// Un seul composant pour **deux** surfaces, comme `VueSuissePublique` : l'appli publique et l'écran
// de salle (`interactif=false`), toutes deux montées par l'aiguilleur `features/en-cours/`.
//
// **Comme le suisse, ce format réclame une navigation d'historique**, et pour la même raison : une
// colline ré-apparie à chaque manche, donc les afficher toutes donnerait une page interminable où
// la manche en cours — la seule que la salle regarde — serait noyée. D'où l'atterrissage sur la
// manche courante et des boutons pour remonter.
//
// ⚠️ **Ce que cette vue montre de plus que les autres formats : la colline elle-même.** Chez le
// suisse, le classement se calcule et n'est qu'un tableau de plus ; ici l'ordre des positions
// **est** le jeu, et c'est ce qu'un spectateur vient lire — qui a monté, qui a descendu. Le
// classement n'est donc pas relégué en bas comme un récapitulatif : c'est le sujet.

import { useState } from 'react'
import { LigneRencontre } from '../../shared/duels/LigneRencontre'
import { participants } from '../../shared/duels/rencontre'
import { decrirePlaces } from '../../shared/salle/place'
import { messageDeLecture } from '../../shared/api/etatDeLecture'
import { type ModeAffichage } from '../../shared/suivis/focus'
import type { manchePublique } from './api'
import { ClassementColline } from './ClassementColline'
import { useEtatColline } from './hooks'
import { decrireDefi, motDeLaFin, nommerAuRepos, nommerFormat } from './presentation'

export function VueCollinePublique({
  tournoiId,
  phaseId,
  interactif = true,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  phaseId: number
  /** `false` sur l'écran projeté : aucune interaction (CA E07US004), donc pas de choix de manche. */
  interactif?: boolean
  mode?: ModeAffichage
  suivis?: number[]
}) {
  const [mancheChoisie, setMancheChoisie] = useState<number | null>(null)
  const etat = useEtatColline(tournoiId, phaseId)
  const donnees = etat.data

  if (donnees === undefined) {
    return <p className="carte__etat">{messageDeLecture(etat)}</p>
  }
  if (donnees.manches.length === 0) {
    return <p className="carte__etat">La première manche n’est pas encore appariée.</p>
  }

  // La manche **qui se joue** : la première non close, sinon la dernière (à 17 h, c'est celle dont
  // on veut voir le résultat). Même règle que chez le suisse et dans `VueTableaux`.
  //
  // ⚠️ Le `?? null` n'est pas décoratif : `noUncheckedIndexedAccess` type `.at(-1)` en
  // `| undefined`, et le garde de liste vide ci-dessus ne le lui apprend pas.
  const courante = donnees.manches.find((m) => !m.close) ?? donnees.manches.at(-1) ?? null
  const manche =
    (interactif && mancheChoisie !== null
      ? donnees.manches.find((m) => m.numero === mancheChoisie)
      : undefined) ?? courante
  if (manche === null || courante === null) {
    return <p className="carte__etat">La première manche n’est pas encore appariée.</p>
  }
  const fin = motDeLaFin(donnees.manches, donnees.nb_manches)

  return (
    <div className="encours">
      <p className="encours__entete">
        Manche {manche.numero} sur {donnees.nb_manches} · {donnees.effectif} archers ·{' '}
        {nommerFormat(donnees.portee_de_defi)}
        {manche.close ? ' · close' : ''}
      </p>

      {/* Une manche qu'aucun bloc de couloirs ne porte : plan non posé, ou salle trop petite. On le
          **dit**, sinon les défis s'affichent sans cible et le spectateur croit à un oubli. C'est le
          correctif que la revue d'E05US031 a dû faire sur le suisse, repris ici d'emblée. */}
      {donnees.conflits.length > 0 && (
        <p className="carte__etat">
          {donnees.conflits.length === 1
            ? 'Un défi n’a pas encore de cibles attribuées.'
            : `${donnees.conflits.length} défis n’ont pas encore de cibles attribuées.`}
        </p>
      )}

      {/* Le choix n'apparaît que s'il y a un choix à faire : une phase à une seule manche n'a pas à
          afficher une barre d'un bouton. */}
      {interactif && donnees.manches.length > 1 && (
        <nav className="encours__rondes" aria-label="Manches jouées">
          {donnees.manches.map((m) => (
            <button
              key={m.numero}
              type="button"
              className={m.numero === manche.numero ? 'onglet onglet--actif' : 'onglet'}
              onClick={() => setMancheChoisie(m.numero)}
            >
              Manche {m.numero}
            </button>
          ))}
        </nav>
      )}

      <BlocManche manche={manche} mode={mode} suivis={suivis} />

      {/* Le mot de la fin ne vaut que pour la manche **courante** : affiché en remontant
          l'historique, il dirait « en attente de la manche 4 » sous la manche 1, ce qui est vrai
          mais incompréhensible à cet endroit. */}
      {manche.numero === courante.numero && fin !== null && (
        <p className="carte__etat">
          {fin.etat === 'fini'
            ? 'Toutes les manches sont jouées — la colline est définitive.'
            : `Manche ${fin.courante} en cours : la manche ${fin.suivante} sera appariée une fois tous ses défis validés.`}
        </p>
      )}

      <ClassementColline classement={donnees.classement} manches={donnees.manches} />
    </div>
  )
}

function BlocManche({
  manche,
  mode,
  suivis,
}: {
  manche: manchePublique
  mode: ModeAffichage
  suivis: readonly number[]
}) {
  const retenus =
    mode === 'suivis'
      ? manche.defis.filter((d) => participants(d).some((id) => suivis.includes(id)))
      : manche.defis
  const auReposSuivis = manche.au_repos.filter((qui) => suivis.includes(qui.archer_id))

  if (retenus.length === 0 && !(mode === 'suivis' && auReposSuivis.length > 0)) {
    if (mode === 'suivis') {
      // ⚠️ **Aucun de vos archers ici ≠ manche vide** (ADR-0079) : un archer suivi peut fort bien
      // tirer dans une autre phase, ou se reposer — cas traité juste au-dessus.
      return (
        <p className="carte__etat">
          Aucun des archers que vous suivez ne tire dans cette manche. Passez à « Tout le tournoi »
          pour la voir en entier.
        </p>
      )
    }
    return <p className="carte__etat">Cette manche n’a aucun défi.</p>
  }

  return (
    <>
      <ul className="encours__lignes">
        {retenus.map((d) => (
          <LigneRencontre
            key={d.numero}
            rencontre={d}
            places={d.couloirs === null ? null : decrirePlaces(d.couloirs)}
            souligne={participants(d).some((id) => suivis.includes(id))}
            prefixe={decrireDefi(d.position_haute, d.position_basse)}
          />
        ))}
      </ul>
      {/* Les archers **au repos**. ⚠️ Ce n'est pas le bye du suisse : personne ne marque et personne
          ne bouge. Le taire ferait chercher leur nom dans une liste où ils ne peuvent pas être, et
          croire à un oubli d'appariement — et ici ce n'est pas un cas limite d'effectif impair,
          c'est **les deux extrémités** une manche sur deux à portée 1.
          ⚠️ **Ils passent par le filtre comme le reste** : c'est le correctif que la revue
          d'E05US031 a dû faire sur le bye du suisse, rendu inconditionnellement alors que
          l'interrupteur d'ADR-0079 vaut « sans exception ». */}
      {(mode !== 'suivis' ? manche.au_repos : auReposSuivis).length > 0 && (
        <p className="encours__bye">
          {nommerAuRepos(mode !== 'suivis' ? manche : { ...manche, au_repos: auReposSuivis }).join(
            ' · ',
          )}{' '}
          ne tire{manche.au_repos.length > 1 ? 'nt' : ''} pas cette manche : personne ne marque et
          personne ne change de position.
        </p>
      )}
    </>
  )
}
