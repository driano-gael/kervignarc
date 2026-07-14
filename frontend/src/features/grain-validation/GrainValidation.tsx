// Grain de validation de la qualification (E01US015, `D-11`) — réservé à l'admin (monté sous
// `estAdmin`).
//
// Définit **quand le scoreur valide** : à la fin de la série, ou toutes les N volées. C'est une
// politique de **phase**, réglée une fois à la configuration et jamais le jour J — elle dimensionne
// la charge des scoreurs (à 3 scoreurs pour ~30 cibles : ~60 validations par départ en fin de
// série, ~180 toutes les 2 volées).
//
// « Fin de duel » n'est pas proposé ici : la qualification se tire en séries, elle ne comporte pas
// de duels. Le grain vit sur la phase de qualification, qui naît avec le **barème** (E01US009) :
// tant qu'il n'est pas défini, il n'y a rien à régler.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import type { TypeGrain } from './api'
import { useDefinirGrain, useGrainValidation } from './hooks'

const CADENCE_PAR_DEFAUT = 2

export function GrainValidation({ tournoiId }: { tournoiId: number }) {
  const grain = useGrainValidation(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Grain de validation</h3>
      {grain.isPending && <p className="carte__etat">Chargement…</p>}
      {grain.isError && <MessageErreur erreur={grain.error} />}
      {grain.isSuccess &&
        (grain.data === null ? (
          <p className="carte__etat">
            Le grain de validation se règle sur la qualification : définissez d'abord son barème
            ci-dessus.
          </p>
        ) : (
          // Clé sur les valeurs serveur : le formulaire se re-sème si le grain change côté serveur
          // (enregistrement, ou diffusion temps réel d'une autre session), sans état à synchroniser.
          <FormulaireGrain
            key={`${grain.data.grain}-${grain.data.n_volees ?? 'x'}`}
            tournoiId={tournoiId}
            grainInitial={grain.data.grain}
            cadenceInitiale={grain.data.n_volees}
          />
        ))}
    </section>
  )
}

function FormulaireGrain({
  tournoiId,
  grainInitial,
  cadenceInitiale,
}: {
  tournoiId: number
  grainInitial: TypeGrain
  cadenceInitiale: number | null
}) {
  const [grain, setGrain] = useState<TypeGrain>(grainInitial)
  const [cadence, setCadence] = useState<string>(String(cadenceInitiale ?? CADENCE_PAR_DEFAUT))
  const definir = useDefinirGrain(tournoiId)

  const parCadence = grain === 'toutes_les_n_volees'
  const cadenceValide = Number.isInteger(Number(cadence)) && Number(cadence) >= 1
  const soumissionPossible = !parCadence || cadenceValide

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    definir.mutate(parCadence ? { grain, n_volees: Number(cadence) } : { grain })
  }

  return (
    <div>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <label className="formulaire__libelle formulaire__libelle--choix">
          <input
            type="radio"
            name="grain-validation"
            value="fin_de_serie"
            checked={grain === 'fin_de_serie'}
            onChange={() => setGrain('fin_de_serie')}
          />
          À la fin de la série
        </label>
        <label className="formulaire__libelle formulaire__libelle--choix">
          <input
            type="radio"
            name="grain-validation"
            value="toutes_les_n_volees"
            checked={parCadence}
            onChange={() => setGrain('toutes_les_n_volees')}
          />
          Toutes les N volées
        </label>
        {parCadence && (
          <label className="formulaire__libelle">
            Nombre de volées entre deux validations
            <input
              className="formulaire__champ"
              type="number"
              min={1}
              value={cadence}
              onChange={(e) => setCadence(e.target.value)}
              aria-label="Nombre de volées entre deux validations"
            />
          </label>
        )}
        <p className="carte__etat">
          {grain === 'fin_de_serie'
            ? 'Le scoreur valide une fois, en fin de série : environ 60 validations par départ sur 30 cibles.'
            : 'Attention à la charge des scoreurs : plus la cadence est courte, plus ils passent souvent (une validation toutes les 40 s à 3 scoreurs pour 30 cibles, si vous validez toutes les 2 volées).'}
        </p>
        <div className="formulaire__actions">
          <button type="submit" disabled={definir.isPending || !soumissionPossible}>
            Enregistrer le grain
          </button>
        </div>
      </form>
      <MessageErreur erreur={definir.error} />
    </div>
  )
}

// DETTE-004 (docs/dette.md) : 8ᵉ copie conforme de ce composant, un par feature. À extraire dans
// `shared/ui/` (E00US013) — le rendu des erreurs doit avoir un point unique, ne serait-ce que pour
// appliquer le token d'alerte ambre du CDC design (`DV-03`) une seule fois.
function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
