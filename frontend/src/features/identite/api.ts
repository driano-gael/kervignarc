// Accès API de la feature « identité visuelle du tournoi » (E16US006, absorbe E01US016). Miroir des
// DTO exposés par `api/v1/identite.py`.
//
// ⚠️ **Ce module ne calcule aucune couleur, et c'est le point le plus important de la feature.** La
// dérivation (`DV-05`) vit dans `backend/domain/identite.py`, pure et éprouvée. La recopier ici
// produirait une **seconde vérité** au mode de panne silencieux : un contraste faux ne lève aucune
// erreur, il rend juste un texte illisible dans un gymnase. Le front reçoit des valeurs **prêtes à
// poser**.

import { fetchJson } from '../../shared/api/client'

/** Les deux marques d'un tournoi : l'édition, et le club qui l'organise (questionnaire A05). */
export type EmplacementLogo = 'evenement' | 'club'

/** Les quatre jetons de marque d'un accent sur un thème — noms miroir de `index.css`. */
export interface JetonsDeMarque {
  /** `--brand-surface` : l'aplat, couleur **exacte** de l'organisateur. */
  surface: string
  /** `--brand-border` : la variante qui tient 3:1 (WCAG 1.4.11). */
  contour: string
  /** `--brand-text` : la variante qui tient 4,5:1 (WCAG 1.4.3). */
  texte: string
  /** `--sur-brand` : ce qui s'écrit sur l'aplat, noir ou blanc. */
  encre: string
}

/** Un accent : la couleur choisie, ses deux déclinaisons, et ses contrastes **mesurés**. */
export interface AccentDecline {
  couleur: string
  sombre: JetonsDeMarque
  clair: JetonsDeMarque
  /** Ratio de la couleur **brute** sur le fond sombre — le chiffre de `P-4`. */
  contraste_sur_sombre: number
  /** Idem sur le fond clair. Les deux thèmes sont annoncés : un accent peut tenir sur l'un seul. */
  contraste_sur_clair: number
}

export interface Identite {
  /** `false` : rien n'a été choisi, les accents rendus sont **hérités** de ceux du club. */
  reglee: boolean
  primaire: AccentDecline
  secondaire: AccentDecline
  /** Les emplacements **pourvus**, triés, avec l'empreinte de leur contenu — jamais les octets. */
  logos: LogoPresent[]
  /** Seuils WCAG servis par le serveur, pour que le front n'en tienne pas sa propre copie. */
  seuil_contour: number
  seuil_texte: number
  /** La limite de poids d'un logo, servie par le serveur — même argument que les deux seuils. */
  poids_logo_max_octets: number
}

export interface LogoPresent {
  emplacement: EmplacementLogo
  /**
   * L'empreinte du **contenu** — le numéro de version que `urlDuLogo` pose dans l'URL.
   *
   * ⚠️ Sans elle, une URL stable ne provoque **aucune** requête sur une image déjà montée : React
   * ne réécrit pas un attribut inchangé, et `Cache-Control: no-cache` ne s'applique à rien — un
   * organisateur qui corrigeait son logo ne le voyait jamais. Versionner par l'horloge faisait
   * l'inverse : 512 Ko retéléchargés à chaque événement WebSocket.
   */
  empreinte: string
}

/** L'empreinte d'un emplacement pourvu, ou `undefined` s'il est vide. */
export function empreinteDuLogo(
  identite: Identite,
  emplacement: EmplacementLogo,
): string | undefined {
  return identite.logos.find((logo) => logo.emplacement === emplacement)?.empreinte
}

export interface AccentsAEnregistrer {
  primaire: string
  secondaire: string
}

/** Lecture **publique** : ni l'écran de salle ni le téléphone d'un spectateur n'ont de session. */
export function getIdentite(tournoiId: number): Promise<Identite> {
  return fetchJson<Identite>(`/api/v1/tournois/${tournoiId}/identite`, undefined, 'aucune')
}

export function enregistrerAccents(
  tournoiId: number,
  accents: AccentsAEnregistrer,
): Promise<Identite> {
  return fetchJson<Identite>(`/api/v1/tournois/${tournoiId}/identite`, {
    method: 'PUT',
    body: JSON.stringify(accents),
  })
}

/**
 * Décline deux couleurs **sans rien enregistrer** — le contrôle « à la saisie ».
 *
 * C'est ce qui permet de montrer le rendu et le chiffre de contraste pendant que l'organisateur
 * choisit, sans que le navigateur ait à refaire le calcul (cf. l'avertissement en tête de module).
 */
export function apercuIdentite(accents: AccentsAEnregistrer): Promise<Identite> {
  const parametres = new URLSearchParams({
    primaire: accents.primaire,
    secondaire: accents.secondaire,
  })
  return fetchJson<Identite>(`/api/v1/identite/apercu?${parametres}`)
}

/**
 * Dépose un logo : **le corps est le fichier**, son format est dans `Content-Type`.
 *
 * Pas de `FormData` — l'API ne lit pas le `multipart/form-data`, qui aurait demandé une dépendance
 * serveur nouvelle (`python-multipart`, règle 11) pour téléverser un fichier sans aucun champ à
 * côté. `fetchJson` accepte l'écrasement de son en-tête par `options.headers`.
 */
export function deposerLogo(
  tournoiId: number,
  emplacement: EmplacementLogo,
  fichier: File,
): Promise<Identite> {
  return fetchJson<Identite>(`/api/v1/tournois/${tournoiId}/identite/logos/${emplacement}`, {
    method: 'PUT',
    body: fichier,
    headers: { 'Content-Type': fichier.type },
  })
}

export function retirerLogo(tournoiId: number, emplacement: EmplacementLogo): Promise<Identite> {
  return fetchJson<Identite>(`/api/v1/tournois/${tournoiId}/identite/logos/${emplacement}`, {
    method: 'DELETE',
  })
}

/** L'adresse des octets d'un logo — à poser dans un `src`, jamais à télécharger soi-même.
 *
 * **Versionnée par le CONTENU, et il a fallu deux rédactions.** `?v=${dataUpdatedAt}` changeait à
 * chaque refetch, donc à chaque événement WebSocket : *cache miss* permanent, jusqu'à 2 × 512 Ko
 * par appareil. Retirer le paramètre faisait l'inverse — avec une URL stable, React ne réécrit pas
 * le `src` d'une image montée, donc remplacer un logo ne changeait plus rien à l'écran (mesuré en
 * revue). L'empreinte ne bouge **que** quand les octets bougent, et c'est la valeur de l'`ETag`.
 */
export function urlDuLogo(
  tournoiId: number,
  emplacement: EmplacementLogo,
  empreinte: string,
): string {
  // `encodeURIComponent` par principe, pas par nécessité : l'empreinte est aujourd'hui produite
  // par le serveur (32 caractères hexadécimaux). C'est la seule des trois colonnes du triplet qui
  // finisse dans une URL, et le module d'adapter enveloppe déjà les deux autres à la relecture —
  // on ne fait pas confiance à la base sur les deux tiers d'un invariant seulement.
  return `/api/v1/tournois/${tournoiId}/identite/logos/${emplacement}?v=${encodeURIComponent(empreinte)}`
}
