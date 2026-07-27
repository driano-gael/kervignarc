// Écran tactile de saisie en duels (E04US013) — la surface du **scoreur** itinérant (D-12).
//
// Le scoreur, sur son téléphone, choisit une **phase de tableau**, voit la **liste des duels par
// tour**, en ouvre un, et le score : une **grille de manches** (sets ou cumul selon `mode`, résolu
// par arme côté serveur — le front n'en décide pas, ADR-0049), un **barrage** conditionnel (§8.2, à
// égalité : une flèche par camp + désignation du plus près du centre, que l'appli ne mesure pas),
// puis la **validation** du duel tranché (grain fin de duel), qui fait avancer le tableau. Le serveur
// reste l'**autorité** (mode, zones du pavé, résultat) ; le front n'affiche que ce qu'il reçoit. La
// saisie survit à une coupure réseau (file hors-ligne + rejeu, E04US009).

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Cote, Duel, Tableau } from './api'
import {
  estJouable,
  grouperParTour,
  libelleMode,
  mancheExistante,
  nouvelIdentifiant,
  prochaineMancheASaisir,
  statutDuel,
  type StatutDuel,
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

const LIBELLE_STATUT: Record<StatutDuel, string> = {
  bye: 'Exempt (bye)',
  attente_adversaires: 'En attente des adversaires',
  a_saisir: 'À saisir',
  en_cours: 'En cours',
  a_valider: 'À valider',
  valide: 'Validé',
}

export function SaisieDuels({ tournoiId }: { tournoiId: number }) {
  // Rejeu de la file hors-ligne à la reconnexion (E04US009) : monté ici, seul endroit où le scoreur
  // saisit — inutile de le faire tourner ailleurs.
  useRejeuDuelsHorsLigne()

  const phases = usePhases(tournoiId)
  const [phaseId, setPhaseId] = useState<number | null>(null)

  // La saisie en duels ne vaut que pour une phase de **tableau** : on ne propose que celles-là (le
  // serveur reste l'autorité — `phase_pas_un_tableau` si l'on force — mais restreindre évite d'y
  // arriver par mégarde). Jumeau du sélecteur du plan de duels (E03US009).
  const tableaux = (phases.data ?? []).filter((p) => p.type === 'elimination_directe')

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
          value={phaseId ?? ''}
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
      {phaseId !== null && <TableauScoreur key={phaseId} tournoiId={tournoiId} phaseId={phaseId} />}
    </div>
  )
}

// Bandeau discret d'actes en attente d'envoi (hors-ligne) — le voyant global de connexion
// (`IndicateurConnexion`) reste dans l'en-tête de l'app ; celui-ci précise la file **des duels**.
function IndicateurAttente() {
  const enAttente = useDuelsEnAttente()
  if (enAttente === 0) return null
  return (
    <span className="duels-saisie__attente" role="status">
      {enAttente} saisie{enAttente > 1 ? 's' : ''} en attente d’envoi
    </span>
  )
}

function TableauScoreur({ tournoiId, phaseId }: { tournoiId: number; phaseId: number }) {
  const tableau = useTableau(tournoiId, phaseId)
  const [matchOuvert, setMatchOuvert] = useState<number | null>(null)

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
      />
    )
  }

  return <ListeDuels tableau={tableau.data} onOuvrir={setMatchOuvert} />
}

// La liste des duels **groupés par libellé de tour** (finale en tête). Le regroupement (par libellé,
// pas par `tour` brut — pour ne pas ranger la petite finale sous « Finale ») est une **logique pure**
// portée par `grouperParTour` (testée dans `duel.ts`). Un duel jouable est tapable pour l'ouvrir ; un
// bye ou un duel sans adversaires connus est affiché mais non ouvrable.
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
  const ouvrable = statut !== 'bye' && statut !== 'attente_adversaires'
  const haut = duel.haut ? `${duel.haut.nom} ${duel.haut.prenom}` : '—'
  const bas = duel.bas ? `${duel.bas.nom} ${duel.bas.prenom}` : '—'

  const contenu = (
    <>
      <span className="duels-liste__duellistes">
        <span>{haut}</span>
        <span className="duels-liste__contre">contre</span>
        <span>{bas}</span>
      </span>
      <span className={`duels-liste__statut duels-liste__statut--${statut}`}>
        {LIBELLE_STATUT[statut]}
      </span>
    </>
  )

  if (!ouvrable) {
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

function Podium({ tableau }: { tableau: Tableau }) {
  return (
    <section className="duels-podium" aria-label="Podium">
      <h4 className="duels-liste__titre">Podium</h4>
      <ol className="duels-podium__places">
        {tableau.podium.map((place) => (
          <li key={place.rang}>
            <strong>{place.rang}.</strong> {place.duelliste.nom} {place.duelliste.prenom}
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
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  onRetour: () => void
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
        />
      )}
    </div>
  )
}

function DuelCharge({
  tournoiId,
  phaseId,
  matchNumero,
  duel,
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  duel: Duel
}) {
  const haut = duel.haut ? `${duel.haut.nom} ${duel.haut.prenom}` : '—'
  const bas = duel.bas ? `${duel.bas.nom} ${duel.bas.prenom}` : '—'
  // Verrou : duel validé (autorité serveur) OU **validation en file hors-ligne** — dans ce dernier cas
  // on ferme la saisie **localement**, comme le ferait le serveur en ligne (`DuelVerrouille`). Sans ce
  // verrou optimiste, le scoreur pourrait rééditer une manche APRÈS avoir validé hors-ligne : au rejeu
  // FIFO, la validation scellerait le résultat d'avant correction, et la manche corrigée rebondirait en
  // 422 (perte silencieuse). Se réconcilie à la relecture serveur post-rejeu (revue adversariale).
  const verrou = duel.validee_par !== null || duel.validation_en_attente === true

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
  const modeLibelle = libelleMode(duel.mode)

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
        <p className="duel__meta">
          {modeLibelle}
          {duel.mode === 'sets' && duel.points_pour_gagner !== null
            ? ` — premier à ${duel.points_pour_gagner} points`
            : ''}
          {duel.en_attente === true ? ' · en attente d’envoi' : ''}
        </p>
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
        />
      )}

      {resultat?.barrage_requis === true && !verrou && (
        <SaisieBarrage
          tournoiId={tournoiId}
          phaseId={phaseId}
          matchNumero={matchNumero}
          duel={duel}
        />
      )}

      <Validation tournoiId={tournoiId} phaseId={phaseId} matchNumero={matchNumero} duel={duel} />
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
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  duel: Duel
}) {
  const nbManches = duel.nb_manches ?? 1
  const nbFleches = duel.nb_fleches_par_volee ?? 3
  const saisir = useSaisirManche(tournoiId, phaseId, matchNumero)

  const [numeroChoisi, setNumeroChoisi] = useState<number | null>(null)
  const numeroActif = numeroChoisi ?? prochaineMancheASaisir(duel, nbManches)
  const existante = mancheExistante(duel, numeroActif)

  // Tampons remis au contenu **persisté** de la manche visée quand elle change (ajustement d'état
  // **au rendu**, pas en effet — le pattern recommandé pour réinitialiser sans cascade).
  const signature = `${numeroActif}:${(existante?.haut ?? []).join(',')}:${(existante?.bas ?? []).join(',')}`
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

  const buffer = campActif === 'haut' ? bufferHaut : bufferBas
  const poserBuffer = campActif === 'haut' ? setBufferHaut : setBufferBas
  const campComplet = buffer.length >= nbFleches
  const deuxComplets = bufferHaut.length >= nbFleches && bufferBas.length >= nbFleches

  const ajouter = (zone: string) => {
    if (campComplet || saisir.isPending) return
    poserBuffer((actuel) => {
      const suite = [...actuel, zone]
      // Camp rempli : bascule automatiquement sur l'autre s'il reste à saisir (fluidité tactile).
      if (suite.length >= nbFleches) {
        const autre = campActif === 'haut' ? bufferBas : bufferHaut
        if (autre.length < nbFleches) setCampActif(campActif === 'haut' ? 'bas' : 'haut')
      }
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
          nom={duel.haut ? duel.haut.nom : 'Haut'}
          valeurs={bufferHaut}
          nbFleches={nbFleches}
          actif={campActif === 'haut'}
          onActiver={() => setCampActif('haut')}
        />
        <VoleeCamp
          nom={duel.bas ? duel.bas.nom : 'Bas'}
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
            disabled={campComplet || saisir.isPending}
            onClick={() => ajouter(zone)}
          >
            {zone}
          </button>
        ))}
      </div>

      <div className="saisie__actions">
        <button
          type="button"
          className="bouton--discret"
          disabled={buffer.length === 0 || saisir.isPending}
          onClick={effacer}
        >
          Effacer
        </button>
        <button type="button" disabled={!deuxComplets || saisir.isPending} onClick={enregistrer}>
          {saisir.isPending ? 'Enregistrement…' : 'Enregistrer la manche'}
        </button>
      </div>

      <MessageErreurDuel erreur={saisir.error} />
    </div>
  )
}

// Une volée d'un camp : nom, pastilles des flèches, total provisoire. Tapable pour devenir le camp
// **actif** (celui que le pavé remplit). Cible tactile ≥ 48 px.
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
      <span className="duel__volee-nom">{nom}</span>
      <span className="duel__volee-fleches" aria-live="polite">
        {Array.from({ length: nbFleches }, (_, i) => (
          <span key={i} className="saisie__fleche">
            {valeurs[i] ?? '·'}
          </span>
        ))}
      </span>
      <span className="duel__volee-total">{totalVolee(valeurs)}</span>
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
      {Array.from({ length: nbManches }, (_, i) => {
        const numero = i + 1
        const saisie = duel.manches.some((m) => m.numero === numero)
        const classes = [
          'saisie__nav-volee',
          saisie ? 'saisie__nav-volee--saisie' : '',
          numero === numeroActif ? 'saisie__nav-volee--actif' : '',
        ]
          .filter((c) => c !== '')
          .join(' ')
        return (
          <button
            key={numero}
            type="button"
            className={classes}
            aria-pressed={numero === numeroActif}
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
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  duel: Duel
}) {
  const saisir = useSaisirBarrage(tournoiId, phaseId, matchNumero)
  const [flecheHaut, setFlecheHaut] = useState<string | null>(duel.barrage?.haut ?? null)
  const [flecheBas, setFlecheBas] = useState<string | null>(duel.barrage?.bas ?? null)
  const [designe, setDesigne] = useState<Cote | null>(duel.barrage?.gagnant_designe ?? null)

  // Resynchronisation **au rendu** si le barrage serveur change (rejeu / relecture) pendant que le
  // formulaire reste monté — même pattern que la grille de manche. Sans quoi la sélection resterait
  // figée sur les valeurs du montage.
  const signatureBarrage = `${duel.barrage?.haut ?? ''}:${duel.barrage?.bas ?? ''}:${duel.barrage?.gagnant_designe ?? ''}`
  const [ancreBarrage, setAncreBarrage] = useState(signatureBarrage)
  if (ancreBarrage !== signatureBarrage) {
    setAncreBarrage(signatureBarrage)
    setFlecheHaut(duel.barrage?.haut ?? null)
    setFlecheBas(duel.barrage?.bas ?? null)
    setDesigne(duel.barrage?.gagnant_designe ?? null)
  }

  // La désignation n'est requise (et proposée) que si les deux flèches sont saisies **et égales**.
  const egales = flecheHaut !== null && flecheBas !== null && flecheHaut === flecheBas
  const pretAEnvoyer = flecheHaut !== null && flecheBas !== null && (!egales || designe !== null)

  const enregistrer = () => {
    if (flecheHaut === null || flecheBas === null) return
    saisir.mutate({
      tournoi_id: tournoiId,
      phase_id: phaseId,
      match_numero: matchNumero,
      fleche_haut: flecheHaut,
      fleche_bas: flecheBas,
      gagnant_designe: egales ? designe : null,
      identifiant_saisie: nouvelIdentifiant(),
    })
  }

  return (
    <div className="duel__barrage">
      <p className="duel__barrage-titre">Barrage (une flèche par archer, le plus près du centre)</p>
      <div className="duel__barrage-camps">
        <ChoixFleche
          nom={duel.haut ? duel.haut.nom : 'Haut'}
          zones={duel.zones}
          valeur={flecheHaut}
          onChoisir={setFlecheHaut}
        />
        <ChoixFleche
          nom={duel.bas ? duel.bas.nom : 'Bas'}
          zones={duel.zones}
          valeur={flecheBas}
          onChoisir={setFlecheBas}
        />
      </div>

      {egales && (
        <div className="duel__designation" role="group" aria-label="Plus près du centre">
          <span>Flèches à égalité — qui est le plus près du centre ?</span>
          <div className="duel__designation-choix">
            <button
              type="button"
              className={designe === 'haut' ? undefined : 'bouton--discret'}
              aria-pressed={designe === 'haut'}
              onClick={() => setDesigne('haut')}
            >
              {duel.haut ? duel.haut.nom : 'Haut'}
            </button>
            <button
              type="button"
              className={designe === 'bas' ? undefined : 'bouton--discret'}
              aria-pressed={designe === 'bas'}
              onClick={() => setDesigne('bas')}
            >
              {duel.bas ? duel.bas.nom : 'Bas'}
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

// Choix d'**une** flèche (barrage) parmi les zones du blason : un mini-pavé à sélection unique.
function ChoixFleche({
  nom,
  zones,
  valeur,
  onChoisir,
}: {
  nom: string
  zones: string[]
  valeur: string | null
  onChoisir: (zone: string) => void
}) {
  return (
    <div className="duel__barrage-camp">
      <span className="duel__volee-nom">
        {nom} : <strong>{valeur ?? '·'}</strong>
      </span>
      <div className="saisie__zones">
        {zones.map((zone) => (
          <button
            key={zone}
            type="button"
            className="saisie__zone"
            aria-pressed={valeur === zone}
            onClick={() => onChoisir(zone)}
          >
            {zone}
          </button>
        ))}
      </div>
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
}: {
  tournoiId: number
  phaseId: number
  matchNumero: number
  duel: Duel
}) {
  const valider = useValiderDuel(tournoiId, phaseId, matchNumero)
  // Déjà validé, OU validation déjà en file hors-ligne : rien à proposer (le verrou est affiché plus
  // haut). Masquer sur `validation_en_attente` évite de ré-enfiler des validations à chaque tap.
  if (duel.validee_par !== null || duel.validation_en_attente === true) return null

  const resultat = duel.resultat
  const termine = resultat?.termine === true
  const vainqueur =
    resultat?.vainqueur === 'haut'
      ? (duel.haut?.nom ?? 'Haut')
      : resultat?.vainqueur === 'bas'
        ? (duel.bas?.nom ?? 'Bas')
        : null

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
          valider.mutate({
            tournoi_id: tournoiId,
            phase_id: phaseId,
            match_numero: matchNumero,
            identifiant_saisie: nouvelIdentifiant(),
          })
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
