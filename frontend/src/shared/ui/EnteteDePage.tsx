// L'en-tête d'une **page projetée** : le compteur et le râteau, en grand (P06, 04/08/2026).
//
// ⚠️ **Extrait de `VueAffectations` par E16US009**, quand le classement projeté s'est mis à paginer
// lui aussi. Le recopier aurait été la 2ᵉ occurrence d'un composant jumeau — exactement le
// mécanisme que `DETTE-085` décrit et qui, dans l'US précédente, a produit un écran calculant des
// repères qu'il ne rendait jamais. Deux consommateurs réels, donc `shared/`, comme le module de
// pagination qui l'accompagne.
//
// Le préfixe de classes `salle-pages__` est **historique et reste juste** : les deux consommateurs
// sont bien des pages de salle. Le renommer n'aurait déplacé aucun problème.

/** Les deux seules informations qui servent à quelqu'un debout au fond de la salle : « est-ce que
 * mon nom est sur cette page, et sinon combien de temps j'attends ».
 *
 * P06 : *« grossir le compteur de page, il faut qu'il soit visible, de même que les lettres
 * comprises dans le râteau de nom »* — d'où leur dimensionnement au-dessus du corps de la liste. */
export function EnteteDePage({
  numero,
  total,
  titre,
  rateau,
}: {
  numero: number
  total: number
  titre: string
  rateau: { debut: string; fin: string } | null
}) {
  return (
    <header className="salle-pages__entete">
      <span className="salle-pages__titre">{titre}</span>
      {rateau !== null && (
        <span className="salle-pages__rateau">
          {rateau.debut} <span aria-hidden="true">→</span> {rateau.fin}
        </span>
      )}
      {total > 1 && (
        <span className="salle-pages__compteur">
          {numero}
          <span className="salle-pages__compteur-total">/{total}</span>
        </span>
      )}
    </header>
  )
}
