// Écran « Jeu d'essai » (E15US001) — outil admin de démo/QA.
//
// Deux briques, sur un même écran de la coquille admin :
//  1. **Peupler le tournoi courant** de N archers de test (données réelles) — n'a de sens que si un
//     tournoi est sélectionné (sinon une invite le rappelle) ;
//  2. **Scénarios rejouables** : un catalogue qui instancie d'un coup un tournoi complet, prêt à
//     lancer. À la création, on bascule sur ce nouveau tournoi (callback vers la coquille).
//
// C'est de la **donnée réelle persistée** — à distinguer de la simulation éphémère (E15US002, à
// venir). La graine (déterminisme, règle 9) est réglable pour rejouer exactement le même jeu.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useInstancierScenario, usePeuplerTournoi, useScenarios } from './hooks'

// Champ de graine facultatif, partagé par les deux briques : vide → le serveur prend sa graine
// stable ; un nombre → jeu rejouable à l'identique.
function ChampGraine({ graine, onChange }: { graine: string; onChange: (valeur: string) => void }) {
  return (
    <label className="formulaire__libelle">
      Graine (optionnelle)
      <input
        className="formulaire__champ"
        type="number"
        inputMode="numeric"
        placeholder="stable par défaut"
        value={graine}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  )
}

function grainePour(graine: string): number | undefined {
  const valeur = graine.trim()
  return valeur === '' ? undefined : Number(valeur)
}

// Brique 1 — peupler le tournoi courant.
function PeuplerTournoi({ tournoiId }: { tournoiId: number }) {
  const [nombre, setNombre] = useState(24)
  const [graine, setGraine] = useState('')
  const peupler = usePeuplerTournoi(tournoiId)

  return (
    <section className="carte">
      <h3 className="carte__soustitre">Peupler le tournoi courant</h3>
      <p className="carte__etat">
        Ajoute des archers de test plausibles (noms, clubs, catégories cohérentes) au tournoi
        sélectionné. Si le tournoi n’a pas encore de catégories, le jeu FFTA est chargé au passage.
      </p>
      <div className="formulaire formulaire--colonne">
        <label className="formulaire__libelle">
          Nombre d’archers (1 à 500)
          <input
            className="formulaire__champ"
            type="number"
            min={1}
            max={500}
            value={nombre}
            onChange={(e) => setNombre(Number(e.target.value))}
          />
        </label>
        <ChampGraine graine={graine} onChange={setGraine} />
        <div className="formulaire__actions">
          <button
            type="button"
            disabled={peupler.isPending || nombre < 1 || nombre > 500}
            onClick={() => peupler.mutate({ nombre, graine: grainePour(graine) })}
          >
            {peupler.isPending ? 'Peuplement…' : `Peupler avec ${nombre} archers`}
          </button>
        </div>
      </div>
      {peupler.isSuccess && (
        <p className="carte__etat carte__etat--ok" role="status">
          {peupler.data.nombre_archers_crees} archers de test ajoutés au tournoi.
        </p>
      )}
      <MessageErreur erreur={peupler.error} />
    </section>
  )
}

// Brique 2 — instancier un scénario du catalogue.
function Scenarios({ onTournoiInstancie }: { onTournoiInstancie?: (tournoiId: number) => void }) {
  const scenarios = useScenarios()
  const [graine, setGraine] = useState('')
  const instancier = useInstancierScenario()

  return (
    <section className="carte">
      <h3 className="carte__soustitre">Scénarios rejouables</h3>
      <p className="carte__etat">
        Chaque scénario crée un <strong>nouveau</strong> tournoi complet (catégories, départs,
        archers inscrits), prêt à passer « prêt » puis à lancer.
      </p>
      <ChampGraine graine={graine} onChange={setGraine} />
      {scenarios.isError && <MessageErreur erreur={scenarios.error} />}
      <ul className="jeu-essai__scenarios">
        {(scenarios.data ?? []).map((scenario) => (
          <li key={scenario.id} className="jeu-essai__scenario">
            <div>
              <strong>{scenario.libelle}</strong>
              <p className="carte__etat">{scenario.description}</p>
              <p className="carte__etat">
                {scenario.nombre_archers} archers · {scenario.nombre_departs} départ
                {scenario.nombre_departs > 1 ? 's' : ''}
              </p>
            </div>
            <button
              type="button"
              // Tous désactivés pendant une instanciation (évite deux créations concurrentes), mais
              // seul le bouton cliqué affiche « Création… » — `variables` porte le scénario en cours.
              disabled={instancier.isPending}
              onClick={() =>
                instancier.mutate(
                  { scenarioId: scenario.id, graine: grainePour(graine) },
                  { onSuccess: (resultat) => onTournoiInstancie?.(resultat.tournoi_id) },
                )
              }
            >
              {instancier.isPending && instancier.variables?.scenarioId === scenario.id
                ? 'Création…'
                : 'Instancier'}
            </button>
          </li>
        ))}
      </ul>
      {instancier.isSuccess && (
        <p className="carte__etat carte__etat--ok" role="status">
          Tournoi « {instancier.data.nom} » créé : {instancier.data.nombre_archers} archers sur{' '}
          {instancier.data.nombre_departs} départ
          {instancier.data.nombre_departs > 1 ? 's' : ''}.
        </p>
      )}
      <MessageErreur erreur={instancier.error} />
    </section>
  )
}

export function JeuEssai({
  tournoiId,
  onTournoiInstancie,
}: {
  tournoiId: number | null
  onTournoiInstancie?: (tournoiId: number) => void
}) {
  return (
    <div className="carte carte--large">
      <h2 className="carte__titre">Jeu d’essai</h2>
      <p className="carte__etat">
        Outil de démonstration et de test : peuplez un tournoi de données factices, ou partez d’un
        scénario prêt à l’emploi. Ce sont des <strong>données réelles</strong> — à utiliser sur des
        tournois de test.
      </p>
      {tournoiId === null ? (
        <p className="carte__etat">
          Sélectionnez un tournoi (en haut) pour le peupler, ou instanciez un scénario ci-dessous —
          il créera son propre tournoi.
        </p>
      ) : (
        <PeuplerTournoi tournoiId={tournoiId} />
      )}
      <Scenarios onTournoiInstancie={onTournoiInstancie} />
    </div>
  )
}
