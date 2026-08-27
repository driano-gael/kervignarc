// Bandeau repliable qui **remonte son alerte même refermé** — retour maquettes du 04/08/2026 (A12).
//
// ⚠️ **Ce qui rend ce composant utile, c'est cette dernière clause.** Un simple `<details>` cache
// ce qu'il replie : un bandeau fermé sur trois tablettes mortes ne se distinguerait pas d'un
// bandeau fermé sur un parc intact. Il porte donc **le nombre d'anomalies** en permanence. L'état
// initial suit la même logique — **ouvert s'il y a un problème** — et n'est **jamais
// re-synchronisé** : une anomalie qui apparaît pendant qu'on travaille ne rouvre pas un bandeau
// qu'on vient de fermer sous les doigts.

import { useState, type ReactNode } from 'react'

export function GroupeRepliable({
  titre,
  resume,
  nbAnomalies,
  libelleAnomalies,
  enfants,
}: {
  titre: string
  /** Le décompte normal du groupe (« 28/30 en ligne ») — l'information qu'on lit sans déplier. */
  resume?: ReactNode
  /** Combien d'éléments posent problème. `0` = rien à signaler. */
  nbAnomalies: number
  /** Comment nommer ces anomalies au singulier/pluriel — « hors ligne », « en erreur ». */
  libelleAnomalies: string
  enfants: ReactNode
}) {
  const [ouvert, setOuvert] = useState(nbAnomalies > 0)

  return (
    <section className={nbAnomalies > 0 ? 'groupe groupe--alerte' : 'groupe'}>
      <button
        type="button"
        className="groupe__bandeau"
        aria-expanded={ouvert}
        onClick={() => setOuvert((o) => !o)}
      >
        <span className="groupe__chevron" aria-hidden="true">
          {ouvert ? '▾' : '▸'}
        </span>
        <span className="groupe__titre">{titre}</span>
        {resume !== undefined && <span className="groupe__resume">{resume}</span>}
        {/* `DV-03` : glyphe **et** mot **et** chiffre — jamais la couleur seule. C'est ce qui fait
            que le bandeau replié reste informatif. */}
        {nbAnomalies > 0 && (
          <span className="groupe__alerte">
            <span aria-hidden="true">▲</span> {nbAnomalies} {libelleAnomalies}
          </span>
        )}
      </button>
      {ouvert && <div className="groupe__contenu">{enfants}</div>}
    </section>
  )
}
