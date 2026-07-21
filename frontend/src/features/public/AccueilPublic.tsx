// Consultation publique (E10US001 + E07US001) : sans session admin, la lecture reste ouverte à tous.
// On choisit un tournoi dans la liste, puis on bascule entre ses **vues publiques** — le classement
// en direct et le plan de cibles — par onglets. Aucune authentification, lecture seule, responsive
// mobile (CA E07US001). Le live est automatique : les vues s'appuient sur React Query, invalidé par
// la diffusion temps réel post-commit (E04US009).
//
// Navigation par **état local** (`useState`), pas de `react-router` : cohérent avec l'arbitrage de la
// coquille admin (18/07/2026) — périmètre réseau local, pas de deep-link/URL partagée, la dépendance
// ne se justifie pas (règle 11). Les CA d'E07US001 (classements/plans/live) ne réclament pas d'URL
// partageable. « Suivre des archers » (E07US006) mémorise le choix côté client (`localStorage`), pas
// dans l'URL : c'est un onglet de plus, sélectionné d'entrée si l'on suit déjà quelqu'un.
//
// Extrait de `admin/CoquilleAdmin.tsx` en E07US001 : la zone publique est une surface à part entière,
// pas un repli enfoui dans le module d'administration.

import { useState } from 'react'
import { useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
import type { Tournoi } from '../competition/api'
import { VueClassement } from '../competition/VueClassement'
import { PlanCiblesPublic } from '../placement/PlanCiblesPublic'
import { VueSuivi } from '../suivi/VueSuivi'
import { BadgeStatut, GestionTournois } from '../tournois/Tournois'

// Les vues publiques d'un tournoi. Fermé (pas d'ouverture prévue ici) : les tableaux de duels
// (E07US005) et l'écran de salle (E07US004) sont d'autres US, pas des onglets à réserver.
type Vue = 'suivi' | 'classement' | 'plan'

const VUES: { id: Vue; libelle: string }[] = [
  { id: 'suivi', libelle: 'Suivi' },
  { id: 'classement', libelle: 'Classement' },
  { id: 'plan', libelle: 'Plan de cibles' },
]

export function AccueilPublic() {
  const [selection, setSelection] = useState<Tournoi | null>(null)

  return (
    <div className="app__contenu--colonnes">
      {/* Porte **Public** (E00US017, ADR-0042) : liste en lecture seule **sans** login admin
          (`montrerConnexion={false}`) — le public ne peut pas escalader. Le scoreur et la tablette
          ont désormais leurs propres portes à l'écran d'accueil ; on ne les propose plus ici. */}
      <GestionTournois
        selectionneId={selection?.id ?? null}
        onChoisi={setSelection}
        montrerConnexion={false}
      />

      {/* `key={selection.id}` : changer directement de tournoi (la liste reste cliquable au-dessus)
          **remonte** le sous-arbre au lieu de le réconcilier en place — sinon le filtre catégorie et
          le départ choisis pour le tournoi précédent survivraient et interrogeraient le nouveau
          (classement vide trompeur). Les tournois concurrents sont une capacité voulue, le cas est
          réel. */}
      {selection && (
        <VuesPubliques key={selection.id} tournoi={selection} onFermer={() => setSelection(null)} />
      )}
    </div>
  )
}

function VuesPubliques({ tournoi, onFermer }: { tournoi: Tournoi; onFermer: () => void }) {
  // Si l'on suit déjà quelqu'un sur ce tournoi, on ouvre directement sur « Suivi » — l'appli tombe sur
  // ses archers sans détour (D-09). Sinon, le classement reste la vue d'accueil par défaut.
  const aDesSuivis = useSessionSuivisStore((s) => s.suivis.some((x) => x.tournoiId === tournoi.id))
  const [vue, setVue] = useState<Vue>(aDesSuivis ? 'suivi' : 'classement')

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

      {vue === 'suivi' ? (
        <VueSuivi tournoiId={tournoi.id} />
      ) : vue === 'classement' ? (
        <VueClassement tournoiId={tournoi.id} admin={false} />
      ) : (
        <PlanCiblesPublic tournoiId={tournoi.id} />
      )}
    </section>
  )
}
