// Accueil-tableau de bord contextualisé par tournoi (E14US001, `D-20`).
//
// « Où j'en suis, quoi faire ensuite », sans parcourir ~21 écrans. Il **agrège** des sources déjà
// livrées et ne recalcule **aucune** règle métier : frise du cycle de vie, chiffres-clés
// (paiements, supervision), checklist et alertes dérivées de la complétude. Couverture : deux tests
// de rendu gardent le fait que la checklist ne porte **que** le sportif ; le reste se vérifie à
// l'œil. Les lectures pollent — l'accueil est un écran **live** (ADR-0075).

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { texteErreur } from '../../shared/ui/texteErreur'
import { useMaintenant } from '../../shared/ui/useMaintenant'
import type { LigneCompletude } from '../completude/api'
import { useCompletude } from '../completude/hooks'
import { afficheEtat, detailLigne } from '../completude/presentation'
import type { Tournoi } from '../competition/api'
import { usePaiementsArchers } from '../paiements/hooks'
import type { Supervision } from '../supervision/api'
import { useSupervision } from '../supervision/hooks'
import { BadgeStatut } from '../competition/BadgeStatut'
import { useQueries } from '@tanstack/react-query'
import { phraseDeRelance, resumeDeRelance } from '../../shared/phases/relance'
import { useDeparts } from '../departs/hooks'
import { getArretsEnAttente } from '../suivi-deroule/api'
import { INTERVALLE_POLL_MS, RACINE_ARRETS } from '../suivi-deroule/hooks'
import { FriseCycleDeVie } from './FriseCycleDeVie'

export function Accueil({ tournoi }: { tournoi: Tournoi }) {
  const completude = useCompletude(tournoi.id)
  const supervision = useSupervision(tournoi.id)
  const paiements = usePaiementsArchers(tournoi.id)

  // Une seule source pour inscrits & réglés : le registre de paiements a une ligne par archer inscrit.
  const inscrits = paiements.data?.length ?? null
  const regles = paiements.data?.filter((a) => a.recap.reste_centimes <= 0).length ?? null
  const postesEnLigne = supervision.data?.nb_en_ligne ?? null
  const postesTotal = supervision.data?.nb_total ?? null

  // E16US003 — **le sportif seul**, ici aussi. Le refus d'A14 (« je n'aime pas le mélange entre le
  // déroulé et la gestion administrative ») porte sur l'axe **pilotage**, et ce tableau de bord en
  // est la destination d'ouverture (`AXE_PAR_DESTINATION.accueil === 'pilotage'`) : y laisser
  // « Paiements 113/120 » sous « Qualification 28/30 cibles » aurait rejoué le refus sur l'écran le
  // plus vu de l'axe — le trou aurait été *déplacé*, pas fermé. Le hors-sportif se lit sur l'axe
  // gestion, en tête de l'écran Paiements (`CompletudeAdministrative`). Le chiffre-clé « Réglés »
  // ci-dessus reste, lui : c'est un **repère**, pas une tâche à faire.
  const lignes: LigneCompletude[] = completude.data?.sportif ?? []
  const alertes = construireAlertes(lignes, supervision.data)

  return (
    <section className="carte carte--large accueil">
      <div className="accueil__entete">
        <h2 className="carte__titre">{tournoi.nom}</h2>
        <BadgeStatut statut={tournoi.statut} />
      </div>

      {/* E05US034 — **avant** la frise et les chiffres : quand la salle attend, c'est le seul fait
          qui compte, et le mettre sous une checklist de dix lignes revient à ne pas le mettre. */}
      <PastilleDeRelance tournoiId={tournoi.id} />

      <FriseCycleDeVie tournoi={tournoi} />

      <div className="accueil__chiffres">
        <Chiffre libelle="Inscrits" valeur={inscrits === null ? '—' : String(inscrits)} />
        <Chiffre
          libelle="Réglés"
          valeur={inscrits === null || regles === null ? '—' : `${regles}/${inscrits}`}
        />
        <Chiffre
          libelle="Postes en ligne"
          valeur={postesTotal === null ? '—' : `${postesEnLigne}/${postesTotal}`}
        />
      </div>

      <div className="accueil__grille">
        <div className="carte">
          <h3 className="carte__soustitre">À faire</h3>
          {completude.isError && (
            <p className="carte__etat carte__etat--erreur" role="alert">
              Complétude injoignable — {texteErreur(completude.error)}
            </p>
          )}
          <ul className="checklist">
            {lignes.map((ligne) => {
              const etat = afficheEtat(ligne.etat)
              const detail = detailLigne(ligne)
              return (
                <li key={ligne.cle} className="checklist__ligne">
                  <span
                    className={`checklist__pastille checklist__pastille--${etat.classe}`}
                    aria-hidden="true"
                  />
                  <span className="checklist__libelle">{ligne.libelle}</span>
                  <span className="checklist__etat">{detail ?? etat.libelle}</span>
                </li>
              )
            })}
          </ul>
        </div>

        <div className="carte">
          <h3 className="carte__soustitre">Alertes</h3>
          {alertes.length === 0 ? (
            <p className="carte__etat carte__etat--ok">Aucune alerte.</p>
          ) : (
            <ul className="alertes">
              {alertes.map((alerte) => (
                <li key={alerte.cle} className="alertes__ligne">
                  {alerte.texte}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <MessageErreur erreur={paiements.error} />
    </section>
  )
}

function Chiffre({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div className="chiffre">
      <span className="chiffre__valeur">{valeur}</span>
      <span className="chiffre__libelle">{libelle}</span>
    </div>
  )
}

// Une alerte porte une **clé stable** (`cle`) distincte de son texte : deux lignes de complétude au
// même libellé et même reste produiraient sinon deux `key` React identiques (revue E14US001).
interface Alerte {
  cle: string
  texte: string
}

// Alertes = ce qui appelle une action **maintenant** : lignes de complétude en `alerte` (commencé
// mais incomplet) + postes hors ligne. On ne recalcule rien — on **relit** l'état des sources.
function construireAlertes(lignes: LigneCompletude[], supervision?: Supervision): Alerte[] {
  const alertes: Alerte[] = []
  for (const ligne of lignes) {
    if (ligne.etat !== 'alerte') continue
    const reste = ligne.fait !== null && ligne.total !== null ? ligne.total - ligne.fait : null
    alertes.push({
      cle: `completude-${ligne.cle}`,
      texte:
        reste !== null && reste > 0
          ? `${ligne.libelle} : ${reste} à compléter`
          : `${ligne.libelle} à finir`,
    })
  }
  if (supervision && supervision.nb_total > 0 && supervision.nb_en_ligne < supervision.nb_total) {
    alertes.push({
      cle: 'postes-hors-ligne',
      texte: `${supervision.nb_total - supervision.nb_en_ligne} poste(s) hors ligne`,
    })
  }
  return alertes
}

/** La **pastille de rappel** : « 2 phases attendent votre relance depuis 14 min » (CA E05US034).
 *
 * ⚠️ **C'est le filet de sécurité de la capacité livrée par E05US033.** Une pause programmée
 * éteint une phase toute seule, à la faveur d'une validation faite ailleurs : sans ce rappel,
 * l'organisateur n'apprend qu'une salle attend qu'en ouvrant le pilotage — un **mode de panne
 * neuf**. ⚠️ **Une lecture par créneau, et aucune route neuve** : `useQueries` sur la route que le
 * pilotage polle déjà partage son cache. Ne rend rien quand il n'y a rien à relancer.
 */
function PastilleDeRelance({ tournoiId }: { tournoiId: number }) {
  const departs = useDeparts(tournoiId)
  // Battement à la minute — le grain affiché. Cf. `useMaintenant` : lire l'horloge pendant le rendu
  // est une impureté, et le compteur resterait figé tant que le serveur renvoie la même réponse.
  const maintenant = useMaintenant(60000)
  const parCreneau = useQueries({
    queries: (departs.data ?? []).map((depart) => ({
      queryKey: [...RACINE_ARRETS, depart.id] as const,
      queryFn: () => getArretsEnAttente(depart.id),
      // Même cadence que `useArretsEnAttente`, dont on partage la clé de cache : recopier la
      // valeur à la main les aurait fait diverger au premier ajustement (revue E05US034).
      refetchInterval: INTERVALLE_POLL_MS,
      staleTime: 0,
    })),
  })

  const arrets = parCreneau.flatMap((resultat) => resultat.data ?? [])
  const resume = resumeDeRelance(arrets, maintenant)
  if (resume === null) return null

  return (
    <p className="carte__etat carte__etat--alerte" role="status">
      <strong>{phraseDeRelance(resume)}</strong> Le tir est suspendu&nbsp;: relancez depuis
      «&nbsp;Suivi du déroulé&nbsp;».
    </p>
  )
}
