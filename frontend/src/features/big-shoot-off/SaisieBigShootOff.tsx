// Écran de saisie d'un **Big Shoot Off** (E05US028) — surface **scoreur**.
//
// Jumeau de `SaisiePoules` par la coquille et **différent** par le fond : il n'y a pas de duel —
// tous les finalistes sont sur la ligne, et c'est le **classement de la manche** qui élimine. ⚠️
// `DuelCharge` n'est pas réutilisé : il suppose **deux** duellistes, et l'y forcer aurait demandé
// un adversaire fictif. ⚠️ **Conséquence assumée : pas de file hors-ligne ici** (`DETTE-060`) — une
// coupure LAN pendant une finale fait perdre la volée en cours, que le scoreur retape ; borné, mais
// c'est un écart au régime des autres surfaces de saisie (ADR-0083).

import { useState } from 'react'

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { usePhases } from '../saisie-duels/hooks'
import type { Manche, Tireur } from './api'
import { useEtatBigShootOffSaisie, useSaisirVolee, useValiderManche } from './hooks'

/** Le pavé de saisie d'une volée : autant de champs que de flèches, plus le bouton de validation. */
function LigneTireur({
  tireur,
  manche,
  tournoiId,
  phaseId,
  fleches,
}: {
  tireur: Tireur
  manche: Manche
  tournoiId: number
  phaseId: number
  fleches: number
}) {
  const [valeurs, setValeurs] = useState<string[]>(() => Array.from({ length: fleches }, () => ''))
  const saisir = useSaisirVolee(tournoiId, phaseId)
  const valider = useValiderManche(tournoiId, phaseId)
  const complete = valeurs.every((valeur) => valeur.trim() !== '')

  // ⚠️ **La volée à poser vient du serveur** (revue d'E05US028). Ce composant envoyait
  // `manche.volees[0]` — « la première volée de la manche » — alors que son propre commentaire
  // annonçait « la première non encore posée ». Les deux ne coïncident qu'à `volees = 1`, seule
  // valeur exercée par les tests ; à `volees = 2`, chaque « Enregistrer » réécrivait la volée 1 et
  // la manche ne pouvait jamais se conclure (`RienAValider`). Le front ne re-dérive pas une
  // numérotation qu'il ne persiste pas.
  const prochaine = tireur.prochaine_volee

  // Un archer sorti ne tire plus : on montre son rang, on ne lui ouvre pas de champ. Sans cela, une
  // tablette restée ouverte laisserait saisir des flèches qui n'entreraient dans aucune manche.
  if (!tireur.en_lice) {
    return (
      <li className="carte__ligne">
        <span>
          {tireur.prenom} {tireur.nom}
        </span>
        <span className="carte__etat">Sorti — {tireur.rang}ᵉ</span>
      </li>
    )
  }

  return (
    <li className="carte__ligne">
      <span>
        {tireur.prenom} {tireur.nom}
      </span>
      {tireur.scores.length > 0 && (
        <span className="carte__aide">Manches : {tireur.scores.join(' · ')}</span>
      )}
      <div className="duels-saisie__pave">
        {valeurs.map((valeur, index) => (
          <input
            key={index}
            aria-label={`Flèche ${index + 1} de ${tireur.prenom} ${tireur.nom}`}
            inputMode="numeric"
            value={valeur}
            onChange={(e) => setValeurs(valeurs.map((v, i) => (i === index ? e.target.value : v)))}
          />
        ))}
        <button
          type="button"
          disabled={prochaine === null || !complete || saisir.isPending}
          onClick={() => {
            if (prochaine === null) return
            saisir.mutate(
              { archerId: tireur.archer_id, numero: prochaine, valeurs },
              { onSuccess: () => setValeurs(Array.from({ length: fleches }, () => '')) },
            )
          }}
        >
          {/* Le numéro dans le libellé quand la manche compte plusieurs volées : sans lui, le
              scoreur ne sait pas laquelle des deux il est en train de poser. */}
          {manche.volees.length > 1 && prochaine !== null
            ? `Enregistrer la volée ${prochaine - manche.volees[0]! + 1}/${manche.volees.length}`
            : 'Enregistrer'}
        </button>
        <button
          type="button"
          disabled={valider.isPending}
          onClick={() => valider.mutate({ archerId: tireur.archer_id })}
        >
          Valider la manche
        </button>
      </div>
      {saisir.isError && <MessageErreur erreur={saisir.error} />}
      {valider.isError && <MessageErreur erreur={valider.error} />}
    </li>
  )
}

export function SaisieBigShootOff({
  tournoiId,
  departId,
}: {
  tournoiId: number
  departId: number | null
}) {
  const phases = usePhases(departId)
  const [phaseId, setPhaseId] = useState<number | null>(null)

  const disponibles = (phases.data ?? []).filter((phase) => phase.type === 'big_shoot_off')
  // Changer de créneau rend l'ancien `phaseId` étranger à la liste : le garder ferait scorer la
  // finale de l'autre départ, avec un identifiant valide et donc sans la moindre erreur.
  const phaseRetenue =
    phaseId !== null && disponibles.some((phase) => phase.id === phaseId) ? phaseId : null
  const etat = useEtatBigShootOffSaisie(tournoiId, phaseRetenue)
  const prochaine = (etat.data?.manches ?? []).find((manche) => !manche.jouee) ?? null
  const fleches = etat.data?.projection.fleches_par_volee ?? 3

  return (
    <div className="duels-saisie">
      <div className="duels-saisie__entete">
        <h3 className="carte__soustitre">Saisie du Big Shoot Off</h3>
      </div>

      {phases.isError && <MessageErreur erreur={phases.error} />}
      {phases.isSuccess && disponibles.length === 0 && (
        <p className="carte__etat">
          Aucun Big Shoot Off dans ce créneau : la saisie s’ouvrira quand une phase de ce type aura
          été composée et réglée.
        </p>
      )}
      {disponibles.length > 0 && (
        <select
          className="formulaire__champ"
          aria-label="Phase de Big Shoot Off"
          value={phaseRetenue ?? ''}
          onChange={(e) => setPhaseId(e.target.value === '' ? null : Number(e.target.value))}
        >
          <option value="">Choisir une phase…</option>
          {disponibles.map((phase) => (
            <option key={phase.id} value={phase.id}>
              Phase {phase.ordre}
            </option>
          ))}
        </select>
      )}

      {etat.isError && <MessageErreur erreur={etat.error} />}

      {etat.data !== undefined && (
        <>
          {/* Le barrage qui suspend la phase. Sans ce relais, le scoreur verrait une manche saisie
              **et validée** qui n'élimine personne, sans comprendre pourquoi la suivante refuse de
              s'ouvrir. */}
          {etat.data.barrage !== null && (
            <p className="carte__etat carte__etat--alerte" role="status">
              Barrage à tirer entre {etat.data.barrage.noms.join(', ')} —{' '}
              {etat.data.barrage.places === 1
                ? 'une place d’élimination à départager'
                : `${etat.data.barrage.places} places d’élimination à départager`}
              . La manche reprendra une fois le barrage tranché.
            </p>
          )}

          {etat.data.termine ? (
            <p className="carte__etat" role="status">
              Big Shoot Off terminé : {etat.data.projection.restants} rescapé
              {etat.data.projection.restants > 1 ? 's' : ''}.
            </p>
          ) : (
            prochaine !== null && (
              <p className="carte__aide" role="status">
                Manche {prochaine.numero} — {prochaine.elimine} archer
                {prochaine.elimine > 1 ? 's sortent' : ' sort'} à l’issue de ce tour.
              </p>
            )
          )}

          <ul className="carte__liste">
            {etat.data.tireurs.map((tireur) => (
              <li key={tireur.archer_id}>
                {prochaine === null ? (
                  <span>
                    {tireur.prenom} {tireur.nom}
                    {tireur.rang !== null ? ` — ${tireur.rang}ᵉ` : ''}
                  </span>
                ) : (
                  <ul className="carte__liste">
                    <LigneTireur
                      tireur={tireur}
                      manche={prochaine}
                      tournoiId={tournoiId}
                      phaseId={phaseRetenue as number}
                      fleches={fleches}
                    />
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
