// Hooks React Query de la saisie en duels (E04US013) — état serveur du tableau et des duels, et les
// trois écritures (manche / barrage / validation) avec **file hors-ligne** et **rejeu** (E04US009).
//
// Lectures : les phases du tournoi (publiques, pour choisir un tableau), l'état d'un tableau
// reconstruit, l'état d'un duel précis. Écritures : chaque acte tente un POST ; sur **panne réseau**
// il est **mis en file** et un état **optimiste** est renvoyé (le scoreur continue) ; un **refus
// serveur** (`ErreurApi`) est une vraie erreur, propagée. Le rejeu draine la file à la reconnexion.

import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useConnexionStore } from '../../shared/stores/connexionStore'
import {
  type ActeDuelEnFile,
  type FamilleDuel,
  cleSlot,
  useFileDuelsHorsLigneStore,
} from '../../shared/stores/fileDuelsHorsLigneStore'
import { useSessionScoreurStore } from '../../shared/stores/sessionScoreurStore'
import {
  type Duel,
  getDuel,
  getPhases,
  getTableau,
  saisirBarrage,
  saisirManche,
  type SaisirBarrage,
  type SaisirManche,
  type ValiderDuel,
  validerDuel,
} from './api'
import type { EtatPoulesSaisie } from '../poules/api'
import type { EtatCollineSaisie } from '../colline/api'
import type { EtatSuisseSaisie } from '../suisse/api'
import { injecterBarrage, injecterManche } from './duel'
import { estDejaHorsLigne, estRefusServeur } from './horsLigne'
import { rejouerActes } from './rejeu'

// ⚠️ La clé porte le **créneau**, pas le tournoi : c'est l'avancement d'un départ qu'on cache
// (ADR-0075). Indexée par tournoi, elle aurait servi les phases du matin au scoreur de
// l'après-midi — le cache aurait recréé le bug que la route vient de fermer.
const clePhases = (departId: number) => ['duels-phases', departId] as const
const cleTableau = (tournoiId: number, phaseId: number) =>
  ['duels-tableau', tournoiId, phaseId] as const
const cleDuel = (
  tournoiId: number,
  phaseId: number,
  matchNumero: number,
  famille: FamilleDuel = 'tableau',
) => ['duels-duel', famille, tournoiId, phaseId, matchNumero] as const

// L'etat d'une phase de **poules** (E05US023) : c'est lui qu'une ecriture doit invalider, la ou un
// acte de tableau invalide `cleTableau`. Domicilie ici parce que c'est ici que l'invalidation a
// lieu — la cle doit avoir un domicile unique, pas deux litteraux qui se ressemblent.
export const clePoules = (tournoiId: number, phaseId: number) =>
  ['poules-etat', tournoiId, phaseId] as const

// Une phase de poules se lit sous **deux** formes depuis le correctif de revue d'E05US023 : la
// consultation (contenu restreint, ouverte) et la saisie (le duel entier, scoreur). Ce sont deux
// entrées de cache distinctes, dérivées de `clePoules` — qui reste donc le **préfixe** commun.
//
// C'est ce qui fait que l'invalidation d'écriture n'a pas eu à changer : React Query invalide par
// préfixe, donc `invalidateQueries({ queryKey: clePoules(t, p) })` atteint les deux. Deux clés
// sœurs écrites à la main auraient laissé la vue d'organisation périmée après chaque flèche, sans
// que rien ne le signale.
export const clePoulesSaisie: CleDe<EtatPoulesSaisie> = (tournoiId: number, phaseId: number) =>
  [...clePoules(tournoiId, phaseId), 'saisie'] as const
export const clePoulesPubliques = (tournoiId: number, phaseId: number) =>
  [...clePoules(tournoiId, phaseId), 'publique'] as const

// Le **système suisse** (E05US030) suit exactement le même dessin, et pour les mêmes raisons : deux
// vues (saisie / rédigée) sous un **préfixe** commun, de sorte qu'une invalidation d'écriture
// atteigne les deux sans que personne n'ait à s'en souvenir.
export const cleSuisse = (tournoiId: number, phaseId: number) =>
  ['suisse-etat', tournoiId, phaseId] as const
export const cleSuisseSaisie: CleDe<EtatSuisseSaisie> = (tournoiId: number, phaseId: number) =>
  [...cleSuisse(tournoiId, phaseId), 'saisie'] as const
export const cleSuissePublique = (tournoiId: number, phaseId: number) =>
  [...cleSuisse(tournoiId, phaseId), 'publique'] as const

// La **colline** (E05US027) reprend le même dessin, à l'identique : deux entrées distinctes pour
// deux contenus distincts (rédigé / saisie), et la clé vit ici parce que c'est l'écriture qui
// l'invalide — une clé écrite à deux endroits est une clé qui divergera.
export const cleColline = (tournoiId: number, phaseId: number) =>
  ['colline-etat', tournoiId, phaseId] as const
export const cleCollineSaisie: CleDe<EtatCollineSaisie> = (tournoiId: number, phaseId: number) =>
  [...cleColline(tournoiId, phaseId), 'saisie'] as const
export const cleCollinePublique = (tournoiId: number, phaseId: number) =>
  [...cleColline(tournoiId, phaseId), 'publique'] as const

// `departId` peut être `null` le temps que la liste des créneaux arrive : la requête est alors
// désactivée plutôt que lancée sur un identifiant inventé (convention de `phases/hooks.ts`).
export function usePhases(departId: number | null) {
  return useQuery({
    queryKey: clePhases(departId ?? 0),
    queryFn: () => getPhases(departId as number),
    enabled: departId !== null,
  })
}

export function useTableau(tournoiId: number, phaseId: number) {
  return useQuery({
    queryKey: cleTableau(tournoiId, phaseId),
    queryFn: () => getTableau(tournoiId, phaseId),
    // `retry: false` : un refus déterministe (403 hors tournoi, 409 pas un tableau) ne gagne rien à
    // être réessayé. Pas de refetch au focus : il écraserait une frappe en cours si le scoreur
    // revient sur l'onglet. Le rafraîchissement se fait sur invalidation après écriture.
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useDuel(tournoiId: number, phaseId: number, matchNumero: number) {
  return useQuery({
    queryKey: cleDuel(tournoiId, phaseId, matchNumero),
    queryFn: () => getDuel(tournoiId, phaseId, matchNumero),
    retry: false,
    refetchOnWindowFocus: false,
  })
}

// Un duel « placeholder » pour l'état optimiste quand le cache est vide (cas rare : on n'arrive au
// pavé qu'après avoir lu le duel). Occupants/mode inconnus : l'injection y ajoute au moins l'acte
// saisi pour que l'écran ne reste pas figé, la vérité revenant au rejeu.
function placeholderDuel(matchNumero: number): Duel {
  return {
    numero: matchNumero,
    tour: 0,
    place_en_jeu: null,
    haut: null,
    bas: null,
    est_bye: false,
    mode: null,
    nb_manches: null,
    nb_fleches_par_volee: null,
    points_pour_gagner: null,
    zones: [],
    validee_par: null,
    manches: [],
    barrage: null,
    resultat: null,
  }
}

// --- Ce qui distingue une famille d'une autre (E05US030) -----------------------------------------
//
// ⚠️ **Trois tables, et non trois `if`.** Le mécanisme était binaire — « poule ou tableau » —,
// écrit en ternaire à quatre endroits. Y ajouter le système suisse par une quatrième comparaison
// aurait fait tomber le nouveau format dans la branche **tableau** partout où l'un des quatre
// aurait été oublié : le duel serait parti sur un routeur qui ne connaît pas son `match_numero`. Un
// `Record` exhaustif fait échouer la **compilation** au lieu de laisser le défaut sortir en salle.

/** La clé du **décor** d'une famille : ce qu'une écriture invalide en plus du duel lui-même. */
const CLE_DECOR: Record<FamilleDuel, (tournoiId: number, phaseId: number) => readonly unknown[]> = {
  tableau: cleTableau,
  poule: clePoules,
  suisse: cleSuisse,
  colline: cleColline,
}

/** Une clé de cache **marquée par le DTO qu'elle porte** — marqueur de compilation seulement.
 *
 * ⚠️ Sans lui, `photoDe<E>()` ne confinait qu'à moitié : les lambdas étaient vérifiées contre `E`,
 * mais `cle` restait « une clé quelconque », si bien qu'**intervertir `clePoulesSaisie` et
 * `cleSuisseSaisie` compilait encore** — et produisait le `TypeError` que la fabrique disait avoir
 * supprimé. Vérifié **par sonde** : un marqueur qu'on n'éprouve pas est un commentaire.
 */
type CleDe<E> = ((tournoiId: number, phaseId: number) => readonly unknown[]) & {
  readonly __dto?: E
}

/** La photo de saisie d'une famille : où l'écran lit ses duels, quand ce n'est pas `cleDuel`.
 *
 * `null` pour le tableau, qui lit bien `cleDuel` — c'est la seule famille dans ce cas. Les phases à
 * rencontres portent leurs duels **dans la photo de la phase**, groupés par poule ou par ronde ;
 * `numero` (le `match_numero` de la table `duel`) les identifie de bout en bout.
 */
interface PhotoDeSaisie<E> {
  cle: CleDe<E>
  /** Aplatit la photo en rencontres, quel que soit le niveau intermédiaire (poule, ronde). */
  rencontres: (etat: E) => { numero: number; duel: Duel }[]
  /** Réécrit le duel d'une rencontre dans la photo, en préservant la structure. */
  remplacer: (etat: E, matchNumero: number, duel: Duel) => E
}

/** Confine en **un seul point** l'assertion « cette clé porte ce DTO ».
 *
 * ⚠️ Sans cette fabrique, chaque entrée portait ses propres `as EtatXxx` sur des lambdas `unknown`
 * : intervertir deux `cle` compilait, et la faute ne sortait qu'en `TypeError` dans le chemin
 * **optimiste hors-ligne**, celui qui par construction ne lève aucune erreur visible — le trou que
 * le `Record` exhaustif ferme un cran plus haut, réintroduit un cran plus bas.
 */
function photoDe<E>(photo: PhotoDeSaisie<E>): PhotoDeSaisie<unknown> {
  return photo as PhotoDeSaisie<unknown>
}

const PHOTO: Record<FamilleDuel, PhotoDeSaisie<unknown> | null> = {
  tableau: null,
  poule: photoDe<EtatPoulesSaisie>({
    cle: clePoulesSaisie,
    rencontres: (etat) => etat.poules.flatMap((poule) => poule.rencontres),
    remplacer: (etat, matchNumero, duel) => ({
      ...etat,
      poules: etat.poules.map((poule) => ({
        ...poule,
        rencontres: poule.rencontres.map((rencontre) =>
          rencontre.numero === matchNumero ? { ...rencontre, duel } : rencontre,
        ),
      })),
    }),
  }),
  suisse: photoDe<EtatSuisseSaisie>({
    cle: cleSuisseSaisie,
    rencontres: (etat) => etat.rondes.flatMap((ronde) => ronde.rencontres),
    remplacer: (etat, matchNumero, duel) => ({
      ...etat,
      rondes: etat.rondes.map((ronde) => ({
        ...ronde,
        rencontres: ronde.rencontres.map((rencontre) =>
          rencontre.numero === matchNumero ? { ...rencontre, duel } : rencontre,
        ),
      })),
    }),
  }),
  // E05US027 : même forme à un niveau intermédiaire près — la **manche** au lieu de la ronde.
  colline: photoDe<EtatCollineSaisie>({
    cle: cleCollineSaisie,
    rencontres: (etat) => etat.manches.flatMap((manche) => manche.defis),
    remplacer: (etat, matchNumero, duel) => ({
      ...etat,
      manches: etat.manches.map((manche) => ({
        ...manche,
        defis: manche.defis.map((defi) => (defi.numero === matchNumero ? { ...defi, duel } : defi)),
      })),
    }),
  }),
}

/** Le duel d'une rencontre, lu dans la photo **de saisie** de sa phase (ou `null`). */
function duelDeLaPhase(
  queryClient: QueryClient,
  famille: FamilleDuel,
  tournoiId: number,
  phaseId: number,
  matchNumero: number,
): Duel | null {
  const photo = PHOTO[famille]
  if (photo === null) return null
  const etat = queryClient.getQueryData<unknown>(photo.cle(tournoiId, phaseId))
  if (etat === undefined) return null
  return photo.rencontres(etat).find((r) => r.numero === matchNumero)?.duel ?? null
}

/** Réécrit le duel d'une rencontre **dans la photo de la phase** — l'entrée que l'écran affiche. */
function poserDuelDansLaPhase(
  queryClient: QueryClient,
  famille: FamilleDuel,
  tournoiId: number,
  phaseId: number,
  matchNumero: number,
  duel: Duel,
): void {
  const photo = PHOTO[famille]
  if (photo === null) return
  queryClient.setQueryData<unknown>(photo.cle(tournoiId, phaseId), (etat: unknown) =>
    etat === undefined ? etat : photo.remplacer(etat, matchNumero, duel),
  )
}

// Fabrique une mutation d'acte de duel : chemin nominal (POST direct, l'accusé rafraîchit le cache),
// repli **hors-ligne** (mise en file + état optimiste), et — au succès **en ligne** — invalidation +
// supersession de la file + drainage. `optimiste` construit l'état local à afficher hors-ligne.
function useMutationActe<C extends { identifiant_saisie: string }>(
  tournoiId: number,
  phaseId: number,
  matchNumero: number,
  envoyer: (corps: C) => Promise<Duel>,
  versActe: (corps: C) => ActeDuelEnFile,
  optimiste: (base: Duel, corps: C) => Duel,
  famille: FamilleDuel = 'tableau',
) {
  const queryClient = useQueryClient()
  const mettreEnFile = useFileDuelsHorsLigneStore((state) => state.mettreEnFile)
  return useMutation<Duel, Error, C>({
    mutationFn: async (corps) => {
      const enFile = () => {
        mettreEnFile(versActe(corps))
        // La base de l'état optimiste doit être le **duel réel**, pas un gabarit vide : sinon la
        // manche saisie hors-ligne s'affiche seule, sans les précédentes. En poules, le duel ne vit
        // pas sous `cleDuel` (l'écran ne lit jamais cette entrée) mais dans la photo de la phase.
        const base =
          queryClient.getQueryData<Duel>(cleDuel(tournoiId, phaseId, matchNumero, famille)) ??
          duelDeLaPhase(queryClient, famille, tournoiId, phaseId, matchNumero) ??
          placeholderDuel(matchNumero)
        return optimiste(base, corps)
      }
      // Lien déjà tombé : on met en file sans tenter le POST (qui pendrait jusqu'à expiration).
      if (estDejaHorsLigne(useConnexionStore.getState().statut)) return enFile()
      try {
        return await envoyer(corps)
      } catch (erreur) {
        if (estRefusServeur(erreur)) throw erreur // le serveur a refusé → vraie erreur
        return enFile() // panne réseau → mise en file
      }
    },
    onSuccess: (duel, corps) => {
      queryClient.setQueryData(cleDuel(tournoiId, phaseId, matchNumero, famille), duel)
      // ⚠️ **En poules, l'écran ne lit pas `cleDuel`** — il lit la photo de la phase. Écrire le
      // seul `cleDuel` revenait à mettre à jour une entrée que personne n'affiche : hors-ligne, le
      // scoreur tapait « Enregistrer la manche », l'acte partait bien en file (aucune donnée
      // perdue) et **l'écran ne bougeait pas** — ni les manches, ni l'état « en cours », ni le
      // verrou qui masque le bouton de validation. Il retapait (relevé en revue).
      poserDuelDansLaPhase(queryClient, famille, tournoiId, phaseId, matchNumero, duel)
      const enFile = useFileDuelsHorsLigneStore
        .getState()
        .enAttente.some((a) => a.identifiant_saisie === corps.identifiant_saisie)
      // Hors-ligne (optimiste mis en file) : **ne pas invalider** — une relecture échouerait et
      // ferait retomber l'écran en erreur ; la vérité serveur reviendra au rejeu.
      if (enFile) return
      // Succès **en ligne** : le duel fait autorité. On invalide le duel et le tableau (une manche
      // change le résultat ; une validation fait **avancer** le tableau), on supersède une éventuelle
      // attente hors-ligne du **même** emplacement (une valeur neuve en ligne ne doit pas être
      // réécrasée par un vieux rejeu), et — le réseau étant revenu — on **draine** le reste.
      void queryClient.invalidateQueries({
        queryKey: cleDuel(tournoiId, phaseId, matchNumero, famille),
      })
      // Une manche change le resultat, une validation fait **avancer** la structure : on invalide
      // le decor de la famille concernee — l'arbre du tableau, ou l'etat de la phase de poules,
      // dont dependent le classement de poule et l'annonce de barrage.
      void queryClient.invalidateQueries({
        queryKey: CLE_DECOR[famille](tournoiId, phaseId),
      })
      useFileDuelsHorsLigneStore.getState().retirerSlot(cleSlot(versActe(corps)))
      void draineLaFileDuels(queryClient)
    },
  })
}

export function useSaisirManche(
  tournoiId: number,
  phaseId: number,
  matchNumero: number,
  famille: FamilleDuel = 'tableau',
) {
  return useMutationActe<SaisirManche>(
    tournoiId,
    phaseId,
    matchNumero,
    (corps) => saisirManche(corps, famille),
    (corps) => ({ type: 'manche', famille, ...corps }),
    injecterManche,
    famille,
  )
}

export function useSaisirBarrage(
  tournoiId: number,
  phaseId: number,
  matchNumero: number,
  famille: FamilleDuel = 'tableau',
) {
  return useMutationActe<SaisirBarrage>(
    tournoiId,
    phaseId,
    matchNumero,
    (corps) => saisirBarrage(corps, famille),
    (corps) => ({ type: 'barrage', famille, ...corps }),
    injecterBarrage,
    famille,
  )
}

export function useValiderDuel(
  tournoiId: number,
  phaseId: number,
  matchNumero: number,
  famille: FamilleDuel = 'tableau',
) {
  return useMutationActe<ValiderDuel>(
    tournoiId,
    phaseId,
    matchNumero,
    (corps) => validerDuel(corps, famille),
    (corps) => ({ type: 'validation', famille, ...corps }),
    // Hors-ligne, la validation **verrouille l'écran localement** (`validation_en_attente`) — comme le
    // ferait le serveur en ligne (`DuelVerrouille`). Sinon le scoreur pourrait rééditer une manche
    // APRÈS avoir validé : au rejeu FIFO la validation scellerait le résultat d'avant correction, et la
    // manche corrigée rebondirait en 422 (perte silencieuse, revue adversariale). Réconcilié au rejeu.
    (base) => ({ ...base, en_attente: true, validation_en_attente: true }),
    famille,
  )
}

// Rejoue un acte de la file en le routant vers son endpoint (le champ `type` discrimine).
function envoyerActe(acte: ActeDuelEnFile): Promise<Duel> {
  // Absente = `tableau` : la file est persistee, et une tablette qui avait des actes en attente au
  // moment du deploiement les a ecrits avant que ce champ existe.
  const famille = acte.famille ?? 'tableau'
  if (acte.type === 'manche') {
    return saisirManche(
      {
        tournoi_id: acte.tournoi_id,
        phase_id: acte.phase_id,
        match_numero: acte.match_numero,
        numero: acte.numero,
        valeurs_haut: acte.valeurs_haut,
        valeurs_bas: acte.valeurs_bas,
        identifiant_saisie: acte.identifiant_saisie,
      },
      famille,
    )
  }
  if (acte.type === 'barrage') {
    return saisirBarrage(
      {
        tournoi_id: acte.tournoi_id,
        phase_id: acte.phase_id,
        match_numero: acte.match_numero,
        fleche_haut: acte.fleche_haut,
        fleche_bas: acte.fleche_bas,
        gagnant_designe: acte.gagnant_designe,
        identifiant_saisie: acte.identifiant_saisie,
      },
      famille,
    )
  }
  return validerDuel(
    {
      tournoi_id: acte.tournoi_id,
      phase_id: acte.phase_id,
      match_numero: acte.match_numero,
      identifiant_saisie: acte.identifiant_saisie,
    },
    famille,
  )
}

// Draine la file hors-ligne des duels : rejoue les actes en attente, dans l'ordre, retire les traités
// et invalide les duels/tableaux touchés (vérité serveur). Idempotent et **ré-entrance protégée** par
// le drapeau `synchronisation`. Fonction module (pas un hook) : appelée par le hook de rejeu **et**
// par un succès de saisie en ligne.
async function draineLaFileDuels(queryClient: QueryClient): Promise<void> {
  const store = useFileDuelsHorsLigneStore.getState()
  if (store.enAttente.length === 0 || store.synchronisation) return
  store.demarrerSync()
  try {
    const estEncoreEnFile = (acte: ActeDuelEnFile) =>
      useFileDuelsHorsLigneStore
        .getState()
        .enAttente.some((a) => a.identifiant_saisie === acte.identifiant_saisie)
    const { traites, refuses } = await rejouerActes(store.enAttente, envoyerActe, estEncoreEnFile)
    const { confirmer } = useFileDuelsHorsLigneStore.getState()
    const tableaux = new Set<string>()
    for (const acte of traites) {
      confirmer(acte.identifiant_saisie)
      void queryClient.invalidateQueries({
        queryKey: cleDuel(acte.tournoi_id, acte.phase_id, acte.match_numero, acte.famille),
      })
      tableaux.add(`${acte.famille ?? 'tableau'}:${acte.tournoi_id}:${acte.phase_id}`)
    }
    for (const [, cle] of tableaux.entries()) {
      const [famille, tournoi, phase] = cle.split(':')
      const t = Number(tournoi)
      const p = Number(phase)
      // Le préfixe vient d'une **chaîne** (la clé du `Set`), donc il faut le revalider avant de
      // s'en servir comme index : une famille inconnue — un acte écrit par une version future et
      // relu depuis le `localStorage` — retombe sur le tableau, comme partout ailleurs ici.
      //
      // ⚠️ `Object.hasOwn` et **non `in`** (correctif de revue, relevé par quatre axes) : `in`
      // remonte la chaîne de prototypes, donc `'toString'`, `'constructor'` et `'valueOf'`
      // passaient la garde — et `CLE_DECOR['toString'](t, p)` rend une **chaîne** là où
      // `invalidateQueries` attend un tableau. La garde ne gardait pas ce qu'elle annonçait.
      const connue = famille !== undefined && Object.hasOwn(CLE_DECOR, famille)
      void queryClient.invalidateQueries({
        queryKey: connue ? CLE_DECOR[famille as FamilleDuel](t, p) : cleTableau(t, p),
      })
    }
    for (const acte of refuses) {
      // Refus **définitif** au rejeu (4xx métier). Perte visible (la relecture retire l'optimiste),
      // journalisée. Cas assumé, ADR-0037. Les transitoires (401/409/5xx…) ne passent pas ici.
      console.error('Acte de duel refusé définitivement au rejeu, retiré de la file', acte)
    }
  } finally {
    useFileDuelsHorsLigneStore.getState().terminerSync()
  }
}

// Rejeu de la file hors-ligne des duels. Monté sur l'écran de saisie du scoreur. Draine la file **par
// transition** — reconnexion WebSocket, ou retour du **jeton scoreur** (re-connexion après un 401) —
// jamais sur la longueur de file (boucle chaude). On ne draine pas sans jeton : les endpoints de duel
// sont scopés « scoreur » (un POST sans jeton referait un 401 inutile). (Le 3ᵉ filet — succès d'une
// saisie en ligne — vit dans `onSuccess`.)
export function useRejeuDuelsHorsLigne(): void {
  const queryClient = useQueryClient()
  const statut = useConnexionStore((state) => state.statut)
  const jeton = useSessionScoreurStore((state) => state.jeton)

  useEffect(() => {
    if (statut !== 'connecte' || jeton === null) return
    void draineLaFileDuels(queryClient)
  }, [statut, jeton, queryClient])
}

// Nombre d'actes de duel en attente d'envoi (pour l'annotation « en attente » de l'écran).
export function useDuelsEnAttente(): number {
  return useFileDuelsHorsLigneStore((state) => state.enAttente.length)
}
