// Recherche transverse depuis la sidebar admin (E16US010) — **absorbe** `RechercheArcher`
// (E12US006), le 4ᵉ canal de routage (`D-09`).
//
// Deux comportements pour un champ (A02) : hors pilotage on cherche **toute entité** et on ouvre
// sa fiche en modification ; en pilotage on se concentre sur les archers du tournoi courant, avec
// leur place — ⚠️ **le « il tire là » d'E12US006 est conservé**, le perdre aurait été une
// régression livrée sous couvert de CA neuf. La correspondance est désormais **serveur**
// (`domain.recherche`) et non `filtrerArchers` : même repli casse/accents que les doublons.

import { useState } from 'react'
import type { Axe } from '../admin/axes'
import { PlaceDeLArcher } from '../placement/PlaceDeLArcher'
import type { EntiteRecherchable, ResultatRecherche } from './api'
import { useRecherche } from './hooks'

const LIBELLE_ENTITE: Record<EntiteRecherchable, string> = {
  archer: 'Archer',
  tournoi: 'Tournoi',
  club: 'Club',
}

export function RechercheTransverse({
  tournoiId,
  axe,
  onOuvrir,
}: {
  tournoiId: number | null
  axe: Axe
  onOuvrir: (resultat: ResultatRecherche) => void
}) {
  const [entite, setEntite] = useState<EntiteRecherchable>('archer')
  const [requete, setRequete] = useState('')

  // A09 : « se concentrer sur le tournoi en cours sélectionné ». Le scope ne vaut que pour les
  // archers — clubs et tournois sont des référentiels globaux, les borner les viderait sans le dire.
  const scope = axe === 'pilotage' && entite === 'archer' ? tournoiId : null
  const recherche = useRecherche(entite, requete, scope)
  const resultats = recherche.data?.resultats ?? []
  const total = recherche.data?.total ?? 0
  const requeteVide = requete.trim() === ''

  return (
    <div className="coquille__recherche recherche-archer">
      <label className="formulaire__libelle" htmlFor="recherche-entite">
        Rechercher
      </label>
      <select
        id="recherche-entite"
        className="formulaire__champ"
        value={entite}
        onChange={(e) => setEntite(e.target.value as EntiteRecherchable)}
      >
        {(Object.keys(LIBELLE_ENTITE) as EntiteRecherchable[]).map((cle) => (
          <option key={cle} value={cle}>
            {LIBELLE_ENTITE[cle]}
          </option>
        ))}
      </select>
      {/* Le nom accessible vient du <label> associé (htmlFor) — pas d'aria-label, qui l'écraserait
          en doublon. */}
      <label className="formulaire__libelle" htmlFor="recherche-fragment">
        {LIBELLE_ENTITE[entite]} à trouver
      </label>
      <input
        id="recherche-fragment"
        className="formulaire__champ"
        value={requete}
        onChange={(e) => setRequete(e.target.value)}
        placeholder="Nom, sans accents si besoin…"
        autoComplete="off"
      />

      {!requeteVide &&
        // Ordre : erreur → résultats → chargement → « aucun » en dernier. On ne présente jamais un
        // chargement comme un fait négatif (leçon de revue de `VueSuivi`, conservée d'E12US006).
        (recherche.isError ? (
          <p className="carte__etat carte__etat--erreur">Recherche momentanément indisponible.</p>
        ) : resultats.length > 0 ? (
          <>
            <ul className="recherche-resultats">
              {resultats.map((r) => (
                <li key={`${r.entite}-${r.id}`} className="recherche-resultat">
                  <button
                    type="button"
                    className="recherche-resultat__ouvrir"
                    onClick={() => onOuvrir(r)}
                  >
                    <span className="recherche-resultat__nom">{r.libelle}</span>
                    {r.precision !== null && (
                      <span className="recherche-resultat__precision">{r.precision}</span>
                    )}
                  </button>
                  {scope !== null && <PlaceDeLArcher archerId={r.id} tournoiId={scope} />}
                </li>
              ))}
            </ul>
            {/* Chiffré, jamais « trop de résultats » : `D-16` — une alerte qui ne chiffre pas son
                impact est un clic de plus, pas une protection. */}
            {total > resultats.length && (
              <p className="carte__etat">
                {resultats.length} sur {total} — précisez pour voir les autres.
              </p>
            )}
          </>
        ) : recherche.isSuccess ? (
          <p className="carte__etat">Aucun résultat à ce nom.</p>
        ) : (
          <p className="carte__etat">Chargement…</p>
        ))}
    </div>
  )
}
