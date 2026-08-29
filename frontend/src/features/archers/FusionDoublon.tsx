// La fusion d'une paire de fiches rapprochées (E02US005) — **déplacée** ici par E16US010, où elle
// se déplie sur la ligne de l'archer au lieu d'occuper un écran dédié (CA : « une simple icône
// cliquable sur la ligne de l'archer peut suffire », plutôt qu'« un écran qui pollue »).
//
// Faute de numéro de licence, rien ne rend la double saisie **décidable** : on rapproche, l'admin
// tranche. La fusion garde une fiche maître et **absorbe** l'autre — inscriptions et scores
// passent sur la maître. Geste destructeur mais **non perdant**, d'où la confirmation explicite et
// le message serveur lu tel quel en cas de refus (409).

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useCategories } from '../categories/hooks'
import { useClubs } from '../clubs/hooks'
import type { Archer, Doublon } from './api'
import { useFusionnerArchers } from './hooks'

export function FusionDoublon({ paire, tournoiId }: { paire: Doublon; tournoiId: number }) {
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
    <div className="doublon">
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
    </div>
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
