// Frise du cycle de vie du tournoi (E14US001) — la « où j'en suis » + les actions possibles.
//
// Remplace l'ancien `CycleDeVie` (Tournois.tsx) qui ne gérait que 3 statuts : dès qu'un tournoi
// atteignait `prêt`/`en_pause`/… il n'offrait plus aucun bouton (tournoi bloqué). Ici, la frise
// affiche les 7 statuts (ADR-0026) et **lit** les transitions offertes du serveur (une seule source
// de la topologie — la frise ne décide rien, règle 1). Les transitions qui **figent** ou sont
// terminales sont confirmées ; `terminer` réutilise le message chiffré de la complétude (E12US005).

import { useQueryClient } from '@tanstack/react-query'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { StatutTournoi, Tournoi } from '../competition/api'
import { getCompletude } from '../completude/api'
import { messageConfirmationTerminer } from '../completude/presentation'
import { useTransitionnerTournoi, useTransitions } from './hooks'

// Axe principal du cycle de vie (ADR-0026 §2). `en_pause` se rattache visuellement à `en_cours` ;
// `annulé` est un état terminal **hors axe**, rendu à part.
const AXE: { statut: StatutTournoi; libelle: string }[] = [
  { statut: 'brouillon', libelle: 'Brouillon' },
  { statut: 'pret', libelle: 'Prêt' },
  { statut: 'en_cours', libelle: 'En cours' },
  { statut: 'termine', libelle: 'Terminé' },
  { statut: 'archive', libelle: 'Archivé' },
]

// Rang du statut courant sur l'axe (en_pause ↦ rang d'en_cours ; annulé hors axe → -1).
const RANG: Record<StatutTournoi, number> = {
  brouillon: 0,
  pret: 1,
  en_cours: 2,
  en_pause: 2,
  termine: 3,
  archive: 4,
  annule: -1,
}

export function FriseCycleDeVie({ tournoi }: { tournoi: Tournoi }) {
  const transitions = useTransitions(tournoi.id)
  const transitionner = useTransitionnerTournoi(tournoi.id)
  const queryClient = useQueryClient()
  const rangCourant = RANG[tournoi.statut]

  // Confirme avant les transitions qui figent (terminer) ou sont terminales (annuler/archiver). Pour
  // `terminer`, on chiffre ce qui reste via la même logique que l'écran Complétude ; si sa lecture
  // échoue, on **laisse passer** (dégradé) — ne jamais bloquer la seule action irréversible sur un
  // hoquet réseau (`P-3`, comme l'ancien CycleDeVie).
  const declencher = async (nom: string) => {
    if (nom === 'terminer') {
      let message: string
      try {
        const completude = await queryClient.fetchQuery({
          queryKey: ['completude', tournoi.id],
          queryFn: () => getCompletude(tournoi.id),
        })
        message = messageConfirmationTerminer(completude)
      } catch {
        message =
          'Impossible de vérifier ce qui reste (complétude injoignable). Terminer quand même ?'
      }
      if (!window.confirm(message)) return
    } else if (nom === 'annuler') {
      if (!window.confirm('Annuler ce tournoi ? Il conservera sa trace (≠ suppression).')) return
    } else if (nom === 'archiver') {
      if (!window.confirm('Archiver ce tournoi ? Il passera en lecture seule définitive.')) return
    }
    transitionner.mutate(nom)
  }

  return (
    <div className="frise">
      <ol className="frise__axe">
        {AXE.map((etape, i) => {
          const classe =
            i < rangCourant
              ? 'frise__etape frise__etape--faite'
              : i === rangCourant
                ? 'frise__etape frise__etape--courant'
                : 'frise__etape'
          const enPauseIci = etape.statut === 'en_cours' && tournoi.statut === 'en_pause'
          return (
            <li
              key={etape.statut}
              className={classe}
              aria-current={i === rangCourant ? 'step' : undefined}
            >
              {etape.libelle}
              {enPauseIci && <span className="frise__note"> (en pause)</span>}
            </li>
          )
        })}
        {tournoi.statut === 'annule' && (
          <li
            className="frise__etape frise__etape--courant frise__etape--annule"
            aria-current="step"
          >
            Annulé
          </li>
        )}
      </ol>

      <div className="frise__actions">
        {transitions.isError && (
          <p className="carte__etat carte__etat--erreur" role="alert">
            Actions injoignables — {transitions.error.message}
          </p>
        )}
        {!transitions.isLoading &&
          !transitions.isError &&
          (transitions.data ?? []).length === 0 && (
            <p className="carte__etat">Aucune action disponible à ce stade.</p>
          )}
        {(transitions.data ?? []).map((t) => (
          <button
            key={t.nom}
            type="button"
            className={
              t.nom === 'annuler'
                ? 'bouton--danger'
                : t.nom === 'revenir-brouillon'
                  ? 'bouton--discret'
                  : undefined
            }
            disabled={transitionner.isPending}
            onClick={() => void declencher(t.nom)}
          >
            {t.libelle}
          </button>
        ))}
      </div>
      <MessageErreur erreur={transitionner.error} />
    </div>
  )
}
