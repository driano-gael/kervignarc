// Écran de salle (E07US004, ADR-0064) — la troisième surface, projetée dans le gymnase.
//
// Ses contraintes sont **opposées** à celles des deux autres : ≥ 1920 px, vu de loin, **aucune
// interaction**, allumé huit heures d'affilée sans personne devant. Trois conséquences dans ce
// fichier :
//
// 1. **Aucun élément cliquable.** Pas de sélecteur de catégorie, pas d'onglet, pas de bouton. Ce
//    que l'écran montre vient de son déroulé ou de la consigne de l'admin — jamais d'un geste.
// 2. **Rien ne peut le casser.** Une erreur réseau n'efface pas la vue précédente : l'écran garde
//    ce qu'il affichait et signale discrètement qu'il n'est plus à jour. Un écran noir « ne se
//    plaint pas » (CA) — la panne muette est le mode de défaillance à éviter avant tout.
// 3. **La rotation se déduit du temps écoulé**, jamais d'un compteur incrémenté (cf. `rotation.ts`) :
//    un onglet en arrière-plan voit ses minuteurs bridés, et huit heures de dérive font un écran
//    bloqué sur une vue.
//
// Le compte à rebours d'une prise de contrôle se décompte **en local**, à partir du `reste_s` reçu.
// C'est ce qui rend la reprise du déroulé insensible au réseau : même isolé, l'écran reprend à
// l'heure (ADR-0064).

import { useEffect, useState } from 'react'

import { VueClassement } from '../competition/VueClassement'
import { LIBELLE_VUE, type VueEcran, type VueProgrammee } from '../ecrans/api'
import { useAffichageEcran } from '../ecrans/hooks'
import { PlanCiblesPublic } from '../placement/PlanCiblesPublic'
import { SchemaBraquets } from '../../shared/schema-braquets/SchemaBraquets'
import { useSuiviDeroule } from '../suivi-deroule/hooks'
import { formaterReste, resteDeLaPrise, vueCourante } from './rotation'

/** Cadence du battement local. 1 s suffit : la rotation est au grain de la dizaine de secondes, et
 * seul le compte à rebours d'une prise de contrôle demande une précision à la seconde. */
const BATTEMENT_MS = 1000

export function EcranSalle({ libelle, tournoiId }: { libelle: string | null; tournoiId: number }) {
  const affichage = useAffichageEcran(true)
  const secondes = useHorlogeLocale()

  const sousControle = affichage.data?.sous_controle === true
  const vueFigee = affichage.data?.vue_figee ?? null
  const vues = affichage.data?.vues ?? null

  // L'origine du décompte est l'instant où la réponse a été **reçue**, que React Query horodate
  // pour nous (`dataUpdatedAt`, en millisecondes). Aucun état local à tenir : sans cela, il aurait
  // fallu un `useState` réinitialisé par un effet à chaque réponse — trois lignes de plus, une
  // cascade de rendus, et un écran resté allumé toute la journée qui croirait toutes les prises
  // expirées si l'on oubliait la réinitialisation.
  const depuis = Math.max(0, secondes - affichage.dataUpdatedAt / 1000)
  const reste = resteDeLaPrise(affichage.data?.reste_s ?? null, depuis)
  // La rotation est calée sur l'**heure absolue**, pas sur le temps depuis l'allumage : deux écrans
  // portant le même déroulé basculent alors ensemble, ce qui évite l'effet désagréable de deux
  // projections voisines montrant la même vue à un décalage de sept secondes.
  const rotation = vues === null ? null : vueCourante(vues, secondes)
  const vue: VueEcran | null = vueFigee ?? rotation?.vue.vue ?? null

  return (
    <section className="salle" aria-live="off">
      <BandeauSalle
        libelle={libelle}
        vue={vue}
        sousControle={sousControle}
        reste={reste}
        aJour={affichage.isError !== true}
        rotation={rotation?.vue ?? null}
      />
      <div className="salle__scene">
        {/* Tant que la première réponse n'est pas arrivée, on n'affiche **rien de faux** : un
            message d'attente vaut mieux qu'un classement vide qui ressemblerait à un classement. */}
        {vue === null ? (
          <p className="salle__attente">Connexion à l’écran…</p>
        ) : (
          <VueDeSalle vue={vue} tournoiId={tournoiId} />
        )}
      </div>
    </section>
  )
}

function VueDeSalle({ vue, tournoiId }: { vue: VueEcran; tournoiId: number }) {
  const suivi = useSuiviDeroule(tournoiId)

  if (vue === 'classement') {
    // `admin={false}` : la vue publique du classement, sans les colonnes de gestion.
    return <VueClassement tournoiId={tournoiId} admin={false} />
  }
  if (vue === 'plan_cibles') {
    return <PlanCiblesPublic tournoiId={tournoiId} />
  }
  // Surface **salle** : taille ajustée (le dessin remplit l'écran, le `viewBox` agrandit texte
  // compris) et habillage « identité ». `DV-08` sera honoré quand E01US016 livrera les couleurs du
  // tournoi ; d'ici là l'habillage se distingue de l'outil par sa mise en page, pas par sa palette.
  return (
    <SchemaBraquets
      blocs={suivi.data?.blocs ?? []}
      avancement={suivi.data?.avancement ?? []}
      taille="ajustee"
      habillage="identite"
      messageVide="Le déroulé de ce tournoi n’est pas encore composé."
    />
  )
}

/** Le bandeau permanent : où on est, ce qu'on regarde, et si l'écran est piloté.
 *
 * Il porte le seul indicateur que le CA exige côté salle — savoir que l'écran est **sous contrôle**
 * et pour combien de temps. Sans lui, un podium figé serait indiscernable d'un écran planté, et
 * personne dans le gymnase ne saurait lequel des deux appeler l'organisateur. */
function BandeauSalle({
  libelle,
  vue,
  sousControle,
  reste,
  aJour,
  rotation,
}: {
  libelle: string | null
  vue: VueEcran | null
  sousControle: boolean
  reste: number | null
  aJour: boolean
  rotation: VueProgrammee | null
}) {
  return (
    <header className="salle__bandeau">
      <span className="salle__lieu">{libelle ?? 'Écran de salle'}</span>
      <span className="salle__vue">{vue === null ? '—' : LIBELLE_VUE[vue]}</span>
      {sousControle && (
        <span className="salle__controle" role="status">
          Vue imposée par l’organisation
          {reste === null ? '' : ` · reprise dans ${formaterReste(reste)}`}
        </span>
      )}
      {!sousControle && rotation !== null && (
        <span className="salle__cadence">
          Vue suivante dans {formaterReste(rotation.cadence_s)}
        </span>
      )}
      {!aJour && (
        // `DV-03` : la couleur ne porte pas le sens seule — le mot « hors ligne » est écrit.
        <span className="salle__hors-ligne" role="status">
          ● Hors ligne — affichage figé
        </span>
      )}
    </header>
  )
}

/** L'heure locale, en secondes, rafraîchie au battement.
 *
 * Une horloge et non un compteur : c'est elle qui rend la rotation insensible aux minuteurs bridés
 * d'un onglet en arrière-plan (cf. l'en-tête de `rotation.ts`). */
function useHorlogeLocale(): number {
  const [secondes, setSecondes] = useState(() => Date.now() / 1000)
  useEffect(() => {
    const battement = window.setInterval(() => setSecondes(Date.now() / 1000), BATTEMENT_MS)
    return () => window.clearInterval(battement)
  }, [])
  return secondes
}
