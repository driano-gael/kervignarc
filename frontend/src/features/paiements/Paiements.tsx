// Écran de suivi des paiements (E08US002) — destination admin « Paiements » (CDC §7.1).
//
// Deux vues d'une même capacité : **par archer** (dû / payé / reste, filtrable) et **par club**
// (totaux + détail des archers). Les **règlements groupés** se font ici : marquer d'un geste tout un
// archer (bouton sur sa ligne) ou tout un club (bouton sur l'en-tête du club). Chaque marquage est
// **audité** côté serveur (trace `PAIEMENT`). Le statut de paiement fin (par créneau) reste, lui,
// sur le panneau d'inscription de l'archer (feature « inscriptions »).

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { decrireTarif } from '../competition/format'
import type { LignePaiementArcher, RecapClub, RecapPaiement } from './api'
import { useMarquerArcher, useMarquerClub, usePaiementsArchers, usePaiementsClubs } from './hooks'

type Onglet = 'archers' | 'clubs'

export function Paiements({ tournoiId }: { tournoiId: number }) {
  const [onglet, setOnglet] = useState<Onglet>('archers')

  return (
    <section className="carte">
      <h3 className="carte__titre">Paiements</h3>
      <p className="carte__soustitre">Suivi des règlements par archer et par club.</p>

      <div className="onglets" role="tablist" aria-label="Vue des paiements">
        <button
          type="button"
          role="tab"
          aria-selected={onglet === 'archers'}
          className={onglet === 'archers' ? 'onglet onglet--actif' : 'onglet'}
          onClick={() => setOnglet('archers')}
        >
          Par archer
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={onglet === 'clubs'}
          className={onglet === 'clubs' ? 'onglet onglet--actif' : 'onglet'}
          onClick={() => setOnglet('clubs')}
        >
          Par club
        </button>
      </div>

      {onglet === 'archers' ? (
        <VueParArcher tournoiId={tournoiId} />
      ) : (
        <VueParClub tournoiId={tournoiId} />
      )}
    </section>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Vue par archer : liste filtrable, avec règlement groupé de tout un archer.
// ————————————————————————————————————————————————————————————————————————————————————————————————

function VueParArcher({ tournoiId }: { tournoiId: number }) {
  const paiements = usePaiementsArchers(tournoiId)
  const [filtre, setFiltre] = useState('')

  if (paiements.isError) return <MessageErreur erreur={paiements.error} />
  if (!paiements.data) return <p className="carte__etat">Chargement…</p>
  if (paiements.data.length === 0)
    return <p className="carte__etat">Aucun archer inscrit pour l'instant.</p>

  const terme = filtre.trim().toLowerCase()
  const lignes = terme
    ? paiements.data.filter((l) => `${l.nom} ${l.prenom}`.toLowerCase().includes(terme))
    : paiements.data

  return (
    <>
      <input
        type="search"
        className="formulaire__champ"
        placeholder="Filtrer par nom ou prénom…"
        value={filtre}
        onChange={(e) => setFiltre(e.target.value)}
        aria-label="Filtrer les archers"
      />
      <TotalGeneral recaps={paiements.data.map((l) => l.recap)} />
      <div className="table-defilement">
        <table className="table paiements__table">
          <thead>
            <tr>
              <th scope="col">Archer</th>
              <th scope="col">Dû</th>
              <th scope="col">Payé</th>
              <th scope="col">Reste</th>
              <th scope="col">Statut</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {lignes.map((ligne) => (
              <LigneArcher key={ligne.archer_id} tournoiId={tournoiId} ligne={ligne} />
            ))}
          </tbody>
        </table>
      </div>
      {lignes.length === 0 && <p className="carte__etat">Aucun archer ne correspond au filtre.</p>}
    </>
  )
}

function LigneArcher({ tournoiId, ligne }: { tournoiId: number; ligne: LignePaiementArcher }) {
  const marquer = useMarquerArcher(tournoiId)
  return (
    <tr>
      <td>
        {ligne.nom} {ligne.prenom}
      </td>
      <CellulesMontants recap={ligne.recap} />
      <td>
        <BoutonMarquer
          recap={ligne.recap}
          enCours={marquer.isPending}
          onMarquer={(paye) => marquer.mutate({ archerId: ligne.archer_id, paye })}
        />
        <MessageErreur erreur={marquer.error} />
      </td>
    </tr>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Vue par club : un bloc par club (total + règlement groupé), avec le détail des archers.
// ————————————————————————————————————————————————————————————————————————————————————————————————

function VueParClub({ tournoiId }: { tournoiId: number }) {
  const paiements = usePaiementsClubs(tournoiId)

  if (paiements.isError) return <MessageErreur erreur={paiements.error} />
  if (!paiements.data) return <p className="carte__etat">Chargement…</p>
  if (paiements.data.length === 0)
    return <p className="carte__etat">Aucun archer inscrit pour l'instant.</p>

  return (
    <>
      <TotalGeneral recaps={paiements.data.map((c) => c.recap)} />
      {paiements.data.map((club) => (
        <BlocClub key={club.club_id ?? 'sans-club'} tournoiId={tournoiId} club={club} />
      ))}
    </>
  )
}

function BlocClub({ tournoiId, club }: { tournoiId: number; club: RecapClub }) {
  const marquer = useMarquerClub(tournoiId)
  return (
    <div className="bloc-club">
      <div className="bloc-club__entete">
        <h4 className="carte__soustitre">{club.nom}</h4>
        <span className="bloc-club__total">
          Dû {decrireTarif(club.recap.du_centimes)} · Reste{' '}
          {decrireTarif(club.recap.reste_centimes)}
        </span>
        {/* Le bucket « sans club » (club_id null) n'est pas un club réel : pas de marquage groupé. */}
        {club.club_id !== null && (
          <BoutonMarquer
            recap={club.recap}
            enCours={marquer.isPending}
            onMarquer={(paye) =>
              club.club_id !== null && marquer.mutate({ clubId: club.club_id, paye })
            }
          />
        )}
      </div>
      <MessageErreur erreur={marquer.error} />
      <div className="table-defilement">
        <table className="table paiements__table">
          <thead>
            <tr>
              <th scope="col">Archer</th>
              <th scope="col">Dû</th>
              <th scope="col">Payé</th>
              <th scope="col">Reste</th>
              <th scope="col">Statut</th>
            </tr>
          </thead>
          <tbody>
            {club.archers.map((ligne) => (
              <tr key={ligne.archer_id}>
                <td>
                  {ligne.nom} {ligne.prenom}
                </td>
                <CellulesMontants recap={ligne.recap} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Briques partagées.
// ————————————————————————————————————————————————————————————————————————————————————————————————

// Trois cellules (dû, payé, reste) + une cellule statut — factorisées pour que les deux vues
// affichent les montants **exactement** de la même façon.
function CellulesMontants({ recap }: { recap: RecapPaiement }) {
  return (
    <>
      <td>{decrireTarif(recap.du_centimes)}</td>
      <td>{decrireTarif(recap.paye_centimes)}</td>
      <td>{decrireTarif(recap.reste_centimes)}</td>
      <td>
        <StatutPaiement recap={recap} />
      </td>
    </>
  )
}

// Statut dérivé du récapitulatif : rien à payer (dû 0), réglé (reste 0), partiel (payé entamé) ou dû.
function StatutPaiement({ recap }: { recap: RecapPaiement }) {
  if (recap.du_centimes === 0) return <span className="statut statut--neutre">—</span>
  if (recap.reste_centimes === 0) return <span className="statut statut--regle">Réglé</span>
  if (recap.paye_centimes > 0) return <span className="statut statut--partiel">Partiel</span>
  return <span className="statut statut--du">À régler</span>
}

// Bouton de règlement groupé : propose de tout marquer réglé s'il reste à payer, ou de tout annuler
// s'il y a du payé. Rien à faire quand le périmètre ne doit rien (dû 0).
function BoutonMarquer({
  recap,
  enCours,
  onMarquer,
}: {
  recap: RecapPaiement
  enCours: boolean
  onMarquer: (paye: boolean) => void
}) {
  if (recap.du_centimes === 0) return null
  if (recap.reste_centimes > 0)
    return (
      <button
        type="button"
        className="bouton--discret"
        disabled={enCours}
        onClick={() => onMarquer(true)}
      >
        Marquer réglé
      </button>
    )
  return (
    <button
      type="button"
      className="bouton--discret"
      disabled={enCours}
      onClick={() => onMarquer(false)}
    >
      Marquer non réglé
    </button>
  )
}

function TotalGeneral({ recaps }: { recaps: RecapPaiement[] }) {
  const du = recaps.reduce((s, r) => s + r.du_centimes, 0)
  const paye = recaps.reduce((s, r) => s + r.paye_centimes, 0)
  return (
    <p className="paiements__total">
      Total tournoi — Dû {decrireTarif(du)} · Payé {decrireTarif(paye)} · Reste{' '}
      {decrireTarif(du - paye)}
    </p>
  )
}

function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
