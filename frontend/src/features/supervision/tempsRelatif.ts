// « il y a N mn » — temps écoulé depuis la dernière activité d'un poste (E12US001).
//
// Fonction **pure** (testée en node) : le « maintenant » est **fourni** par l'appelant, jamais lu ici
// — comme le port `Horloge` côté serveur, c'est ce qui la rend déterministe en test. Maison plutôt
// qu'`Intl.RelativeTimeFormat` : le vocabulaire voulu (« à l'instant », « il y a 14 mn », « il y a
// 2 h ») est plus simple à figer et à tester que la sortie localisée du navigateur.
//
// L'instant arrive en ISO **UTC** (le serveur sérialise ses `datetime` aware) ; `Date` compare des
// epochs, le fuseau du navigateur n'entre pas en jeu.

export function tempsRelatif(instantIso: string, maintenant: Date): string {
  const secondes = Math.floor((maintenant.getTime() - new Date(instantIso).getTime()) / 1000)
  if (secondes < 60) return "à l'instant" // couvre aussi un léger décalage d'horloge (secondes < 0)
  const minutes = Math.floor(secondes / 60)
  if (minutes < 60) return `il y a ${minutes} mn`
  const heures = Math.floor(minutes / 60)
  if (heures < 24) return `il y a ${heures} h`
  return `il y a ${Math.floor(heures / 24)} j`
}
