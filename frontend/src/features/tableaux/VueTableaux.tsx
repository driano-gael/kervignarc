// Vue publique des tableaux de duels (E07US005) — maquette **P05**.
//
// Un seul composant pour deux surfaces, comme les affectations (E07US008) et le schéma à braquets
// (E01US024) : l'appli publique (interactive) et l'**écran de salle** (projeté, `interactif=false`,
// aucune interaction — CA E07US004). Les dessiner séparément les ferait diverger sur la seule chose
// qui compte, l'appariement affiché.
//
// **Les deux partis pris de la maquette sont livrés, et l'ordre entre eux est le sien :**
//  - **A · « Mon chemin »**, *recommandé* — « l'archer est le sujet, la compétition est le
//    contexte » (`D-09`). C'est la vue par défaut **dès qu'on suit quelqu'un**, exactement comme
//    l'onglet « Suivi » est la porte d'entrée de l'appli publique ;
//  - **B · « Arbre complet »**, *nécessaire en second* — l'arbre en vraies branches ne tient pas
//    sur 360 px ; en **liste par tour**, si. C'est la concession mobile que la maquette assume, et
//    la seule lecture possible sur l'écran de salle (personne à suivre devant un projecteur).
//
// ⚠️ **Ce que la maquette proposait et qui n'est pas livré : les horaires prévisionnels** (« 1/4 ·
// MARTIN vs DURAND · 14 h 20 »). Arbitrage du 04/08/2026 : le domaine ne porte **aucun** horaire au
// grain de la phase ou du duel — seul le départ en a un (E02US010). Les afficher supposerait un
// moteur d'ordonnancement qui n'existe pas ; les inventer serait pire que les taire, puisque c'est
// précisément le risque que la maquette pointait (« au risque qu'ils glissent et qu'on vous le
// reproche »). La question reste ouverte au questionnaire P05.

import { useMemo, useState } from 'react'
import { nommerType } from '../../shared/phases/catalogue'
import { useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
import { useDeparts } from '../departs/hooks'
import { suivisDuTournoi, type ModeAffichage } from '../public/focus'
import { departDeSalle } from '../salle/rotation'
import type { DuelPublic, DuellistePublic, TableauPublic } from './api'
import { useTableaux } from './hooks'
import { cheminDeArcher, LIBELLE_STATUT, parTour } from './presentation'

type Lecture = 'chemin' | 'complet'

const nomComplet = (qui: DuellistePublic) => `${qui.prenom} ${qui.nom}`.trim()

export function VueTableaux({
  tournoiId,
  interactif = true,
  mode = 'tout',
}: {
  tournoiId: number
  interactif?: boolean
  /** La bascule « mes archers / tout » de l'appli publique (E16US004).
   *
   * ⚠️ **Elle remplace le sélecteur local « Mon chemin / Tableau complet »** que cette vue portait
   * depuis E07US005. Les deux disaient exactement la même chose ; les laisser coexister aurait
   * donné deux interrupteurs contradictoires sur le même écran — un spectateur en « Mes archers »
   * global voyant l'arbre entier parce qu'un second bouton, ailleurs, dit le contraire. Le CA P05
   * (*« une bascule pour suivre tous les tableaux du tournoi ou uniquement centré sur les archers
   * que l'on choisit de suivre »*) est désormais servi par l'interrupteur d'en-tête. */
  mode?: ModeAffichage
}) {
  // ⚠️ Sélecteur **stable** : on lit la référence brute `s.suivis`, puis on filtre dans le corps.
  // Filtrer DANS le sélecteur rend un tableau neuf à chaque appel, donc un `getSnapshot` instable
  // pour `useSyncExternalStore` → **boucle de rendu infinie** en Zustand v5 / React 19, y compris
  // avec zéro suivi. C'est le correctif que `VueSuivi` porte déjà, sur le **même store** : un
  // premier jet de cette US l'avait réintroduit à l'identique, et aucune porte mécanique ne peut
  // l'attraper — d'où le test de montage `VueTableaux.test.tsx`, qui, lui, le peut.
  const tousLesSuivis = useSessionSuivisStore((s) => s.suivis)
  const suivis = useMemo(
    () => suivisDuTournoi(tousLesSuivis, tournoiId),
    [tousLesSuivis, tournoiId],
  )
  const [phaseChoisie, setPhaseChoisie] = useState<number | null>(null)
  // ⚠️ **Les arbres appartiennent à un créneau** (E01US025, ADR-0075). Ni l'écran de salle ni
  // l'appli publique n'ont de sélecteur de départ ici — le CA veut « aucune interaction » sur le
  // premier et une lecture immédiate sur le second : on prend donc le créneau **qu'on est en train
  // de tirer**, par le même helper pur que le classement et le plan de cibles.
  const departs = useDeparts(tournoiId)
  const departId = departDeSalle(departs.data ?? [])?.id ?? null
  const tableaux = useTableaux(departId)
  const donnees = tableaux.data

  // Les **données priment sur l'erreur** : React Query garde le `data` de la dernière lecture
  // réussie pendant un échec. Tester `isError` d'abord jetterait un arbre encore exact au premier
  // clignotement réseau et laisserait l'écran projeté sur un message d'erreur ≥ 20 s — le défaut
  // qu'E07US008 a dû corriger en revue, à ne pas refaire ici.
  if (departs.isSuccess && (departs.data ?? []).length === 0) {
    return <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
  }
  if (donnees === undefined) {
    return (
      <p className="carte__etat">
        {tableaux.isError
          ? 'Connexion momentanément perdue — mise à jour au retour.'
          : 'Chargement…'}
      </p>
    )
  }
  // L'écran de salle ne peut rien choisir : il montre le tableau **qui se joue** — le premier non
  // terminé, sinon le dernier (à 17 h, c'est celui dont on veut voir le podium). Même règle que le
  // plan de cibles de salle, calé sur le départ en cours et non sur le premier.
  const courant = donnees.tableaux.find((t) => !t.est_termine) ?? donnees.tableaux.at(-1)
  const tableau =
    (interactif && phaseChoisie !== null
      ? donnees.tableaux.find((t) => t.phase_id === phaseChoisie)
      : undefined) ?? courant
  if (tableau === undefined) {
    // Liste vide : ni erreur ni page blanche. Le matin, les tableaux n'existent pas encore, et le
    // dire évite de laisser croire à une panne devant un écran vide. (Le test `undefined` porte
    // aussi la garde d'indexation — une liste non vide rend toujours un élément.)
    return <p className="carte__etat">Pas encore de tableau — les duels ne sont pas lancés.</p>
  }
  // Sur l'écran de salle il n'y a personne à suivre : la lecture y est **toujours** l'arbre complet
  // (CA E07US004, « aucune interaction »). Dans l'appli publique, c'est l'interrupteur d'en-tête qui
  // décide — et lui ne rend « suivis » que s'il y a au moins un archer suivi (`modeEffectif`).
  const lectureEffective: Lecture = interactif && mode === 'suivis' ? 'chemin' : 'complet'

  return (
    <div className="tableaux">
      {interactif && (
        <div className="tableaux__barre">
          {/* Le choix de phase n'apparaît que s'il y a un choix à faire : un tournoi à un seul
              tableau n'a pas à afficher une liste d'un élément. */}
          {donnees.tableaux.length > 1 && (
            <label className="tableaux__phase">
              <span className="tableaux__phase-libelle">Tableau</span>
              <select
                value={tableau.phase_id}
                onChange={(e) => setPhaseChoisie(Number(e.target.value))}
              >
                {donnees.tableaux.map((t) => (
                  <option key={t.phase_id} value={t.phase_id}>
                    {nommerType(t.type)} — {t.effectif} archers
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}

      <p className="tableaux__entete">
        {nommerType(tableau.type)} · {tableau.effectif} archers
        {tableau.est_termine ? ' · terminé' : ''}
      </p>

      {lectureEffective === 'chemin' ? (
        <MonChemin tableau={tableau} suivis={suivis} />
      ) : (
        <ArbreComplet tableau={tableau} />
      )}

      {tableau.podium.length > 0 && <Podium places={tableau.podium} />}
    </div>
  )
}

/** Variante A : l'arbre réduit à la trajectoire de chaque archer suivi. */
function MonChemin({ tableau, suivis }: { tableau: TableauPublic; suivis: number[] }) {
  if (suivis.length === 0) {
    // Défense en profondeur : l'interrupteur d'en-tête ne rend « suivis » qu'avec au moins un
    // archer suivi (`modeEffectif`), donc ce cas ne devrait pas se produire depuis l'appli publique.
    // On ne bascule pas d'autorité sur l'autre lecture — ce serait répondre à côté sans le dire —
    // et l'on nomme le geste manquant : la liste se remplit dans l'onglet « Suivi » (E07US006), et
    // nulle part ailleurs.
    return (
      <p className="carte__etat">
        Aucun archer suivi. Ajoutez-en dans l’onglet « Suivi » pour voir son parcours ici, ou
        repassez l’affichage sur « Tout le tournoi ».
      </p>
    )
  }
  return (
    <ul className="tableaux__chemins">
      {suivis.map((archerId) => (
        <CheminArcher key={archerId} tableau={tableau} archerId={archerId} />
      ))}
    </ul>
  )
}

function CheminArcher({ tableau, archerId }: { tableau: TableauPublic; archerId: number }) {
  const etapes = cheminDeArcher(tableau, archerId)
  // Le nom vient du tableau lui-même : il n'est pas mémorisé côté client (un archer renommé garde
  // son suivi sans afficher un nom périmé — cf. `sessionSuivisStore`).
  const moi = tableau.duels
    .flatMap((duel) => [duel.haut, duel.bas])
    .find((qui) => qui?.archer_id === archerId)

  if (etapes.length === 0 || moi === undefined || moi === null) {
    // Suivi d'un archer qui n'est pas dans **ce** tableau (autre catégorie, sorti en qualification,
    // ou tableau d'une autre phase) : le dire vaut mieux qu'une carte vide inexplicable.
    return (
      <li className="tableaux__chemin">
        <span className="tableaux__chemin-nom">Archer suivi</span>
        <p className="carte__etat">Pas engagé dans ce tableau.</p>
      </li>
    )
  }

  const sorti = etapes.at(-1)?.statut === 'perdu'
  return (
    <li className="tableaux__chemin">
      <span className="tableaux__chemin-nom">{nomComplet(moi)}</span>
      <ol className="tableaux__etapes">
        {etapes.map((etape) => (
          <li
            key={etape.tour}
            className={`tableaux__etape tableaux__etape--${etape.statut.replace('_', '-')}`}
          >
            {/* Le libellé vient du serveur. `null` — trop de branches possibles pour nommer — met
                un tiret et non « À venir » : le statut de la ligne le dit déjà, l'écrire deux fois
                sur la même ligne n'apprend rien (correctif de revue). */}
            <span className="tableaux__tour">{etape.libelle ?? '—'}</span>
            <span className="tableaux__contre">
              {etape.adversaire === null ? '—' : nomComplet(etape.adversaire)}
              {etape.score !== null && <strong className="tableaux__score"> {etape.score}</strong>}
            </span>
            <span className="tableaux__statut">{LIBELLE_STATUT[etape.statut]}</span>
          </li>
        ))}
      </ol>
      {sorti && <p className="tableaux__sortie">Parcours terminé dans ce tableau.</p>}
    </li>
  )
}

/** Variante B : l'arbre complet, en **liste par tour** (concession mobile assumée, maquette P05). */
function ArbreComplet({ tableau }: { tableau: TableauPublic }) {
  const groupes = parTour(tableau)
  if (groupes.length === 0) {
    return <p className="carte__etat">Aucun duel à afficher dans ce tableau.</p>
  }
  return (
    <div className="tableaux__tours">
      {groupes.map((groupe) => (
        <section key={groupe.libelle} className="tableaux__tour-bloc">
          <h4 className="tableaux__tour-titre">{groupe.libelle}</h4>
          <ul className="tableaux__duels">
            {groupe.duels.map((duel) => (
              <LigneDuel key={duel.numero} duel={duel} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

function LigneDuel({ duel }: { duel: DuelPublic }) {
  const score =
    duel.points_haut === null || duel.points_bas === null
      ? null
      : `${duel.points_haut} — ${duel.points_bas}`
  return (
    <li className="tableaux__duel">
      <span className={duel.validee && duel.vainqueur === 'haut' ? 'tableaux__gagnant' : undefined}>
        {duel.haut === null ? '—' : nomComplet(duel.haut)}
      </span>
      <span className="tableaux__vs">{score ?? 'vs'}</span>
      <span className={duel.validee && duel.vainqueur === 'bas' ? 'tableaux__gagnant' : undefined}>
        {duel.bas === null ? '—' : nomComplet(duel.bas)}
      </span>
      {duel.termine && !duel.validee && (
        <span className="tableaux__attente">En attente de validation</span>
      )}
    </li>
  )
}

function Podium({ places }: { places: TableauPublic['podium'] }) {
  return (
    <section className="tableaux__podium">
      <h4 className="tableaux__tour-titre">Places acquises</h4>
      <ol className="tableaux__places">
        {places.map((place) => (
          <li key={place.rang} className="tableaux__place">
            <span className="tableaux__rang">{place.rang}</span>
            <span>{nomComplet(place.duelliste)}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
