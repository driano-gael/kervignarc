// Barrages de places décisives (E06US003, ADR-0066) — surface **admin** du classement.
//
// Deux moitiés, dans l'ordre où l'organisateur les vit : les égalités que le format réclame de
// trancher au tir (« faire tirer »), puis les barrages en cours, avec la saisie de leur manche.
//
// Rien ne s'affiche tant qu'aucun seuil de barrage n'est réglé sur la phase de qualification : le
// défaut du produit reste l'ex æquo partagé (E06US001), et un panneau vide en permanence sur les
// tournois qui ne barrent pas serait du bruit sur l'écran qu'on regarde toute la journée.
//
// ⚠️ **Un groupe se retire en entier.** Le serveur refuse une manche où une partie seulement du
// groupe a tiré — deux ex æquo dont un seul a retiré ne se départagent sur rien. Le formulaire
// soumet donc **tout le groupe** d'un coup, et un tireur qu'on n'a pas renseigné part « absent »
// seulement si on l'a coché : sans cela, un oubli de saisie ferait perdre quelqu'un qui a tiré.

import { useState } from 'react'
import type { Barrage, EgaliteADepartager, LigneClassement } from './api'
import { mancheComplete, type SaisieTir, TIR_VIERGE, versTirs } from './barrage'
import { useAnnoncerBarrage, useBarrages, useCloreBarrage, useSaisirMancheBarrage } from './hooks'

export function PanneauBarrages({
  tournoiId,
  egalites,
  lignes,
}: {
  tournoiId: number
  egalites: EgaliteADepartager[]
  /** Le classement affiché — sert à **nommer** les archers d'un barrage.
   *
   * Le barrage ne connaît que des identifiants (le moteur oppose des participants opaques,
   * ADR-0028) ; c'est la couche d'affichage qui résout l'identité. On réutilise les lignes déjà
   * chargées plutôt que d'interroger `/archers` : elles sont là, à jour, et une seconde source
   * afficherait un nom périmé après une correction d'état civil. */
  lignes: LigneClassement[]
}) {
  const barrages = useBarrages(tournoiId)
  const enCours = (barrages.data ?? []).filter((barrage) => !barrage.clos)
  const nomDe = (archerId: number) => {
    const ligne = lignes.find((candidate) => candidate.archer_id === archerId)
    return ligne ? `${ligne.nom} ${ligne.prenom}` : `Archer ${archerId}`
  }

  // Le panneau ne s'affiche que s'il y a quelque chose à faire ou à suivre.
  if (egalites.length === 0 && enCours.length === 0) {
    return null
  }

  return (
    <section className="carte carte--barrages">
      <h3 className="carte__soustitre">Barrages — places décisives</h3>
      {egalites.length > 0 && (
        <ul className="barrages__egalites">
          {egalites.map((egalite) => (
            <EgaliteALancer
              key={egalite.rang}
              tournoiId={tournoiId}
              egalite={egalite}
              nomDe={nomDe}
              dejaOuvert={enCours.some((barrage) => barrage.rang_dispute === egalite.rang)}
            />
          ))}
        </ul>
      )}
      {enCours.map((barrage) => (
        <BarrageEnCours key={barrage.id} tournoiId={tournoiId} barrage={barrage} nomDe={nomDe} />
      ))}
    </section>
  )
}

/** Une égalité signalée par le format, avec le bouton qui l'ouvre. */
function EgaliteALancer({
  tournoiId,
  egalite,
  nomDe,
  dejaOuvert,
}: {
  tournoiId: number
  egalite: EgaliteADepartager
  nomDe: (archerId: number) => string
  dejaOuvert: boolean
}) {
  const annoncer = useAnnoncerBarrage(tournoiId)
  return (
    <li className="barrages__egalite">
      <span>
        <strong>{egalite.rang}ᵉ place</strong> — {egalite.archer_ids.map(nomDe).join(', ')}
      </span>
      {!dejaOuvert && (
        <button
          type="button"
          onClick={() => annoncer.mutate(egalite.rang)}
          disabled={annoncer.isPending}
        >
          Faire tirer
        </button>
      )}
      {annoncer.isError && (
        <span className="carte__etat carte__etat--erreur" role="alert">
          {annoncer.error.message}
        </span>
      )}
    </li>
  )
}

/** Un barrage ouvert : ce qu'il reste à faire tirer, ou son verdict. */
function BarrageEnCours({
  tournoiId,
  barrage,
  nomDe,
}: {
  tournoiId: number
  barrage: Barrage
  nomDe: (archerId: number) => string
}) {
  const clore = useCloreBarrage(tournoiId)
  return (
    <article className="barrage">
      <h4 className="barrage__titre">
        {barrage.rang_dispute}ᵉ place — manche {barrage.manches.length + 1}
      </h4>
      {barrage.est_resolu ? (
        <>
          <p className="barrage__verdict">
            Départagé : {barrage.ordre.map(nomDe).join(' devant ')}
          </p>
          <button type="button" onClick={() => clore.mutate(barrage.id)} disabled={clore.isPending}>
            Acter le résultat
          </button>
        </>
      ) : (
        // Un groupe par égalité restante : ils se retirent **séparément**, et les fusionner
        // ferait passer un tireur à 8 devant un tireur à 10 que le tir précédent avait départagé.
        barrage.groupes_a_rejouer.map((groupe) => (
          <SaisieGroupe
            key={groupe.join('-')}
            tournoiId={tournoiId}
            barrage={barrage}
            groupe={groupe}
            nomDe={nomDe}
          />
        ))
      )}
      {clore.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          {clore.error.message}
        </p>
      )}
    </article>
  )
}

/** Le formulaire d'un groupe à départager : une flèche par tireur, la manche soumise d'un bloc. */
function SaisieGroupe({
  tournoiId,
  barrage,
  groupe,
  nomDe,
}: {
  tournoiId: number
  barrage: Barrage
  groupe: number[]
  nomDe: (archerId: number) => string
}) {
  const [saisies, setSaisies] = useState<Record<number, SaisieTir>>({})
  const saisir = useSaisirMancheBarrage(tournoiId)
  const lire = (archerId: number) => saisies[archerId] ?? TIR_VIERGE
  const modifier = (archerId: number, champ: Partial<SaisieTir>) =>
    setSaisies((actuel) => ({ ...actuel, [archerId]: { ...lire(archerId), ...champ } }))

  // Le groupe se retire en entier : tant qu'un tireur n'est ni noté ni déclaré absent, on ne
  // soumet pas. Le serveur refuserait de toute façon (« un groupe se retire en entier ou pas du
  // tout ») — on l'annonce ici plutôt que de laisser partir une requête vouée au 422.
  const complet = mancheComplete(groupe, saisies)

  const soumettre = () => saisir.mutate({ barrageId: barrage.id, tirs: versTirs(groupe, saisies) })

  return (
    <div className="barrage__groupe">
      {groupe.map((archerId) => {
        const tir = lire(archerId)
        return (
          <div key={archerId} className="barrage__tireur">
            <span className="barrage__nom">{nomDe(archerId)}</span>
            <label>
              Flèche{' '}
              <input
                type="number"
                inputMode="numeric"
                min={0}
                max={10}
                value={tir.score}
                disabled={tir.absent}
                onChange={(e) => modifier(archerId, { score: e.target.value })}
              />
            </label>
            <label
              title="Distance du centre à l'impact, en dixièmes de millimètre. À ne renseigner
que si les flèches sont à égalité et que le juge a mesuré — une mesure absente n'est pas une
distance nulle : le barrage se retire."
            >
              Distance (⅒ mm){' '}
              <input
                type="number"
                inputMode="numeric"
                min={0}
                value={tir.distance}
                disabled={tir.absent}
                onChange={(e) => modifier(archerId, { distance: e.target.value })}
              />
            </label>
            <label title="Absent au barrage annoncé : l'archer est déclaré perdant (art. B.6.5.2.4).">
              <input
                type="checkbox"
                checked={tir.absent}
                onChange={(e) => modifier(archerId, { absent: e.target.checked })}
              />{' '}
              Absent
            </label>
          </div>
        )
      })}
      <button type="button" onClick={soumettre} disabled={!complet || saisir.isPending}>
        Enregistrer la manche
      </button>
      {!complet && (
        <p className="carte__etat">
          Un groupe se retire en entier : notez la flèche de chaque tireur, ou déclarez-le absent.
        </p>
      )}
      {saisir.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          {saisir.error.message}
        </p>
      )}
    </div>
  )
}
