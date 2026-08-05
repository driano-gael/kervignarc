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

import { BoutonConfirme } from '../../shared/ui/BoutonConfirme'
import { VueClassement } from '../competition/VueClassement'
import { LIBELLE_VUE, type VueEcran } from '../ecrans/api'
import { useAffichageEcran } from '../ecrans/hooks'
import { PlanCiblesDeSalle } from '../placement/PlanCiblesPublic'
import { VuePalmares } from '../palmares/VuePalmares'
import { VueAffectations } from '../routage/VueAffectations'
import { VueTableaux } from '../tableaux/VueTableaux'
import { SchemaBraquets } from '../../shared/schema-braquets/SchemaBraquets'
import { useSuiviDeroule } from '../suivi-deroule/hooks'
import {
  formaterReste,
  resteDeLaPrise,
  vueAAfficher,
  vueCourante,
  type EtatRotation,
} from './rotation'

/** Cadence du battement local. 1 s suffit : la rotation est au grain de la dizaine de secondes, et
 * seul le compte à rebours d'une prise de contrôle demande une précision à la seconde. */
const BATTEMENT_MS = 1000

export function EcranSalle({
  libelle,
  tournoiId,
  onDecrocher,
}: {
  libelle: string | null
  tournoiId: number
  // Décrocher cet écran (S01, retour maquettes du 04/08/2026 : *« on doit pouvoir décrocher un
  // écran »*). Fourni par `EspacePoste`, qui possède la session — l'écran de salle ne connaît pas le
  // jeton, et lui faire importer la feature `poste` créerait un cycle d'imports.
  //
  // ⚠️ **Ce n'est pas une entorse à « aucune interaction »** (CA E07US004) : la règle vise ce qui se
  // voit depuis la salle, à dix mètres, sur un écran que personne ne touche. L'affordance reste donc
  // **invisible au repos** et n'apparaît qu'au survol ou au focus clavier — c'est-à-dire uniquement
  // pour quelqu'un physiquement devant la machine, exactement la personne qui a le droit de la
  // reconfigurer. Sans elle, un écran rattaché au mauvais tournoi n'était récupérable qu'en allant
  // chercher l'organisateur pour révoquer le jeton depuis l'admin.
  onDecrocher?: () => void
}) {
  const affichage = useAffichageEcran(true)
  const secondes = useHorlogeLocale()

  const sousControle = affichage.data?.sous_controle === true
  const vueFigee = affichage.data?.vue_figee ?? null
  // Ce qui tourne **maintenant** ; et le repli, toujours le déroulé propre de l'écran. Les deux sont
  // distincts parce qu'une séquence **imposée** occupe `vues` : à l'échéance, retomber sur `vues`
  // reviendrait à continuer de jouer la consigne (2ᵉ passe de revue).
  const vues = affichage.data?.vues ?? null
  const repli = affichage.data?.deroule_repli ?? null

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
  // ⚠️ **La prise de contrôle se termine en local** — la garantie qui justifie toute l'architecture
  // « état lu » d'ADR-0064. L'arbitrage vit dans `rotation.ts` (`vueAAfficher`), pas ici : il y est
  // **testé**, alors qu'écrit dans ce rendu il ne l'était pas — c'est le reproche de la 2ᵉ passe de
  // revue, et il était juste (la fonction qui porte la promesse centrale de l'ADR n'avait aucun
  // verrou).
  const echue = sousControle && reste !== null && reste <= 0
  // À l'échéance on tourne sur le **repli**, pas sur `vues` : une séquence imposée y serait encore.
  const aJouer = echue ? repli : vues
  const rotation = aJouer === null ? null : vueCourante(aJouer, secondes)
  const affiche = vueAAfficher({
    sous_controle: sousControle,
    vue_figee: vueFigee,
    reste,
    rotation,
  })

  return (
    <section className="salle" aria-live="off">
      <BandeauSalle
        libelle={libelle}
        vue={affiche.vue}
        sousControle={affiche.sous_controle}
        aJour={affichage.isError !== true}
        rotation={rotation}
      />
      {onDecrocher !== undefined && (
        // ⚠️ **Confirmé, comme les sept autres gestes destructeurs du produit.** Une première version
        // décrochait au premier clic : sur un parc tactile il n'y a **pas de survol**, donc rien ne
        // se révélait — le premier tap dans le coin agissait directement, et sur un PC de projection
        // ce coin est exactement l'endroit où l'on va chercher la fermeture d'une fenêtre. Le
        // recouvrement, lui, coûte de retaper un code à six caractères en pleine salle (revue du
        // 05/08/2026, axes A et C1).
        <BoutonConfirme
          libelle="Décrocher cet écran"
          className="salle__decrocher"
          ton="danger"
          titre="Décrocher cet écran ?"
          message="Cet appareil quitte le tournoi et revient à l’écran de choix."
          detail="Il faudra retaper son code pour le rattacher."
          libelleConfirmer="Décrocher"
          onConfirmer={onDecrocher}
        />
      )}
      <div className="salle__scene">
        {/* Tant que la première réponse n'est pas arrivée, on n'affiche **rien de faux** : un
            message d'attente vaut mieux qu'un classement vide qui ressemblerait à un classement. */}
        {affiche.vue === null ? (
          <p className="salle__attente">Connexion à l’écran…</p>
        ) : (
          <VueDeSalle vue={affiche.vue} tournoiId={tournoiId} />
        )}
      </div>
    </section>
  )
}

function VueDeSalle({ vue, tournoiId }: { vue: VueEcran; tournoiId: number }) {
  // `admin={false}` : la vue publique du classement. `filtrable={false}` : **aucune interaction**
  // sur un écran projeté — un `<select>` que personne ne peut actionner (correctif de revue).
  if (vue === 'classement') {
    return <VueClassement tournoiId={tournoiId} admin={false} filtrable={false} />
  }
  if (vue === 'plan_cibles') {
    // Variante sans sélecteur, calée sur le départ **en cours** et non sur le premier.
    return <PlanCiblesDeSalle tournoiId={tournoiId} />
  }
  if (vue === 'suivi_deroule') {
    return <SuiviDeSalle tournoiId={tournoiId} />
  }
  if (vue === 'affectations') {
    // `interactif={false}` : **aucune interaction** sur un écran projeté (CA E07US004). Ce n'est pas
    // qu'une question de boutons inutiles — c'est ce qui fixe la lecture sur l'ordre du **pas de
    // tir**, le seul qui se lise de loin quand on cherche sa butte (`Q-UX2`).
    return <VueAffectations tournoiId={tournoiId} interactif={false} />
  }
  if (vue === 'tableaux') {
    // `interactif={false}` : ni sélecteur de phase ni bascule « mon chemin » (CA E07US004 — aucune
    // interaction). Ce n'est pas qu'une question de boutons inutiles : « mon chemin » n'a aucun
    // sens devant un projecteur, personne n'y suit d'archer. L'écran montre donc **l'arbre
    // complet** du tableau qui se joue, seule lecture qui informe une salle entière.
    return <VueTableaux tournoiId={tournoiId} interactif={false} />
  }
  if (vue === 'palmares') {
    // `interactif={false}` : ni filtre ni bouton d'export sur un écran projeté (CA E07US004). La
    // vue garde ses podiums par catégorie — c'est ce qu'on vient lire à 17 h.
    return <VuePalmares tournoiId={tournoiId} interactif={false} />
  }
  // Vue **inconnue** : un SPA resté ouvert pendant une montée de version peut recevoir une valeur
  // que ce bundle ne connaît pas. On le **dit** plutôt que de retomber en silence sur une autre vue
  // — un écran qui montre autre chose que ce qui a été demandé, sans le signaler, est indétectable
  // depuis la salle (correctif de revue).
  return (
    <p className="salle__attente">
      Cette vue n’est pas prise en charge par cet écran. Rechargez-le pour le mettre à jour.
    </p>
  )
}

/** Le suivi du déroulé, **dans son propre composant**.
 *
 * Séparé pour que `useSuiviDeroule` ne soit monté que quand cette vue est réellement affichée.
 * Appelé en tête de `VueDeSalle`, il interrogeait l'endpoint le plus coûteux du serveur (une
 * reconstruction de tous les tableaux) toutes les 10 s **pendant les deux tiers du cycle** où
 * l'écran montre autre chose — soit, sur huit heures, des milliers de reconstructions inutiles,
 * sur un endpoint public non authentifié (correctif de revue). */
function SuiviDeSalle({ tournoiId }: { tournoiId: number }) {
  const suivi = useSuiviDeroule(tournoiId)
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
 * Il porte le seul indicateur que le CA exige côté salle — savoir que l'écran est **sous contrôle**.
 * Sans lui, un podium figé serait indiscernable d'un écran planté, et personne dans le gymnase ne
 * saurait lequel des deux appeler l'organisateur.
 *
 * **Le compte à rebours de reprise en a été retiré** (P07, retour maquettes du 04/08/2026 : *« bruit
 * à l'écran, seulement visible côté admin »*). Le fait — « cette vue est imposée » — reste écrit,
 * parce qu'il répond à la question que se pose la salle ; l'échéance à la seconde ne répond qu'à
 * celle de l'organisateur, qui la lit sur son propre écran. `reste` n'est donc plus un paramètre du
 * bandeau — il continue de piloter l'**expiration locale** dans `EcranSalle`, ce qui est le cœur
 * d'ADR-0064 et n'a jamais dépendu de son affichage. */
function BandeauSalle({
  libelle,
  vue,
  sousControle,
  aJour,
  rotation,
}: {
  libelle: string | null
  vue: VueEcran | null
  sousControle: boolean
  aJour: boolean
  rotation: EtatRotation | null
}) {
  return (
    <header className="salle__bandeau">
      <span className="salle__lieu">{libelle ?? 'Écran de salle'}</span>
      <span className="salle__vue">
        {vue === null ? '—' : (LIBELLE_VUE[vue] ?? 'Vue inconnue')}
      </span>
      {sousControle && (
        <span className="salle__controle" role="status">
          Vue imposée par l’organisation
        </span>
      )}
      {/* `reste_s` de la **rotation**, pas la cadence de l'étape : la première version affichait
          `cadence_s`, donc une **constante** (« Vue suivante dans 30 s », en permanence). La
          fonction pure calculait bien le reste et son test le prouvait — c'est le consommateur qui
          lisait le mauvais champ (correctif de revue). */}
      {!sousControle && rotation !== null && (
        <span className="salle__cadence">Vue suivante dans {formaterReste(rotation.reste_s)}</span>
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
