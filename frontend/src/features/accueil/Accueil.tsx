// Accueil-tableau de bord contextualisé par tournoi (E14US001, `D-20` ; E16US021).
//
// « Où j'en suis, quoi faire ensuite », sans parcourir ~21 écrans. Il **agrège** des sources déjà
// livrées et ne recalcule **aucune** règle métier. Toutes ses lectures pollent — écran **live**.

// ⚠️ **Trois surfaces, pas quatre** (E16US021) : les blocs par départ ont retiré la pastille de
// relance (absorbée dans le bloc du créneau) et le chiffre « Inscrits » (que la somme des effectifs
// redit). Ne pas en empiler une de plus sans dire laquelle elle remplace — c'est `DETTE-082`.

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { texteErreur } from '../../shared/ui/texteErreur'
import type { LigneCompletude } from '../completude/api'
import { useCompletude } from '../completude/hooks'
import { afficheEtat, detailLigne } from '../completude/presentation'
import type { Tournoi } from '../competition/api'
import { usePaiementsArchers } from '../paiements/hooks'
import type { Supervision } from '../supervision/api'
import { useSupervision } from '../supervision/hooks'
import { BadgeStatut } from '../competition/BadgeStatut'
import { BlocsParDepart } from './BlocsParDepart'
import { FriseCycleDeVie, type RenvoiJalon } from './FriseCycleDeVie'

export function Accueil({
  tournoi,
  jalons,
}: {
  tournoi: Tournoi
  /** Renvois de la frise vers les écrans « prêt à… » (E16US021) — la coquille tient libellé et chemin. */
  jalons?: Readonly<Record<string, RenvoiJalon>>
}) {
  const completude = useCompletude(tournoi.id)
  const supervision = useSupervision(tournoi.id)
  const paiements = usePaiementsArchers(tournoi.id)

  // ⚠️ **Ce chiffre compte les ARCHERS DU TOURNOI, pas des engagements** : `lister_par_archer`
  // rend une ligne par archer saisi, inscrit ou non. Il n'est donc **pas** la somme des effectifs
  // des blocs (qui, eux, comptent un archer une fois par créneau) — d'où le libellé explicite
  // ci-dessous, et d'où son retrait comme chiffre autonome par E16US021 : affiché seul à côté des
  // blocs, il se lisait comme un total qu'aucune addition ne retrouvait.
  const archersDuTournoi = paiements.data?.length ?? null
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

      {/* CA A02 — **en tête**, avant la frise et les chiffres : c'est « j'arrive et je vois », et
          la pause d'un créneau (E05US034) s'y lit sur le bloc qu'elle concerne. La mettre sous une
          checklist de dix lignes reviendrait à ne pas la mettre. */}
      <BlocsParDepart tournoiId={tournoi.id} />

      <FriseCycleDeVie tournoi={tournoi} jalons={jalons} />

      <div className="accueil__chiffres">
        <Chiffre
          libelle="Réglés (archers du tournoi)"
          valeur={
            archersDuTournoi === null || regles === null ? '—' : `${regles}/${archersDuTournoi}`
          }
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
