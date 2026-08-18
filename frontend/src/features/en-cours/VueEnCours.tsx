// L'onglet **« En cours »** — ce qui se joue maintenant, quel que soit le format (E05US031,
// ADR-0089).
//
// **Pourquoi un aiguilleur et non un onglet de plus.** Le manque relevé au cadrage d'`E05US030`
// n'était pas « une vue publique du système suisse » mais celui des **trois** formats sans arbre :
// poules (E05US023), Big Shoot Off (E05US028) et suisse (E05US026) sont livrés jouables sans qu'un
// seul n'atteigne jamais l'application publique. Ajouter un onglet par format aurait fait deviner
// au spectateur lequel regarder, et laissé la moitié d'entre eux vides toute la journée.
//
// **Pourquoi « En cours » et non « Phases ».** `Tableau` désigne au glossaire un « arbre de matchs à
// élimination » : garder ce libellé sur une vue qui rend aussi une poule aurait été faux (règle 3).
// `Phase` était le mot juste du domaine, mais il demande au spectateur un vocabulaire qu'il n'a pas.
// « En cours » ne nomme aucun format, dit ce que l'écran fait, et reste vrai quand un dixième type
// de phase arrivera. Arbitrage du commanditaire, 18/08/2026.
//
// ⚠️ `# DETTE-031` **élargie par cette US** : selon le format de la phase affichée, cet onglet monte
// `/poules/etat/`, `/suisse/etat/` ou `/big-shoot-off/etat/` — trois routes qui **rejouent la phase
// entière** à chaque lecture, sur une surface publique donc en autant d'exemplaires qu'il y a de
// spectateurs. Deux bornes tiennent, et elles sont volontaires : une seule route est montée à la
// fois (celle du format courant), et **rien** n'est monté tant que l'onglet n'est pas ouvert — « En
// cours » n'est pas l'onglet d'atterrissage, contrairement au cas d'`E16US004`. Ce qui n'est pas
// borné est le pic de validation de fin de tour. Cf. `docs/dette.md`.
//
// ⚠️ **Avec l'historique, l'onglet n'est plus *strictement* « en cours »** — on peut remonter le
// déroulé du départ. Ce qui rend le nom honnête est l'**atterrissage** : la phase qui se joue est
// celle qu'on voit en arrivant, remonter est un geste volontaire.

import { useState } from 'react'
import { nommerType } from '../../shared/phases/catalogue'
import { type ModeAffichage } from '../../shared/suivis/focus'
import { VueBigShootOffPublique } from '../big-shoot-off/VueBigShootOffPublique'
import { useDeparts } from '../departs/hooks'
import { useAvancementPhases } from '../phases/hooks'
import { VuePoulesPublique } from '../poules/VuePoulesPublique'
import { departDeSalle } from '../salle/rotation'
import { VueSuissePublique } from '../suisse/VueSuissePublique'
import { VueTableaux } from '../tableaux/VueTableaux'
import { phaseAAtterrir, type PhaseLisible } from './presentation'

export function VueEnCours({
  tournoiId,
  interactif = true,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  /** `false` sur l'écran projeté : aucune interaction (CA E07US004), donc aucun choix de phase — il
   * montre **ce qui se joue**, et rien d'autre. */
  interactif?: boolean
  /** La bascule « mes archers / tout » de l'appli publique (ADR-0079), descendue telle quelle à
   * chaque format : l'interrupteur est unique pour tout l'onglet public, sans exception. */
  mode?: ModeAffichage
  /** Les archers suivis **sur ce tournoi**, descendus par l'appelant — jamais lus au store ici,
   * cette vue servant aussi l'écran de salle (règle posée par `VueTableaux`). */
  suivis?: number[]
}) {
  const [phaseChoisie, setPhaseChoisie] = useState<number | null>(null)
  // ⚠️ **Le déroulé appartient à un créneau** (ADR-0075, ADR-0076). Ni la salle ni l'appli publique
  // n'ont de sélecteur de départ : on prend le créneau **qu'on est en train de tirer**, par le même
  // helper pur que le classement, le plan de cibles et les tableaux.
  const departs = useDeparts(tournoiId)
  const departId = departDeSalle(departs.data ?? [])?.id ?? null
  const phases = useAvancementPhases(departId)
  const donnees = phases.data

  if (departs.isSuccess && (departs.data ?? []).length === 0) {
    return <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
  }
  // Les **données priment sur l'erreur** : React Query garde le `data` de la dernière lecture
  // réussie pendant un échec. Tester `isError` d'abord jetterait un déroulé encore exact au premier
  // clignotement réseau et laisserait l'écran projeté sur un message d'erreur ≥ 20 s.
  if (donnees === undefined) {
    return (
      <p className="carte__etat">
        {phases.isError ? 'Connexion momentanément perdue — mise à jour au retour.' : 'Chargement…'}
      </p>
    )
  }

  const courante = phaseAAtterrir(donnees)
  if (courante === null) {
    return <p className="carte__etat">Le déroulé de ce départ n’est pas encore composé.</p>
  }
  const phase =
    (interactif && phaseChoisie !== null
      ? donnees.find((p) => p.id === phaseChoisie)
      : undefined) ?? courante

  return (
    <div className="encours">
      {/* Le fil du déroulé : toutes les phases du départ, la courante ouverte d'entrée. N'apparaît
          que s'il y a un choix à faire — un départ à une seule phase n'a pas à afficher une barre
          d'un bouton. */}
      {interactif && donnees.length > 1 && (
        <nav className="encours__deroule" aria-label="Déroulé du départ">
          {[...donnees]
            .sort((a, b) => a.ordre - b.ordre)
            .map((p) => (
              <button
                key={p.id}
                type="button"
                className={p.id === phase.id ? 'onglet onglet--actif' : 'onglet'}
                onClick={() => setPhaseChoisie(p.id)}
              >
                {p.ordre}. {nommerType(p.type)}
                {p.statut === 'terminee' ? ' ✓' : p.id === courante.id ? ' ▶' : ''}
              </button>
            ))}
        </nav>
      )}

      <h3 className="encours__phase">
        {phase.ordre}. {nommerType(phase.type)}
        {phase.statut === 'a_venir' && (
          <span className="encours__statut"> · pas encore lancée</span>
        )}
        {phase.statut === 'en_pause' && <span className="encours__statut"> · en pause</span>}
        {phase.statut === 'terminee' && <span className="encours__statut"> · terminée</span>}
      </h3>

      <Format
        phase={phase}
        tournoiId={tournoiId}
        interactif={interactif}
        mode={mode}
        suivis={suivis}
      />
    </div>
  )
}

/** L'aiguillage proprement dit : un type de phase, une vue.
 *
 * ⚠️ **Un `switch` exhaustif et non une table**, à la différence des libellés de
 * `shared/phases/catalogue.ts`. La raison est qu'il ne s'agit pas de données mais de **composants
 * aux props différentes** : `VueTableaux` prend un `tournoiId` et résout son créneau seule,
 * `VuePoulesPublique` prend un `phaseId`. Une table les uniformiserait de force, et le premier
 * format qui demanderait une prop de plus la ferait éclater.
 *
 * ⚠️ **Le `default` ne rend jamais une page blanche.** Un type inconnu de ce bundle — serveur plus
 * récent, appli publique restée ouverte des heures sur un téléphone — est **nommé** au lieu d'être
 * ignoré. Même parti que `VueDeSalle` (`features/salle/EcranSalle.tsx`) : un écran qui montre autre
 * chose que ce qui est demandé, sans le dire, est indétectable devant une salle.
 */
function Format({
  phase,
  tournoiId,
  interactif,
  mode,
  suivis,
}: {
  phase: PhaseLisible
  tournoiId: number
  interactif: boolean
  mode: ModeAffichage
  suivis: number[]
}) {
  switch (phase.type) {
    case 'elimination_directe':
    case 'placement':
      // L'arbre est rendu par la vue livrée en E07US005, à qui l'on **impose** la phase : sans cela
      // elle choisirait la sienne, et le fil du déroulé ci-dessus mentirait dès qu'un départ porte
      // deux tableaux.
      return (
        <VueTableaux
          tournoiId={tournoiId}
          phaseId={phase.id}
          interactif={interactif}
          mode={mode}
          suivis={suivis}
        />
      )
    case 'poules':
      return (
        <VuePoulesPublique tournoiId={tournoiId} phaseId={phase.id} mode={mode} suivis={suivis} />
      )
    case 'suisse':
      return (
        <VueSuissePublique
          tournoiId={tournoiId}
          phaseId={phase.id}
          interactif={interactif}
          mode={mode}
          suivis={suivis}
        />
      )
    case 'big_shoot_off':
      return (
        <VueBigShootOffPublique
          tournoiId={tournoiId}
          phaseId={phase.id}
          mode={mode}
          suivis={suivis}
        />
      )
    case 'qualification':
      // Pas de rencontre à montrer : une qualification est un tir au cumul, et son résultat *est*
      // le classement. On **renvoie** plutôt que de rendre une liste vide — et « Classement » nomme
      // aussi bien l'onglet public que la vue de salle, donc la phrase vaut sur les deux surfaces.
      return (
        <p className="carte__etat">
          Tir de qualification : il n’y a pas de rencontre à suivre. Le résultat se lit sur «
          Classement ».
        </p>
      )
    case 'echauffement':
      return (
        <p className="carte__etat">
          Échauffement : ce tir ne compte pas et ne produit aucun classement.
        </p>
      )
    case 'barrage':
      return (
        <p className="carte__etat">
          Barrage de départage : le détail se lit sur l’écran d’organisation.
        </p>
      )
    case 'colline':
      // Le moteur ne sait pas encore jouer la colline (E05US027 reste à livrer). Le dire vaut mieux
      // que de laisser croire à une panne — et cette branche disparaîtra avec l'US en question.
      return (
        <p className="carte__etat">
          Ce format ne s’affiche pas encore ici — il n’est pas jouable dans l’outil pour l’instant.
        </p>
      )
    default: {
      // ⚠️ **Double garde, et les deux servent.** L'affectation à `never` rend **non compilable**
      // l'ajout d'un type à `TypePhase` sans branche ici — même exigence d'exhaustivité que les
      // `Record<TypePhase, …>` de `shared/phases/catalogue.ts`, et c'est ce qui remplace la table
      // « types dessinés » qu'une première rédaction avait posée en double. Le rendu, lui, couvre
      // le cas que le compilateur ne peut pas voir : un **serveur plus récent** que ce bundle,
      // l'appli publique restant ouverte des heures sur un téléphone.
      const inconnu: never = phase.type
      return (
        <p className="carte__etat">
          Le format « {nommerType(inconnu)} » n’a pas de rendu dans cette version de l’application.
        </p>
      )
    }
  }
}
