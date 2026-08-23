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
  chargement?: boolean
  erreur?: ReactNode
  // Le pied de l'écran : ce que l'action implique, puis l'action elle-même. Hors de la garde
  // `lignes`, volontairement — cf. `Completude.tsx` : un manque d'information ne doit jamais
  // verrouiller l'action.
  children?: ReactNode
}) {
  const { ton, texte } = verdict(pret, bloquant)
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
          <SectionCompletude titre={titreSection} complet={pret} lignes={lignes} />
        </>
      )}

      {children}
    </section>
  )
}
