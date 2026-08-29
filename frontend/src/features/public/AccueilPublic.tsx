// Consultation publique (E10US001 + E07US001) : sans session admin, la lecture reste ouverte à
// tous. Onglets entre les vues publiques d'un tournoi, aucune authentification, responsive mobile.
// Le live est automatique (React Query invalidé par la diffusion post-commit).
//
// Navigation par **état local**, pas de `react-router` : même arbitrage que la coquille admin
// (18/07/2026) — réseau local, pas de deep-link, la dépendance ne se justifie pas (règle 11).
// Extrait de `admin/CoquilleAdmin.tsx` en E07US001 : la zone publique est une surface à part
// entière, pas un repli enfoui dans le module d'administration.

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
import { HabillageIdentite, LogoDuTournoi } from '../identite/HabillageIdentite'
import { GestionTournois } from '../tournois/Tournois'

// Les vues publiques d'un tournoi. Fermé : l'écran de salle (E07US004) n'est pas un onglet, c'est
// un **poste**. L'ordre suit la journée de l'archer (qui je suis, où je tire, contre qui, qui a
// gagné), pas la structure du logiciel.
//
// ⚠️ **« Tableaux » est devenu « En cours » en E05US031** (ADR-0089), et ce n'est pas un renommage
// d'étiquette : l'onglet montre **la phase qui se joue**, quel qu'en soit le format. Un onglet par
// format aurait fait deviner au spectateur lequel regarder ; « Tableaux » élargi aurait menti,
// `Tableau` désignant au glossaire un arbre à élimination (règle 3).
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
      {/* ⚠️ Aucune fiche ne s'ouvre ici : sous la porte Public, `estAdmin` est faux et les
          contrôles d'écriture ne sont pas rendus. Les deux props sont **requises** depuis la revue
          d'E16US010 — c'est ce montage-là que leur optionalité laissait passer en silence. */}
      <GestionTournois
        selectionneId={selection?.id ?? null}
        onChoisi={setSelection}
        ouvrir={null}
        onOuvrir={() => {}}
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
    // ⚠️ **L'identité du tournoi habille l'appli publique** (E16US006, `D-27`) — et elle est posée
    // **ici**, sur les vues d'un tournoi choisi, plutôt qu'à la racine de la coquille : la liste des
    // tournois n'appartient à aucune édition, l'habiller aux couleurs de la première l'aurait fait
    // mentir. Changer de tournoi change donc d'identité, ce qui est exactement l'intention.
    <HabillageIdentite tournoiId={tournoi.id}>
      <section className="carte carte--large">
        <button type="button" className="lien" onClick={onFermer}>
          ← Tous les tournois
        </button>
        <h2 className="carte__titre">
          {/* Les deux marques, au titre du tournoi. Facultatives : rien ne s'affiche si rien n'a été
              déposé (questionnaire A05, « bien sûr cela reste optionnel »).
              `decoratif` parce qu'elles sont **dans** le titre, qui dit déjà le nom du tournoi. */}
          <LogoDuTournoi tournoiId={tournoi.id} emplacement="evenement" decoratif />
          <LogoDuTournoi tournoiId={tournoi.id} emplacement="club" decoratif />
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
    </HabillageIdentite>
  )
}

/** L'interrupteur « mes archers / tout » (E16US004) — **un seul pour tout l'onglet public**.
 *
 * Le commanditaire suit plusieurs archers et veut lire chaque écran des deux façons (P03, P05) ;
 * un interrupteur **par vue** aurait obligé à le redire à chaque onglet (arbitrage du 08/08/2026).
 * Même grammaire visuelle que les onglets, mais `role="group"` et `aria-pressed` : ce ne sont pas
 * des destinations, c'est un choix d'affichage. Le compte est écrit en toutes lettres, ce qui
 * évite d'attribuer à une panne un écran soudain court.
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
