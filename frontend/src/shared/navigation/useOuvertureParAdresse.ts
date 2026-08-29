// L'ouverture d'une ligne de liste : pilotée par **l'adresse** (E16US010, ADR-0100).
//
// ⚠️ **Une seule source, jamais deux.** Un état local *synchronisé* sur l'adresse par un effet
// diverge dès qu'on referme la fiche : l'adresse continue de la désigner, et le même lien cesse
// de la rouvrir. Ici l'ouverture **est** l'adresse — un F5 et un lien copié rendent la même vue.
// ⚠️ Le repli en état local a été **retiré en revue** : il n'était plus atteint que par les tests,
// et il laissait un montage qui oublie `onOuvrir` diverger en silence au lieu de ne pas compiler.

export function useOuvertureParAdresse(
  id: number,
  ouvrir: number | null,
  onOuvrir: (id: number | null) => void,
): [boolean, (ouverte: boolean) => void] {
  return [id === ouvrir, (ouverte: boolean) => onOuvrir(ouverte ? id : null)]
}
