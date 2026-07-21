// Barème de qualification d'un tournoi (E01US009) — réservé à l'admin (monté sous `estAdmin`).
//
// Définit comment se tire et se compte la qualification : un nombre de **volées** de chacune un
// nombre de **flèches**, au **cumul**. Le preset FFTA 18 m (20 volées de 3 = 60 flèches) est
// proposé par défaut et applicable d'un clic, mais toutes les valeurs restent **modifiables**
// (principe « le règlement est un template »).

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useBaremeQualification, useDefinirBareme } from './hooks'

// Preset FFTA 18 m (référentiel §6.1) : 20 volées de 3 flèches (60 flèches).
const PRESET_FFTA = { nb_volees: 20, nb_fleches_par_volee: 3 }
const VALEUR_FLECHE_MAX = 10

export function BaremeQualification({ tournoiId }: { tournoiId: number }) {
  const bareme = useBaremeQualification(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Barème de qualification</h3>
      {bareme.isPending && <p className="carte__etat">Chargement…</p>}
      {bareme.isError && <MessageErreur erreur={bareme.error} />}
      {bareme.isSuccess && (
        // Clé sur les valeurs serveur : le formulaire se re-sème si le barème change côté serveur
        // (enregistrement, ou diffusion temps réel d'une autre session), sans état à synchroniser.
        <FormulaireBareme
          key={`${bareme.data?.nb_volees ?? 'x'}-${bareme.data?.nb_fleches_par_volee ?? 'x'}`}
          tournoiId={tournoiId}
          nbVoleesInitial={bareme.data?.nb_volees ?? PRESET_FFTA.nb_volees}
          nbFlechesInitial={bareme.data?.nb_fleches_par_volee ?? PRESET_FFTA.nb_fleches_par_volee}
          defini={bareme.data !== null}
        />
      )}
    </section>
  )
}

function FormulaireBareme({
  tournoiId,
  nbVoleesInitial,
  nbFlechesInitial,
  defini,
}: {
  tournoiId: number
  nbVoleesInitial: number
  nbFlechesInitial: number
  defini: boolean
}) {
  const [nbVolees, setNbVolees] = useState<string>(String(nbVoleesInitial))
  const [nbFleches, setNbFleches] = useState<string>(String(nbFlechesInitial))
  const definir = useDefinirBareme(tournoiId)

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
