// Accueil-tableau de bord contextualisé par tournoi (E14US001, `D-20`).
//
// « Où j'en suis, quoi faire ensuite », sans parcourir ~21 écrans. **Agrège** des sources déjà
// livrées — il ne recalcule **aucune** règle métier (cadrage E14US001) :
//  - frise du cycle de vie 7 statuts + actions (`FriseCycleDeVie`, transitions du serveur) ;
//  - chiffres-clés : inscrits & réglés (paiements, E08US002), postes en ligne (supervision, E12US001) ;
//  - checklist « à faire » et alertes dérivées de la complétude (E12US005) + des postes hors ligne.
//
// Front sans test de rendu (règle 9) → à vérifier **à l'écran**. Les lectures pollent (complétude,
// supervision) : l'accueil est un écran **live**.

import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { LigneCompletude } from '../completude/api'
import { useCompletude } from '../completude/hooks'
import { afficheEtat, detailLigne } from '../completude/presentation'
import type { Tournoi } from '../competition/api'
import { usePaiementsArchers } from '../paiements/hooks'
import type { Supervision } from '../supervision/api'
import { useSupervision } from '../supervision/hooks'
import { BadgeStatut } from '../competition/BadgeStatut'
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

  const lignes: LigneCompletude[] = [
    ...(completude.data?.sportif ?? []),
    ...(completude.data?.hors_sportif ?? []),
  ]
  const alertes = construireAlertes(lignes, supervision.data)

  return (
    <section className="carte carte--large accueil">
      <div className="accueil__entete">
        <h2 className="carte__titre">{tournoi.nom}</h2>
        <BadgeStatut statut={tournoi.statut} />
      </div>

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
              Complétude injoignable — {completude.error.message}
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
