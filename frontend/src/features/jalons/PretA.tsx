// Coquille **commune** des écrans « prêt à… » (E16US012, ADR-0096).
//
// Quatre écrans — prêt à démarrer / terminer / archiver / exporter — répondent à la **même**
// question (« puis-je passer à l'étape suivante, et sinon qu'est-ce qui manque ? ») et doivent donc
// se lire pareil. Le commanditaire a tranché le 23/08/2026 : **une forme unique paramétrée**, et
// non quatre écrans jumeaux. C'est ce composant qui la porte.
//
// **Présentationnel, pas connecté.** Il reçoit ce qu'il affiche ; il ne choisit pas d'où ça vient.
// C'est délibéré : `Prêt à démarrer ?` lit le nouvel endpoint `/jalons/demarrer`, tandis que
// `Prêt à terminer ?` continue de lire `/completude` — la **même** réponse, dont il a en plus
// besoin du volet administratif pour chiffrer sa confirmation (les impayés, cf. `Completude.tsx`).
// Le brancher de force sur `/jalons/terminer` aurait ajouté un **second poll de 5 s** sur chaque
// tablette pour une réponse identique. Que les deux ne puissent pas diverger n'est pas laissé à la
// vigilance : `test_jalons_api.py` épingle `/jalons/terminer` ≡ `/completude.sportif`.
//
// ⚠️ **Aucun bouton n'est jamais désactivé ici**, ni par `pret`, ni par `bloquant`. E05US021 avait
// déjà tranché pour le démarrage : l'avertissement se lit avant le clic, le refus remonte du
// serveur (`D-15`). Un front qui grise le bouton se met à décider d'une garde — et devient la
// seconde source que le CA interdit.

// ⚠️ `DETTE-083` — ces deux imports **ferment un cycle** : `completude/Completude.tsx` importe cette
// coquille, qui réimporte `completude`. Réutiliser le rendu plutôt que le dupliquer est le bon geste
// (`DETTE-065`), mais la coquille de la famille dépend ainsi d'un de ses membres. Résorption :
// remonter `SectionCompletude`, `LigneCompletude`, `afficheEtat` et `detailLigne` dans `shared/` —
// rangement transverse, donc US dédiée (règle 16), à traiter avec les autres cycles du dépôt.
import type { ReactNode } from 'react'
import type { LigneCompletude } from '../completude/api'
import { SectionCompletude } from '../completude/SectionCompletude'
import { verdict } from './presentation'

export function PretA({
  question,
  intro,
  titreSection,
  lignes,
  pret,
  bloquant,
  moment,
  detail = null,
  complet,
  chargement = false,
  erreur = null,
  children,
}: {
  question: string
  intro: ReactNode
  titreSection: string
  // `null` tant que la réponse n'est pas là : l'écran dit qu'il n'a pas pu vérifier, il n'invente
  // pas une liste vide (qui se lirait « rien ne manque »).
  lignes: LigneCompletude[] | null
  pret: boolean
  bloquant: boolean
  // *Quand* le refus tombe — « au démarrage ». Cf. `verdict` : sans ce mot, la phrase se lit comme
  // un refus immédiat, que l'action offerte dément parfois.
  moment?: string
  // La **cause chiffrée** du blocage, telle que le serveur la rend. Jamais rédigée ici : c'est la
  // phrase du refus lui-même, pour que l'avertissement ne dise pas autre chose que le 409.
  detail?: string | null
  // Le badge « complet / incomplet » de la section. **Distinct de `pret`** : `pret` dit *si
  // l'action passera*, ce badge dit *si la liste est finie*, et les deux se séparent dès qu'une
  // ligne manque sans bloquer (le déroulé non composé). Les confondre affichait « Avant de démarrer
  // — complet » au-dessus d'une ligne « En attente » (relevé en revue par trois axes). Omis, le
  // badge ne s'affiche pas : c'est le défaut du membre *démarrer*, dont le verdict en tête répond
  // déjà à la question binaire.
  complet?: boolean
  chargement?: boolean
  erreur?: ReactNode
  // Le pied de l'écran : ce que l'action implique, puis l'action elle-même. Hors de la garde
  // `lignes`, volontairement — cf. `Completude.tsx` : un manque d'information ne doit jamais
  // verrouiller l'action.
  children?: ReactNode
}) {
  const { ton, texte } = verdict(pret, bloquant, moment)
  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">{question}</h2>
      <p className="completude__intro">{intro}</p>

      {chargement && <p className="carte__etat">Chargement…</p>}
      {erreur}

      {lignes !== null && (
        <>
          {/* Le verdict d'abord, la liste ensuite : la question est binaire, la liste dit
              *pourquoi*. `role="status"` parce qu'il change sous le poll sans action de
              l'utilisateur. La couleur n'est jamais seule (pastille + texte, `DV-03`). */}
          <p className={`completude__verdict completude__verdict--${ton}`} role="status">
            <span className="indicateur__pastille" aria-hidden="true" />
            {texte}
          </p>
          {/* La cause, sous le verdict : « 8 archer(s) inscrit(s) sur le départ 2 pour 34 requis ».
              `D-16` / `P-4` — une alerte qui ne chiffre pas son impact est un clic de plus, pas une
              protection ; sur un tournoi à deux créneaux, « 8/34 » seul semble contredire le total
              affiché ailleurs (relevé en revue, axe D). */}
          {detail !== null && <p className="completude__implication">{detail}</p>}
          <SectionCompletude titre={titreSection} complet={complet} lignes={lignes} />
        </>
      )}

      {children}
    </section>
  )
}
