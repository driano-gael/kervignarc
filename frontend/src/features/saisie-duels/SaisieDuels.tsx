// Écran tactile de saisie en duels (E04US013) — la surface du **scoreur** itinérant (D-12).
//
// Le scoreur choisit une phase de tableau, voit la liste des duels par tour, en ouvre un et le
// score : grille de manches (sets ou cumul selon `mode`, **résolu par arme côté serveur** — le
// front n'en décide pas, ADR-0049), barrage conditionnel (§8.2, que l'appli ne mesure pas), puis
// validation du duel tranché. Le serveur reste l'**autorité** ; le front n'affiche que ce qu'il
// reçoit. La saisie survit à une coupure réseau (file hors-ligne + rejeu, E04US009).

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { FamilleDuel } from '../../shared/stores/fileDuelsHorsLigneStore'
import { useDeclarerForfaitDuel } from '../forfaits/hooks'
import { PanneauRoutage } from '../routage/PanneauRoutage'
import type { Cote, Duel, EquipeEcartee, Tableau } from './api'
import {
  archersARouter,
  baremeDeManche,
  campApresFleche,
  duellistesDuForfait,
  estJouable,
  estOuvrable,
  etatBarrage,
  etatManche,
  flechesApresZone,
  grouperParTour,
  mancheExistante,
  nouvelIdentifiant,
  pastillesManches,
  retenirPhase,
  phasesDeTableau,
  prochaineMancheASaisir,
  saisieVerrouillee,
  signatureBarrage,
  signatureManche,
  statutDuel,
  totalVolee,
} from './duel'
import {
  useDuel,
  useDuelsEnAttente,
  useRejeuDuelsHorsLigne,
  useSaisirBarrage,
  useSaisirManche,
  useTableau,
  useValiderDuel,
  usePhases,
} from './hooks'
import {
  libelleMetaDuel,
  libelleSaisiesEnAttente,
  libelleStatut,
  motifsEcart,
  nomCamp,
  nomCourt,
  nomVainqueur,
  titreBarrage,
} from './presentation'

/**
 * `departId` vient de l'**espace scoreur** depuis E05US030 (`DETTE-056` refermée) : les quatre
 * panneaux de saisie partagent un seul créneau, choisi une fois en tête d'écran. Chacun appelait
 * auparavant `useCreneauDesDuels` pour son compte, avec un `useState` local — donc quatre
 * sélecteurs côte à côte, qui divergeaient au premier changement. Le scoreur changeait de créneau
 * dans un panneau, saisissait dans l'autre, et scorait les rencontres du mauvais départ **avec des
 * identifiants valides, donc sans la moindre erreur**.
 */
export function SaisieDuels({
  tournoiId,
  departId,
}: {
  tournoiId: number
  departId: number | null
}) {
  // Rejeu de la file hors-ligne à la reconnexion (E04US009) : monté ici, seul endroit où le scoreur
  // saisit — inutile de le faire tourner ailleurs.
  useRejeuDuelsHorsLigne()

  const phases = usePhases(departId)
  const [phaseId, setPhaseId] = useState<number | null>(null)

  const tableaux = phasesDeTableau(phases.data ?? [])
  const phaseRetenue = retenirPhase(phaseId, tableaux)

  return (
    <div className="duels-saisie">
      <div className="duels-saisie__entete">
        <h3 className="carte__soustitre">Saisie des duels</h3>
        <IndicateurAttente />
      </div>

      {phases.isError && <MessageErreur erreur={phases.error} />}
      {phases.isSuccess && tableaux.length === 0 && (
        <p className="carte__etat">
          Aucune phase de tableau (élimination directe) dans ce tournoi : la saisie en duels
          s’ouvrira quand une phase d’élimination aura été créée et peuplée.
        </p>
      )}
      {tableaux.length > 0 && (
        <select
          className="formulaire__champ"
          value={phaseRetenue ?? ''}
          onChange={(e) => setPhaseId(e.target.value === '' ? null : Number(e.target.value))}
          aria-label="Phase de tableau à scorer"
        >
          <option value="">Choisir une phase…</option>
          {tableaux.map((phase) => (
            <option key={phase.id} value={phase.id}>
              Phase {phase.ordre} — élimination directe
            </option>
          ))}
        </select>
      )}

      {/* `key` sur la phase : en changer **remonte** le sous-arbre (reset propre de la sélection). */}
      {phaseRetenue !== null && (
        <TableauScoreur key={phaseRetenue} tournoiId={tournoiId} phaseId={phaseRetenue} />
      )}
    </div>
  )
}

// Bandeau discret d'actes en attente d'envoi (hors-ligne) — le voyant global de connexion
// (`IndicateurConnexion`) reste dans l'en-tête de l'app ; celui-ci précise la file **des duels**.
function IndicateurAttente() {
  const libelle = libelleSaisiesEnAttente(useDuelsEnAttente())
  if (libelle === null) return null
  return (
    <span className="duels-saisie__attente" role="status">
      {libelle}
    </span>
  )
}

function TableauScoreur({ tournoiId, phaseId }: { tournoiId: number; phaseId: number }) {
  const tableau = useTableau(tournoiId, phaseId)
  const [matchOuvert, setMatchOuvert] = useState<number | null>(null)
  // Le duel qu'on vient de valider (E04US018) : la validation fait avancer le tableau, donc la
  // destination des deux duellistes est **immédiatement** lisible côté serveur. `null` = aucun duel
  // validé sur cette tablette. ⚠️ **Ne se remet plus à `null` à la fermeture** (E16US018) : c'est ce
  // qui rend le panneau rouvrable. ⚠️ Il porte donc le **numéro** : à 11 h, la poignée rouvre le
  // duel validé à 9 h 40, et un lien muet promettrait le duel qu'on vient de regarder.
  const [routageDe, setRoutageDe] = useState<{ numero: number; archers: number[] } | null>(null)
  const [panneauFerme, setPanneauFerme] = useState(false)

  // Panneau de routage (E04US018) : il **remplace** la grille dès le duel tranché — les deux archers
  // sont encore là, c'est la seconde où l'information leur sert. Il se referme au bouton, ou seul
  // au bout de trois minutes (E16US018) ; dans les deux cas il reste rouvrable depuis la liste.
  //
  // ⚠️ **Avant les sorties `isPending` / `isError`, et c'est le correctif d'E16US018** : le panneau
  // ne lit pas `tableau`, il a ses propres données. Placé après, un refetch en échec (`retry: false`,
  // et `useRealtime` invalide sans clé) le démontait puis le remontait — le minuteur repartait à
  // zéro, si bien que sur un wifi de salle il pouvait ne **jamais** se refermer.
  if (routageDe !== null && !panneauFerme) {
    return (
      <PanneauRoutage
        tournoiId={tournoiId}
        archerIds={routageDe.archers}
        phaseId={phaseId}
        titrePanneau={`Où tire-t-on ensuite ? — duel n°${routageDe.numero}`}
        libelleRetour="Retour à la liste"
        onRetour={() => {
          setPanneauFerme(true)
          setMatchOuvert(null)
        }}
      />
    )
  }

  if (tableau.isPending) return <p className="carte__etat">Chargement du tableau…</p>
  if (tableau.isError) {
    return (
      <div>
        <MessageErreur erreur={tableau.error} />
        <p className="carte__etat">
          La saisie suppose une phase de tableau (élimination directe) dont les duellistes sont
          connus (classement figé, phase peuplée).
        </p>
      </div>
    )
  }

  if (matchOuvert !== null) {
    return (
      <GrilleDuel
        key={matchOuvert}
        tournoiId={tournoiId}
        phaseId={phaseId}
        matchNumero={matchOuvert}
        onRetour={() => setMatchOuvert(null)}
        onValide={(duellistes) => {
          setRoutageDe({ numero: matchOuvert, archers: duellistes })
          setPanneauFerme(false)
        }}
      />
    )
  }

  return (
    <>
      {/* La poignée que la qualification a depuis E04US018, et que les duels n'avaient pas : sans
          elle, la fermeture automatique serait irréversible pour ce duel — l'écran qui dit à un
          repêché qu'il repart, ou à un sorti quelle place il prend. ⚠️ Elle **nomme** son duel : en
          qualification le panneau suit la cible affichée, ici il rouvre un instantané qui peut
          dater d'une heure. */}
      {routageDe !== null && (
        <button type="button" className="lien" onClick={() => setPanneauFerme(false)}>
          Où tire-t-on ensuite ? — duel n°{routageDe.numero}
        </button>
      )}
      <ListeDuels tableau={tableau.data} onOuvrir={setMatchOuvert} />
    </>
  )
}

// La liste des duels **groupés par libellé de tour** (finale en tête). Le regroupement (par libellé,
// pas par `tour` brut — pour ne pas ranger la petite finale sous « Finale ») est une **logique pure**
// portée par `grouperParTour` (testée dans `duel.ts`). Un duel jouable est tapable pour l'ouvrir ;
// les autres sont affichés mais non ouvrables (`estOuvrable`).
function ListeDuels({
  tableau,
  onOuvrir,
}: {
  tableau: Tableau
  onOuvrir: (matchNumero: number) => void
}) {
  const groupes = grouperParTour(tableau.duels, tableau.nb_tours)

  return (
    <div className="duels-liste">
      {tableau.est_termine && tableau.podium.length > 0 && <Podium tableau={tableau} />}
      {tableau.duels.length === 0 && (
        <p className="carte__aide">
          Moins de deux équipes engagées : aucun duel à jouer.
          {tableau.equipes_ecartees.length > 0 &&
            ' Les motifs des équipes écartées figurent ci-dessous.'}
        </p>
      )}
      {tableau.equipes_ecartees.length > 0 && (
        <EquipesEcartees equipes={tableau.equipes_ecartees} />
      )}
      {groupes.map((groupe) => (
        <section key={groupe.titre} className="duels-liste__tour">
          <h4 className="duels-liste__titre">{groupe.titre}</h4>
          <ul className="duels-liste__matchs">
            {groupe.duels.map((duel) => (
              <LigneDuel key={duel.numero} duel={duel} onOuvrir={onOuvrir} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

function LigneDuel({ duel, onOuvrir }: { duel: Duel; onOuvrir: (n: number) => void }) {
  const statut = statutDuel(duel)
  const haut = nomCamp(duel.haut)
  const bas = nomCamp(duel.bas)

  const contenu = (
    <>
      <span className="duels-liste__duellistes">
        <span>{haut}</span>
        <span className="duels-liste__contre">contre</span>
        <span>{bas}</span>
      </span>
      <span className={`duels-liste__statut duels-liste__statut--${statut}`}>
        {libelleStatut(statut)}
      </span>
    </>
  )

  if (!estOuvrable(statut)) {
    return <li className="duels-liste__match duels-liste__match--inerte">{contenu}</li>
  }
  return (
    <li>
      <button
        type="button"
        className="duels-liste__match duels-liste__match--ouvrable"
        onClick={() => onOuvrir(duel.numero)}
      >
        {contenu}
      </button>
    </li>
  )
}

function EquipesEcartees({ equipes }: { equipes: EquipeEcartee[] }) {
  return (
    <section className="duels-podium" aria-label="Équipes non engagées">
      <h4 className="duels-liste__titre">Équipes non engagées</h4>
      <ul className="duels-podium__places">
        {equipes.map((equipe) => (
          <li key={equipe.equipe_id}>
            <strong>{equipe.nom}</strong> — {motifsEcart(equipe)}
          </li>
        ))}
      </ul>
    </section>
  )
}

function Podium({ tableau }: { tableau: Tableau }) {
  return (
    <section className="duels-podium" aria-label="Podium">
      <h4 className="duels-liste__titre">Podium</h4>
      <ol className="duels-podium__places">
        {tableau.podium.map((place) => (
          <li key={place.rang}>
            <strong>{place.rang}.</strong> {nomCamp(place.duelliste)}
          </li>
        ))}
      </ol>
    </section>
  )
}

// La grille d'un duel : en-tête, navigateur de manches, saisie de la manche active (deux camps + un
// pavé), résultat courant, barrage conditionnel, validation. Le verrou (`validee_par`) ferme tout.
function GrilleDuel({
  tournoiId,
  phaseId,
  matchNumero,
  onRetour,
  onValide,
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  onRetour: () => void
  onValide: (archerIds: number[]) => void
}) {
  const requete = useDuel(tournoiId, phaseId, matchNumero)

  return (
    <div className="duel">
      <button type="button" className="lien duel__retour" onClick={onRetour}>
        ← Retour à la liste
      </button>
      {requete.isPending && <p className="carte__etat">Chargement du duel…</p>}
      {requete.isError && <MessageErreur erreur={requete.error} />}
      {requete.isSuccess && (
        <DuelCharge
          tournoiId={tournoiId}
          phaseId={phaseId}
          matchNumero={matchNumero}
          duel={requete.data}
          onValide={onValide}
        />
      )}
    </div>
  )
}

/** Le **pavé de saisie d'un duel chargé** — en-tête, manches, barrage, validation.
 *
 * ⚠️ **Exporté depuis E05US023**, et c'est ce qui rend les poules jouables sans second écran : une
 * rencontre de poule *est* un duel ordinaire (ADR-0083 §7). `famille` dit seulement **où écrire**
 * ; tout le reste est identique. Une seule chose ne traverse pas : le **forfait** — un *walkover*
 * fait passer l'adversaire (ADR-0050), et en poule le CA ne l'ouvre pas. Le bouton n'est donc
 * rendu que pour un tableau.
 */
export function DuelCharge({
  tournoiId,
  phaseId,
  matchNumero,
  duel,
  onValide,
  famille = 'tableau',
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  duel: Duel
  onValide: (archerIds: number[]) => void
  famille?: FamilleDuel
}) {
  const haut = nomCamp(duel.haut)
  const bas = nomCamp(duel.bas)
  const verrou = saisieVerrouillee(duel)
  const forfait = duellistesDuForfait(duel, famille)

  if (!estJouable(duel)) {
    return (
      <div>
        <p className="duel__entete">
          <strong>{haut}</strong> contre <strong>{bas}</strong>
        </p>
        <p className="carte__etat">
          Pas de pavé pour ce match : adversaires non connus, bye, ou blason indéterminable.
        </p>
      </div>
    )
  }

  const resultat = duel.resultat

  return (
    <div className="duel__corps">
      <div className="duel__entete">
        <div className="duel__camps">
          <span className="duel__camp">{haut}</span>
          <span className="duel__vs">
            {resultat ? `${resultat.points_haut} – ${resultat.points_bas}` : 'vs'}
          </span>
          <span className="duel__camp">{bas}</span>
        </div>
        <p className="duel__meta">{libelleMetaDuel(duel)}</p>
      </div>

      {verrou ? (
        <p className="duel__verrou" role="status">
          {duel.validee_par !== null ? (
            <>
              Duel validé par <strong>{duel.validee_par}</strong> — la saisie est close.
            </>
          ) : (
            <>Validation en attente d’envoi — la saisie est close jusqu’à la reconnexion.</>
          )}
        </p>
      ) : (
        <SaisieManche
          tournoiId={tournoiId}
          phaseId={phaseId}
          matchNumero={matchNumero}
          duel={duel}
          famille={famille}
        />
      )}

      {forfait !== null && (
        <ForfaitDuel
          tournoiId={tournoiId}
          phaseId={phaseId}
          hautId={forfait.hautId}
          hautNom={haut}
          basId={forfait.basId}
          basNom={bas}
        />
      )}

      {resultat?.barrage_requis === true && !verrou && (
        <SaisieBarrage
          tournoiId={tournoiId}
          phaseId={phaseId}
          matchNumero={matchNumero}
          duel={duel}
          famille={famille}
        />
      )}

      <Validation
        tournoiId={tournoiId}
        phaseId={phaseId}
        matchNumero={matchNumero}
        duel={duel}
        onValide={onValide}
        famille={famille}
      />
    </div>
  )
}

// Forfait d'un duelliste (E04US015, ADR-0050) : abandon en cours de tableau. L'adversaire passe
// d'office (walkover côté serveur) et le tableau se reconstruit ; le scoreur revient à la liste où le
// match apparaît tranché.
// ⚠️ DETTE-090 : ce bloc annonçait « réversible depuis le panneau de qualification ou par
// re-régénération » — les DEUX chemins sont faux. `annuler_en_qualification` résout la phase de
// QUALIFICATION (un forfait de duel y est introuvable) et `regenerer` ne touche aucun forfait.
// Aucun écran ne défait un forfait de duel aujourd'hui.
function ForfaitDuel({
  tournoiId,
  phaseId,
  hautId,
  hautNom,
  basId,
  basNom,
}: {
  tournoiId: number
  phaseId: number
  hautId: number
  hautNom: string
  basId: number
  basNom: string
}) {
  const declarer = useDeclarerForfaitDuel(tournoiId, phaseId)

  return (
    <div className="duel__forfaits">
      <p className="duel__forfaits-titre">Forfait / abandon — l'adversaire passe</p>
      <div className="duel__forfaits-actions">
        <button
          type="button"
          className="lien"
          disabled={declarer.isPending}
          onClick={() => declarer.mutate({ archerId: hautId, nature: 'abandon' })}
        >
          {hautNom} abandonne
        </button>
        <button
          type="button"
          className="lien"
          disabled={declarer.isPending}
          onClick={() => declarer.mutate({ archerId: basId, nature: 'abandon' })}
        >
          {basNom} abandonne
        </button>
      </div>
      <MessageErreur erreur={declarer.error} />
    </div>
  )
}

// Saisie d'une **manche** (les deux volées opposées d'un même set). Un pavé unique, un **camp actif**
// qu'on remplit puis on bascule sur l'autre ; « Enregistrer la manche » quand les deux volées sont
// complètes. Réédition d'une manche déjà saisie via le navigateur, tant que le duel n'est pas validé.
function SaisieManche({
  tournoiId,
  phaseId,
  matchNumero,
  duel,
  famille,
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  duel: Duel
  famille: FamilleDuel
}) {
  const { nbManches, nbFleches } = baremeDeManche(duel)
  const saisir = useSaisirManche(tournoiId, phaseId, matchNumero, famille)

  const [numeroChoisi, setNumeroChoisi] = useState<number | null>(null)
  const numeroActif = numeroChoisi ?? prochaineMancheASaisir(duel, nbManches)
  const existante = mancheExistante(duel, numeroActif)

  // Tampons remis au contenu **persisté** de la manche visée quand elle change (ajustement d'état
  // **au rendu**, pas en effet — le pattern recommandé pour réinitialiser sans cascade).
  const signature = signatureManche(numeroActif, existante)
  const [ancre, setAncre] = useState(signature)
  const [bufferHaut, setBufferHaut] = useState<string[]>(existante?.haut ?? [])
  const [bufferBas, setBufferBas] = useState<string[]>(existante?.bas ?? [])
  const [campActif, setCampActif] = useState<Cote>('haut')
  if (ancre !== signature) {
    setAncre(signature)
    setBufferHaut(existante?.haut ?? [])
    setBufferBas(existante?.bas ?? [])
    setCampActif('haut')
  }

  const poserBuffer = campActif === 'haut' ? setBufferHaut : setBufferBas
  const { zonesActives, effacable, enregistrable } = etatManche({
    bufferHaut,
    bufferBas,
    campActif,
    nbFleches,
    envoiEnCours: saisir.isPending,
  })

  const ajouter = (zone: string) => {
    if (!zonesActives) return
    poserBuffer((actuel) => {
      const suite = [...actuel, zone]
      const autre = campActif === 'haut' ? bufferBas : bufferHaut
      const suivant = campApresFleche(campActif, suite.length, autre.length, nbFleches)
      if (suivant !== campActif) setCampActif(suivant)
      return suite
    })
  }
  const effacer = () => poserBuffer((actuel) => actuel.slice(0, -1))
  const enregistrer = () => {
    saisir.mutate(
      {
        tournoi_id: tournoiId,
        phase_id: phaseId,
        match_numero: matchNumero,
        numero: numeroActif,
        valeurs_haut: bufferHaut,
        valeurs_bas: bufferBas,
        identifiant_saisie: nouvelIdentifiant(),
      },
      { onSuccess: () => setNumeroChoisi(null) },
    )
  }

  return (
    <div className="duel__manche">
      <NavigateurManches
        nbManches={nbManches}
        duel={duel}
        numeroActif={numeroActif}
        onChoisir={setNumeroChoisi}
      />

      <p className="duel__manche-titre">
        Manche {numeroActif}/{nbManches}
      </p>

      <div className="duel__volees">
        <VoleeCamp
          nom={nomCourt(duel.haut, 'haut')}
          valeurs={bufferHaut}
          nbFleches={nbFleches}
          actif={campActif === 'haut'}
          onActiver={() => setCampActif('haut')}
        />
        <VoleeCamp
          nom={nomCourt(duel.bas, 'bas')}
          valeurs={bufferBas}
          nbFleches={nbFleches}
          actif={campActif === 'bas'}
          onActiver={() => setCampActif('bas')}
        />
      </div>

      <div className="saisie__zones duel__zones">
        {duel.zones.map((zone) => (
          <button
            key={zone}
            type="button"
            className="saisie__zone"
            disabled={!zonesActives}
            onClick={() => ajouter(zone)}
          >
            {zone}
          </button>
        ))}
      </div>

      <div className="saisie__actions">
        <button type="button" className="bouton--discret" disabled={!effacable} onClick={effacer}>
          Effacer
        </button>
        <button type="button" disabled={!enregistrable} onClick={enregistrer}>
          {saisir.isPending ? 'Enregistrement…' : 'Enregistrer la manche'}
        </button>
      </div>

      <MessageErreurDuel erreur={saisir.error} />
    </div>
  )
}

// Une volée d'un camp : nom et total sur une première ligne, pastilles des flèches sur une seconde.
// Tapable pour devenir le camp **actif**. Cible tactile ≥ 48 px.
//
// **Deux hauteurs, pas une seule rangée** — retour maquettes du 04/08/2026 (S05). Nuance utile : la
// variante critiquée (« deux colonnes symétriques ») était celle de la **maquette**, le code
// empilait déjà les deux camps. Ce qui restait juste, c'est l'intérieur de chaque camp — nom,
// flèches et total se partageaient **une** rangée, si bien qu'un nom long écrasait les cases, seule
// zone qu'on vise du doigt.
function VoleeCamp({
  nom,
  valeurs,
  nbFleches,
  actif,
  onActiver,
}: {
  nom: string
  valeurs: string[]
  nbFleches: number
  actif: boolean
  onActiver: () => void
}) {
  return (
    <button
      type="button"
      className={`duel__volee${actif ? ' duel__volee--actif' : ''}`}
      aria-pressed={actif}
      onClick={onActiver}
    >
      <span className="duel__volee-entete">
        <span className="duel__volee-nom">{nom}</span>
        <span className="duel__volee-total">{totalVolee(valeurs)}</span>
      </span>
      <span className="duel__volee-fleches" aria-live="polite">
        {Array.from({ length: nbFleches }, (_, i) => (
          <span key={i} className="saisie__fleche">
            {valeurs[i] ?? '·'}
          </span>
        ))}
      </span>
    </button>
  )
}

// Navigateur de manches : une pastille par manche du barème. Saisie = pleine, visée = surlignée.
// Tapable pour revenir corriger une manche non validée, ou repartir sur la suivante.
function NavigateurManches({
  nbManches,
  duel,
  numeroActif,
  onChoisir,
}: {
  nbManches: number
  duel: Duel
  numeroActif: number
  onChoisir: (numero: number) => void
}) {
  return (
    <div className="saisie__nav" role="group" aria-label="Manches">
      {pastillesManches(duel, nbManches, numeroActif).map(({ numero, classes, fermee, active }) => {
        return (
          <button
            key={numero}
            type="button"
            className={classes}
            aria-pressed={active}
            disabled={fermee}
            onClick={() => onChoisir(numero)}
          >
            {numero}
          </button>
        )
      })}
    </div>
  )
}

// Saisie du **barrage** (shoot-off, §8.2) : une flèche par camp. À flèches égales, l'appli ne mesure
// pas la distance → le scoreur **désigne** le plus près du centre (`gagnant_designe`), sans quoi le
// serveur refuse (`barrage_indecis`). Rééditable tant que le duel n'est pas validé.
function SaisieBarrage({
  tournoiId,
  phaseId,
  matchNumero,
  duel,
  famille,
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  duel: Duel
  famille: FamilleDuel
}) {
  const saisir = useSaisirBarrage(tournoiId, phaseId, matchNumero, famille)
  const nbFleches = duel.nb_fleches_barrage ?? 1
  const [flechesHaut, setFlechesHaut] = useState<string[]>(duel.barrage?.haut ?? [])
  const [flechesBas, setFlechesBas] = useState<string[]>(duel.barrage?.bas ?? [])
  const [designe, setDesigne] = useState<Cote | null>(duel.barrage?.gagnant_designe ?? null)

  // Resynchronisation **au rendu** si le barrage serveur change (rejeu / relecture) pendant que le
  // formulaire reste monté — même pattern que la grille de manche. Sans quoi la sélection resterait
  // figée sur les valeurs du montage.
  const signature = signatureBarrage(duel.barrage)
  const [ancreBarrage, setAncreBarrage] = useState(signature)
  if (ancreBarrage !== signature) {
    setAncreBarrage(signature)
    setFlechesHaut(duel.barrage?.haut ?? [])
    setFlechesBas(duel.barrage?.bas ?? [])
    setDesigne(duel.barrage?.gagnant_designe ?? null)
  }

  const { complets, egales, pretAEnvoyer } = etatBarrage(
    flechesHaut,
    flechesBas,
    designe,
    nbFleches,
  )

  // Une désignation vaut pour les flèches qu'elle a vues : toute correction la redemande.
  const changerFleches = (poser: (valeurs: string[]) => void, valeurs: string[]) => {
    poser(valeurs)
    setDesigne(null)
  }

  const enregistrer = () => {
    if (!complets) return
    saisir.mutate({
      tournoi_id: tournoiId,
      phase_id: phaseId,
      match_numero: matchNumero,
      fleches_haut: flechesHaut,
      fleches_bas: flechesBas,
      gagnant_designe: egales ? designe : null,
      identifiant_saisie: nouvelIdentifiant(),
    })
  }

  return (
    <div className="duel__barrage">
      <p className="duel__barrage-titre">{titreBarrage(nbFleches)}</p>
      <div className="duel__barrage-camps">
        <ChoixFleches
          nom={nomCourt(duel.haut, 'haut')}
          zones={duel.zones}
          nbFleches={nbFleches}
          valeurs={flechesHaut}
          onChanger={(valeurs) => changerFleches(setFlechesHaut, valeurs)}
        />
        <ChoixFleches
          nom={nomCourt(duel.bas, 'bas')}
          zones={duel.zones}
          nbFleches={nbFleches}
          valeurs={flechesBas}
          onChanger={(valeurs) => changerFleches(setFlechesBas, valeurs)}
        />
      </div>

      {egales && (
        <div className="duel__designation" role="group" aria-label="Plus près du centre">
          <span>
            {nbFleches === 1 ? 'Flèches' : 'Totaux'} à égalité — qui est le plus près du centre ?
          </span>
          <div className="duel__designation-choix">
            <button
              type="button"
              className={designe === 'haut' ? undefined : 'bouton--discret'}
              aria-pressed={designe === 'haut'}
              onClick={() => setDesigne('haut')}
            >
              {nomCourt(duel.haut, 'haut')}
            </button>
            <button
              type="button"
              className={designe === 'bas' ? undefined : 'bouton--discret'}
              aria-pressed={designe === 'bas'}
              onClick={() => setDesigne('bas')}
            >
              {nomCourt(duel.bas, 'bas')}
            </button>
          </div>
        </div>
      )}

      <button type="button" disabled={!pretAEnvoyer || saisir.isPending} onClick={enregistrer}>
        {saisir.isPending ? 'Enregistrement…' : 'Enregistrer le barrage'}
      </button>
      <MessageErreurDuel erreur={saisir.error} />
    </div>
  )
}

// Les flèches de barrage d'un camp parmi les zones du blason (`flechesApresZone` : remplacer ou
// ajouter). À plusieurs flèches, elles s'ajoutent jusqu'à `nbFleches` et « Effacer » retire la
// dernière, comme la volée d'une manche.
function ChoixFleches({
  nom,
  zones,
  nbFleches,
  valeurs,
  onChanger,
}: {
  nom: string
  zones: string[]
  nbFleches: number
  valeurs: string[]
  onChanger: (valeurs: string[]) => void
}) {
  const unique = nbFleches === 1
  const complet = valeurs.length >= nbFleches
  return (
    <div className="duel__barrage-camp" role="group" aria-label={`Flèches de barrage de ${nom}`}>
      <span className="duel__volee-nom">
        {nom} : <strong>{valeurs.length === 0 ? '·' : valeurs.join(' ')}</strong>
        {!unique && ` (${totalVolee(valeurs)})`}
      </span>
      <div className="saisie__zones">
        {zones.map((zone) => (
          <button
            key={zone}
            type="button"
            className="saisie__zone"
            aria-pressed={unique ? valeurs[0] === zone : undefined}
            disabled={!unique && complet}
            onClick={() => onChanger(flechesApresZone(valeurs, zone, nbFleches))}
          >
            {zone}
          </button>
        ))}
      </div>
      {!unique && (
        <button
          type="button"
          className="bouton--discret"
          aria-label={`Effacer la dernière flèche de barrage de ${nom}`}
          disabled={valeurs.length === 0}
          onClick={() => onChanger(valeurs.slice(0, -1))}
        >
          Effacer
        </button>
      )}
    </div>
  )
}

// Validation du duel **tranché** (grain fin de duel) : scelle le vainqueur au nom du scoreur, ce qui
// fait avancer le tableau. Activée seulement quand le serveur dit le duel `termine` et non déjà validé.
function Validation({
  tournoiId,
  phaseId,
  matchNumero,
  duel,
  onValide,
  famille,
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  duel: Duel
  onValide: (archerIds: number[]) => void
  famille: FamilleDuel
}) {
  const valider = useValiderDuel(tournoiId, phaseId, matchNumero, famille)
  // Déjà validé, OU validation déjà en file hors-ligne : rien à proposer (le verrou est affiché plus
  // haut). Masquer sur `validation_en_attente` évite de ré-enfiler des validations à chaque tap.
  if (saisieVerrouillee(duel)) return null

  const termine = duel.resultat?.termine === true
  const vainqueur = nomVainqueur(duel)

  return (
    <div className="duel__validation">
      {termine ? (
        <p className="duel__validation-etat" role="status">
          Duel tranché — vainqueur : <strong>{vainqueur}</strong>.
        </p>
      ) : (
        <p className="carte__etat">
          Saisissez les manches (et le barrage si l’égalité l’exige) jusqu’à ce qu’un vainqueur soit
          connu pour valider.
        </p>
      )}
      <button
        type="button"
        disabled={!termine || valider.isPending}
        onClick={() =>
          valider.mutate(
            {
              tournoi_id: tournoiId,
              phase_id: phaseId,
              match_numero: matchNumero,
              identifiant_saisie: nouvelIdentifiant(),
            },
            {
              // Bascule en panneau de routage (E04US018), si `archersARouter` en rend.
              onSuccess: (duelValide) => {
                const archers = archersARouter(duel, duelValide)
                if (archers.length > 0) onValide(archers)
              },
            },
          )
        }
      >
        {valider.isPending ? 'Validation…' : 'Valider le duel'}
      </button>
      <MessageErreurDuel erreur={valider.error} />
    </div>
  )
}

// Message d'erreur d'une écriture de duel. Un `409 duel_desynchronise` (le classement a bougé depuis)
// n'est pas un incident dur : ton **ambre** (DV-03), non bloquant — on invite à régénérer le
// classement, comme le refus de déplacement du plan de duels. Le reste passe par `MessageErreur`.
function MessageErreurDuel({ erreur }: { erreur: Error | null }) {
  if (erreur instanceof ErreurApi && erreur.code === 'duel_desynchronise') {
    return (
      <p className="placement__alerte" role="alert">
        {erreur.message}
      </p>
    )
  }
  return <MessageErreur erreur={erreur} />
}
