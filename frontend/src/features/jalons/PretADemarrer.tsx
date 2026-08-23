// Écran « **Prêt à démarrer ?** » (E16US012) — le premier membre neuf de la famille.
//
// **Ce qu'il apporte.** Les deux gardes du feu vert existaient déjà, mais n'étaient lisibles
// **qu'en échouant** : `vers_pret` lève `TournoiSansDepart`, `demarrer` lève
// `EffectifInsuffisantPourDemarrer`. Une exception ne rend que le **premier** manquement — on
// ajoute un créneau, on reclique, et on découvre alors l'effectif. Cet écran les **énumère** avant
// le clic, toutes ensemble (ADR-0096).
//
// **L'action se lit du serveur, elle ne se déduit pas du statut.** `useTransitions` est la source
// unique de la topologie du cycle de vie (ADR-0026 §2), déjà consommée par `FriseCycleDeVie` — le
// CA « sans doublonner ce qui existe » interdisait d'en tenir une seconde table ici. Deux
// transitions mènent au départ (`vers-pret` depuis *brouillon*, `demarrer` depuis *prêt*) : on
// propose celle que le serveur offre, quelle qu'elle soit.
//
// ⚠️ **Le bouton n'est jamais grisé**, même quand `pret` est faux : le refus remonte du serveur
// (`D-15`, et l'arbitrage d'E05US021). C'est aussi ce qui évite la seconde source — le front ne
// décide d'aucune garde, il annonce seulement ce qui va se passer.

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { texteErreur } from '../../shared/ui/texteErreur'
import { useTransitionnerTournoi, useTransitions } from '../accueil/hooks'
import type { StatutTournoi } from '../competition/api'
import { usePreparationJalon } from './hooks'
import { PretA } from './PretA'

// Les transitions qui mènent au départ, dans l'ordre où on les rencontre. Une **liste** et non un
// `switch` sur le statut : c'est le serveur qui dit laquelle est offerte, on ne fait que retenir
// celles qui concernent cet écran.
const VERS_LE_DEPART = ['vers-pret', 'demarrer']

const INTRO =
  'Ce qui doit être en place avant de lancer le tournoi. Les manques marqués « en attente » ou ' +
  '« à finir » seront refusés au démarrage — sauf le déroulé, qui n’est qu’un conseil.'

export function PretADemarrer({ tournoiId, statut }: { tournoiId: number; statut: StatutTournoi }) {
  const preparation = usePreparationJalon(tournoiId, 'demarrer')
  const transitions = useTransitions(tournoiId)
  const transitionner = useTransitionnerTournoi(tournoiId)

  const offerte = (transitions.data ?? []).find((t) => VERS_LE_DEPART.includes(t.nom))
  const dejaLance = statut !== 'brouillon' && statut !== 'pret'

  return (
    <PretA
      question="Prêt à démarrer ?"
      intro={INTRO}
      titreSection="Avant de démarrer"
      lignes={preparation.data?.lignes ?? null}
      pret={preparation.data?.pret ?? false}
      bloquant={preparation.data?.bloquant ?? true}
      chargement={preparation.isPending}
      erreur={
        preparation.isError && (
          <p className="carte__etat carte__etat--erreur" role="alert">
            Préparation injoignable — {texteErreur(preparation.error)}
          </p>
        )
      }
    >
      {/* Hors de la garde sur les données : si la lecture échoue (LAN coupé à l'ouverture de
          l'écran), l'action doit rester accessible. C'est le correctif de revue d'E16US003 sur
          l'écran jumeau — le manque d'information ne verrouille jamais l'action. */}
      {dejaLance ? (
        <p className="completude__implication">
          Ce tournoi est déjà lancé : il n’y a plus rien à préparer ici.
        </p>
      ) : (
        offerte && (
          <div className="completude__actions">
            {/* Sans classe de ton, comme les transitions de la frise : c'est l'action nominale
                de l'écran, pas une action destructrice. */}
            <button
              type="button"
              disabled={transitionner.isPending}
              onClick={() => transitionner.mutate(offerte.nom)}
            >
              {transitionner.isPending ? 'En cours…' : offerte.libelle}
            </button>
            <MessageErreur erreur={transitionner.error} />
          </div>
        )
      )}
    </PretA>
  )
}
