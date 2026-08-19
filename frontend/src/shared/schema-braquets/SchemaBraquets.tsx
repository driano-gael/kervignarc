// Le **schéma à braquets** — un seul composant de dessin, trois surfaces (E07US004, ADR-0064).
//
// C'est la décision de conception centrale du CA d'E07US004, et elle mérite d'être justifiée ici
// plutôt que dans une story qu'on ne lit pas en codant :
//
// | Surface                     | Écran            | Interaction | Habillage             |
// |-----------------------------|------------------|-------------|-----------------------|
// | Atelier — composer          | PC               | on compose  | outil (jamais d'identité, `D-27`) |
// | Pilotage — suivre           | PC               | oui         | outil                 |
// | Salle — projeter            | ≥ 1920 px, de loin | **aucune** | identité du tournoi (`D-27`, `DV-08`) |
//
// Le dessiner pour une seule condamnerait les deux autres : les contraintes sont **opposées**.
// D'où trois props de variation — et **aucune** variation de géométrie : `geometrie.ts` produit le
// même `Plan` partout, parce que le CA dit « le **même** schéma ». C'est le `viewBox` du SVG qui met
// le dessin à l'échelle, texte compris — un écran de salle affiche donc *le dessin de l'atelier*,
// simplement plus gros, et non un cousin qu'il faudrait réapprendre à lire.
//
// Le calque d'`avancement` (E07US004) est **superposé**, jamais fondu dans les blocs : c'est ce qui
// garantit qu'un bloc se dessine identiquement avec ou sans réalité par-dessus.

import { useMemo } from 'react'

import { LIBELLE_TYPE } from '../phases/catalogue'
import { disposer, type Arete, type Noeud } from './geometrie'
import { LIBELLE_STATUT, type AvancementBloc, type Bloc } from './modele'

/** Comment le SVG occupe la place qu'on lui donne.
 *
 * `fixe` : dimensions en pixels, le conteneur défile — l'atelier et le pilotage, où l'on veut lire
 * les chiffres à taille de lecture confortable et faire défiler un long déroulé.
 * `ajustee` : largeur 100 %, le dessin **remplit** l'écran — la salle, où personne ne peut faire
 * défiler et où plus c'est grand, mieux ça se lit de loin. */
export type Taille = 'fixe' | 'ajustee'

/** Registre visuel : `outil` (neutre, `D-27`) ou `identite` (les couleurs du tournoi, `DV-08`). */
export type Habillage = 'outil' | 'identite'

export interface SchemaBraquetsProps {
  blocs: readonly Bloc[]
  /** Le calque de réalité, apparié aux blocs par `ordre`. Absent = on regarde un format, pas une
   * édition en cours (l'atelier). */
  avancement?: readonly AvancementBloc[]
  taille?: Taille
  habillage?: Habillage
  /** Texte du cas vide — il diffère selon la surface (« ajoutez une phase » n'a aucun sens en
   * salle, où personne ne peut rien ajouter). */
  messageVide?: string
}

export function SchemaBraquets({
  blocs,
  avancement,
  taille = 'fixe',
  habillage = 'outil',
  messageVide = 'Aucune phase à afficher pour le moment.',
}: SchemaBraquetsProps) {
  const plan = useMemo(() => disposer(blocs), [blocs])
  // Indexé par **position**, pas par `ordre` : deux étapes de même ordre sont un brouillon licite
  // (anomalie bloquante, mais enregistrable), et une `Map` par ordre en perdrait une.
  const tries = useMemo(() => [...blocs].sort((a, b) => a.ordre - b.ordre), [blocs])
  const parOrdre = useMemo(() => new Map((avancement ?? []).map((a) => [a.ordre, a])), [avancement])

  if (blocs.length === 0) {
    return (
      <p className="carte__etat" role="note">
        {messageVide}
      </p>
    )
  }

  const ajustee = taille === 'ajustee'
  return (
    <div className={`schema-braquets schema-braquets--${habillage}`}>
      <svg
        viewBox={`0 0 ${plan.largeur} ${plan.hauteur}`}
        // En `ajustee`, on laisse le SVG se dimensionner par CSS (100 % de large, hauteur
        // proportionnelle) : c'est le viewBox qui agrandit tout, y compris les textes.
        {...(ajustee ? {} : { width: plan.largeur, height: plan.hauteur })}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Schéma du déroulé, une case par phase et une flèche par prélèvement"
      >
        <defs>
          <marker
            id="schema-braquets-pointe"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="4"
            orient="auto"
          >
            <path d="M 0 0 L 8 4 L 0 8 z" fill="var(--brand-text)" />
          </marker>
        </defs>
        {plan.aretes.map((arete) => (
          <FlecheDuSchema key={arete.cle} arete={arete} />
        ))}
        {plan.noeuds.map((noeud) => {
          const bloc = tries[noeud.index]
          return bloc === undefined ? null : (
            <BlocDuSchema
              key={noeud.index}
              noeud={noeud}
              bloc={bloc}
              avancement={parOrdre.get(bloc.ordre)}
            />
          )
        })}
      </svg>
    </div>
  )
}

function FlecheDuSchema({ arete }: { arete: Arete }) {
  return (
    <g className="schema-braquets__fleche">
      <path d={arete.trace} markerEnd="url(#schema-braquets-pointe)" />
      <text x={arete.etiquette_x} y={arete.etiquette_y} textAnchor="middle">
        {arete.effectif === null ? '?' : arete.effectif}
      </text>
    </g>
  )
}

function BlocDuSchema({
  noeud,
  bloc,
  avancement,
}: {
  noeud: Noeud
  bloc: Bloc
  avancement?: AvancementBloc
}) {
  const anomalies = bloc.anomalies ?? []
  const bloquant = anomalies.some((a) => a.gravite === 'bloquante')
  const alerte = anomalies.length > 0
  // Le statut prime sur l'anomalie quand on suit une édition : un tournoi en cours n'est plus un
  // brouillon qu'on diagnostique, et l'organisateur cherche « où on en est », pas « ce qui cloche ».
  const modificateur = avancement
    ? ` schema-braquets__bloc--${avancement.statut}`
    : bloquant
      ? ' schema-braquets__bloc--bloquant'
      : alerte
        ? ' schema-braquets__bloc--alerte'
        : ''
  return (
    <g
      className={`schema-braquets__bloc${modificateur}`}
      transform={`translate(${noeud.x} ${noeud.y})`}
    >
      <rect width={noeud.largeur} height={noeud.hauteur} rx="10" />
      <text className="schema-braquets__bloc-titre" x="12" y="24">
        {bloc.ordre}. {LIBELLE_TYPE[bloc.type]}
      </text>
      {avancement === undefined ? null : (
        <text
          className="schema-braquets__bloc-statut"
          x={noeud.largeur - 12}
          y="24"
          textAnchor="end"
        >
          {LIBELLE_STATUT[avancement.statut]}
        </text>
      )}
      {/* Question 1 du CA : qui est là — combien, et quelle tranche de rangs. */}
      <text className="schema-braquets__bloc-ligne" x="12" y="46">
        {bloc.effectif === null ? 'effectif inconnu' : `${bloc.effectif} archers`}
        {bloc.tranche === null ? '' : ` · rangs ${bloc.tranche[0]}–${bloc.tranche[1]}`}
      </text>
      {/* Question 2 : ce qu'on leur demande — ou, en suivi, où en sont les duels. */}
      <text className="schema-braquets__bloc-ligne" x="12" y="64">
        {avancement !== undefined && avancement.duels_attendus > 0
          ? `${avancement.duels_joues} / ${avancement.duels_attendus} duels joués`
          : bloc.nb_volees === null
            ? bloc.type === 'qualification'
              ? 'barème à définir'
              : 'duels'
            : `${bloc.nb_volees} volées de ${bloc.nb_fleches_par_volee}`}
      </text>
      {/* Question 4, cas des formats **sans braquet** (E05US032) : la phase avance par tours mais
          n'attribue pas de rangs au fil de l'eau, donc il n'y a aucune ligne de braquet où loger le
          tour courant. On l'annonce alors sur sa propre ligne, dans le mot de la salle servi par le
          backend — « Ronde 3 », « Tour 2 », « Manche 2 ».

          ⚠️ **Ici et pas seulement dans l'en-tête du suivi** : l'en-tête ne parle que de la phase
          `ordre_courant`, alors que le CA dit « **chaque** phase démarrée ». Et c'est ce composant,
          pas l'en-tête, que monte l'écran de salle — la surface que l'US invoque. Sans cette ligne,
          l'écran projeté continuait de ne rien dire hors tableau. Arbitrage du commanditaire rendu
          en revue, sur une divergence `stories/` ↔ `docs/fonctionnel/` relevée par l'axe C1. */}
      {bloc.tours.length === 0 && avancement?.libelle_tour_courant != null && (
        <text
          className="schema-braquets__bloc-braquet schema-braquets__bloc-braquet--courant"
          x="12"
          y="88"
        >
          ▶ {avancement.libelle_tour_courant}
        </text>
      )}
      {/* Question 4 : combien de tours — et la Règle R, tour par tour. En suivi, chaque braquet
          porte son propre remplissage, et celui qui tourne est mis en évidence. */}
      {bloc.tours.map((tour, index) => {
        const reel = avancement?.tours.find((t) => t.tour === tour.tour)
        const courant = avancement?.tour_courant === tour.tour
        return (
          <text
            className={`schema-braquets__bloc-braquet${courant ? ' schema-braquets__bloc-braquet--courant' : ''}`}
            key={tour.tour}
            x="12"
            y={88 + index * 18}
          >
            {courant ? '▶ ' : ''}T{tour.tour} ·{' '}
            {reel === undefined
              ? `${tour.duels} duel(s)`
              : `${reel.duels_joues}/${reel.duels_attendus} duels`}{' '}
            → perdants rangs {tour.plage_perdants[0]}–{tour.plage_perdants[1]}
          </text>
        )
      })}
      {/* Question 3 : où ils vont après — ce qui reste s'arrête ici. */}
      <text className="schema-braquets__bloc-ligne" x="12" y={noeud.hauteur - 14}>
        {/* `sans_suite` est **signé** depuis la revue d'E01US024 : un négatif dit qu'on prélève
            plus d'archers qu'il n'y en a. L'afficher tel quel donnait « -1 au classement final »,
            un fait faux à côté de l'avertissement juste. */}
        {bloc.sans_suite === null
          ? 'suite inconnue'
          : bloc.sans_suite < 0
            ? `${-bloc.sans_suite} pris deux fois !`
            : bloc.sans_suite === 0
              ? 'tous repartent en phase suivante'
              : `${bloc.sans_suite} au classement final`}
      </text>
    </g>
  )
}
