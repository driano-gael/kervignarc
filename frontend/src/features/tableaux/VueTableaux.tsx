// Vue publique des tableaux de duels (E07US005) — maquette **P05**.
//
// Un seul composant pour deux surfaces (appli publique interactive, écran de salle projeté) : les
// dessiner séparément les ferait diverger sur la seule chose qui compte, l'appariement affiché.
// Deux lectures : **« Mon chemin »**, par défaut dès qu'on suit quelqu'un (`D-09`), et **« Arbre
// complet »**, en liste par tour — l'arbre en vraies branches ne tient pas sur 360 px. ⚠️ **Les
// horaires prévisionnels ne sont pas livrés** (arbitrage du 04/08/2026) : le domaine n'en porte
// aucun au grain de la phase, et les inventer serait pire que les taire.

import { useState } from 'react'
import { nommerType } from '../../shared/phases/catalogue'
import { useDeparts } from '../departs/hooks'
import { type ModeAffichage } from '../../shared/suivis/focus'
import { departDeSalle } from '../salle/rotation'
import type { DuelPublic, DuellistePublic, TableauPublic } from './api'
import { useTableaux } from './hooks'
import { cheminDeArcher, LIBELLE_STATUT, parTour } from './presentation'

const nomComplet = (qui: DuellistePublic) => `${qui.prenom} ${qui.nom}`.trim()

export function VueTableaux({
  tournoiId,
  phaseId = null,
  interactif = true,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  /** La phase à montrer, **imposée** par l'appelant — `null` = cette vue choisit elle-même.
   *
   * Ajouté par E05US031 : quand l'onglet « En cours » pilote, le tableau affiché doit être celui
   * qu'il désigne — sinon il annoncerait « 3. Élimination directe » au-dessus d'un autre arbre dès
   * qu'un départ porte deux tableaux. ⚠️ **Imposer la phase éteint aussi le sélecteur local** :
   * deux barres de choix concurrentes donneraient deux vérités contradictoires.
   */
  phaseId?: number | null
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
  /** Les archers suivis **sur ce tournoi**, descendus par `AccueilPublic` — jamais lus au store ici.
   *
   * ⚠️ Cette vue était la seule des cinq à **rebâtir** la liste depuis le store alors qu'elle
   * recevait déjà `mode` en prop (correctif de revue). L'exception rendait invérifiable la règle
   * qu'elle enfreignait : « le mode public ne se lit pas au store dans une vue partagée », posée
   * précisément parce que cette vue sert aussi l'écran de salle. Elle abonnait au passage la salle
   * à un store public dont elle n'a que faire, et faisait dériver « les suivis de ce tournoi » à
   * trois endroits du même arbre. */
  suivis?: number[]
}) {
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
  // Trois sources, dans cet ordre de priorité : la phase **imposée** par l'appelant, celle que le
  // spectateur a choisie dans le sélecteur local, puis le tableau qui se joue.
  const impose = phaseId === null ? undefined : donnees.tableaux.find((t) => t.phase_id === phaseId)
  const tableau =
    impose ??
    (interactif && phaseChoisie !== null
      ? donnees.tableaux.find((t) => t.phase_id === phaseChoisie)
      : undefined) ??
    courant
  // ⚠️ **Une phase imposée mais absente de la liste n'est pas un vide** : c'est une phase en
  // tableau dont l'arbre n'existe pas encore (elle prélève des places qu'une phase amont n'a pas
  // attribuées — ADR-0081). Retomber en silence sur « le tableau qui se joue » ferait afficher un
  // arbre sous un titre qui en annonce un autre, ce qui est pire que de dire ce qui manque.
  if (phaseId !== null && impose === undefined) {
    // ⚠️ **Sans cause annoncée** (correctif de revue, axe C1). Une première rédaction expliquait
    // « les archers qui s'y affronteront ne sont pas tous connus » — or ce cas-là est **présent**
    // dans la liste, avec `en_attente_de`, et traité plus bas. Ce chemin-ci ne s'atteint que si
    // `pour_depart` a avalé un échec, ou si les deux caches (`avancement-phases` et `tableaux`,
    // clés et invalidations distinctes) sont momentanément désaccordés. Le message annonçait donc
    // une cause qui n'est généralement pas la bonne, et le spectateur n'a rien à réparer.
    return <p className="carte__etat">Cet arbre n’est pas encore disponible.</p>
  }
  if (tableau === undefined) {
    // Liste vide : ni erreur ni page blanche. Le matin, les tableaux n'existent pas encore, et le
    // dire évite de laisser croire à une panne devant un écran vide. (Le test `undefined` porte
    // aussi la garde d'indexation — une liste non vide rend toujours un élément.)
    return <p className="carte__etat">Pas encore de tableau — les duels ne sont pas lancés.</p>
  }
  // Sur l'écran de salle il n'y a personne à suivre : la lecture y est **toujours** l'arbre complet
  // (CA E07US004, « aucune interaction »). Dans l'appli publique, c'est l'interrupteur d'en-tête qui
  // décide — et lui ne rend « suivis » que s'il y a au moins un archer suivi (`modeEffectif`).
  const centrerSurSuivis = interactif && mode === 'suivis'

  return (
    <div className="tableaux">
      {interactif && phaseId === null && (
        <div className="tableaux__barre">
          {/* Le choix de phase n'apparaît que s'il y a un choix à faire : un tournoi à un seul
              tableau n'a pas à afficher une liste d'un élément. Ni quand la phase est **imposée**
              par l'appelant — c'est alors son fil de déroulé qui porte le choix. */}
          {donnees.tableaux.length > 1 && (
            <label className="tableaux__phase">
              <span className="tableaux__phase-libelle">Tableau</span>
              <select
                value={tableau.phase_id}
                onChange={(e) => setPhaseChoisie(Number(e.target.value))}
              >
                {donnees.tableaux.map((t) => (
                  <option key={t.phase_id} value={t.phase_id}>
                    {/* ⚠️ L'`ordre` est affiché depuis E05US024 : le message « en attente du
                        tableau n » ci-dessous le désigne, et sans lui le spectateur lisait « le
                        tableau 2 » devant deux entrées toutes deux nommées « Élimination
                        directe » — une référence sans référent (relevé en revue). */}
                    {t.ordre}. {nommerType(t.type)} —{' '}
                    {t.en_attente_de != null ? 'en attente' : `${t.effectif} archers`}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}

      <p className="tableaux__entete">
        {nommerType(tableau.type)}
        {tableau.en_attente_de != null ? '' : ` · ${tableau.effectif} archers`}
        {tableau.est_termine ? ' · terminé' : ''}
      </p>

      {/* ⚠️ **Une phase peut exister sans arbre** (E05US024, ADR-0081) : elle prélève des places
          que sa source n'a pas encore attribuées. On le **dit** au lieu d'afficher un bracket
          plausible et faux — c'est le cas d'une consolante composée le matin, avant que les quarts
          du tableau principal ne soient tirés. La phase n'était alors pas montrée du tout : un
          tableau à venir était indiscernable d'un tableau cassé. */}
      {tableau.en_attente_de != null ? (
        <p className="carte__etat">
          Les places disputées ici ne sont pas encore connues : le tableau {tableau.en_attente_de}
          {nomDeLOrdre(donnees.tableaux, tableau.en_attente_de)} doit d’abord être joué. L’arbre
          s’affichera dès que ses matchs auront départagé les archers concernés.
        </p>
      ) : (
        <>
          {centrerSurSuivis ? (
            <MonChemin tableau={tableau} suivis={suivis} />
          ) : (
            <ArbreComplet tableau={tableau} />
          )}

          {tableau.podium.length > 0 && <Podium places={tableau.podium} />}
        </>
      )}
    </div>
  )
}

/** Le nom lisible de la phase d'un `ordre` donné, pour que « le tableau 2 » ait un référent.
 *
 * Rend une chaîne vide si l'ordre ne correspond à aucun tableau du créneau — c'est le cas quand la
 * phase attendue n'est pas elle-même un tableau (une qualification, par exemple) : le numéro seul
 * reste alors juste, et inventer un nom serait pire que de n'en donner aucun.
 */
function nomDeLOrdre(tableaux: TableauPublic[], ordre: number): string {
  const cible = tableaux.find((t) => t.ordre === ordre)
  return cible ? ` (${nommerType(cible.type)})` : ''
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
  // ⚠️ **Aucun de vos archers ici ≠ aucun archer** (correctif de revue). Le cas est banal — on suit
  // des archers d'une catégorie, on regarde le tableau d'une autre — et il n'était pas traité : on
  // rendait **une carte anonyme par archer suivi**, toutes identiques (« Archer suivi / Pas engagé
  // dans ce tableau »), sans jamais nommer le filtre ni proposer d'en sortir. Anonymes par
  // construction, d'ailleurs : le nom se lit dans les duels du tableau, où l'archer n'est pas.
  // C'est la seule des cinq vues qui manquait à la règle « chaque écran nomme son propre vide ».
  const engages = suivis.filter((archerId) => cheminDeArcher(tableau, archerId).length > 0)
  if (engages.length === 0) {
    return (
      <p className="carte__etat">
        Aucun des archers que vous suivez n’est engagé dans ce tableau. Passez à « Tout le tournoi »
        pour voir l’arbre complet.
      </p>
    )
  }
  return (
    <>
      <ul className="tableaux__chemins">
        {engages.map((archerId) => (
          <CheminArcher key={archerId} tableau={tableau} archerId={archerId} />
        ))}
      </ul>
      {/* Cas mixte : on dit **combien** manquent plutôt que d'aligner des cartes sans nom. */}
      {engages.length < suivis.length && (
        <p className="carte__etat">
          {suivis.length - engages.length === 1
            ? 'Un autre archer suivi n’est pas engagé dans ce tableau.'
            : `${suivis.length - engages.length} autres archers suivis ne sont pas engagés dans ce tableau.`}
        </p>
      )}
    </>
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
    // Défense en profondeur : `MonChemin` ne monte plus que les archers dont le chemin est non
    // vide, et un chemin non vide implique un duel où l'archer figure — donc un nom trouvable.
    // Le garde reste pour le typage et pour qu'un futur appelant direct ne rende pas une carte
    // muette ; ce n'est plus lui qui porte le cas « pas engagé », traité collectivement au-dessus.
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

/** Variante B : l'arbre complet, en **liste par tour** (concession mobile assumée, maquette P05).
 *
 * ⚠️ `# DETTE-072` — `LigneDuel` ci-dessous rend la même ligne que
 * `shared/duels/LigneRencontre.tsx`, que les trois formats sans arbre partagent depuis E05US031.
 * Les deux vivent dans le **même onglet public** (« En cours »). Voir `docs/dette.md`. */
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
