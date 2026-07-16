// Formatage partagé de l'**argent** — le tarif d'un départ (E02US004, ADR-0017), consommé par la
// feature « departs ».
//
// Règle du projet (**ADR-0012**) : l'argent circule et se stocke en **centimes entiers**, jamais en
// flottants. Les euros n'existent qu'ici, à la frontière de l'écran : ce module est le **seul**
// endroit où l'on convertit, dans un sens comme dans l'autre.
//
// Couvert par `format.test.ts` (E00US014, vitest) : l'aller-retour et le sens de complétion des
// décimales (`padEnd` vs `padStart`) sont testés — une régression qui fausserait le montant dû
// (EF-8.1) casse la CI au lieu de passer en silence.

const CENTIMES_PAR_EURO = 100

// Saisie d'un montant en euros : chiffres, séparateur `,` ou `.`, au plus 2 décimales.
// Ex. acceptés : « 8 », « 8,1 », « 8,10 », « 0 ». Refusés : « 8,105 », « -8 », « huit ».
const SAISIE_EUROS = /^\d+([.,]\d{1,2})?$/

// Centimes → saisie éditable en euros, sans symbole (ex. 810 → « 8,10 »). Sert à **semer** le
// champ du formulaire : ce qu'on relit doit pouvoir être réémis tel quel.
export function centimesVersSaisieEuros(centimes: number): string {
  const euros = Math.trunc(centimes / CENTIMES_PAR_EURO)
  const reste = centimes % CENTIMES_PAR_EURO
  return `${euros},${String(reste).padStart(2, '0')}`
}

// Saisie en euros → centimes entiers, ou `null` si la saisie n'est pas un montant valide.
// La conversion passe par les **chiffres du texte**, pas par `parseFloat * 100` : multiplier un
// flottant par 100 rouvre exactement le problème qu'on cherche à éviter.
export function saisieEurosVersCentimes(saisie: string): number | null {
  const normalisee = saisie.trim()
  if (!SAISIE_EUROS.test(normalisee)) return null
  const [euros, decimales = ''] = normalisee.replace(',', '.').split('.')
  const centimes = decimales.padEnd(2, '0')
  return Number(euros) * CENTIMES_PAR_EURO + Number(centimes)
}

// Centimes → libellé lisible. Le tarif d'un créneau est **obligatoire** (ADR-0017) : il n'y a plus
// d'état « non défini » ; seul `0` (gratuit) se distingue d'un montant.
export function decrireTarif(centimes: number): string {
  if (centimes === 0) return 'Gratuit'
  return `${centimesVersSaisieEuros(centimes)} €`
}
