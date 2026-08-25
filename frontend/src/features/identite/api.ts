// Accès API de la feature « identité visuelle du tournoi » (E16US006, absorbe E01US016).
// Miroir des DTO exposés par `api/v1/identite.py`.
//
// ⚠️ **Ce module ne calcule aucune couleur, et c'est le point le plus important de la feature.**
// La dérivation « teinte et saturation conservées, clarté ajustée jusqu'au seuil AA » (`DV-05`) vit
// dans `backend/domain/identite.py`, où elle est pure, typée strictement et éprouvée contre la
// déclinaison que la charte avait calculée à la main. La recopier ici produirait une **seconde
// vérité** dont le mode de panne est silencieux : un contraste faux ne lève aucune erreur, il rend
// juste un texte illisible dans un gymnase. Le front reçoit donc des valeurs **prêtes à poser**.

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
  /** Les emplacements **pourvus**, triés — jamais les octets. */
  logos: EmplacementLogo[]
  /** Seuils WCAG servis par le serveur, pour que le front n'en tienne pas sa propre copie. */
  seuil_contour: number
  seuil_texte: number
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

/**
 * L'adresse des octets d'un logo — à poser dans un `src`, jamais à télécharger soi-même.
 *
 * `v` porte la **version** : le navigateur cache l'image par URL, et sans ce paramètre un
 * organisateur qui corrige son fichier continuerait de voir l'ancien jusqu'à vider son cache. La
 * valeur vient du nombre d'enregistrements de la requête React Query — elle change à chaque
 * réponse fraîche, ce qui suffit ; l'`ETag` du serveur fait le reste (une revalidation à 304, pas
 * un rechargement complet).
 */
export function urlDuLogo(
  tournoiId: number,
  emplacement: EmplacementLogo,
  version: number,
): string {
  return `/api/v1/tournois/${tournoiId}/identite/logos/${emplacement}?v=${version}`
}
