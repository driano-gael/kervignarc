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
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useQualifications } from '../bareme/hooks'
import type { TypeGrain } from './api'
import { useDefinirGrain, useDefinirGrainEtape, useGrainValidation } from './hooks'

const CADENCE_PAR_DEFAUT = 2

// E05US025 (ADR-0082) : **un formulaire par qualification**. Le CA veut que chacune ait ses propres
// réglages — barème *et* grain. Un premier jet ne livrait que le barème : la route par étape
// existait côté serveur, testée, mais aucun écran ne l'appelait, si bien que le grain de la *haute*
// et de la *basse* n'était modifiable par aucun chemin (correctif de revue).
//
// Symétrique de `BaremeQualification` : même découpage, même règle d'affichage du titre, et le
// tout premier réglage garde son formulaire propre (il parle à la route « du tournoi »).
export function GrainValidation({ tournoiId }: { tournoiId: number }) {
  const qualifications = useQualifications(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Grain de validation</h3>
      {qualifications.isPending && <p className="carte__etat">Chargement…</p>}
      {qualifications.isError && <MessageErreur erreur={qualifications.error} />}
      {qualifications.isSuccess &&
        (qualifications.data.length === 0 ? (
          <PremierGrain tournoiId={tournoiId} />
        ) : (
          qualifications.data.map((qualification) => (
            <div key={qualification.etape_id}>
              {/* Le titre n'apparaît qu'à partir de deux : sur un tournoi ordinaire, l'écran reste
                  exactement celui d'avant l'US. */}
              {qualifications.data.length > 1 && (
                <h4 className="carte__soustitre">{qualification.libelle}</h4>
              )}
              {qualification.grain === null ? (
                <p className="carte__etat">
                  Le grain de validation se règle sur la qualification : définissez d'abord son
                  barème ci-dessus.
                </p>
              ) : (
                <FormulaireGrain
                  // Clé sur les valeurs serveur : le formulaire se re-sème si le grain change côté
                  // serveur (enregistrement, ou diffusion temps réel d'une autre session).
                  key={`${qualification.grain}-${qualification.grain_n_volees ?? 'x'}`}
                  tournoiId={tournoiId}
                  etapeId={qualification.etape_id}
                  grainInitial={qualification.grain}
                  cadenceInitiale={qualification.grain_n_volees}
                />
              )}
            </div>
          ))
        ))}
    </section>
  )
}

// Le tout premier réglage d'un tournoi neuf : son déroulé est encore vide, donc aucune étape à
// désigner. Il parle à la route « du tournoi », celle qui suit le barème créé au même écran.
function PremierGrain({ tournoiId }: { tournoiId: number }) {
  const grain = useGrainValidation(tournoiId)
  if (grain.isPending) return <p className="carte__etat">Chargement…</p>
  if (grain.isError) return <MessageErreur erreur={grain.error} />
  if (grain.data === null)
    return (
      <p className="carte__etat">
        Le grain de validation se règle sur la qualification : définissez d'abord son barème
        ci-dessus.
      </p>
    )
  return (
    <FormulaireGrain
      key={`${grain.data.grain}-${grain.data.n_volees ?? 'x'}`}
      tournoiId={tournoiId}
      etapeId={null}
      grainInitial={grain.data.grain}
      cadenceInitiale={grain.data.n_volees}
    />
  )
}

function FormulaireGrain({
  tournoiId,
  etapeId,
  grainInitial,
  cadenceInitiale,
}: {
  tournoiId: number
  // `null` = le tout premier réglage, qui parle à la route « du tournoi ». Sinon l'étape désignée
  // (E05US025).
  etapeId: number | null
  grainInitial: TypeGrain
  cadenceInitiale: number | null
}) {
  const [grain, setGrain] = useState<TypeGrain>(grainInitial)
  const [cadence, setCadence] = useState<string>(String(cadenceInitiale ?? CADENCE_PAR_DEFAUT))
  // Les deux hooks sont appelés inconditionnellement (règle des hooks) ; seul le résultat retenu
  // dépend de `etapeId`. `etapeId ?? 0` n'est jamais appelé quand il vaut `null`.
  const definirTournoi = useDefinirGrain(tournoiId)
  const definirEtape = useDefinirGrainEtape(tournoiId, etapeId ?? 0)
  const definir = etapeId === null ? definirTournoi : definirEtape

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
