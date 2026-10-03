import type { Sauvegarde } from './api'

export function datePrise(sauvegarde: Pick<Sauvegarde, 'prise_le'>): string {
  return new Date(sauvegarde.prise_le).toLocaleString('fr-FR', {
    dateStyle: 'short',
    timeStyle: 'medium',
  })
}

export function taille(octets: number): string {
  if (octets < 1024 * 1024) return `${Math.max(1, Math.round(octets / 1024))} Ko`
  return `${(octets / (1024 * 1024)).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} Mo`
}
