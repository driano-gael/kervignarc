// Carte d'état du backend (E00US010) : prouve que le fetch/cache React Query fonctionne.

import { useEtatBackend } from './useEtatBackend'

export function EtatBackend() {
  const { data, isPending, isError, error } = useEtatBackend()

  return (
    <section className="carte">
      <h2 className="carte__titre">Backend</h2>
      {isPending && <p className="carte__etat">Interrogation…</p>}
      {isError && <p className="carte__etat carte__etat--erreur">Injoignable — {error.message}</p>}
      {data && <p className="carte__etat carte__etat--ok">Opérationnel ({data.status})</p>}
    </section>
  )
}
