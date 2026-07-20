// Consultation publique (E10US001 + E07US001) : sans session admin, la lecture reste ouverte à tous.
// On choisit un tournoi dans la liste, puis on bascule entre ses **vues publiques** — le classement
// en direct et le plan de cibles — par onglets. Aucune authentification, lecture seule, responsive
// mobile (CA E07US001). Le live est automatique : les vues s'appuient sur React Query, invalidé par
// la diffusion temps réel post-commit (E04US009).
//
// Navigation par **état local** (`useState`), pas de `react-router` : cohérent avec l'arbitrage de la
// coquille admin (18/07/2026) — périmètre réseau local, pas de deep-link/URL partagée, la dépendance
// ne se justifie pas (règle 11). Les CA d'E07US001 (classements/plans/live) ne réclament pas d'URL
// partageable ; « ouvrir l'appli sur ma journée » (mémorisation, deep-link) relève d'E07US006/008.
//
// Extrait de `admin/CoquilleAdmin.tsx` en E07US001 : la zone publique est une surface à part entière,
// pas un repli enfoui dans le module d'administration.

import { useState } from 'react'
import type { Tournoi } from '../competition/api'
import { VueClassement } from '../competition/VueClassement'
import { PlanCiblesPublic } from '../placement/PlanCiblesPublic'
import { EspaceScoreur } from '../scoreur-session/EspaceScoreur'
import { BadgeStatut, GestionTournois } from '../tournois/Tournois'

// Les deux vues publiques d'un tournoi. Fermé (pas d'ouverture prévue en E07US001) : les tableaux de
// duels (E07US005) et l'écran de salle (E07US004) sont d'autres US, pas des onglets à réserver ici.
type Vue = 'classement' | 'plan'

const VUES: { id: Vue; libelle: string }[] = [
  { id: 'classement', libelle: 'Classement' },
  { id: 'plan', libelle: 'Plan de cibles' },
]

export function AccueilPublic() {
  const [selection, setSelection] = useState<Tournoi | null>(null)

  return (
    <div className="app__contenu--colonnes">
      {/* En public, `GestionTournois` présente l'écran de connexion + la liste en lecture seule. */}
      <GestionTournois selectionneId={selection?.id ?? null} onChoisi={setSelection} />

      {selection && <VuesPubliques tournoi={selection} onFermer={() => setSelection(null)} />}

      <aside className="carte">
        {/* L'entrée du scoreur : il ouvre l'app sur son téléphone et tape son code, sans passer par
            l'admin (E10US003). */}
        <EspaceScoreur />
        {/* Entrée « poste de cible » (E04US001) : normalement on arrive par le QR de sa cible
            (`?poste=<code>`, E09US008) ; ce lien de secours ouvre l'écran de poste sans QR — une
            fois la tablette rattachée, l'app y va d'elle-même (App.tsx), ce lien ne resert plus. */}
        <p className="carte__etat">
          <a className="lien" href="?poste">
            Cette tablette est un poste de cible ›
          </a>
        </p>
      </aside>
    </div>
  )
}

function VuesPubliques({ tournoi, onFermer }: { tournoi: Tournoi; onFermer: () => void }) {
  const [vue, setVue] = useState<Vue>('classement')

  return (
    <section className="carte carte--large">
      <button type="button" className="lien" onClick={onFermer}>
        ← Tous les tournois
      </button>
      <h2 className="carte__titre">
        {tournoi.nom} <BadgeStatut statut={tournoi.statut} />
      </h2>

      <nav className="onglets" aria-label="Vues publiques du tournoi">
        {VUES.map((v) => (
          <button
            key={v.id}
            type="button"
            className={v.id === vue ? 'onglet onglet--actif' : 'onglet'}
            aria-current={v.id === vue ? 'page' : undefined}
            onClick={() => setVue(v.id)}
          >
            {v.libelle}
          </button>
        ))}
      </nav>

      {vue === 'classement' ? (
        <VueClassement tournoiId={tournoi.id} admin={false} />
      ) : (
        <PlanCiblesPublic tournoiId={tournoi.id} />
      )}
    </section>
  )
}
