// Cockpit de simulation (E15US003) — bot pilote automatique pausable + reprise en main multi-vues.
//
// Rejoue le tournoi courant **sans rien enregistrer** (ADR-0054/0055) : un bot génère des scores et
// fait avancer qualif → duels → classement. Le pilote automatique est un **ticker** qui appelle
// « avancer » tant que la session est *en cours* (ADR-0055 §2, décision serveur : pas de boucle de
// fond). Mettre en pause suspend le bot et **ouvre la reprise en main** : l'humain saisit une volée
// (rôle cible) ou désigne un vainqueur (rôle scoreur) sur la **même** unité que le bot, puis rend la
// main. Une navbar bascule entre les vues cible / archer / scoreur / public de l'état simulé.
//
// ⚠️ Front sans tests de rendu (story E15US003) : à vérifier à l'écran. Le canal `/ws/simulation`
// (isolé) invalide l'état si un autre client agit ; chaque action renvoyant déjà l'état frais, il
// n'est qu'un filet de synchronisation.

import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { RealtimeClient } from '../../shared/realtime/RealtimeClient'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { TableClassement } from '../competition/TableClassement'
import { arreter } from './api'
import type { EtatSession, ProchaineVolee, TableauSimule } from './api'
import {
  cleSession,
  useAvancer,
  useDemarrerSimulation,
  useDesignerVainqueur,
  useDetailArcher,
  useEtatSimulation,
  usePause,
  useReprendre,
  useSaisirVolee,
  useTerminer,
} from './hooks'

const DELAI_TICK_MS = 450
const VITESSES: { libelle: string; pas: number }[] = [
  { libelle: 'Lent', pas: 1 },
  { libelle: 'Normal', pas: 4 },
  { libelle: 'Rapide', pas: 15 },
]

type Vue = 'public' | 'cible' | 'archer' | 'scoreur'

export function Simulation({ tournoiId }: { tournoiId: number }) {
  const queryClient = useQueryClient()
  const [sessionId, setSessionId] = useState<number | null>(null)
  const etatQuery = useEtatSimulation(sessionId)
  const etat = etatQuery.data ?? null

  // Ré-abonnement au canal **isolé** de la simulation : sur signal, on invalide l'état de la session
  // (un autre admin a pu agir). Détaché du canal réel et de son indicateur de connexion.
  useEffect(() => {
    if (sessionId === null) return
    const client = new RealtimeClient({
      chemin: '/ws/simulation',
      onStatut: () => {},
      onEvenement: () => {
        void queryClient.invalidateQueries({ queryKey: cleSession(sessionId) })
      },
    })
    client.connecter()
    return () => client.fermer()
  }, [sessionId, queryClient])

  if (sessionId === null || etat === null) {
    return (
      <Demarrage
        tournoiId={tournoiId}
        onDemarre={(nouvelEtat) => {
          queryClient.setQueryData(cleSession(nouvelEtat.session_id), nouvelEtat)
          setSessionId(nouvelEtat.session_id)
        }}
      />
    )
  }

  // « Arrêter » **libère la session serveur** (DELETE idempotent) avant de détacher le front — sinon
  // le harnais in-memory resterait dans le registre jusqu'au redémarrage (fuite mémoire, revue C1).
  const arreterSession = () => {
    void arreter(sessionId).catch(() => {})
    setSessionId(null)
  }
  return <Cockpit etat={etat} sessionId={sessionId} onArrete={arreterSession} />
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Démarrage d'une session
// ————————————————————————————————————————————————————————————————————————————————————————————————

function Demarrage({
  tournoiId,
  onDemarre,
}: {
  tournoiId: number
  onDemarre: (etat: EtatSession) => void
}) {
  const [graine, setGraine] = useState('')
  const demarrer = useDemarrerSimulation()

  const lancer = () => {
    const valeur = graine.trim() === '' ? undefined : Number(graine)
    demarrer.mutate({ tournoiId, graine: valeur }, { onSuccess: onDemarre })
  }

  return (
    <section className="carte">
      <h2 className="carte__titre">Simulation du tournoi</h2>
      <p className="carte__etat">
        Un robot rejoue ce tournoi en accéléré <strong>sans rien enregistrer</strong> :
        qualifications puis duels, jusqu'au classement. Vous pouvez mettre en pause à tout moment
        pour saisir vous-même à la place d'un rôle, puis rendre la main.
      </p>
      <div className="formulaire__ligne">
        <label className="formulaire__libelle" htmlFor="simulation-graine">
          Graine (facultatif — rend le tirage rejouable)
        </label>
        <input
          id="simulation-graine"
          className="formulaire__champ"
          type="number"
          value={graine}
          onChange={(e) => setGraine(e.target.value)}
          placeholder="ex. 42"
        />
      </div>
      <MessageErreur erreur={demarrer.error} />

      <button type="button" onClick={lancer} disabled={demarrer.isPending}>
        {demarrer.isPending ? 'Démarrage…' : 'Démarrer la simulation'}
      </button>
    </section>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Cockpit : bandeau de pilotage + navbar + vue active
// ————————————————————————————————————————————————————————————————————————————————————————————————

function Cockpit({
  etat,
  sessionId,
  onArrete,
}: {
  etat: EtatSession
  sessionId: number
  onArrete: () => void
}) {
  const [vue, setVue] = useState<Vue>('public')
  const [vitesse, setVitesse] = useState(VITESSES[1]!.pas)
  const avancer = useAvancer()
  const pause = usePause()
  const reprendre = useReprendre()
  const terminer = useTerminer()

  const enCours = etat.etat_pilote === 'en_cours'
  const enPause = etat.etat_pilote === 'en_pause'
  const terminee = etat.etat_pilote === 'terminee'

  // Pilote automatique : tant que la session est *en cours*, on replanifie un pas après chaque
  // avancée (dépendances primitives : le pas se déclenche quand les compteurs changent). Mettre en
  // pause ou terminer coupe la boucle (l'état n'est plus « en cours »).
  const avancerMutate = avancer.mutate
  useEffect(() => {
    if (!enCours) return
    const minuterie = setTimeout(() => avancerMutate({ sessionId, nbPas: vitesse }), DELAI_TICK_MS)
    return () => clearTimeout(minuterie)
  }, [
    enCours,
    sessionId,
    vitesse,
    avancerMutate,
    etat.progression.volees_faites,
    etat.progression.duels_faits,
  ])

  return (
    <section className="carte">
      <h2 className="carte__titre">Simulation — {etat.tournoi_nom}</h2>

      <div className="simulation__bandeau">
        <EtatBadge etat={etat} />
        <Progression etat={etat} />
        {/* Un échec de pilotage (ex. session perdue au redémarrage serveur) ne doit pas figer le
            cockpit en silence : le pilote automatique s'arrête, on le dit (revue B/C1/D). */}
        <MessageErreur erreur={avancer.error ?? pause.error ?? reprendre.error ?? terminer.error} />
        <div className="simulation__controles">
          {enCours && (
            <button type="button" onClick={() => pause.mutate(sessionId)}>
              ⏸ Pause
            </button>
          )}
          {enPause && (
            <button type="button" onClick={() => reprendre.mutate(sessionId)}>
              ▶ Reprendre
            </button>
          )}
          {!terminee && (
            <button type="button" onClick={() => terminer.mutate(sessionId)}>
              ⏭ Terminer
            </button>
          )}
          <label className="simulation__vitesse">
            Vitesse
            <select
              className="formulaire__champ"
              value={vitesse}
              onChange={(e) => setVitesse(Number(e.target.value))}
              disabled={terminee}
            >
              {VITESSES.map((v) => (
                <option key={v.pas} value={v.pas}>
                  {v.libelle}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={onArrete}>
            ✕ Arrêter
          </button>
        </div>
      </div>

      <nav className="simulation__navbar" aria-label="Vues de la simulation">
        {(
          [
            ['public', 'Public'],
            ['cible', 'Cible'],
            ['archer', 'Archer'],
            ['scoreur', 'Scoreur'],
          ] as [Vue, string][]
        ).map(([id, libelle]) => (
          <button
            key={id}
            type="button"
            className={
              id === vue ? 'simulation__onglet simulation__onglet--actif' : 'simulation__onglet'
            }
            aria-current={id === vue ? 'page' : undefined}
            onClick={() => setVue(id)}
          >
            {libelle}
          </button>
        ))}
      </nav>

      <div className="simulation__vue">
        {vue === 'public' && <VuePublic etat={etat} />}
        {vue === 'cible' && <VueCible etat={etat} sessionId={sessionId} enPause={enPause} />}
        {vue === 'archer' && <VueArcher etat={etat} sessionId={sessionId} />}
        {vue === 'scoreur' && <VueScoreur etat={etat} sessionId={sessionId} enPause={enPause} />}
      </div>
    </section>
  )
}

function EtatBadge({ etat }: { etat: EtatSession }) {
  const libellePilote =
    etat.etat_pilote === 'en_cours'
      ? 'En cours'
      : etat.etat_pilote === 'en_pause'
        ? 'En pause'
        : 'Terminée'
  const libelleEtape =
    etat.etape === 'qualification' ? 'Qualifications' : etat.etape === 'duels' ? 'Duels' : 'Terminé'
  return (
    <p className="simulation__etat">
      <span className={`simulation__pastille simulation__pastille--${etat.etat_pilote}`}>
        {libellePilote}
      </span>{' '}
      · Étape : <strong>{libelleEtape}</strong> · graine {etat.graine}
    </p>
  )
}

function Progression({ etat }: { etat: EtatSession }) {
  const { volees_faites, volees_total, duels_faits, duels_total } = etat.progression
  return (
    <div className="simulation__progression">
      <label>
        Volées {volees_faites}/{volees_total}
        <progress value={volees_faites} max={Math.max(volees_total, 1)} />
      </label>
      <label>
        Duels {duels_faits}/{duels_total}
        <progress value={duels_faits} max={Math.max(duels_total, 1)} />
      </label>
    </div>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Vue publique : classement + tableaux
// ————————————————————————————————————————————————————————————————————————————————————————————————

function VuePublic({ etat }: { etat: EtatSession }) {
  return (
    <div>
      <h3 className="carte__sous-titre">Classement</h3>
      <TableClassement tournoiId={etat.tournoi_id} lignes={etat.classement.lignes} admin={false} />
      {etat.tableaux.map((tableau, index) => (
        <TableauDuels key={index} tableau={tableau} />
      ))}
    </div>
  )
}

function TableauDuels({ tableau }: { tableau: TableauSimule }) {
  return (
    <div className="simulation__tableau">
      <h3 className="carte__sous-titre">
        Tableau à {tableau.effectif} — {tableau.est_termine ? 'terminé' : 'en cours'}
      </h3>
      {tableau.podium.length > 0 && (
        <ol className="simulation__podium">
          {tableau.podium.map((place) => (
            <li key={place.rang}>
              {place.rang}. {place.duelliste.nom} {place.duelliste.prenom}
            </li>
          ))}
        </ol>
      )}
      <ListeDuels duels={tableau.duels} />
    </div>
  )
}

function ListeDuels({ duels }: { duels: TableauSimule['duels'] }) {
  const jouables = duels.filter((duel) => !duel.est_bye && duel.haut && duel.bas)
  if (jouables.length === 0) return <p className="carte__etat">Aucun duel à afficher.</p>
  return (
    <table className="table">
      <thead>
        <tr>
          <th scope="col">Tour</th>
          <th scope="col">Duel</th>
          <th scope="col">Vainqueur</th>
        </tr>
      </thead>
      <tbody>
        {jouables.map((duel) => {
          const vainqueur =
            duel.resultat?.vainqueur === 'haut'
              ? duel.haut
              : duel.resultat?.vainqueur === 'bas'
                ? duel.bas
                : null
          return (
            <tr key={duel.numero}>
              <td>{duel.tour}</td>
              <td>
                {duel.haut?.nom} {duel.haut?.prenom} vs {duel.bas?.nom} {duel.bas?.prenom}
              </td>
              <td>{vainqueur ? `${vainqueur.nom} ${vainqueur.prenom}` : '—'}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Vue cible : la volée en cours + saisie manuelle en pause
// ————————————————————————————————————————————————————————————————————————————————————————————————

function VueCible({
  etat,
  sessionId,
  enPause,
}: {
  etat: EtatSession
  sessionId: number
  enPause: boolean
}) {
  const unite = etat.prochaine_unite
  if (etat.etape !== 'qualification' || unite?.genre !== 'volee' || unite.volee === null) {
    return (
      <p className="carte__etat">
        Les qualifications sont terminées : rien à saisir sur une cible.
      </p>
    )
  }
  const volee = unite.volee
  return (
    <div>
      <p className="carte__etat">
        Prochaine volée :{' '}
        <strong>
          {volee.archer_nom} {volee.archer_prenom}
        </strong>
        , volée n°
        {volee.numero_volee} ({volee.nb_fleches} flèches).
      </p>
      {enPause ? (
        <SaisieVolee
          key={`${volee.archer_id}-${volee.numero_volee}`}
          sessionId={sessionId}
          volee={volee}
        />
      ) : (
        <p className="carte__etat">
          Mettez en pause pour saisir cette volée à la place de la cible.
        </p>
      )}
    </div>
  )
}

function SaisieVolee({ sessionId, volee }: { sessionId: number; volee: ProchaineVolee }) {
  const premiere = volee.zones[0] ?? 'M'
  const [valeurs, setValeurs] = useState<string[]>(() => Array(volee.nb_fleches).fill(premiere))
  const saisir = useSaisirVolee()

  const soumettre = () => {
    saisir.mutate({
      sessionId,
      archerId: volee.archer_id,
      numeroVolee: volee.numero_volee,
      valeurs,
    })
  }

  return (
    <div className="simulation__saisie">
      {valeurs.map((valeur, index) => (
        <select
          key={index}
          className="formulaire__champ"
          aria-label={`Flèche ${index + 1}`}
          value={valeur}
          onChange={(e) =>
            setValeurs((precedent) => precedent.map((v, i) => (i === index ? e.target.value : v)))
          }
        >
          {volee.zones.map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </select>
      ))}
      <MessageErreur erreur={saisir.error} />
      <button type="button" onClick={soumettre} disabled={saisir.isPending}>
        Valider la volée
      </button>
    </div>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Vue archer : sa journée (volées, cumul)
// ————————————————————————————————————————————————————————————————————————————————————————————————

function VueArcher({ etat, sessionId }: { etat: EtatSession; sessionId: number }) {
  const [archerId, setArcherId] = useState<number | null>(null)
  const detail = useDetailArcher(sessionId, archerId)

  return (
    <div>
      <div className="formulaire__ligne">
        <label className="formulaire__libelle" htmlFor="simulation-archer">
          Archer à suivre
        </label>
        <select
          id="simulation-archer"
          className="formulaire__champ"
          value={archerId ?? ''}
          onChange={(e) => setArcherId(e.target.value === '' ? null : Number(e.target.value))}
        >
          <option value="">— Choisir un archer —</option>
          {etat.classement.lignes.map((ligne) => (
            <option key={ligne.archer_id} value={ligne.archer_id}>
              {ligne.nom} {ligne.prenom} — {ligne.total} pts
            </option>
          ))}
        </select>
      </div>
      {detail.data && (
        <div>
          <p className="carte__etat">
            <strong>
              {detail.data.nom} {detail.data.prenom}
            </strong>{' '}
            — cumul {detail.data.cumul} pts
          </p>
          {detail.data.volees.length === 0 ? (
            <p className="carte__etat">Cet archer n'a pas encore tiré.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Volée</th>
                  <th scope="col">Flèches</th>
                  <th scope="col">Points</th>
                  <th scope="col">Saisie</th>
                </tr>
              </thead>
              <tbody>
                {detail.data.volees.map((v) => (
                  <tr key={v.numero}>
                    <td>{v.numero}</td>
                    <td>{v.valeurs.join(' · ')}</td>
                    <td className="table__total">{v.points}</td>
                    <td>{v.validee_par ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Vue scoreur : les duels + désignation manuelle du vainqueur en pause
// ————————————————————————————————————————————————————————————————————————————————————————————————

function VueScoreur({
  etat,
  sessionId,
  enPause,
}: {
  etat: EtatSession
  sessionId: number
  enPause: boolean
}) {
  const unite = etat.prochaine_unite
  const designer = useDesignerVainqueur()

  if (etat.tableaux.length === 0) {
    return <p className="carte__etat">Les duels n'ont pas encore commencé.</p>
  }

  return (
    <div>
      {etat.tableaux.map((tableau, index) => (
        <TableauDuels key={index} tableau={tableau} />
      ))}
      {enPause &&
      unite?.genre === 'duel' &&
      unite.duel !== null &&
      unite.duel.haut &&
      unite.duel.bas ? (
        <div className="simulation__saisie">
          <p className="carte__etat">
            Désignez le vainqueur du duel {unite.duel.haut.nom} {unite.duel.haut.prenom} vs{' '}
            {unite.duel.bas.nom} {unite.duel.bas.prenom} :
          </p>
          <button
            type="button"
            disabled={designer.isPending}
            onClick={() =>
              designer.mutate({
                sessionId,
                phaseId: unite.duel!.phase_id,
                matchNumero: unite.duel!.match_numero,
                cote: 'haut',
              })
            }
          >
            {unite.duel.haut.nom} l'emporte
          </button>
          <button
            type="button"
            disabled={designer.isPending}
            onClick={() =>
              designer.mutate({
                sessionId,
                phaseId: unite.duel!.phase_id,
                matchNumero: unite.duel!.match_numero,
                cote: 'bas',
              })
            }
          >
            {unite.duel.bas.nom} l'emporte
          </button>
          <MessageErreur erreur={designer.error} />
        </div>
      ) : (
        etat.etape === 'duels' && (
          <p className="carte__etat">
            Mettez en pause pour arbitrer un duel à la place du scoreur.
          </p>
        )
      )}
    </div>
  )
}
