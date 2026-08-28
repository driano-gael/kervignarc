// L'onglet **« En cours »** — ce qui se joue maintenant, quel que soit le format (E05US031).
//
// **Un aiguilleur et non un onglet de plus** : les trois formats sans arbre étaient livrés jouables
// sans qu'un seul n'atteigne l'appli publique, et un onglet par format aurait fait deviner au
// spectateur lequel regarder. **« En cours » et non « Phases »** (ADR-0089) : `Tableau` désigne au
// glossaire un arbre (règle 3) et `Phase` demande un vocabulaire que le spectateur n'a pas.
// ⚠️ `# DETTE-031` **élargie** : une seule route de format montée à la fois, rien tant que l'onglet
// est fermé.

import { useState } from 'react'
import { nommerType } from '../../shared/phases/catalogue'
import { messageDeLecture } from '../../shared/api/etatDeLecture'
import { type ModeAffichage } from '../../shared/suivis/focus'
import { VueBigShootOffPublique } from '../big-shoot-off/VueBigShootOffPublique'
import { useDeparts } from '../departs/hooks'
import { BandeauDePause } from '../../shared/ui/BandeauDePause'
import { useAvancementPhases } from '../phases/hooks'
import { VuePoulesPublique } from '../poules/VuePoulesPublique'
import { departDeSalle } from '../salle/rotation'
import { VueCollinePublique } from '../colline/VueCollinePublique'
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
  // ⚠️ `# DETTE-071` — `GET /departs/{id}/phases` sert le `PhaseReponse` **entier** à un anonyme :
  // sources, effectif et réglages de format compris. Cet onglet est le consommateur **public** de
  // cette route, sur deux surfaces ouvertes (appli publique et écran de salle). Le hook rend le type
  // `Phase` complet — le front ne filtre rien, contrairement à ce que le registre affirmait avant
  // d'être corrigé en revue. Résorption : `E10US009` (DTO d'avancement étroit).
  const phases = useAvancementPhases(departId)
  const donnees = phases.data

  if (departs.isSuccess && (departs.data ?? []).length === 0) {
    return <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
  }
  // Les **données priment sur l'erreur** : React Query garde le `data` de la dernière lecture
  // réussie pendant un échec. Tester `isError` d'abord jetterait un déroulé encore exact au premier
  // clignotement réseau et laisserait l'écran projeté sur un message d'erreur ≥ 20 s.
  if (donnees === undefined) {
    // ⚠️ **L'erreur des départs compte autant que celle des phases** (correctif de revue, axe C1).
    // Si `useDeparts` échoue sans cache, `departId` reste `null`, `useAvancementPhases` est
    // désactivée, donc `phases.isError` vaut `false` : l'écran affichait « Chargement… »
    // **indéfiniment** au lieu de nommer la panne. Le défaut était hérité de `VueTableaux`, mais
    // reproduit dans un fichier neuf et sur toutes les surfaces de l'onglet.
    return <p className="carte__etat">{messageDeLecture(departs.isError ? departs : phases)}</p>
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

      {/* CA E05US034 — **la pause se voit**, et se distingue d'un simple délai. Un suffixe de
          titre en petits caractères se lit à un mètre, pas depuis les gradins ni sur l'écran
          projeté (E07US004) : un spectateur qui voit la salle immobile et un écran muet conclut
          à une **panne**. */}

      {/* ⚠️ **`interactif` discrimine les deux surfaces** (correctif de 2ᵉ passe) : un écran de
          salle dont le déroulé contient cette vue empilait deux bandeaux identiques — celui,
          permanent, de `MentionDePause`, et celui-ci. En 1,1 em sur un projecteur, le doublon
          n'est pas discret. */}
      {interactif && phase.statut === 'en_pause' && <BandeauDePause />}

      {/* ⚠️ `key={phase.id}` : **remonte** le composant de format à chaque changement de phase
          (correctif de revue, axe C1). Sans elle, React réconcilie en place quand le type est
          identique, et l'état local du format survit — sur un départ à deux phases suisse, on
          atterrissait sur « ronde 3 » de la nouvelle phase au lieu de sa ronde courante. Le geste
          ferme la classe entière du défaut pour les formats à venir. */}
      <Format
        key={phase.id}
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
 * ⚠️ **Un `switch` exhaustif et non une table** : il ne s'agit pas de données mais de **composants
 * aux props différentes**, qu'une table uniformiserait de force. ⚠️ **Le `default` ne rend jamais
 * une page blanche** : un type inconnu de ce bundle — serveur plus récent, appli restée ouverte
 * des heures — est **nommé** au lieu d'être ignoré, car un écran qui montre autre chose sans le
 * dire est indétectable devant une salle.
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
    // E05US027 : la branche de repli « pas encore jouable » qui vivait ici a fait son temps. Elle
    // avait été écrite en annonçant sa propre disparition ; c'est cette US-là.
    case 'colline':
      return (
        <VueCollinePublique
          tournoiId={tournoiId}
          phaseId={phase.id}
          interactif={interactif}
          mode={mode}
          suivis={suivis}
        />
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
