// Barème de qualification d'un tournoi (E01US009) — réservé à l'admin (monté sous `estAdmin`).
//
// Définit comment se tire et se compte la qualification : un nombre de **volées** de chacune un
// nombre de **flèches**, au **cumul**. Le preset FFTA 18 m (20 volées de 3 = 60 flèches) est
// proposé par défaut et applicable d'un clic, mais toutes les valeurs restent **modifiables**
// (principe « le règlement est un template »).

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import {
  useBaremeQualification,
  useDefinirBareme,
  useDefinirBaremeEtape,
  useQualifications,
} from './hooks'

// Preset FFTA 18 m (référentiel §6.1) : 20 volées de 3 flèches (60 flèches).
const PRESET_FFTA = { nb_volees: 20, nb_fleches_par_volee: 3 }
const VALEUR_FLECHE_MAX = 10

export function BaremeQualification({ tournoiId }: { tournoiId: number }) {
  const qualifications = useQualifications(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Barème de qualification</h3>
      {qualifications.isPending && <p className="carte__etat">Chargement…</p>}
      {qualifications.isError && <MessageErreur erreur={qualifications.error} />}
      {qualifications.isSuccess &&
        (qualifications.data.length === 0 ? (
          <PremierBareme tournoiId={tournoiId} />
        ) : (
          qualifications.data.map((qualification) => (
            <div key={qualification.etape_id}>
              {/* Le titre n'apparaît qu'à partir de deux : sur un tournoi ordinaire — une seule
                  qualification — l'écran reste exactement celui d'avant l'US, sans intitulé de
                  section superflu au-dessus d'un unique formulaire. */}
              {qualifications.data.length > 1 && (
                <h4 className="carte__soustitre">{qualification.libelle}</h4>
              )}
              <FormulaireBareme
                // Clé sur les valeurs serveur : le formulaire se re-sème si le barème change côté
                // serveur (enregistrement, ou diffusion temps réel d'une autre session), sans état
                // à synchroniser.
                key={`${qualification.bareme?.nb_volees ?? 'x'}-${
                  qualification.bareme?.nb_fleches_par_volee ?? 'x'
                }`}
                tournoiId={tournoiId}
                etapeId={qualification.etape_id}
                nbVoleesInitial={qualification.bareme?.nb_volees ?? PRESET_FFTA.nb_volees}
                nbFlechesInitial={
                  qualification.bareme?.nb_fleches_par_volee ?? PRESET_FFTA.nb_fleches_par_volee
                }
                defini={qualification.bareme !== null}
              />
            </div>
          ))
        ))}
    </section>
  )
}

// Le tout premier réglage d'un tournoi neuf : son déroulé est encore vide, donc il n'y a **aucune**
// étape à désigner. C'est le seul chemin qui *crée* la qualification (elle naît en tête du déroulé,
// cf. `ServiceBaremeQualification.definir`) — d'où un formulaire séparé plutôt qu'un cas de plus
// dans le précédent : les deux ne parlent pas à la même route et ne font pas le même geste.
function PremierBareme({ tournoiId }: { tournoiId: number }) {
  const bareme = useBaremeQualification(tournoiId)
  if (bareme.isPending) return <p className="carte__etat">Chargement…</p>
  if (bareme.isError) return <MessageErreur erreur={bareme.error} />
  return (
    <FormulaireBareme
      key={`${bareme.data?.nb_volees ?? 'x'}-${bareme.data?.nb_fleches_par_volee ?? 'x'}`}
      tournoiId={tournoiId}
      etapeId={null}
      nbVoleesInitial={bareme.data?.nb_volees ?? PRESET_FFTA.nb_volees}
      nbFlechesInitial={bareme.data?.nb_fleches_par_volee ?? PRESET_FFTA.nb_fleches_par_volee}
      defini={bareme.data !== null}
    />
  )
}

function FormulaireBareme({
  tournoiId,
  etapeId,
  nbVoleesInitial,
  nbFlechesInitial,
  defini,
}: {
  tournoiId: number
  // `null` = le tout premier réglage, qui **crée** la qualification en tête du déroulé. Sinon
  // l'étape désignée, réglée sans rien créer (E05US025).
  etapeId: number | null
  nbVoleesInitial: number
  nbFlechesInitial: number
  defini: boolean
}) {
  const [nbVolees, setNbVolees] = useState<string>(String(nbVoleesInitial))
  const [nbFleches, setNbFleches] = useState<string>(String(nbFlechesInitial))
  // Les deux hooks sont appelés inconditionnellement (règle des hooks) ; seul le résultat retenu
  // dépend de `etapeId`. `etapeId ?? 0` n'est jamais appelé quand il vaut `null`.
  const definirTournoi = useDefinirBareme(tournoiId)
  const definirEtape = useDefinirBaremeEtape(tournoiId, etapeId ?? 0)
  const definir = etapeId === null ? definirTournoi : definirEtape

  const voleesValide = Number.isInteger(Number(nbVolees)) && Number(nbVolees) >= 1
  const flechesValide = Number.isInteger(Number(nbFleches)) && Number(nbFleches) >= 1
  const soumissionPossible = voleesValide && flechesValide

  // Aperçu des dérivées (total de flèches, score max) tant que les valeurs sont valides.
  const total = soumissionPossible ? Number(nbVolees) * Number(nbFleches) : null
  const scoreMax = total === null ? null : total * VALEUR_FLECHE_MAX

  const appliquerPreset = () => {
    setNbVolees(String(PRESET_FFTA.nb_volees))
    setNbFleches(String(PRESET_FFTA.nb_fleches_par_volee))
  }

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    definir.mutate({ nb_volees: Number(nbVolees), nb_fleches_par_volee: Number(nbFleches) })
  }

  return (
    <div>
      {!defini && (
        <p className="carte__etat">
          Aucun barème défini. Le preset FFTA 18 m (20 volées de 3) est proposé ci-dessous ;
          ajustez-le si besoin puis enregistrez.
        </p>
      )}
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <label className="formulaire__libelle">
          Nombre de volées
          <input
            className="formulaire__champ"
            type="number"
            min={1}
            value={nbVolees}
            onChange={(e) => setNbVolees(e.target.value)}
            aria-label="Nombre de volées"
          />
        </label>
        <label className="formulaire__libelle">
          Flèches par volée
          <input
            className="formulaire__champ"
            type="number"
            min={1}
            value={nbFleches}
            onChange={(e) => setNbFleches(e.target.value)}
            aria-label="Nombre de flèches par volée"
          />
        </label>
        {total !== null && (
          <p className="carte__etat">
            {total} flèches · {scoreMax} points max (au cumul)
          </p>
        )}
        <div className="formulaire__actions">
          <button type="submit" disabled={definir.isPending || !soumissionPossible}>
            {defini ? 'Enregistrer le barème' : 'Enregistrer'}
          </button>
          <button type="button" className="bouton--discret" onClick={appliquerPreset}>
            Preset FFTA 18 m
          </button>
        </div>
      </form>
      <MessageErreur erreur={definir.error} />
    </div>
  )
}
