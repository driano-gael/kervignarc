// Écran « Suivi du déroulé » (E07US004) — axe **pilotage**, sur une édition en cours.
//
// La deuxième des trois surfaces du schéma à braquets. Elle montre exactement ce que l'écran de
// salle montre, mais à un poste PC : *« ce plan de suivi est aussi une destination de l'axe pilotage
// — l'organisateur le consulte à son poste sans dépendre d'un écran projeté »* (CA).
//
// Elle ne contient donc presque rien : le dessin est dans `shared/schema-braquets`, la donnée dans
// `hooks.ts`. C'est le signe que le partage a fonctionné — si cet écran avait dû réécrire du dessin,
// c'est que le composant n'aurait pas été assez paramétré.

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { SchemaBraquets } from '../../shared/schema-braquets/SchemaBraquets'
import { LIBELLE_STATUT, type AvancementBloc } from '../../shared/schema-braquets/modele'
import type { SuiviDeroule as SuiviDerouleData } from './api'
import { useSuiviDeroule } from './hooks'

export function SuiviDeroule({ tournoiId }: { tournoiId: number }) {
  const suivi = useSuiviDeroule(tournoiId)

  return (
    <section className="carte">
      <h2>Suivi du déroulé</h2>
      <p className="carte__aide">
        Le déroulé composé pour ce tournoi, rempli par la réalité : phase terminée, en cours ou à
        venir, tour en cours, et duels joués sur duels attendus. C’est le même schéma que l’écran de
        salle affiche au public.
      </p>
      <MessageErreur erreur={suivi.error} />
      {suivi.data === undefined ? (
        <p className="carte__etat">Chargement du déroulé…</p>
      ) : (
        <>
          <EnTeteSuivi suivi={suivi.data} />
          {/* Surface **pilotage** : taille fixe (on lit les chiffres, on fait défiler), habillage
              outil (`D-27`), et le calque d'avancement superposé. */}
          <SchemaBraquets
            blocs={suivi.data.blocs}
            avancement={suivi.data.avancement}
            messageVide="Aucune phase n’est encore appliquée à ce tournoi : appliquez un format depuis « Assemblage » pour voir le déroulé se dessiner."
          />
        </>
      )}
    </section>
  )
}

/** La phrase d'en-tête : ce qu'un organisateur veut lire **sans regarder le schéma**.
 *
 * Elle double volontairement l'information du dessin : de loin, ou en diagonale entre deux tâches,
 * une ligne de texte se lit plus vite qu'un graphe. Le schéma sert à comprendre la structure, cette
 * phrase à savoir où on en est. */
function EnTeteSuivi({ suivi }: { suivi: SuiviDerouleData }) {
  const courant = suivi.avancement.find((bloc) => bloc.ordre === suivi.ordre_courant)
  return (
    <p className="carte__resume" role="status">
      {suivi.effectif} archer(s) engagé(s) ·{' '}
      {courant === undefined ? 'aucune phase en cours' : phraseDePhase(courant)}
    </p>
  )
}

function phraseDePhase(bloc: AvancementBloc): string {
  const tour = bloc.tour_courant === null ? '' : ` · tour ${bloc.tour_courant}`
  const duels =
    bloc.duels_attendus === 0 ? '' : ` · ${bloc.duels_joues}/${bloc.duels_attendus} duels joués`
  return `phase ${bloc.ordre} ${LIBELLE_STATUT[bloc.statut]}${tour}${duels}`
}
