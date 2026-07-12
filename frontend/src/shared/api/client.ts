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

export async function fetchJson<T>(chemin: string, options?: RequestInit): Promise<T> {
  const jeton = lireJetonAdmin()
  const enteteAuth: Record<string, string> = jeton ? { Authorization: `Bearer ${jeton}` } : {}
  const reponse = await fetch(chemin, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...enteteAuth, ...options?.headers },
  })

  if (!reponse.ok) {
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
