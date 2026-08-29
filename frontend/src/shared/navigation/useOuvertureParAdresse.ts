// L'ouverture d'une ligne de liste : pilotée par **l'adresse** quand quelqu'un la pilote
// (E16US010, ADR-0100), locale sinon.
//
// ⚠️ **Une seule source, jamais deux.** Un état local *synchronisé* sur l'adresse par un effet
// diverge dès qu'on referme la fiche : l'adresse continue de la désigner, et le même lien cesse
// de la rouvrir. Ici l'ouverture **est** l'adresse — un F5 et un lien copié rendent la même vue.
// Le repli local garde les points de montage qui ne routent pas (tests, écrans autonomes).

import { useState } from 'react'

export function useOuvertureParAdresse(
  id: number,
  ouvrir: number | null,
  onOuvrir?: (id: number | null) => void,
): [boolean, (ouverte: boolean) => void] {
  const [locale, setLocale] = useState(false)
  if (onOuvrir === undefined) return [locale, setLocale]
  return [id === ouvrir, (ouverte: boolean) => onOuvrir(ouverte ? id : null)]
}
