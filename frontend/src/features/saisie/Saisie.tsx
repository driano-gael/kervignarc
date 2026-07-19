// Écran de saisie du poste de cible (E04US002) — le poste du **marqueur**.
//
// « La tablette appartient à la cible, pas à la personne » (CDC UX §7.2). Un marqueur (un archer de
// la cible, désigné FFTA B.6.1.1) tape ce que chacun annonce : une grille des 3–4 archers, un pavé
// **déduit du blason** (touches illégales absentes), le **grain de validation** affiché (D-11), le
// marqueur **discret et tapable** (D-04 : l'interface ne s'organise pas autour d'un changement rare).
//
// Périmètre de cette tranche : la **saisie** (et la ré-édition avant validation). La **validation**
// et la **correction** sont l'acte du **scoreur**, sur sa propre surface (§7.3) — hors d'ici. Le
// **panneau de routage** post-validation est E04US018 (bloquée) ; la **file hors-ligne** et la
// **diffusion live**, E04US009.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import type { Bareme, LigneGrille } from './api'
import {
  useBareme,
  useDeparts,
  useFixerDepart,
  useGrain,
  useGrille,
  useSaisirVolee,
  useSerie,
} from './hooks'
import {
  heureSaisie,
  libelleGrain,
  nouvelIdentifiant,
  prochaineASaisir,
  totalVolee,
  voleeExistante,
} from './volees'

export function Saisie({ tournoiId, cibleIndex }: { tournoiId: number; cibleIndex: number }) {
  const grille = useGrille()
  const bareme = useBareme(tournoiId)
  const grain = useGrain(tournoiId)

  const [archerChoisi, setArcherChoisi] = useState<number | null>(null)
  const [marqueur, setMarqueur] = useState<string | null>(null)

  // Départ courant non fixé : le serveur refuse la grille (409, ADR-0034 §1). C'est un état attendu,
  // pas un incident — on invite à choisir un départ plutôt que d'afficher une erreur.
  const besoinDepart =
    grille.isError &&
    grille.error instanceof ErreurApi &&
    grille.error.code === 'depart_courant_non_defini'

  const lignes = grille.data ?? []

  // Archer et marqueur actifs **dérivés** (pas d'état par défaut posé en effet, qui cascaderait) : le
  // choix explicite s'il est encore dans la grille, sinon le premier archer (position A). Ainsi le
  // pavé est utilisable tout de suite, et un choix devenu obsolète (changement de départ) retombe
  // proprement sur A au lieu de pointer un archer disparu.
  const premier = lignes[0]
  const archerActif =
    archerChoisi !== null && lignes.some((l) => l.archer_id === archerChoisi)
      ? archerChoisi
      : (premier?.archer_id ?? null)
  const marqueurActif =
    marqueur !== null && lignes.some((l) => l.nom === marqueur) ? marqueur : (premier?.nom ?? null)

  const ligneActive = lignes.find((l) => l.archer_id === archerActif) ?? null

  return (
    <div className="saisie">
      <div className="saisie__entete">
        <strong>Cible {cibleIndex}</strong>
        {lignes.length > 0 && (
          <SelecteurMarqueur lignes={lignes} marqueur={marqueurActif} onChoisir={setMarqueur} />
        )}
      </div>

      {besoinDepart || grille.isSuccess ? (
        <SelecteurDepart tournoiId={tournoiId} obligatoire={besoinDepart} />
      ) : null}

      {grille.isError && !besoinDepart && <MessageErreur erreur={grille.error} />}

      {grille.isSuccess && lignes.length === 0 && (
        <p className="saisie__vide" role="status">
          Aucun archer placé sur cette cible pour ce départ.
        </p>
      )}

      {grille.isSuccess && lignes.length > 0 && (
        <>
          <ul className="saisie__grille">
            {lignes.map((ligne) => (
              <LigneArcher
                key={ligne.archer_id}
                tournoiId={tournoiId}
                ligne={ligne}
                nbVolees={bareme.data?.nb_volees ?? null}
                actif={ligne.archer_id === archerActif}
                onSelectionner={() => setArcherChoisi(ligne.archer_id)}
              />
            ))}
          </ul>

          {ligneActive !== null && bareme.data !== null && bareme.data !== undefined ? (
            <PaveArcher
              key={ligneActive.archer_id}
              tournoiId={tournoiId}
              ligne={ligneActive}
              bareme={bareme.data}
              marqueur={marqueurActif}
            />
          ) : bareme.isSuccess && bareme.data === null ? (
            <p className="saisie__vide" role="status">
              Barème de qualification non défini pour ce tournoi : configurez la phase avant de
              saisir.
            </p>
          ) : null}
        </>
      )}

      <p className="saisie__grain">{libelleGrain(grain.data ?? null)}</p>
    </div>
  )
}

// Le marqueur : discret par défaut (« Marqueur : NOM »), une liste qui se déplie au besoin (D-04).
// Chaque volée enregistrera ce nom (`saisie_par`) — l'équivalent numérique de la signature.
function SelecteurMarqueur({
  lignes,
  marqueur,
  onChoisir,
}: {
  lignes: LigneGrille[]
  marqueur: string | null
  onChoisir: (nom: string) => void
}) {
  const [ouvert, setOuvert] = useState(false)
  return (
    <div className="saisie__marqueur">
      <button
        type="button"
        className="lien saisie__marqueur-libelle"
        aria-expanded={ouvert}
        onClick={() => setOuvert((o) => !o)}
      >
        Marqueur : <strong>{marqueur ?? '—'}</strong> ▾
      </button>
      {ouvert && (
        <ul className="saisie__marqueur-choix" role="listbox" aria-label="Choisir le marqueur">
          {lignes.map((ligne) => (
            <li key={ligne.archer_id}>
              <button
                type="button"
                className="lien"
                aria-selected={ligne.nom === marqueur}
                onClick={() => {
                  onChoisir(ligne.nom)
                  setOuvert(false)
                }}
              >
                {ligne.nom} {ligne.prenom}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// « Mettre le poste en mode départ X » (ADR-0034). Affiché en grand tant que le départ n'est pas
// fixé (`obligatoire`), sinon repliable (« Changer de départ ») — un poste sert le même départ toute
// la matinée, le sélecteur ne doit pas encombrer.
function SelecteurDepart({ tournoiId, obligatoire }: { tournoiId: number; obligatoire: boolean }) {
  const departs = useDeparts(tournoiId)
  const fixer = useFixerDepart()
  const [ouvert, setOuvert] = useState(false)
  const deplie = obligatoire || ouvert

  return (
    <div className="saisie__departs">
      {obligatoire ? (
        <p className="saisie__vide" role="status">
          Choisissez le départ que sert cette cible pour afficher la grille.
        </p>
      ) : (
        <button type="button" className="lien" onClick={() => setOuvert((o) => !o)}>
          Changer de départ
        </button>
      )}
      {deplie && (
        <div className="saisie__departs-liste">
          {departs.data?.map((depart) => (
            <button
              key={depart.id}
              type="button"
              className="bouton--discret"
              disabled={fixer.isPending}
              aria-pressed={fixer.data?.depart_id === depart.id}
              onClick={() => {
                fixer.mutate(depart.id, { onSuccess: () => setOuvert(false) })
              }}
            >
              Départ {depart.numero}
              {depart.horaire !== null ? ` — ${depart.horaire}` : ''}
            </button>
          ))}
          <MessageErreur erreur={fixer.error} />
        </div>
      )}
    </div>
  )
}

// Une ligne de la grille : position, nom, cumul (validé) et avancement. Tapable pour devenir
// l'archer **actif** (celui dont le pavé saisit). Cible tactile ≥ 48 px (écran de saisie).
function LigneArcher({
  tournoiId,
  ligne,
  nbVolees,
  actif,
  onSelectionner,
}: {
  tournoiId: number
  ligne: LigneGrille
  nbVolees: number | null
  actif: boolean
  onSelectionner: () => void
}) {
  const serie = useSerie(tournoiId, ligne.archer_id)
  const nbSaisies = serie.data?.volees.length ?? 0
  const cumul = serie.data?.cumul ?? 0

  return (
    <li>
      <button
        type="button"
        className={`saisie__ligne${actif ? ' saisie__ligne--actif' : ''}`}
        aria-pressed={actif}
        onClick={onSelectionner}
      >
        <span className="saisie__position">{ligne.position}</span>
        <span className="saisie__nom">
          {ligne.nom} <span className="saisie__prenom">{ligne.prenom}</span>
        </span>
        <span className="saisie__avancement">
          {nbSaisies}/{nbVolees ?? '?'} volées
        </span>
        <span className="saisie__cumul">{cumul}</span>
      </button>
    </li>
  )
}

// Le pavé de l'archer actif : les zones **de son blason** (touches illégales absentes), la volée en
// cours de frappe, correction (Effacer) et enregistrement. La saisie passe par la file d'écriture
// serveur ; l'identifiant rend le geste **idempotent** (ADR-0036) — un identifiant neuf par volée.
// Un **navigateur de volées** permet de revenir sur une volée déjà saisie tant qu'elle n'est pas
// verrouillée (CA « édition avant validation »).
function PaveArcher({
  tournoiId,
  ligne,
  bareme,
  marqueur,
}: {
  tournoiId: number
  ligne: LigneGrille
  bareme: Bareme
  marqueur: string | null
}) {
  const serie = useSerie(tournoiId, ligne.archer_id)
  const saisir = useSaisirVolee(tournoiId, ligne.archer_id)
  const volees = serie.data?.volees ?? []

  // Volée visée : le choix explicite (navigateur), sinon la prochaine non saisie.
  const [numeroChoisi, setNumeroChoisi] = useState<number | null>(null)
  const numeroActif = numeroChoisi ?? prochaineASaisir(volees, bareme.nb_volees)
  const existante = voleeExistante(volees, numeroActif)
  const verrouillee = existante?.verrouillee ?? false
  const valeursExistantes = existante?.valeurs

  // Tampon de la frappe, remis au contenu **persisté** de la volée visée quand celle-ci change (ou
  // quand la série relue change après un enregistrement). Ajustement d'état **au rendu** (pas en
  // effet) : le pattern recommandé pour réinitialiser un état sur changement d'entrée sans cascade.
  const signature = `${numeroActif}:${(valeursExistantes ?? []).join(',')}`
  const [ancre, setAncre] = useState(signature)
  const [buffer, setBuffer] = useState<string[]>(valeursExistantes ?? [])
  if (ancre !== signature) {
    setAncre(signature)
    setBuffer(valeursExistantes ?? [])
  }

  if (ligne.zones.length === 0) {
    return (
      <p className="saisie__vide" role="status">
        Pavé indisponible pour {ligne.nom} : blason non configuré.
      </p>
    )
  }

  // Tant que la série n'est pas chargée, `volees` est vide et `numeroActif` pointerait la volée 1
  // par défaut : on désactive la frappe pour ne pas saisir « à l'aveugle » puis voir le tampon se
  // réinitialiser à l'arrivée des données (perte silencieuse). Fenêtre courte en LAN, verrou franc.
  const chargee = serie.isSuccess
  const complet = buffer.length >= bareme.nb_fleches_par_volee
  const ajouter = (valeur: string) => {
    if (chargee && !complet && !verrouillee) setBuffer((actuel) => [...actuel, valeur])
  }
  const effacer = () => setBuffer((actuel) => actuel.slice(0, -1))
  const enregistrer = () => {
    saisir.mutate(
      {
        tournoi_id: tournoiId,
        archer_id: ligne.archer_id,
        numero: numeroActif,
        valeurs: buffer,
        // Nouvelle volée : le marqueur actif la signe. Ré-édition d'une volée déjà saisie : `null`,
        // pour que le domaine **préserve** le marqueur d'origine (une correction ne réattribue pas
        // la signature — cf. `Serie.saisir_volee`, chemin « saisie_par is None »).
        saisie_par: existante !== null ? null : marqueur,
        identifiant_saisie: nouvelIdentifiant(),
      },
      // De retour en mode « prochaine à saisir » : après avoir enregistré la volée visée, on avance.
      { onSuccess: () => setNumeroChoisi(null) },
    )
  }

  return (
    <div className="saisie__pave">
      <NavigateurVolees
        nbVolees={bareme.nb_volees}
        volees={volees}
        numeroActif={numeroActif}
        onChoisir={setNumeroChoisi}
      />

      <div className="saisie__pave-entete">
        <span>
          Volée {numeroActif}/{bareme.nb_volees} — <strong>{ligne.nom}</strong>
        </span>
        <span className="saisie__total">
          {buffer.length}/{bareme.nb_fleches_par_volee} · {totalVolee(buffer)} pts
        </span>
      </div>

      {existante !== null && (
        <p className="saisie__meta">
          Saisie par <strong>{existante.saisie_par ?? '—'}</strong>
          {existante.saisie_le !== null ? ` à ${heureSaisie(existante.saisie_le)}` : ''}
          {existante.validee_par !== null ? ` · validée par ${existante.validee_par}` : ''}
        </p>
      )}

      {verrouillee && (
        <p className="saisie__vide" role="status">
          Volée validée par {existante?.validee_par ?? 'le scoreur'} — sa correction relève du
          scoreur.
        </p>
      )}

      <div className="saisie__buffer" aria-live="polite">
        {Array.from({ length: bareme.nb_fleches_par_volee }, (_, i) => (
          <span key={i} className="saisie__fleche">
            {buffer[i] ?? '·'}
          </span>
        ))}
      </div>

      <div className="saisie__zones">
        {ligne.zones.map((zone) => (
          <button
            key={zone}
            type="button"
            className="saisie__zone"
            disabled={!chargee || complet || verrouillee || saisir.isPending}
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
          disabled={buffer.length === 0 || verrouillee || saisir.isPending}
          onClick={effacer}
        >
          Effacer
        </button>
        <button
          type="button"
          disabled={!chargee || !complet || verrouillee || saisir.isPending}
          onClick={enregistrer}
        >
          {saisir.isPending ? 'Enregistrement…' : 'Enregistrer la volée'}
        </button>
      </div>

      <MessageErreur erreur={saisir.error} />
    </div>
  )
}

// Navigateur de volées : une pastille par volée du barème. Saisie = pleine, verrouillée = cadenassée,
// visée = surlignée. Tapable pour revenir corriger une volée non encore validée (édition avant
// validation), ou repartir sur la suivante.
function NavigateurVolees({
  nbVolees,
  volees,
  numeroActif,
  onChoisir,
}: {
  nbVolees: number
  volees: { numero: number; verrouillee: boolean }[]
  numeroActif: number
  onChoisir: (numero: number) => void
}) {
  return (
    <div className="saisie__nav" role="group" aria-label="Volées">
      {Array.from({ length: nbVolees }, (_, i) => {
        const numero = i + 1
        const volee = volees.find((v) => v.numero === numero)
        const classes = [
          'saisie__nav-volee',
          volee !== undefined ? 'saisie__nav-volee--saisie' : '',
          volee?.verrouillee ? 'saisie__nav-volee--verrou' : '',
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

// DETTE-004 (docs/dette.md) : copie conforme du composant d'erreur, une par feature (extraction en
// E00US013). Non factorisée ici — toucherait les autres features, hors périmètre de cette US.
function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
