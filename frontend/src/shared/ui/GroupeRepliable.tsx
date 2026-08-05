// Bandeau repliable qui **remonte son alerte même refermé** — retour maquettes du 04/08/2026 (A12).
//
// *« Chaque type d'écran est sous un bandeau repliable de type ; si besoin d'info (erreur,
// déconnexion, …), le bandeau affiche une icône d'erreur ; quand on déplie, on peut voir les postes
// en erreur avec plus de détail. »*
//
// **Ce qui rend ce composant utile, c'est la deuxième moitié de la phrase.** Un simple `<details>`
// cache ce qu'il replie, ce qui est exactement ce qu'il ne faut pas d'un écran de supervision : un
// bandeau fermé sur trois tablettes mortes ne se distinguerait pas d'un bandeau fermé sur un parc
// intact. Le bandeau porte donc **le nombre d'anomalies** en permanence, replié ou non, et ne
// s'ouvre que pour en montrer le détail.
//
// L'état d'ouverture initial suit la même logique : **ouvert s'il y a un problème**, replié sinon.
// C'est la transposition, au niveau du groupe, de ce que A13 demande au niveau de l'écran — *« seuls
// les problèmes sautent aux yeux »*. Et il n'est **jamais re-synchronisé** ensuite : une anomalie
// qui apparaît pendant qu'on travaille ne rouvre pas un bandeau qu'on vient de fermer sous les
// doigts. Elle se signale sur le bandeau, ce qui suffit à la retrouver.

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
