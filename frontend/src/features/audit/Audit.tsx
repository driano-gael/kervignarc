// Consultation du journal d'audit (E16US016) — réservé à l'admin, comme la route qu'il appelle.
//
// La planche A18 fait foi (ADR-0074) : compteurs, recherche libre, filtre des corrections, et une
// ligne par acte avec son détail. ⚠️ Le filtrage et la pagination sont **côté client**, sur le
// journal entier chargé en une fois : le serveur ne sait pas filtrer (`AuditRepository.par_tournoi`)
// et lui apprendre était hors du périmètre arbitré. Coût assumé et chiffré en `DETTE-101`.

import { useMemo, useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { EntreeAudit } from './api'
import { useAudit } from './hooks'
import {
  actionsPresentes,
  estCorrective,
  filtrer,
  heureLocale,
  libelleAction,
} from './presentation'

// Assez pour couvrir une matinée sans faire défiler mille lignes, assez peu pour que le rendu
// reste immédiat sur la tablette la plus lente de la salle.
const PAR_PAGE = 50

export function Audit({ tournoiId }: { tournoiId: number }) {
  const journal = useAudit(tournoiId)
  const [action, setAction] = useState('')
  const [recherche, setRecherche] = useState('')
  const [page, setPage] = useState(0)

  // ⚠️ **Antichronologique**, à rebours du port : `AuditRepository.par_tournoi` garantit
  // l'ordre croissant, et l'**export** le conserve — un journal de preuve se lit dans le sens
  // du temps. L'écran, lui, sert à retrouver l'acte qui vient d'avoir lieu : sur les ~1 284
  // entrées d'une matinée (planche A18), le laisser croissant ouvrait 25 pages trop tôt.
  // Arbitrage du commanditaire du 18/09/2026, reversé au CA.
  const entrees = useMemo(() => [...(journal.data ?? [])].reverse(), [journal.data])
  const filtrees = useMemo(() => filtrer(entrees, action, recherche), [entrees, action, recherche])
  const corrections = useMemo(() => entrees.filter(estCorrective).length, [entrees])

  // ⚠️ La page courante est **bornée au rendu** plutôt que remise à zéro par un effet : filtrer
  // depuis la page 12 laisserait sinon un tableau vide sous une pagination qui annonce des pages.
  const pages = Math.max(1, Math.ceil(filtrees.length / PAR_PAGE))
  const pageCourante = Math.min(page, pages - 1)
  const visibles = filtrees.slice(pageCourante * PAR_PAGE, (pageCourante + 1) * PAR_PAGE)

  return (
    <section>
      <h3 className="carte__soustitre">Journal d’audit</h3>
      <p className="carte__etat">
        Qui a fait quoi, quand, et ce qui a changé. Une correction porte toujours son motif et
        l’ancienne valeur reste lisible : c’est ce qui distingue un journal d’audit d’un historique.
      </p>

      {journal.isError && <MessageErreur erreur={journal.error} />}
      {journal.isPending && <p className="carte__etat">Chargement du journal…</p>}

      {journal.data && (
        <>
          <div className="audit__barre">
            <label className="formulaire__libelle">
              Rechercher
              <input
                className="formulaire__champ"
                type="search"
                placeholder="Archer, cible, scoreur…"
                value={recherche}
                onChange={(e) => {
                  setRecherche(e.target.value)
                  setPage(0)
                }}
              />
            </label>
            <label className="formulaire__libelle">
              Type d’acte
              <select
                className="formulaire__champ"
                value={action}
                onChange={(e) => {
                  setAction(e.target.value)
                  setPage(0)
                }}
              >
                <option value="">Tous les actes</option>
                {actionsPresentes(entrees).map((slug) => (
                  <option key={slug} value={slug}>
                    {libelleAction(slug)}
                  </option>
                ))}
              </select>
            </label>
            <p className="audit__compteurs">
              <span className="badge">{entrees.length} entrées</span>{' '}
              <span className="badge badge--correction">{corrections} corrections</span>
            </p>
          </div>

          {entrees.length === 0 && (
            <p className="carte__etat">
              Aucun acte tracé pour l’instant — c’est l’état normal d’un tournoi qui n’a pas
              commencé.
            </p>
          )}
          {entrees.length > 0 && filtrees.length === 0 && (
            <p className="carte__etat">Aucune entrée ne correspond à cette recherche.</p>
          )}

          {visibles.length > 0 && (
            <div className="audit__tableau">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Heure</th>
                    <th scope="col">Qui</th>
                    <th scope="col">Action</th>
                    <th scope="col">Objet</th>
                    <th scope="col">Détail</th>
                  </tr>
                </thead>
                <tbody>
                  {visibles.map((entree) => (
                    <LigneAudit key={entree.id} entree={entree} />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {pages > 1 && (
            <nav className="audit__pagination" aria-label="Pages du journal">
              <button
                type="button"
                className="bouton bouton--discret"
                onClick={() => setPage(pageCourante - 1)}
                disabled={pageCourante === 0}
              >
                Précédent
              </button>
              <span className="carte__etat">
                Page {pageCourante + 1} sur {pages}
              </span>
              <button
                type="button"
                className="bouton bouton--discret"
                onClick={() => setPage(pageCourante + 1)}
                disabled={pageCourante >= pages - 1}
              >
                Suivant
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  )
}

function LigneAudit({ entree }: { entree: EntreeAudit }) {
  const aUnDetail = entree.avant !== null || entree.apres !== null
  return (
    <tr>
      <td>{heureLocale(entree.horodatage)}</td>
      <td>{entree.auteur}</td>
      <td>
        <span className={estCorrective(entree) ? 'badge badge--correction' : undefined}>
          {libelleAction(entree.action)}
        </span>
      </td>
      <td>{entree.objet}</td>
      <td>
        {aUnDetail ? (
          <details>
            <summary>Avant / après</summary>
            <p className="audit__avant-apres">
              <span className="audit__avant">{entree.avant ?? '—'}</span>
              {' → '}
              <span className="audit__apres">{entree.apres ?? '—'}</span>
            </p>
          </details>
        ) : (
          // Une validation n'a pas d'état antérieur : le dire, plutôt qu'un dépliage vide qui
          // laisserait croire à une donnée manquante.
          <span className="carte__etat">—</span>
        )}
      </td>
    </tr>
  )
}
