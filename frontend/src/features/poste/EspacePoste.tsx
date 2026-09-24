// Espace poste (E04US001 ; élargi E07US004) — l'écran d'un appareil rattaché à un lieu.
//
// Le bénévole **scanne le QR** de sa cible ou **tape le code** imprimé en secours ; session
// persistée localement, la tablette **retrouve sa cible sans rien redemander** (D-13), et sa
// luminosité revient toute seule (D-26). **Deux natures de poste passent par ici** (E07US004 : «
// c'est un poste, même mécanisme de jeton ») — c'est le `type` rendu par le serveur qui aiguille
// vers la saisie ou l'affichage plein écran. ⚠️ L'adresse du monde reste `/cible` même pour un
// écran de salle : imprécision **assumée**, on arrive par QR ou par le menu.

import { useEffect, useRef, useState } from 'react'
import { EcranSalle } from '../salle/EcranSalle'
import { Saisie } from '../saisie/Saisie'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { PaveCode } from '../../shared/ui/PaveCode'
import { type PosteRattache, useSessionPosteStore } from '../../shared/stores/sessionPosteStore'
import type { Theme } from '../../shared/theme'
import { useDetacherPoste, useHeartbeatPoste, useRattacherPoste, useVerifierPoste } from './hooks'

// Ce que **cet appareil vient faire**, tel que l'adresse le dit (`/cible` ou `/salle`). Depuis le
// retour maquettes du 04/08/2026 (A00), les deux usages ont leur propre porte à l'écran de choix :
// la vocation ne change **rien à la mécanique** (même code, même jeton, même heartbeat) — elle
// change les **mots** de l'écran de rattachement, qui est le seul moment où l'appareil ne sait pas
// encore ce qu'il est. Une fois rattaché, la vérité vient du serveur (`poste.type`), pas d'ici.
export type Vocation = 'cible' | 'salle'

export function EspacePoste({
  codeInitial,
  vocation = 'cible',
}: {
  codeInitial: string | null
  vocation?: Vocation
}) {
  const jeton = useSessionPosteStore((s) => s.jeton)
  const poste = useSessionPosteStore((s) => s.poste)
  // Réouverture : dès qu'un jeton est présent, on vérifie qu'il vaut toujours (révocation → purge).
  useVerifierPoste(jeton !== null)
  // Signe de vie périodique tant que la session est active → « en ligne » dans la supervision.
  useHeartbeatPoste(jeton !== null)
  // Appelé **avant** tout retour anticipé (règles des hooks) : l'écran de salle en a besoin autant
  // que la cible depuis que S01 réclame de pouvoir décrocher un écran.
  const decrochage = useDetacherPoste()

  // Un **écran de salle** rattaché sort de la coquille « carte » : il doit remplir l'écran, sans
  // titre ni sélecteur de luminosité (« aucune interaction », CA). Le rattachement, lui, garde la
  // coquille — c'est un geste humain, fait de près, sur un appareil qu'on tient encore en main.
  if (jeton !== null && poste !== null && poste.type === 'ecran') {
    return (
      <EcranSalle
        libelle={poste.libelle}
        tournoiId={poste.tournoi_id}
        onDecrocher={decrochage.detacher}
      />
    )
  }

  // ⚠️ **Deux formes, pas une.** Le rattachement est une colonne étroite et centrée — planche S01,
  // verdict « un écran, une question » —, et c'est la forme qu'`E17US003` a déjà donnée à A01 pour
  // le même geste. Une fois rattaché, le même cadre porte la **grille de saisie**, qui veut au
  // contraire toute la largeur de la tablette (S02) : resserrer ici la rétrécirait aussi.
  if (jeton !== null && poste !== null) {
    return (
      <section className="carte carte--large">
        <PosteDeCible poste={poste} />
        <BasculeTheme />
      </section>
    )
  }

  return (
    <section className="carte rattachement">
      {/* L'écran **demande**, il ne se nomme pas : c'est le parti pris de la planche, pas une
          tournure. « Poste de saisie » disait au bénévole où il était, pas ce qu'on attend de lui. */}
      <h2 className="carte__titre rattachement__titre">
        {vocation === 'salle' ? 'Quel écran de salle ?' : 'Quelle cible ?'}
      </h2>
      <FormulaireRattachement codeInitial={codeInitial} vocation={vocation} />
      <BasculeTheme />
    </section>
  )
}

function FormulaireRattachement({
  codeInitial,
  vocation,
}: {
  codeInitial: string | null
  vocation: Vocation
}) {
  const [code, setCode] = useState(codeInitial ?? '')
  const rattacher = useRattacherPoste()
  const entreeValide = code.trim() !== ''
  const salle = vocation === 'salle'

  // Scan du QR : l'URL a pré-rempli un code → rattachement **automatique**, une seule fois.
  const autoFait = useRef(false)
  useEffect(() => {
    if (!autoFait.current && codeInitial !== null && codeInitial.trim() !== '') {
      autoFait.current = true
      rattacher.mutate(codeInitial)
    }
  }, [codeInitial, rattacher])

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!entreeValide) return
    rattacher.mutate(code)
  }

  return (
    <div>
      {/* **Le code domine, le QR est le secours** — questionnaire S01 du 04/08/2026 : *« je ne suis
          pas sûr que les caméras soient toujours accessibles »*. ⚠️ Ne pas citer la **lettre** du
          questionnaire (« variante B ») : ses lettres ne désignent plus les variantes de la planche,
          redessinée le lendemain — c'est la planche **A** qui porte ce choix. Relevé, `epics/EPIC-17`. */}
      <p className="carte__etat">
        {salle
          ? 'Entrez le code imprimé sur l’écran de salle pour y rattacher cet appareil.'
          : 'Entrez le code imprimé sur votre cible pour y rattacher cet appareil.'}
      </p>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <PaveCode
          code={code}
          onChange={setCode}
          libelle={salle ? 'Code de l’écran de salle' : 'Code de la cible'}
          desactive={rattacher.isPending}
        />
        <button
          type="submit"
          className="bouton--geant"
          disabled={rattacher.isPending || !entreeValide}
        >
          {salle ? 'Rattacher cet écran' : 'Rattacher cet appareil'}
        </button>
      </form>
      <p className="carte__etat">
        Le QR collé à côté du code fait la même chose, sans rien taper — si l’appareil photo répond.
      </p>
      <MessageErreur erreur={rattacher.error} />
    </div>
  )
}

function PosteDeCible({ poste }: { poste: PosteRattache }) {
  const { detacher, enCours, erreur } = useDetacherPoste()

  // `cible_index` est facultatif au type depuis E07US004 (un écran n'en a pas) ; ici il est garanti
  // par l'aiguillage sur `type` — la garde protège d'une réponse serveur incohérente plutôt que
  // d'afficher « cible null » à un bénévole.
  if (poste.cible_index === null) {
    return <p className="carte__etat">Ce poste n’est pas rattaché à une cible.</p>
  }

  return (
    <div>
      <Saisie tournoiId={poste.tournoi_id} cibleIndex={poste.cible_index} />
      <button type="button" className="lien saisie__detacher" disabled={enCours} onClick={detacher}>
        Détacher cet appareil
      </button>
      <MessageErreur erreur={erreur} />
    </div>
  )
}

// Luminosité du poste (D-26) : « Système » (suit `prefers-color-scheme`), « Clair » ou « Sombre »
// forcés. Le choix est persisté et revient tout seul à la réouverture (cf. `sessionPosteStore`).
//
// Tant que **rien** n'a été choisi, le thème appliqué est le **sombre de la charte** (`DV-02`) — pas
// « Système ». La bascule le dit : c'est « Sombre » qui apparaît actif, parce que c'est ce qui est à
// l'écran. Afficher « Système » actif par défaut serait le mensonge qui a masqué le défaut corrigé à
// la revue d'E17US001.
function BasculeTheme() {
  const theme = useSessionPosteStore((s) => s.theme)
  const definirTheme = useSessionPosteStore((s) => s.definirTheme)
  const options: { valeur: Theme; libelle: string }[] = [
    { valeur: 'systeme', libelle: 'Système' },
    { valeur: 'clair', libelle: 'Clair' },
    { valeur: 'sombre', libelle: 'Sombre' },
  ]

  return (
    <div className="bascule-theme" role="group" aria-label="Luminosité de ce poste">
      <span className="carte__soustitre">Luminosité</span>
      {options.map((o) => (
        <button
          key={o.libelle}
          type="button"
          className="lien"
          aria-pressed={(theme ?? 'sombre') === o.valeur}
          onClick={() => definirTheme(o.valeur)}
        >
          {o.libelle}
        </button>
      ))}
    </div>
  )
}
