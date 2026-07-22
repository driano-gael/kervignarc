// Écran d'administration des doublons (E02US005) — réservé à l'admin (monté sous `estAdmin`).
//
// La double saisie du même archer est l'erreur la plus banale d'une table d'inscription. Faute de
// numéro de licence (repoussé à E02US007), rien ne la rend **décidable** : on **rapproche** des
// paires vraisemblables (mêmes nom/prénom/club, ou approximatif) et l'admin tranche. Deux niveaux
// (voir `presentation.ts`) : « doublons probables » et « à vérifier ».
//
// La **fusion** est le geste qui nettoie : l'admin choisit la fiche à **garder** (maître), l'autre
// est **absorbée** — ses inscriptions et scores passent sur la maître, puis elle disparaît. Geste
// destructeur (une fiche part) mais **non perdant** (les données sont reprises) : d'où la
// confirmation explicite avant d'agir, et le message serveur lu tel quel en cas de refus (409 :
// les deux fiches ont déjà tiré, ou fusion structurellement impossible).

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useCategories } from '../categories/hooks'
import { useClubs } from '../clubs/hooks'
import type { Archer, Doublon } from './api'
import { grouperDoublons } from './presentation'
import { useDoublons, useFusionnerArchers } from './hooks'

export function Doublons({ tournoiId }: { tournoiId: number }) {
  const doublons = useDoublons(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Doublons</h3>
      <p className="carte__etat">
        Fiches qui se ressemblent — un même archer saisi deux fois. Choisissez la fiche à garder :
        l'autre y est fusionnée (inscriptions et scores repris), puis supprimée.
      </p>
      {doublons.isError && <MessageErreur erreur={doublons.error} />}
      {/* `isSuccess` et non `data ?? []` : tant que la requête court, `data` est `undefined` et le
          message « aucun doublon » s'afficherait à tort sur un tournoi qui en a. */}
      {doublons.isSuccess && doublons.data.length === 0 && (
        <p className="carte__etat">Aucun doublon détecté.</p>
      )}
      {doublons.data && doublons.data.length > 0 && (
        <>
          {grouperDoublons(doublons.data).map((groupe) => (
            <section key={groupe.niveau}>
              <h4 className="carte__soustitre">{groupe.libelle}</h4>
              <ul className="liste-archers">
                {groupe.paires.map((paire) => (
                  <PaireDoublon
                    key={`${paire.a.id}-${paire.b.id}`}
                    paire={paire}
                    tournoiId={tournoiId}
                  />
                ))}
              </ul>
            </section>
          ))}
        </>
      )}
    </section>
  )
}

function PaireDoublon({ paire, tournoiId }: { paire: Doublon; tournoiId: number }) {
  // La fiche que l'admin a choisi de **garder** (maître), avec celle qui sera absorbée. Tant que
  // `null`, on n'affiche que les deux fiches et leur bouton « Garder » — pas de geste armé.
  const [choix, setChoix] = useState<{ gagnant: Archer; perdant: Archer } | null>(null)
  const fusionner = useFusionnerArchers(tournoiId)
  const clubs = useClubs()
  const categories = useCategories(tournoiId)

  // Choisir (ou changer d'avis) **efface** un refus 409 en cours : sans ce `reset`, un message
  // d'erreur d'un choix précédent resterait affiché sous une confirmation qui ne le concerne plus.
  const choisir = (gagnant: Archer, perdant: Archer) => {
    fusionner.reset()
    setChoix({ gagnant, perdant })
  }

  const annuler = () => {
    fusionner.reset()
    setChoix(null)
  }

  return (
    <li className="doublon">
      {[paire.a, paire.b].map((archer) => (
        <FicheResume
          key={archer.id}
          archer={archer}
          clubs={clubs.data}
          categories={categories.data}
          // « Garder cette fiche » n'apparaît que tant qu'aucun choix n'est fait : une fois la
          // confirmation ouverte, on ne propose plus que Confirmer / Annuler.
          surGarder={
            choix === null
              ? () => choisir(archer, archer.id === paire.a.id ? paire.b : paire.a)
              : undefined
          }
        />
      ))}
      {choix !== null && (
        <div className="carte__etat" role="alert">
          <p>
            « {choix.perdant.nom} {choix.perdant.prenom} » sera fusionnée dans « {choix.gagnant.nom}{' '}
            {choix.gagnant.prenom} » : ses inscriptions et ses scores sont repris, la fiche absorbée
            disparaît définitivement.
          </p>
          <span className="archer__actions">
            <button
              type="button"
              className="bouton--danger"
              disabled={fusionner.isPending}
              onClick={() =>
                fusionner.mutate({ gagnantId: choix.gagnant.id, perdantId: choix.perdant.id })
              }
            >
              Fusionner
            </button>
            <button
              type="button"
              className="bouton--discret"
              disabled={fusionner.isPending}
              onClick={annuler}
            >
              Annuler
            </button>
          </span>
        </div>
      )}
      {/* Refus fermes du serveur (409 `fusion_archers_engages` / `fusion_impossible`) : aucun drapeau
          ne les lève, on affiche le message tel quel — c'est lui qui explique quoi corriger. */}
      {fusionner.isError && <MessageErreur erreur={fusionner.error} />}
    </li>
  )
}

function FicheResume({
  archer,
  clubs,
  categories,
  surGarder,
}: {
  archer: Archer
  clubs: { id: number; nom: string }[] | undefined
  categories: { id: number; libelle: string }[] | undefined
  surGarder?: () => void
}) {
  const categorie = categories?.find((c) => c.id === archer.categorie_id)
  const club = clubs?.find((c) => c.id === archer.club_id)

  return (
    <div className="archer__ligne">
      <span className="archer__identite">
        {archer.nom} {archer.prenom}
      </span>
      <span className="archer__details">
        {categorie?.libelle ?? '—'}
        {club !== undefined && ` · ${club.nom}`}
        {/* Même signal qu'ailleurs : un club inconnu est une anomalie, et ici il peut être ce qui
            distingue les deux fiches (le pont avec/sans club est un doublon probable). */}
        {archer.club_id === null && ' · club inconnu'}
        {archer.cible !== null && ` · cible ${archer.cible}`}
      </span>
      {surGarder !== undefined && (
        <span className="archer__actions">
          <button type="button" className="bouton--discret" onClick={surGarder}>
            Garder cette fiche
          </button>
        </span>
      )}
    </div>
  )
}
