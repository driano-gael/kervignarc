/** L'annonce publique d'une pause — **le même composant sur les deux surfaces** (CA E05US034).
 *
 * ⚠️ **Partagé, et c'est la raison d'être du fichier.** Le CA dit « la pause se voit du public
 * **et** de l'écran de salle » : deux rendus séparés auraient divergé au premier ajustement de
 * formulation, et rien ne l'aurait signalé — les deux surfaces ne sont jamais regardées en même
 * temps par la même personne. Une seule phrase, un seul style, deux points de montage.
 *
 * ⚠️ **`portee` existe parce que partager le composant ne suffisait pas** (correctif de bloquant de
 * 2ᵉ passe, axe B). L'onglet public affiche le bandeau **sous le titre d'une phase précise** : le
 * contexte est donné par la page, « le tir est suspendu » ne peut pas s'y méprendre. L'écran de
 * salle, lui, s'adresse au **gymnase entier**, et la portée par défaut d'un arrêt est
 * `PorteeArret.PHASE` — rien n'interdit qu'une phase soit en pause pendant qu'une autre tire. Une
 * annonce non qualifiée y aurait fait arrêter des archers qui n'étaient pas concernés : un défaut
 * plus grave que celui qu'on venait de corriger, et le seul mode de panne que la surface collective
 * puisse produire.
 *
 * D'où deux formes, et **elles se choisissent sur un fait, pas sur la surface** : si tout ce qui
 * tournait est arrêté, la phrase est générale ; sinon elle **nomme** ce qui est suspendu.
 *
 * **Sobre, et sans promesse d'horaire** : le serveur n'a aucune heure de reprise à tenir — l'arrêt
 * se lève d'un geste d'organisateur, quand il le décide. Annoncer « reprise à 14 h 30 » serait une
 * promesse que rien ne fait respecter, donc la façon la plus sûre de transformer une pause
 * maîtrisée en incident.
 *
 * `role="status"` : l'annonce est lue par les technologies d'assistance à son apparition, sans
 * voler le focus (`DV-03` — l'information ne passe pas que par la couleur, la phrase la porte).
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
