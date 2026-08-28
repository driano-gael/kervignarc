/** L'annonce publique d'une pause — **le même composant sur les deux surfaces** (CA E05US034).
 *
 * ⚠️ **Partagé, et c'est la raison d'être du fichier** : deux rendus séparés auraient divergé au
 * premier ajustement de formulation, sans que rien ne le signale. ⚠️ **`portee` existe parce que
 * partager le composant ne suffisait pas** : l'écran de salle s'adresse au **gymnase entier**, et
 * la portée par défaut d'un arrêt est la phase — une annonce non qualifiée y ferait arrêter des
 * archers non concernés. **Sans promesse d'horaire** : l'arrêt se lève d'un geste. `role="status"`.
 */
export function BandeauDePause({ suspendu }: { suspendu?: readonly string[] }) {
  const nomme = suspendu !== undefined && suspendu.length > 0
  return (
    <p className="bandeau-pause" role="status">
      <strong>Pause</strong> —{' '}
      {nomme
        ? `le tir est suspendu par l’organisation pour : ${suspendu.join(', ')}.`
        : 'le tir est suspendu par l’organisation.'}{' '}
      La reprise sera annoncée en salle&nbsp;; il n’y a rien à faire en attendant.
    </p>
  )
}
