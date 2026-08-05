// Console de supervision des postes (E12US001, ADR-0038 ; écrans de salle : E07US004, ADR-0064) —
// l'écran du jour J.
//
// « Ce n'est pas un graphique de progression : c'est une console de supervision. » Elle distingue
// *ils tirent lentement* (en ligne, mais dernière activité ancienne) de *leur tablette est morte*
// (hors ligne). Live par poll court (cf. `useSupervision`). L'état se rend en **couleur + pastille +
// texte** (jamais la couleur seule) ; hors ligne = **ambre**, pas rouge (arbitrage ADR-0038 / DV-03).
//
// **Les écrans de salle y figurent aussi** (E07US004), dans un second tableau — pas dans un autre
// écran. Le CA le dit sans détour : *« un écran figé ne se plaint pas, seule la supervision le
// révèle »*. C'est aussi d'ici que l'organisateur **impose une vue** sans traverser le gymnase, et
// qu'il voit, en rouge, les prises de contrôle qu'il a oublié de rendre.

import { ErreurApi } from '../../shared/api/client'
import { BoutonConfirme } from '../../shared/ui/BoutonConfirme'
import { GroupeRepliable } from '../../shared/ui/GroupeRepliable'
import type { PosteSupervision } from './api'
import { PiloterEcrans } from './PiloterEcrans'
import { afficheEtat, avancementLibelle } from './etat'
import { useRevoquerPoste, useSupervision } from './hooks'
import { tempsRelatif } from './tempsRelatif'

export function Supervision({ tournoiId }: { tournoiId: number }) {
  const supervision = useSupervision(tournoiId)
  // Les deux natures de poste, séparées **une fois** : elles alimentent chacune leur bandeau, et
  // chaque bandeau a besoin de son décompte d'anomalies avant même d'être déplié (A12).
  const postes = supervision.data?.postes ?? []
  const cibles = postes.filter((poste) => poste.type === 'cible')
  const ecrans = postes.filter((poste) => poste.type === 'ecran')
  // ⚠️ **Anomalie = `hors_ligne`, jamais `non_rattache`.** Un poste non rattaché est l'état
  // **nominal** de la préparation : compter les 30 cibles avant distribution des tablettes faisait
  // hurler « 30 à vérifier » toute la matinée, et un signal qui hurle dans l'état normal cesse
  // d'être lu le jour où il dit vrai — l'inverse d'A13, « seuls les problèmes sautent aux yeux ».
  // Hors ligne, en revanche, c'est un poste **rattaché qui s'est tu** : là, il y a quelqu'un à
  // envoyer. (Revue du 05/08/2026, axe C1.)
  const muets = (liste: typeof postes) => liste.filter((p) => p.etat === 'hors_ligne').length

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Supervision des postes</h2>

      {supervision.isPending && <p className="carte__etat">Chargement…</p>}
      {supervision.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Supervision injoignable — {supervision.error.message}
        </p>
      )}

      {supervision.data && (
        <>
          <p className="supervision__compteur" role="status">
            <strong>
              {supervision.data.nb_en_ligne}/{supervision.data.nb_total}
            </strong>{' '}
            en ligne
          </p>

          {supervision.data.nb_total === 0 ? (
            <p className="carte__etat">
              Aucun poste préparé pour ce tournoi (préparez les codes de cible dans «&nbsp;Postes de
              cible&nbsp;»).
            </p>
          ) : (
            <GroupeRepliable
              titre="Écrans de cible"
              resume={`${supervision.data.nb_en_ligne}/${supervision.data.nb_total} en ligne`}
              nbAnomalies={muets(cibles)}
              libelleAnomalies="à vérifier"
              enfants={
                <table className="table supervision__table">
                  <thead>
                    <tr>
                      <th scope="col">Cible</th>
                      <th scope="col">État</th>
                      <th scope="col">Dernière activité</th>
                      <th scope="col">Avancement</th>
                      <th scope="col">IP</th>
                      <th scope="col">
                        <span className="sr-only">Action</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {cibles.map((poste) => (
                      <LignePoste key={poste.poste_id} poste={poste} tournoiId={tournoiId} />
                    ))}
                  </tbody>
                </table>
              }
            />
          )}

          {/* Second bandeau : les écrans de salle. Deux natures de poste, deux groupes — c'est
              exactement le découpage qu'A12 demande (« chaque type d'écran est sous un bandeau
              repliable de type »), et il existait déjà en substance ici, sans repli ni remontée
              d'alerte. */}
          <GroupeRepliable
            titre="Écrans de salle"
            resume={`${supervision.data.nb_ecrans_en_ligne}/${supervision.data.nb_ecrans} en ligne`}
            nbAnomalies={muets(ecrans)}
            libelleAnomalies="à vérifier"
            enfants={
              <PiloterEcrans
                tournoiId={tournoiId}
                ecrans={ecrans}
                nbEnLigne={supervision.data.nb_ecrans_en_ligne}
              />
            }
          />
        </>
      )}
    </section>
  )
}

function LignePoste({ poste, tournoiId }: { poste: PosteSupervision; tournoiId: number }) {
  const revoquer = useRevoquerPoste(tournoiId)
  const { classe, libelle } = afficheEtat(poste.etat)
  const rattache = poste.etat !== 'non_rattache'

  return (
    <tr>
      <td>Cible {poste.cible_index ?? '—'}</td>
      <td>
        <span className={`supervision__etat supervision__etat--${classe}`}>
          <span className="indicateur__pastille" aria-hidden="true" />
          {libelle}
        </span>
      </td>
      <td>
        {poste.derniere_saisie === null ? '—' : tempsRelatif(poste.derniere_saisie, new Date())}
      </td>
      <td>{avancementLibelle(poste.avancement)}</td>
      {/* IP en diagnostic (D-06), jamais une identité : sert à retrouver physiquement la tablette. */}
      <td className="supervision__ip">{poste.ip ?? '—'}</td>
      <td>
        {rattache && (
          /* Garde-fou tactile : révoquer un poste en cours de tir le coupe. Vrai dialogue depuis
             le retour maquettes du 04/08/2026 (A15) ; le calcul d'impact chiffré reste E12US007. */
          <BoutonConfirme
            libelle="Révoquer"
            className="lien"
            disabled={revoquer.isPending}
            enCours={revoquer.isPending}
            titre={`Révoquer la cible ${poste.cible_index ?? '?'} ?`}
            message="L’appareil repasse à l’écran de rattachement. S’il est en cours de saisie, il est coupé."
            libelleConfirmer="Révoquer"
            ton="danger"
            onConfirmer={() => revoquer.mutate(poste.poste_id)}
          />
        )}
        {revoquer.isError && (
          <span className="carte__etat--erreur" role="alert">
            {revoquer.error instanceof ErreurApi
              ? revoquer.error.message
              : 'Échec de la révocation.'}
          </span>
        )}
      </td>
    </tr>
  )
}
