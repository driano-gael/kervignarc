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
  // pas une liste vide (qui se lirait « rien ne manque »).
  //
  // ⚠️ Une liste **vide** est autre chose encore : le serveur a répondu, et il n'y a rien à
  // préparer — un tournoi déjà lancé, annulé, archivé. On ne rend alors ni verdict ni section, mais
  // on rend le `detail`, qui dit pourquoi. C'est ce qui dispense l'écran de redéduire la garde du
  // statut (2ᵉ passe de revue, axe D).
  //
  // ⚠️⚠️ **Cela vaut pour les membres dont la liste EST la préparation** — `démarrer` aujourd'hui.
  // Le membre `terminer` rend toujours son état sportif, à tout statut : c'est `questionPosee` qui
  // y coupe le verdict, pas la liste. Ne pas déduire « la question se pose » de `lignes.length > 0`
  // dans un écran neuf sans vérifier de quel côté tombe son membre (5ᵉ passe, quatre axes).
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
  // La question « prêt à… ? » se pose-t-elle encore ? À `false`, **le verdict n'est pas rendu** — la
  // liste, elle, peut très bien l'être.
  //
  // ⚠️ **C'est la distinction qui manquait**, et son absence a coûté deux défauts opposés. Piloter le
  // verdict par `lignes.length > 0` a d'abord fait dire « ce qui manque **ci-dessous** sera refusé »
  // au-dessus de lignes vertes (3ᵉ passe) ; puis, en vidant la liste pour l'éviter, a **supprimé un
  // affichage livré** — l'écran « Prêt à terminer ? » ne montrait plus où en est la qualification sur
  // un tournoi en pause, c'est-à-dire pendant la pause déjeuner du jour J (4ᵉ passe, axe C1). Le
  // verdict et la liste répondent à deux questions différentes : ils se gardent séparément.
  // ⚠️ **Obligatoire, sans valeur par défaut.** Elle en a eu une (`true`) le temps d'une passe, et
  // c'est ce qui rendait le piège invisible : un écran neuf qui l'oubliait obtenait un verdict rendu
  // sur un jalon dont la question ne se pose plus. `tsc` force désormais chaque membre à trancher —
  // une garde mécanique plutôt qu'un commentaire d'avertissement (6ᵉ passe, axes C1 et D).
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

      {/* Le verdict d'abord, la liste ensuite : la question est binaire, la liste dit *pourquoi*.
          `role="status"` parce qu'il change sous le poll sans action de l'utilisateur. La couleur
          n'est jamais seule (pastille + texte, `DV-03`).

          ⚠️ Gardé par `questionPosee` **seul** — plus par `lignes.length > 0`. Ce conjoint était le
          dernier endroit où la coquille déduisait de la liste ce que le champ porte, et il piégeait
          les membres à venir : `archiver` n'a que le **statut** pour garde, donc sur un tournoi
          terminé il répond `question_posee: true`, `pret: true` et **aucune ligne** — l'écran
          n'aurait pas affiché son verdict au moment exact où la réponse est « oui » (7ᵉ passe de
          revue, axe D). La section, elle, garde bien `lignes.length > 0` : une liste vide n'a rien
          à montrer. */}
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
