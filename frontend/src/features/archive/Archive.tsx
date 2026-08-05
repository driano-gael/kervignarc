// Écran « Archive » de l'appli admin (E11US003) — destination prévue au CDC UX §7.1, matérialisée
// ici. Produit un **paquet ZIP** de fin de tournoi : instantané complet de la base (anti-plantage),
// données en CSV (ouvrables dans un tableur), documents PDF régénérés, et un manifeste. L'organisateur
// **coche ce qu'il veut** dans l'archive (tout par défaut = archive complète).
//
// Un téléchargement est une **action** (`useMutation`, pas de cache) ; le bouton se désactive pendant
// la génération (`isPending`, l'archive peut être lourde) et toute erreur s'affiche via `MessageErreur`.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { OPTIONS_ARCHIVE_DEFAUT, type OptionsArchive } from './api'
import { useTelechargerArchive } from './hooks'

// Une ligne à cocher = une partie de l'archive. `cle` indexe `OptionsArchive` (typage exhaustif).
const PARTIES: ReadonlyArray<{ cle: keyof OptionsArchive; libelle: string; description: string }> =
  [
    {
      cle: 'base',
      libelle: 'Base de données complète (SQLite)',
      description:
        'Instantané fidèle de tout le contenu — le filet de sécurité contre un plantage.',
    },
    {
      cle: 'donneesCsv',
      libelle: 'Données en CSV',
      description: 'Chaque table exportée en tableur (archers, inscriptions, scores, paiements…).',
    },
    {
      cle: 'feuillesDeMarque',
      libelle: 'Feuilles de marque (PDF)',
      description: 'Une par départ, régénérées à partir du plan de cibles.',
    },
    {
      cle: 'listePlacement',
      libelle: 'Liste de placement (PDF)',
      description: 'Qui tire sur quelle cible et dans quel couloir de tir.',
    },
    {
      cle: 'listeClubPaiement',
      libelle: 'Liste club & paiement (PDF)',
      description: 'Par club : dû, réglé et totaux.',
    },
  ]

export function Archive({ tournoiId }: { tournoiId: number }) {
  const [options, setOptions] = useState<OptionsArchive>(OPTIONS_ARCHIVE_DEFAUT)
  const telecharger = useTelechargerArchive(tournoiId)

  const basculer = (cle: keyof OptionsArchive) =>
    setOptions((prec) => ({ ...prec, [cle]: !prec[cle] }))

  // Une archive vide (rien de coché) n'a pas de sens : le bouton ne s'active que si au moins une
  // partie est retenue (le manifeste, lui, est toujours présent côté serveur).
  const auMoinsUne = Object.values(options).some(Boolean)

  return (
    <section>
      <h3 className="carte__soustitre">Archive de fin de tournoi</h3>
      <p className="carte__etat">
        Constituez un paquet à conserver en fin d'événement. Cochez ce que l'archive doit contenir —
        tout est sélectionné par défaut.
      </p>

      <fieldset className="formulaire__champ formulaire__tranches">
        <legend>Contenu de l'archive</legend>
        {PARTIES.map((partie) => (
          <label key={partie.cle} className="formulaire__tranche">
            <input
              type="checkbox"
              checked={options[partie.cle]}
              onChange={() => basculer(partie.cle)}
            />
            <span>
              <strong>{partie.libelle}</strong> — {partie.description}
            </span>
          </label>
        ))}
      </fieldset>

      <div className="formulaire__actions">
        <button
          type="button"
          disabled={telecharger.isPending || !auMoinsUne}
          onClick={() => telecharger.mutate(options)}
        >
          {telecharger.isPending ? 'Génération…' : "Télécharger l'archive (ZIP)"}
        </button>
      </div>
      <MessageErreur erreur={telecharger.error} />
    </section>
  )
}
