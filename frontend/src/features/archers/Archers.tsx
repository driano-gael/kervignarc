// Écran d'administration des archers (E02US003) — réservé à l'admin (monté sous `estAdmin`).
//
// Liste des inscrits du tournoi (triée serveur, nom puis prénom), édition des quatre champs et
// désinscription à confirmation. C'est la surface où le **club inconnu** devient corrigeable :
// jusqu'ici l'anomalie se voyait au classement (ADR-0014) sans qu'on puisse rien en faire.
//
// **Trois refus serveur, deux natures.** L'écran ne les traite pas pareil, et c'est le fond de
// l'US :
//   - `homonyme_archer` et `changement_categorie_archer_engage` sont des **signalements** — la
//     machine constate un fait dont elle ignore le sens. Ton neutre, et un bouton pour passer
//     outre qui rejoue l'appel avec le drapeau correspondant (ADR-0015).
//   - `archer_engage` est un **refus** — aucun bouton ne le lève. Il s'affiche comme une erreur,
//     parce que c'en est une : le geste demandé n'aura pas lieu.
// Offrir un bouton « quand même » sur le troisième mentirait sur ce que fait le serveur.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { useCategories } from '../categories/hooks'
import { useClubs } from '../clubs/hooks'
import type { Archer, ModifierArcher } from './api'
import { useArchers, useModifierArcher, useSupprimerArcher } from './hooks'

export function Archers({ tournoiId }: { tournoiId: number }) {
  const archers = useArchers(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Archers inscrits</h3>
      {archers.isError && <MessageErreur erreur={archers.error} />}
      {/* `isSuccess` et non `data ?? []` : tant que la requête court, `data` est `undefined` et
          le message s'afficherait à tort sur un tournoi qui a bel et bien des inscrits. */}
      {archers.isSuccess && archers.data.length === 0 && (
        <p className="carte__etat">Aucun archer inscrit pour l'instant.</p>
      )}
      {archers.data && archers.data.length > 0 && (
        <ul className="liste-archers">
          {archers.data.map((archer) => (
            <LigneArcher key={archer.id} archer={archer} tournoiId={tournoiId} />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneArcher({ archer, tournoiId }: { archer: Archer; tournoiId: number }) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerArcher(tournoiId)
  const clubs = useClubs()
  const categories = useCategories(tournoiId)

  if (edition) {
    return (
      <li>
        <FormulaireArcher
          archer={archer}
          tournoiId={tournoiId}
          onTermine={() => setEdition(false)}
        />
      </li>
    )
  }

  // Nom **et** prénom : deux homonymes confirmés (un père et son fils) peuvent coexister depuis
  // E02US002 — les distinguer à l'œil est le minimum vital sur un écran de correction.
  const identite = `${archer.nom} ${archer.prenom}`
  const categorie = categories.data?.find((c) => c.id === archer.categorie_id)
  const club = clubs.data?.find((c) => c.id === archer.club_id)

  return (
    <li>
      <div className="archer__ligne">
        <span className="archer__identite">
          {identite}
          {/* Même signal qu'au classement (`table__anomalie`) : un seul vocabulaire visuel pour
              une seule anomalie. Ici, il est enfin actionnable — « Modifier » ouvre le select. */}
          {archer.club_id === null && (
            <span
              className="table__anomalie"
              title="Renseignez son club pour compléter l'inscription"
            >
              {' '}
              Club inconnu
            </span>
          )}
        </span>
        <span className="archer__details">
          {categorie?.libelle ?? '—'}
          {club !== undefined && ` · ${club.nom}`}
          {archer.cible !== null && ` · cible ${archer.cible}`}
        </span>
        <span className="archer__actions">
          <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
            Modifier
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate(archer.id)}
              >
                Confirmer la suppression
              </button>
              <button
                type="button"
                className="bouton--discret"
                onClick={() => setConfirmationSuppression(false)}
              >
                Annuler
              </button>
            </>
          ) : (
            <button
              type="button"
              className="bouton--danger"
              onClick={() => setConfirmationSuppression(true)}
            >
              Supprimer
            </button>
          )}
        </span>
      </div>
      {/* `archer_engage` arrive ici : un refus, affiché comme tel. Le message du serveur dit quoi
          faire d'abord (retirer le placement, effacer les scores). */}
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

function FormulaireArcher({
  archer,
  tournoiId,
  onTermine,
}: {
  archer: Archer
  tournoiId: number
  onTermine: () => void
}) {
  const [nom, setNom] = useState(archer.nom)
  const [prenom, setPrenom] = useState(archer.prenom)
  const [categorieId, setCategorieId] = useState(String(archer.categorie_id))
  const [clubId, setClubId] = useState(archer.club_id === null ? '' : String(archer.club_id))
  const clubs = useClubs()
  const categories = useCategories(tournoiId)
  const modifier = useModifierArcher(tournoiId)

  // Reprend la règle du domaine (nom et prénom non vides) pour éviter une requête vouée au 422 ;
  // le serveur reste l'autorité (revalidation à la frontière).
  const incomplet = nom.trim() === '' || prenom.trim() === '' || categorieId === ''

  const code = modifier.error instanceof ErreurApi ? modifier.error.code : null
  const homonymeSignale = code === 'homonyme_archer'
  const categorieSignalee = code === 'changement_categorie_archer_engage'

  // Un 409 porte sur **les valeurs exactes** envoyées. Dès qu'un champ change, le signalement ne
  // s'y applique plus : on l'efface, sinon « Enregistrer quand même » confirmerait une saisie que
  // le serveur n'a jamais examinée — et le doublon que l'US refuse passerait par le bouton même
  // prévu pour l'autoriser. Même parti qu'à l'inscription (E02US002) : `reset()` plutôt que de
  // comparer les clés, ce qui exigerait de réimplémenter `cle_nom` en TS.
  const surChamp = (poser: (valeur: string) => void) => (valeur: string) => {
    if (modifier.error !== null) modifier.reset()
    poser(valeur)
  }

  const enregistrer = (confirmations: Partial<ModifierArcher>) => {
    modifier.mutate(
      {
        id: archer.id,
        entree: {
          nom,
          prenom,
          categorie_id: Number(categorieId),
          club_id: clubId === '' ? null : Number(clubId),
          ...confirmations,
        },
      },
      { onSuccess: onTermine },
    )
  }

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (incomplet) return
    enregistrer({})
  }

  return (
    <div>
      <h4 className="carte__soustitre">Modifier l'archer</h4>
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => surChamp(setNom)(e.target.value)}
          placeholder="Nom de l'archer"
          aria-label="Nom de l'archer"
        />
        <input
          className="formulaire__champ"
          value={prenom}
          onChange={(e) => surChamp(setPrenom)(e.target.value)}
          placeholder="Prénom de l'archer"
          aria-label="Prénom de l'archer"
        />
        <select
          className="formulaire__champ"
          value={categorieId}
          onChange={(e) => surChamp(setCategorieId)(e.target.value)}
          aria-label="Catégorie de l'archer"
        >
          <option value="">Choisir une catégorie…</option>
          {(categories.data ?? []).map((categorie) => (
            <option key={categorie.id} value={categorie.id}>
              {categorie.libelle}
            </option>
          ))}
        </select>
        <select
          className="formulaire__champ"
          value={clubId}
          onChange={(e) => surChamp(setClubId)(e.target.value)}
          aria-label="Club de l'archer"
        >
          <option value="">Club inconnu</option>
          {(clubs.data ?? []).map((club) => (
            <option key={club.id} value={club.id}>
              {club.nom}
            </option>
          ))}
        </select>
        <div className="formulaire__actions">
          <button type="submit" disabled={modifier.isPending || incomplet}>
            Enregistrer
          </button>
          <button type="button" className="bouton--discret" onClick={onTermine}>
            Annuler
          </button>
        </div>
      </form>
      {/* Ton **neutre** (pas de `--erreur`) et une action : ces deux-là ne sont pas des erreurs,
          l'édition reste possible. Chaque bouton ne pose que **son** drapeau : si les deux faits
          sont vrais, l'admin voit le second signalement après avoir levé le premier. Un bouton qui
          poserait les deux d'un coup ferait confirmer un motif jamais affiché.
          À reprendre avec E00US013, qui factorisera les briques d'UI (DETTE-004). */}
      {homonymeSignale && (
        <div className="carte__etat" role="alert">
          <p>{modifier.error?.message}</p>
          <button
            type="button"
            onClick={() => enregistrer({ autoriser_homonyme: true })}
            disabled={modifier.isPending || incomplet}
          >
            Enregistrer quand même
          </button>
        </div>
      )}
      {categorieSignalee && (
        <div className="carte__etat" role="alert">
          <p>{modifier.error?.message}</p>
          <button
            type="button"
            onClick={() => enregistrer({ autoriser_changement_categorie: true })}
            disabled={modifier.isPending || incomplet}
          >
            Changer quand même de catégorie
          </button>
        </div>
      )}
      {!homonymeSignale && !categorieSignalee && <MessageErreur erreur={modifier.error} />}
    </div>
  )
}

// DETTE-004 (docs/dette.md) : 10ᵉ copie conforme de ce composant, une par feature. À extraire dans
// `shared/` — E00US013. Non factorisée ici, pour la même raison qu'en E02US001 : l'extraire pour la
// seule feature neuve donnerait « 9 copies + 1 brique partagée », soit deux conventions au lieu
// d'une, alors que E00US013 doit pouvoir relire un remplacement homogène.
function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
