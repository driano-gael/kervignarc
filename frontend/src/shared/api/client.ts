// Client HTTP minimal du backend (E00US010).
//
// URLs **relatives** : en dev, le proxy Vite les route vers le backend ; en production,
// FastAPI sert le build front au même origin (E00US012). Les erreurs suivent le format
// normalisé de la frontière API `{ code, message, details? }` (ADR-0007).

export interface CorpsErreur {
  code: string
  message: string
  details?: unknown
}

export class ErreurApi extends Error {
  readonly statut: number
  readonly code: string
  readonly details?: unknown

  constructor(statut: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'ErreurApi'
    this.statut = statut
    this.code = code
    this.details = details
  }
}

// Jeton d'accès administrateur (E10US002) : joint automatiquement en `Authorization: Bearer`
// quand une session admin est ouverte. Le store de session s'enregistre ici (inversion de
// dépendance : le client ne connaît pas le store). Sans session, les requêtes restent anonymes
// (la lecture publique n'exige rien) ; le serveur ignore l'en-tête sur les routes non protégées.
let lireJetonAdmin: () => string | null = () => null

export function enregistrerJetonAdmin(fournisseur: () => string | null): void {
  lireJetonAdmin = fournisseur
}

// Réaction centralisée à un 401 (session absente/expirée) : le store de session s'y branche
// pour se purger, ce qui ramène l'UI à l'écran de connexion. Évite de recâbler ce cas sur
// chaque mutation admin (E10US001 : plusieurs écritures protégées).
let surNonAutorise: () => void = () => {}

export function enregistrerSurNonAutorise(rappel: () => void): void {
  surNonAutorise = rappel
}

// Jeton de session scoreur (E10US003) : joint en en-tête **dédié** `X-Jeton-Scoreur`, distinct du
// Bearer admin — les deux modes d'identité sont **orthogonaux** (D-13). Un scoreur (sur son
// téléphone) et l'admin (sur le PC) peuvent donc coexister sans que l'un masque l'autre. Même
// inversion de dépendance : le store de session scoreur s'enregistre ici.
let lireJetonScoreur: () => string | null = () => null

export function enregistrerJetonScoreur(fournisseur: () => string | null): void {
  lireJetonScoreur = fournisseur
}

let surNonAutoriseScoreur: () => void = () => {}

export function enregistrerSurNonAutoriseScoreur(rappel: () => void): void {
  surNonAutoriseScoreur = rappel
}

// Jeton de session de poste (E04US001) : joint en en-tête **dédié** `X-Jeton-Poste`, distinct du
// Bearer admin et du `X-Jeton-Scoreur` — les trois modes d'identité sont **orthogonaux** (D-13). Une
// tablette-poste, un scoreur et l'admin peuvent coexister sans qu'un 401 sur l'un purge un autre.
let lireJetonPoste: () => string | null = () => null

export function enregistrerJetonPoste(fournisseur: () => string | null): void {
  lireJetonPoste = fournisseur
}

let surNonAutorisePoste: () => void = () => {}

export function enregistrerSurNonAutorisePoste(rappel: () => void): void {
  surNonAutorisePoste = rappel
}

// Portée d'identité d'une requête : **une seule** à la fois. C'est ce qui empêche qu'un 401 sur un
// mode purge la session d'un **autre** — le piège quand admin, scoreur et poste cohabitent dans le
// même navigateur. `'aucune'` = appel d'authentification (login / rattachement) : aucun jeton joint,
// et un refus n'expire aucune session existante.
export type PorteeAuth = 'admin' | 'scoreur' | 'poste' | 'aucune'

export async function fetchJson<T>(
  chemin: string,
  options?: RequestInit,
  portee: PorteeAuth = 'admin',
): Promise<T> {
  // Seul le jeton du mode demandé est joint (les autres restent `null`) : une requête n'engage
  // qu'une identité, donc un 401 ne peut invalider que celle-là.
  const jetonAdmin = portee === 'admin' ? lireJetonAdmin() : null
  const jetonScoreur = portee === 'scoreur' ? lireJetonScoreur() : null
  const jetonPoste = portee === 'poste' ? lireJetonPoste() : null
  const entetes: Record<string, string> = { 'Content-Type': 'application/json' }
  if (jetonAdmin) entetes.Authorization = `Bearer ${jetonAdmin}`
  if (jetonScoreur) entetes['X-Jeton-Scoreur'] = jetonScoreur
  if (jetonPoste) entetes['X-Jeton-Poste'] = jetonPoste
  const reponse = await fetch(chemin, {
    ...options,
    headers: { ...entetes, ...options?.headers },
  })

  if (!reponse.ok) {
    // 401 alors que le jeton de la portée était joint → session expirée/invalide (serveur
    // redémarré, ou scoreur supprimé côté admin) : on purge **cette seule** session. Un login
    // (`portee: 'aucune'`) ne joint aucun jeton, donc un refus n'expire rien — on n'y touche pas.
    if (reponse.status === 401) {
      if (jetonAdmin) surNonAutorise()
      if (jetonScoreur) surNonAutoriseScoreur()
      if (jetonPoste) surNonAutorisePoste()
    }
    const corps = (await reponse.json().catch(() => null)) as CorpsErreur | null
    throw new ErreurApi(
      reponse.status,
      corps?.code ?? 'erreur_inconnue',
      corps?.message ?? reponse.statusText,
      corps?.details,
    )
  }

  // 204 No Content (ex. déconnexion) : pas de corps à décoder.
  if (reponse.status === 204) return undefined as T

  return (await reponse.json()) as T
}
