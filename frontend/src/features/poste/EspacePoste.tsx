// Espace poste (E04US001 ; élargi E07US004) — l'écran d'un appareil rattaché à un lieu.
//
// Le bénévole **scanne le QR** de sa cible (l'URL pré-remplit le code → rattachement automatique) ou
// **tape le code** imprimé en secours. Une session de poste s'ouvre alors, persistée localement pour
// survivre à la fermeture de l'onglet, à une veille, à un redémarrage — la tablette **retrouve sa
// cible sans rien redemander** (D-13). Le poste peut choisir sa **luminosité** (D-26), qui revient
// toute seule. La **saisie** des scores relève d'E04US002 ; ici, on rattache et on détache.
//
// **Depuis E07US004, deux natures de poste passent par ici.** Le CA de l'écran de salle est
// explicite : *« c'est un poste, comme une tablette de cible — même mécanisme de jeton »*. Un même
// code, un même endpoint, un même écran de rattachement ; c'est le `type` rendu par le serveur qui
// aiguille ensuite vers la **saisie** (cible) ou l'**affichage plein écran** (écran de salle).
// Dupliquer le formulaire dans un monde « salle » aurait recopié le QR, le heartbeat, la
// persistance et la révocation — pour n'en changer que la dernière ligne.
//
// ⚠️ L'adresse de ce monde reste `/cible` (routeur maison, `Monde = 'tablette'`), y compris pour un
// écran de salle. C'est une imprécision **assumée** : personne ne tape cette adresse (on arrive par
// QR ou par le menu), et renommer le monde toucherait le routeur, ses tests et la résolution de
// rôle pour un gain purement cosmétique.

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

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">
        {vocation === 'salle' ? 'Écran de salle' : 'Poste de saisie'}
      </h2>
      {jeton !== null && poste !== null ? (
        <PosteDeCible poste={poste} />
      ) : (
        <FormulaireRattachement codeInitial={codeInitial} vocation={vocation} />
      )}
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
      {/* **Le code domine, le QR est le secours** — retour maquettes du 04/08/2026 (S01), variante B :
          *« je ne suis pas sûr que les caméras soient toujours accessibles »*. L'ordre des deux
          phrases était l'inverse ; sur un parc dont on ne sait pas si les appareils photo marchent,
          annoncer le QR en premier envoie le bénévole vers la voie la moins sûre. */}
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
        <button type="submit" disabled={rattacher.isPending || !entreeValide}>
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
