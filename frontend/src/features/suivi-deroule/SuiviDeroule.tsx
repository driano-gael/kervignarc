// Écran « Suivi du déroulé » (E07US004) — axe **pilotage**, sur une édition en cours.
//
// La deuxième des trois surfaces du schéma à braquets. Elle montre exactement ce que l'écran de
// salle montre, mais à un poste PC : *« ce plan de suivi est aussi une destination de l'axe pilotage
// — l'organisateur le consulte à son poste sans dépendre d'un écran projeté »* (CA).
//
// Elle ne contient donc presque rien : le dessin est dans `shared/schema-braquets`, la donnée dans
// `hooks.ts`. C'est le signe que le partage a fonctionné — si cet écran avait dû réécrire du dessin,
// c'est que le composant n'aurait pas été assez paramétré.

import { useState } from 'react'

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { SchemaBraquets } from '../../shared/schema-braquets/SchemaBraquets'
import { LIBELLE_STATUT, type AvancementBloc } from '../../shared/schema-braquets/modele'
import { ChoixCreneau } from '../departs/ChoixCreneau'
import { creneauRetenu } from '../departs/libelle'
import { useDeparts } from '../departs/hooks'
import { departDeSalle } from '../salle/rotation'
import type { SuiviDeroule as SuiviDerouleData } from './api'
import { useSuiviDeroule } from './hooks'
import { PilotageCreneau } from './PilotageCreneau'

export function SuiviDeroule({ tournoiId }: { tournoiId: number }) {
  // ⚠️ **Le suivi est celui d'un créneau** (E01US025, ADR-0075) : un départ rejoue le tournoi en
  // entier, donc le dessin *et* son remplissage dépendent du créneau — l'effectif projeté n'est pas
  // le même à 100 inscrits le matin et 60 l'après-midi. Le choix est hissé ici plutôt que laissé au
  // panneau de pilotage : il commande les deux, et deux sélecteurs indépendants laisseraient lire
  // l'avancement d'un créneau sous le dessin d'un autre.
  const [choixDepart, setChoixDepart] = useState<number | null>(null)
  const departs = useDeparts(tournoiId)
  const liste = departs.data ?? []
  // Défaut : le créneau qu'on est en train de tirer (`salle/rotation.ts`, pur et testé) — le même
  // que le classement et le plan de cibles. Retomber sur `departs[0]` afficherait le suivi du
  // matin, clos depuis des heures, sans rien signaler.
  const departId = creneauRetenu(liste, choixDepart, departDeSalle)
  const suivi = useSuiviDeroule(departId)

  return (
    <>
      <section className="carte">
        <h2>Suivi du déroulé</h2>
        <p className="carte__aide">
          Le déroulé composé pour ce tournoi, rempli par la réalité : phase terminée, en cours ou à
          venir, tour en cours, et duels joués sur duels attendus. C’est le même schéma que l’écran
          de salle affiche au public.
        </p>
        <ChoixCreneau departs={liste} valeur={departId} surChangement={setChoixDepart} />
        <MessageErreur erreur={suivi.error} />
        {departs.isSuccess && liste.length === 0 ? (
          <p className="carte__etat">
            Aucun départ n’est encore défini pour ce tournoi : il n’y a rien à suivre.
          </p>
        ) : suivi.data === undefined ? (
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
      {/* La **commande**, sous la vue d'ensemble (ADR-0076). Le schéma dit où en est le tournoi ; le
          cycle de vie, lui, s'exerce dans un créneau — c'est le seul endroit où il a un
          destinataire. Le rapprochement est délibéré : on agit là où l'on vient de lire. */}
      <PilotageCreneau
        tournoiId={tournoiId}
        departId={departId}
        aucunCreneau={departs.isSuccess && liste.length === 0}
      />
    </>
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
