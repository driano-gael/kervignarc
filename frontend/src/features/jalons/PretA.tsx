// Coquille **commune** des écrans « prêt à… » (E16US012, ADR-0096).
//
// Quatre écrans répondent à la **même** question et doivent se lire pareil : le commanditaire a
// tranché le 23/08/2026 pour **une forme unique paramétrée**. **Présentationnel, pas connecté** —
// `Prêt à démarrer ?` lit `/jalons/demarrer`, `Prêt à terminer ?` continue de lire `/completude`
// dont il a besoin du volet administratif ; le brancher de force aurait ajouté un **second poll de
// 5 s** par tablette (`test_jalons_api.py` épingle l'équivalence). ⚠️ **Aucun bouton n'est jamais
// désactivé ici** : l'avertissement se lit avant le clic, le refus remonte du serveur (`D-15`).

// DETTE-083 — ⚠️ ces deux imports **ferment un cycle** : `completude/Completude.tsx` importe cette
// coquille, qui réimporte `completude`. Réutiliser le rendu plutôt que le dupliquer est le bon geste
// (`DETTE-065`), mais la coquille de la famille dépend ainsi d'un de ses membres. Résorption :
// remonter **`PretA` elle-même** dans `shared/`, avec ce qu'elle traîne (`SectionCompletude`, le type
// `LigneCompletude`, `afficheEtat`/`detailLigne`). ⚠️ Remonter la seule `SectionCompletude` — ce que
// ce marqueur a d'abord annoncé — **ne casse pas la composante** : `completude → jalons → accueil →
// completude` resterait. C'est l'arête `completude → jalons` qu'il faut couper. Rangement
// transverse, donc US dédiée (règle 16), à traiter avec les autres cycles du dépôt.
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
  questionPosee,
  chargement = false,
  erreur = null,
  children,
}: {
  question: string
  intro: ReactNode
  titreSection: string
  // `null` tant que la réponse n'est pas là : l'écran dit qu'il n'a pas pu vérifier, il n'invente
  // pas une liste vide (qui se lirait « rien ne manque »). ⚠️ Une liste **vide** est autre chose :
  // le serveur a répondu et il n'y a rien à préparer — on rend alors le `detail`, pas de verdict.
  //
  // ⚠️⚠️ **Cela vaut pour les membres dont la liste EST la préparation** — `démarrer` aujourd'hui.
  // `terminer` rend toujours son état sportif : c'est `questionPosee` qui y coupe le verdict, pas
  // la liste. Ne pas déduire « la question se pose » de `lignes.length > 0` (5ᵉ passe).
  lignes: LigneCompletude[] | null
  pret: boolean
  bloquant: boolean
  // *Quand* le refus tombe — « au démarrage ». Cf. `verdict` : sans ce mot, la phrase se lit comme
  // un refus immédiat, que l'action offerte dément parfois.
  moment?: string | null
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
  // La question « prêt à… ? » se pose-t-elle encore ? À `false`, **le verdict n'est pas rendu** —
  // la liste, elle, peut très bien l'être. ⚠️ **C'est la distinction qui manquait** : la piloter
  // par `lignes.length > 0` a fait dire « ce qui manque ci-dessous sera refusé » au-dessus de
  // lignes vertes (3ᵉ passe), puis, en vidant la liste pour l'éviter, a **supprimé un affichage
  // livré** — « Prêt à terminer ? » ne montrait plus où en est la qualification pendant la pause
  // déjeuner (4ᵉ passe). ⚠️ **Obligatoire, sans valeur par défaut** : elle en a eu une le temps
  // d'une passe, et c'est ce qui rendait le piège invisible. `tsc` force désormais chaque membre à
  // trancher.
  questionPosee: boolean
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

      {/* Le verdict d'abord, la liste ensuite : la question est binaire, la liste dit
          *pourquoi*. `role=status` parce qu'il change sous le poll sans action de
          l'utilisateur. La couleur n'est jamais seule (pastille + texte, `DV-03`). */}

      {/* ⚠️ Gardé par `questionPosee` **seul**, plus par `lignes.length` : `archiver` n'a que
          le statut pour garde, donc sur un tournoi terminé il répond « prêt » **sans aucune
          ligne** — l'écran n'aurait pas affiché son verdict au moment exact où la réponse est «
          oui » (7ᵉ passe, axe D). La section, elle, garde `lignes.length` : une liste vide n'a
          rien à montrer. */}
      {questionPosee && lignes !== null && (
        <p className={`completude__verdict completude__verdict--${ton}`} role="status">
          <span className="indicateur__pastille" aria-hidden="true" />
          {texte}
        </p>
      )}

      {lignes !== null && lignes.length > 0 && (
        <SectionCompletude titre={titreSection} complet={complet} lignes={lignes} />
      )}

      {/* La cause, hors de la garde sur la liste : elle porte aussi le cas « plus rien à préparer »,
          où il n'y a précisément aucune ligne à montrer. `D-16` / `P-4` — une alerte qui ne chiffre
          pas son impact est un clic de plus, pas une protection. */}
      {detail ? <p className="completude__implication">{detail}</p> : null}

      {children}
    </section>
  )
}
