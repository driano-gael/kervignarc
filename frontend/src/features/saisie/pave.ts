// Ce que le pavé de l'archer actif permet et affiche (E04US002) — logique **pure** (E00US024).

import { ErreurApi } from '../../shared/api/client'
import type { Bareme, Volee } from './api'
import { tamponDeVolee, type Brouillons } from './brouillons'
import type { Ouverture } from './poste'
import { heureSaisie, voleeExistante, voleeOuverte } from './volees'

export interface EtatPave {
  numeroActif: number
  // La flèche que la prochaine frappe remplace, `null` = à la suite.
  fleche: number | null
  existante: Volee | null
  verrouillee: boolean
  buffer: string[]
  // Une frappe est-elle acceptée, indépendamment de l'envoi en cours.
  frappable: boolean
  zonesActives: boolean
  effacable: boolean
  enregistrable: boolean
}

export function etatPave(pave: {
  archerId: number
  volees: readonly Volee[]
  bareme: Pick<Bareme, 'nb_volees' | 'nb_fleches_par_volee'>
  brouillons: Brouillons
  ouverture: Pick<Ouverture, 'numero' | 'fleche'> | null
  serieChargee: boolean
  envoiEnCours: boolean
}): EtatPave {
  const { archerId, volees, bareme, brouillons, ouverture, serieChargee, envoiEnCours } = pave
  // Volée visée : le choix explicite (navigateur, case de ligne), sinon la prochaine non saisie.
  const numeroActif = voleeOuverte(ouverture?.numero ?? null, volees, bareme.nb_volees)
  const fleche = ouverture?.fleche ?? null
  const existante = voleeExistante(volees, numeroActif)
  const verrouillee = existante?.verrouillee ?? false
  const buffer = tamponDeVolee(brouillons, archerId, numeroActif, volees)
  const complet = buffer.length >= bareme.nb_fleches_par_volee
  // Une volée pleine reste frappable **sur la flèche visée** : c'est la correction avant envoi.
  const bloque = complet && fleche === null
  // ⚠️ Série pas chargée : `volees` est vide et `numeroActif` pointerait la volée 1 par défaut — on
  // ne frappe pas « à l'aveugle » pour voir le tampon se réinitialiser à l'arrivée des données.
  return {
    numeroActif,
    fleche,
    existante,
    verrouillee,
    buffer,
    frappable: serieChargee && !verrouillee,
    zonesActives: serieChargee && !bloque && !verrouillee && !envoiEnCours,
    effacable: buffer.length > 0 && !verrouillee && !envoiEnCours,
    enregistrable: serieChargee && complet && !verrouillee && !envoiEnCours,
  }
}

// La suite de « Saisie par NOM » : l'heure, le validateur — omis tant que la volée est rendue en
// correction — et l'attente d'envoi hors ligne.
// DETTE-124 : un horodatage illisible laisse « à » seul — défaut hérité, figé par son test.
export function complementMeta(existante: Volee): string {
  const heure = existante.saisie_le !== null ? ` à ${heureSaisie(existante.saisie_le)}` : ''
  const validee =
    existante.validee_par !== null && existante.en_correction !== true
      ? ` · validée par ${existante.validee_par}`
      : ''
  const attente = existante.en_attente === true ? ' · en attente d’envoi' : ''
  return `${heure}${validee}${attente}`
}

// Un `409 ecriture_de_role_inferieur` (E16US020) : un **arbitrage** de préséance, pas un incident.
export function estRefusDePreseance(erreur: unknown): erreur is ErreurApi {
  return erreur instanceof ErreurApi && erreur.code === 'ecriture_de_role_inferieur'
}

// Pastille du navigateur de volées : saisie = pleine, verrouillée = cadenassée, visée = surlignée.
export function classesPastille(
  numero: number,
  volee: { verrouillee: boolean } | undefined,
  numeroActif: number,
): string {
  return [
    'saisie__nav-volee',
    volee !== undefined ? 'saisie__nav-volee--saisie' : '',
    volee?.verrouillee ? 'saisie__nav-volee--verrou' : '',
    numero === numeroActif ? 'saisie__nav-volee--actif' : '',
  ]
    .filter((c) => c !== '')
    .join(' ')
}
