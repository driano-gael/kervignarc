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

export async function fetchJson<T>(chemin: string, options?: RequestInit): Promise<T> {
  const reponse = await fetch(chemin, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
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

  return (await reponse.json()) as T
}
