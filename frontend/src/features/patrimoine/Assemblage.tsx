// Assembler un tournoi depuis le patrimoine du club (E01US023, ADR-0060) — écran de **pilotage**.
//
// Le pendant exact de « Plan de salle » face à « Gabarits » : la bibliothèque vit dans l'atelier,
// la **copie** d'une édition se travaille ici, là où l'on a un tournoi sous la main.
//
// Deux gestes, qui sont les deux sens de circulation arbitrés avec le commanditaire :
//
// - **assembler** — le tournoi reçoit une copie des briques du club. Modifier la copie ne remonte
//   pas ; modifier la bibliothèque ne redescend pas. C'est ce qui garantit qu'un tarif changé en
//   2027 ne réécrit pas le tournoi 2026 archivé (ADR-0060 §2) ;
// - **rendre permanent** — « si les modifications sont permanentes, on doit pouvoir le dire » : la
//   copie ajustée remonte dans la bibliothèque, **sans** rétroagir sur les éditions déjà assemblées.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useBlasons } from '../blasons/hooks'
import { useCategories } from '../categories/hooks'
import { usePhases } from '../phases/hooks'
import { decrireEtape, decrireRapport } from './format'
import {
  useAppliquerFormat,
  useAssemblerTournoi,
  useFormats,
  usePromouvoirBlason,
  usePromouvoirCategorie,
  usePromouvoirFormat,
} from './hooks'

export function Assemblage({ tournoiId }: { tournoiId: number }) {
  return (
    <section>
      <h3 className="carte__soustitre">Assembler depuis le patrimoine du club</h3>
      <CopieDesBriques tournoiId={tournoiId} />
      <ApplicationDuFormat tournoiId={tournoiId} />
      <PromotionDuFormat tournoiId={tournoiId} />
    </section>
  )
}

function CopieDesBriques({ tournoiId }: { tournoiId: number }) {
  const assembler = useAssemblerTournoi(tournoiId)
  const categories = useCategories(tournoiId)
  const blasons = useBlasons(tournoiId)
  const promouvoirCategorie = usePromouvoirCategorie(tournoiId)
  const promouvoirBlason = usePromouvoirBlason(tournoiId)

  return (
    <>
      <p className="carte__etat">
        Ce tournoi reçoit une <strong>copie</strong> des catégories et blasons du club. Vous pouvez
        les ajuster ici sans rien changer au club — et sans que les éditions passées ne bougent.
      </p>
      <button type="button" disabled={assembler.isPending} onClick={() => assembler.mutate()}>
        Copier les briques du club dans ce tournoi
      </button>
      {assembler.data && <p className="carte__etat">{decrireRapport(assembler.data)}</p>}
      <MessageErreur erreur={assembler.error} />

      <h4 className="carte__soustitre">Reporter au club — catégories</h4>
      {categories.isError && <MessageErreur erreur={categories.error} />}
      {(categories.data ?? []).length === 0 ? (
        <p className="carte__etat">
          Aucune catégorie dans ce tournoi : copiez celles du club ci-dessus, ou créez-en une plus
          bas.
        </p>
      ) : (
        <ul className="liste-gabarits">
          {(categories.data ?? []).map((categorie) => (
            <li key={categorie.id} className="gabarit">
              <div className="gabarit__ligne">
                <span className="gabarit__nom">{categorie.libelle}</span>
                <span className="gabarit__actions">
                  <BoutonPermanent
                    enCours={promouvoirCategorie.isPending}
                    onConfirmer={() => promouvoirCategorie.mutate(categorie.id)}
                  />
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
      <MessageErreur erreur={promouvoirCategorie.error} />

      <h4 className="carte__soustitre">Reporter au club — blasons</h4>
      {blasons.isError && <MessageErreur erreur={blasons.error} />}
      {(blasons.data ?? []).length === 0 ? (
        <p className="carte__etat">Aucun blason dans ce tournoi : copiez ceux du club ci-dessus.</p>
      ) : (
        <ul className="liste-gabarits">
          {(blasons.data ?? []).map((blason) => (
            <li key={blason.id} className="gabarit">
              <div className="gabarit__ligne">
                <span className="gabarit__nom">{blason.nom}</span>
                <span className="gabarit__actions">
                  <BoutonPermanent
                    enCours={promouvoirBlason.isPending}
                    onConfirmer={() => promouvoirBlason.mutate(blason.id)}
                  />
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
      <MessageErreur erreur={promouvoirBlason.error} />
    </>
  )
}

/**
 * « Rendre permanent », en deux temps.
 *
 * La promotion **écrit dans le patrimoine du club** — elle dépasse le tournoi courant, ce qui est
 * exactement ce qu'un geste d'un seul clic ne doit pas faire passer inaperçu. La confirmation dit
 * aussi ce que la promotion **ne fait pas** : les éditions passées ne bougeront pas. C'est la
 * question que l'organisateur se pose à cet instant précis.
 */
function BoutonPermanent({ enCours, onConfirmer }: { enCours: boolean; onConfirmer: () => void }) {
  const [confirmation, setConfirmation] = useState(false)

  if (!confirmation) {
    return (
      <button type="button" className="bouton--discret" onClick={() => setConfirmation(true)}>
        Rendre permanent
      </button>
    )
  }
  return (
    <>
      <span className="carte__etat">
        Reporter dans le patrimoine du club&nbsp;? Les tournois déjà assemblés ne changeront pas.
      </span>
      <button type="button" disabled={enCours} onClick={onConfirmer}>
        Confirmer
      </button>
      <button type="button" className="bouton--discret" onClick={() => setConfirmation(false)}>
        Annuler
      </button>
    </>
  )
}

function ApplicationDuFormat({ tournoiId }: { tournoiId: number }) {
  const formats = useFormats()
  const appliquer = useAppliquerFormat(tournoiId)
  const phases = usePhases(tournoiId)
  const [choisi, setChoisi] = useState<string>('')

  const disponibles = formats.data ?? []
  const aDesPhases = (phases.data ?? []).length > 0

  return (
    <>
      <h4 className="carte__soustitre">Déroulé (format)</h4>
      <p className="carte__etat">
        Appliquer un format <strong>crée les phases</strong> de ce tournoi.
        {aDesPhases &&
          ' Les phases actuelles seront remplacées — impossible si l’une est démarrée.'}
      </p>
      {formats.isError && <MessageErreur erreur={formats.error} />}
      {disponibles.length === 0 ? (
        <p className="carte__etat">
          Aucun format dans le patrimoine : créez-en un depuis l’atelier («&nbsp;Formats&nbsp;»).
        </p>
      ) : (
        <form
          className="formulaire"
          onSubmit={(evenement) => {
            evenement.preventDefault()
            if (choisi !== '') appliquer.mutate(Number(choisi))
          }}
        >
          <select
            className="formulaire__champ"
            value={choisi}
            onChange={(e) => setChoisi(e.target.value)}
            aria-label="Format à appliquer"
          >
            <option value="">Choisir un format…</option>
            {disponibles.map((format) => (
              <option key={format.id} value={format.id}>
                {format.nom} — {format.etapes.map(decrireEtape).join(' → ')}
              </option>
            ))}
          </select>
          <button type="submit" disabled={appliquer.isPending || choisi === ''}>
            Appliquer à ce tournoi
          </button>
        </form>
      )}
      <MessageErreur erreur={appliquer.error} />
    </>
  )
}

function PromotionDuFormat({ tournoiId }: { tournoiId: number }) {
  const promouvoir = usePromouvoirFormat(tournoiId)
  const [nom, setNom] = useState('')

  return (
    <>
      <h4 className="carte__soustitre">Garder ce déroulé pour les prochaines années</h4>
      <p className="carte__etat">
        Enregistre les phases de ce tournoi comme un format du club. Les tournois déjà assemblés ne
        changeront pas&nbsp;: seuls les prochains en hériteront.
      </p>
      <form
        className="formulaire"
        onSubmit={(evenement) => {
          evenement.preventDefault()
          if (nom.trim() !== '') promouvoir.mutate(nom)
        }}
      >
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom du format (ex. Format Kervignac)"
          aria-label="Nom du format à enregistrer"
        />
        <button type="submit" disabled={promouvoir.isPending || nom.trim() === ''}>
          Enregistrer comme format du club
        </button>
      </form>
      {promouvoir.data && (
        <p className="carte__etat">Format «&nbsp;{promouvoir.data.nom}&nbsp;» enregistré.</p>
      )}
      <MessageErreur erreur={promouvoir.error} />
    </>
  )
}
