// Frise du cycle de vie du tournoi (E14US001) — la « où j'en suis » + les actions possibles.
//
// Remplace l'ancien `CycleDeVie` (Tournois.tsx) qui ne gérait que 3 statuts : dès qu'un tournoi
// atteignait `prêt`/`en_pause`/… il n'offrait plus aucun bouton (tournoi bloqué). Ici, la frise
// affiche les 7 statuts (ADR-0026) et **lit** les transitions offertes du serveur (une seule source
// de la topologie — la frise ne décide rien, règle 1). Les transitions qui **figent** ou sont
// terminales sont confirmées ; `terminer` réutilise le message chiffré de la complétude (E12US005).

import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { DialogueConfirmation } from '../../shared/ui/DialogueConfirmation'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { StatutTournoi, Tournoi } from '../competition/api'
import { getCompletude } from '../completude/api'
import { messageConfirmationTerminer } from '../completude/presentation'
import type { ExigenceEffectif } from './api'
import { useExigenceEffectif, useTransitionnerTournoi, useTransitions } from './hooks'

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

// E05US021 — l'avertissement d'effectif, **avant** le clic « Démarrer ».
//
// Ambre (`--danger`), jamais rouge : ce n'est pas encore un refus, c'est ce qui l'annonce (`DV-03`).
// Le refus, lui, remontera du serveur par `MessageErreur` (rouge, `role="alert"`). Et jamais la
// couleur seule — glyphe **et** mot portent le sens.
//
// Le message **chiffre** son impact et **nomme la cause** (`D-16` / `P-4`) : « une alerte qui ne
// chiffre pas son impact est un clic de plus, pas une protection ». Sans la phase, l'organisateur
// saurait qu'il manque du monde sans savoir quoi corriger dans son format.
function AvertissementEffectif({ exigence }: { exigence: ExigenceEffectif }) {
  // ⚠️ La cause se lit sur `origine`, **jamais** sur `ordre_phase === null`. Le déduire de l'absence
  // de phase faisait annoncer « ce minimum est celui exigé pour ce format » — une règle de club —
  // sur le simple plancher structurel d'une qualification seule, c'est-à-dire sur le format nominal
  // du projet. Le produit inventait une cause (défaut relevé en revue).
  const cause =
    exigence.origine === 'club'
      ? ' Ce format exige ce minimum, au-delà de ce que son déroulé impose.'
      : exigence.ordre_phase === null
        ? ' Son déroulé ne peut pas se jouer à moins que cela.'
        : ` La phase ${exigence.ordre_phase} prélève à partir du rang ${exigence.rang_debut} :` +
          ` il lui faut au moins ${exigence.minimum} classés pour avoir des tireurs.`
  return (
    <p className="carte__etat carte__etat--alerte" role="status">
      <span aria-hidden="true">▲</span> <strong>Effectif insuffisant</strong> — {exigence.inscrits}{' '}
      inscrit{exigence.inscrits > 1 ? 's' : ''} / {exigence.minimum} requis.
      {cause}
    </p>
  )
}

export function FriseCycleDeVie({ tournoi }: { tournoi: Tournoi }) {
  const transitions = useTransitions(tournoi.id)
  const transitionner = useTransitionnerTournoi(tournoi.id)
  const exigence = useExigenceEffectif(tournoi.id)
  const queryClient = useQueryClient()
  const rangCourant = RANG[tournoi.statut]
  // Signalé tant que le compte n'y est pas — et **seulement** avant le départ : une fois le tournoi
  // lancé, le rappeler serait un reproche sans action possible. Une lecture en échec n'affiche
  // rien : l'avertissement est un confort, il ne doit pas transformer un hoquet réseau en alarme.
  const manqueDuMonde =
    exigence.data !== undefined &&
    !exigence.data.suffisant &&
    (tournoi.statut === 'brouillon' || tournoi.statut === 'pret')

  // Confirme avant les transitions qui figent (terminer) ou sont terminales (annuler/archiver). Pour
  // `terminer`, on chiffre ce qui reste via la même logique que l'écran Complétude ; si sa lecture
  // échoue, on **laisse passer** (dégradé) — ne jamais bloquer la seule action irréversible sur un
  // hoquet réseau (`P-3`, comme l'ancien CycleDeVie).
  //
  // La confirmation passe par un **vrai dialogue** depuis le retour maquettes du 04/08/2026 (A15) :
  // `window.confirm` bloquait le fil sur un écran temps réel et ne proposait que « OK / Annuler » —
  // ambigu au point d'être trompeur sur la transition « annuler », où « Annuler » désignait à la
  // fois le geste et son abandon.
  //
  // La transition en attente de confirmation, `null` si aucune. Elle porte **son** texte : les trois
  // gestes qui se confirment n'ont ni le même ton ni les mêmes conséquences, et le message de
  // « terminer » se calcule (chiffrage de ce qui reste) avant même que le dialogue s'ouvre.
  const [aConfirmer, setAConfirmer] = useState<{
    nom: string
    titre: string
    message: string
    detail: string | null
    libelleConfirmer: string
  } | null>(null)

  const declencher = async (nom: string) => {
    if (nom === 'terminer') {
      let detail: string
      try {
        const completude = await queryClient.fetchQuery({
          queryKey: ['completude', tournoi.id],
          queryFn: () => getCompletude(tournoi.id),
        })
        detail = messageConfirmationTerminer(completude)
      } catch {
        // Dégradé **volontaire** (`P-3`) : ne jamais bloquer la seule action irréversible sur un
        // hoquet réseau. On dit qu'on n'a pas pu vérifier, et on laisse passer.
        detail = 'Impossible de vérifier ce qui reste (complétude injoignable).'
      }
      setAConfirmer({
        nom,
        titre: 'Terminer ce tournoi ?',
        message: 'Les résultats sportifs sont figés. Les paiements, eux, restent ouverts.',
        detail,
        libelleConfirmer: 'Terminer',
      })
      return
    }
    if (nom === 'annuler') {
      setAConfirmer({
        nom,
        titre: 'Annuler ce tournoi ?',
        message: 'Il conserve sa trace et reste consultable — ce n’est pas une suppression.',
        detail: null,
        libelleConfirmer: 'Annuler le tournoi',
      })
      return
    }
    if (nom === 'archiver') {
      setAConfirmer({
        nom,
        titre: 'Archiver ce tournoi ?',
        message:
          'Il passe en lecture seule définitive : plus aucune modification ne sera possible.',
        detail: null,
        libelleConfirmer: 'Archiver',
      })
      return
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

      {manqueDuMonde && exigence.data !== undefined && (
        <AvertissementEffectif exigence={exigence.data} />
      )}

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

      {/* Un seul dialogue pour les trois transitions qui se confirment : c'est le même cadre, seul
          son contenu change. `ton="danger"` — terminer fige, annuler et archiver sont terminaux
          (A15 : *« une pop-up propre et bien design »*, en remplacement du `window.confirm`). */}
      <DialogueConfirmation
        ouvert={aConfirmer !== null}
        titre={aConfirmer?.titre ?? ''}
        message={aConfirmer?.message ?? ''}
        detail={aConfirmer?.detail ?? null}
        libelleConfirmer={aConfirmer?.libelleConfirmer ?? 'Confirmer'}
        ton="danger"
        enCours={transitionner.isPending}
        onAnnuler={() => setAConfirmer(null)}
        onConfirmer={() => {
          const nom = aConfirmer?.nom
          setAConfirmer(null)
          if (nom !== undefined) transitionner.mutate(nom)
        }}
      />
    </div>
  )
}
