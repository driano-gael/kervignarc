// Accès HTTP de la **surface scoreur** de la qualification (E16US019) — valider, annuler.
//
// Le backend expose ces routes depuis E04US002 ; aucun écran ne les appelait (`EspaceScoreur`
// renvoyait à « une surface distincte, §7.3 »). Cette feature est cette surface. Portée `'scoreur'`
// **explicite** partout, comme dans `forfaits/api.ts` : l'identité émise ne doit jamais dépendre
// d'un défaut. ⚠️ La lecture partage l'URL de `saisie/api.ts` mais **pas** sa portée — celle-là
// émet le jeton de poste, qu'un scoreur n'a pas.

import { fetchJson } from '../../shared/api/client'
import type { Serie } from '../saisie/api'

// `departId` : le créneau choisi à l'écran (E04US019). `null` = le serveur le devine (`DETTE-052`).
export function getSerieScoreur(
  tournoiId: number,
  archerId: number,
  departId: number | null,
): Promise<Serie> {
  const creneau = departId === null ? '' : `?depart_id=${departId}`
  return fetchJson<Serie>(
    `/api/v1/saisie/series/${tournoiId}/${archerId}${creneau}`,
    undefined,
    'scoreur',
  )
}

// Une ligne de la file du scoreur (E04US019). L'attente est calculée **par le serveur**.
export interface ArcherEnAttente {
  archer_id: number
  nom: string
  prenom: string
  position: string
  attente_secondes: number
}

export interface CibleEnAttente {
  cible_index: number
  attente_secondes: number
  archers: ArcherEnAttente[]
}

export function getFileScoreur(tournoiId: number, departId: number): Promise<CibleEnAttente[]> {
  return fetchJson<CibleEnAttente[]>(
    `/api/v1/saisie/file/${tournoiId}/${departId}`,
    undefined,
    'scoreur',
  )
}

export function validerSerie(
  tournoiId: number,
  archerId: number,
  departId: number | null,
  identifiantSaisie: string,
): Promise<Serie> {
  return fetchJson<Serie>(
    '/api/v1/saisie/validations',
    {
      method: 'POST',
      body: JSON.stringify({
        tournoi_id: tournoiId,
        archer_id: archerId,
        depart_id: departId,
        identifiant_saisie: identifiantSaisie,
      }),
    },
    'scoreur',
  )
}

// Referme le lot rouvert qui contient `numero`. ⚠️ Route **distincte** de `validerSerie` : le lot
// doit être **nommé**, le serveur refusant de deviner lequel le scoreur vient de relire (E16US019).
export function refermerCorrection(
  tournoiId: number,
  archerId: number,
  numero: number,
  departId: number | null,
  identifiantSaisie: string,
): Promise<Serie> {
  return fetchJson<Serie>(
    '/api/v1/saisie/refermetures',
    {
      method: 'POST',
      body: JSON.stringify({
        tournoi_id: tournoiId,
        archer_id: archerId,
        numero,
        depart_id: departId,
        identifiant_saisie: identifiantSaisie,
      }),
    },
    'scoreur',
  )
}

// `numero` désigne **une** volée ; c'est tout son lot de validation que le serveur rouvre.
export function annulerValidation(
  tournoiId: number,
  archerId: number,
  numero: number,
  departId: number | null,
  identifiantSaisie: string,
): Promise<Serie> {
  return fetchJson<Serie>(
    '/api/v1/saisie/annulations',
    {
      method: 'POST',
      body: JSON.stringify({
        tournoi_id: tournoiId,
        archer_id: archerId,
        numero,
        depart_id: departId,
        identifiant_saisie: identifiantSaisie,
      }),
    },
    'scoreur',
  )
}
