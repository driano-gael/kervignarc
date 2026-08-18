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

import { useMemo, useState } from 'react'
import { useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
import type { Tournoi } from '../competition/api'
import { modeEffectif, suivisDuTournoi, type ModeAffichage } from '../../shared/suivis/focus'
import { VueClassement } from '../competition/VueClassement'
import { VuePalmares } from '../palmares/VuePalmares'
import { PlanCiblesPublic } from '../placement/PlanCiblesPublic'
import { VueAffectations } from '../routage/VueAffectations'
import { VueSuivi } from '../suivi/VueSuivi'
import { VueEnCours } from '../en-cours/VueEnCours'
import { BadgeStatut } from '../competition/BadgeStatut'
import { GestionTournois } from '../tournois/Tournois'

// Les vues publiques d'un tournoi. Fermé (pas d'ouverture prévue ici) : l'écran de salle (E07US004)
// n'est pas un onglet du tout, c'est un **poste**.
//
// « Tableaux » (E07US005) est arrivé le 04/08/2026, exactement comme cette liste l'annonçait — un
// onglet de plus, ni réservé ni anticipé. Il se place **après** « Affectations » et avant les
// classements : l'ordre suit la journée de l'archer (qui je suis, où je tire, contre qui, qui a
// gagné), pas la structure du logiciel.
//
// ⚠️ **« Tableaux » est devenu « En cours » en E05US031** (ADR-0089), et ce n'est pas un renommage
// d'étiquette : l'onglet ne montre plus un arbre de duels mais **la phase qui se joue**, quel qu'en
// soit le format — poule, ronde de système suisse, manche de Big Shoot Off, arbre. Les trois
// premiers étaient jouables depuis des semaines sans qu'aucun n'atteigne jamais l'appli publique.
// Un onglet par format aurait fait deviner au spectateur lequel regarder et en aurait laissé la
// moitié vides ; « Tableaux » élargi aurait menti, `Tableau` désignant au glossaire un arbre à
// élimination (règle 3). Sa place dans la liste ne bouge pas — l'ordre suit toujours la journée de
// l'archer.
//
// « Affectations » (E07US008) sert deux publics d'un coup : l'archer qui cherche sa butte et la
// **table de l'organisation**, qui vérifie le pas de tir — c'est la même lecture, et le CA n'en
// demandait qu'une. On la place après le suivi (« mes archers » reste la porte d'entrée, `D-09`).
//
// « Palmarès » (E06US004) est le **classement final** — podiums en tête. Il vient après
// « Classement » (celui de la qualification) et non à sa place : les deux se consultent, et à des
// moments différents de la journée. On les distingue par le libellé plutôt que de renommer l'un des
// deux, qui ferait chercher longtemps celui qu'on connaissait.
type Vue = 'suivi' | 'affectations' | 'en_cours' | 'classement' | 'palmares' | 'plan'

const VUES: { id: Vue; libelle: string }[] = [
  { id: 'suivi', libelle: 'Suivi' },
  { id: 'affectations', libelle: 'Affectations' },
  { id: 'en_cours', libelle: 'En cours' },
  { id: 'classement', libelle: 'Classement' },
  { id: 'palmares', libelle: 'Palmarès' },
  { id: 'plan', libelle: 'Plan de cibles' },
]

export function AccueilPublic() {
  const [selection, setSelection] = useState<Tournoi | null>(null)

  return (
    <div className="app__contenu--colonnes">
      {/* Porte **Public** (E00US017, ADR-0042) : liste en lecture seule. `GestionTournois` ne porte
          plus le login admin (parti dans `CoquilleAdmin`, porte Admin) — le public ne peut pas
          escalader. Le scoreur et la tablette ont désormais leurs propres portes ; plus proposés ici. */}
      <GestionTournois selectionneId={selection?.id ?? null} onChoisi={setSelection} />

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
  // ⚠️ Sélecteur **stable** : on lit la référence brute `s.suivis`, jamais un tableau dérivé — un
  // `getSnapshot` instable boucle indéfiniment en Zustand v5 / React 19. C'est le correctif que
  // `VueSuivi` et `VueTableaux` portent déjà sur ce même store ; il se réintroduit à chaque nouveau
  // lecteur, d'où la répétition de l'avertissement.
  const tousLesSuivis = useSessionSuivisStore((s) => s.suivis)
  const suivisIci = useMemo(
    () => suivisDuTournoi(tousLesSuivis, tournoi.id),
    [tousLesSuivis, tournoi.id],
  )
  const centrerSurSuivis = useSessionSuivisStore((s) => s.centrerSurSuivis)
  const centrer = useSessionSuivisStore((s) => s.centrer)
  const mode = modeEffectif(centrerSurSuivis, suivisIci)

  // Si l'on suit déjà quelqu'un sur ce tournoi, on ouvre directement sur « Suivi » — l'appli tombe sur
  // ses archers sans détour (D-09). Sinon, le classement reste la vue d'accueil par défaut.
  const [vue, setVue] = useState<Vue>(suivisIci.length > 0 ? 'suivi' : 'classement')

  return (
    <section className="carte carte--large">
      <button type="button" className="lien" onClick={onFermer}>
        ← Tous les tournois
      </button>
      <h2 className="carte__titre">
        {tournoi.nom} <BadgeStatut statut={tournoi.statut} />
      </h2>

      {/* L'interrupteur ne s'affiche que s'il y a quelque chose à centrer : proposer « mes archers »
          à qui n'en suit aucun offrirait un bouton dont le seul effet serait de vider l'écran. Le
          geste manquant se fait dans l'onglet « Suivi », et c'est là qu'on l'apprend.
          ⚠️ **Masqué sur l'onglet « Suivi »** (correctif de revue) : cette vue *est* déjà « mes
          archers », elle ne lit donc pas le mode. Or « Suivi » est l'onglet d'atterrissage dès
          qu'on suit quelqu'un — le tout premier geste d'un spectateur était d'actionner un réglage
          qui ne changeait rien sous ses yeux, ce qui fait douter du reste de l'écran. */}
      {suivisIci.length > 0 && vue !== 'suivi' && (
        <BasculeAffichage
          mode={mode}
          nbSuivis={suivisIci.length}
          onChanger={(m) => centrer(m === 'suivis')}
        />
      )}

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

      {/* Le mode descend en **prop explicite**, jamais lu depuis le store par les vues elles-mêmes :
          `VueClassement`, `VueTableaux` et `VueAffectations` servent aussi la coquille admin et
          l'écran de salle, où ce filtre n'a rien à faire (même précaution que `filtrable` et
          `interactif`). */}
      {vue === 'suivi' ? (
        <VueSuivi tournoiId={tournoi.id} />
      ) : vue === 'affectations' ? (
        <VueAffectations tournoiId={tournoi.id} mode={mode} suivis={suivisIci} />
      ) : vue === 'en_cours' ? (
        <VueEnCours tournoiId={tournoi.id} mode={mode} suivis={suivisIci} />
      ) : vue === 'classement' ? (
        <VueClassement
          tournoiId={tournoi.id}
          admin={false}
          mode={mode}
          suivis={suivisIci}
          detailFleches
        />
      ) : vue === 'palmares' ? (
        <VuePalmares tournoiId={tournoi.id} mode={mode} suivis={suivisIci} />
      ) : (
        <PlanCiblesPublic tournoiId={tournoi.id} mode={mode} suivis={suivisIci} />
      )}
    </section>
  )
}

/** L'interrupteur « mes archers / tout » (E16US004) — **un seul pour tout l'onglet public**.
 *
 * Le commanditaire suit plusieurs archers et veut lire chaque écran des deux façons (P03 : *« il me
 * faut les 2 »* ; P05 : *« une bascule pour suivre tous les tableaux du tournoi ou uniquement centré
 * sur les archers que l'on choisit de suivre »*). Un interrupteur **par vue** aurait obligé à le
 * redire à chaque onglet — arbitrage du cadrage, 08/08/2026.
 *
 * Même grammaire visuelle que les onglets (pilules, `.onglet--actif` en aplat de marque) mais
 * `role="group"` et `aria-pressed` : ce ne sont pas des destinations, c'est un choix d'affichage.
 * Le compte est écrit en toutes lettres — « Mes archers (3) » dit combien on va voir avant de
 * cliquer, ce qui évite d'attribuer à une panne un écran soudain court.
 */
function BasculeAffichage({
  mode,
  nbSuivis,
  onChanger,
}: {
  mode: ModeAffichage
  nbSuivis: number
  onChanger: (mode: ModeAffichage) => void
}) {
  return (
    <div className="onglets bascule-suivis" role="group" aria-label="Affichage">
      <span className="bascule-suivis__libelle">Affichage</span>
      <button
        type="button"
        className={mode === 'tout' ? 'onglet onglet--actif' : 'onglet'}
        aria-pressed={mode === 'tout'}
        onClick={() => onChanger('tout')}
      >
        Tout le tournoi
      </button>
      <button
        type="button"
        className={mode === 'suivis' ? 'onglet onglet--actif' : 'onglet'}
        aria-pressed={mode === 'suivis'}
        onClick={() => onChanger('suivis')}
      >
        Mes archers ({nbSuivis})
      </button>
    </div>
  )
}
