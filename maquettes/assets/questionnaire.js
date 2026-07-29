/* ═══════════════════════════════════════════════════════════════════════════
   Kervignarc — moteur de questionnaire
   ---------------------------------------------------------------------------
   Trois responsabilités, et rien d'autre :

   1. SAUVEGARDE LOCALE  — chaque frappe est conservée dans le navigateur, pour
      qu'un onglet fermé ne fasse pas perdre vingt minutes de réponses. Le
      stockage peut être refusé (fichier ouvert en file://, navigateur
      verrouillé) : tout passe par un try/catch et l'échec est DIT, pas masqué.

   2. EXPORT MARKDOWN    — le fichier téléchargé est exactement celui qui doit
      atterrir dans questionnaires/. C'est lui le livrable versionné ; la page
      n'est qu'un moyen de le remplir confortablement.

   3. COPIE              — navigator.clipboard n'existe pas en contexte non
      sécurisé (file://), d'où le repli sur execCommand. Même piège que le jour
      J en http sur le réseau local.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict'

  var modele = JSON.parse(document.getElementById('q-modele').textContent)
  var cle = 'kervignarc-questionnaire-' + modele.slug
  var form = document.getElementById('q-form')
  var etat = document.getElementById('q-etat')
  var apercu = document.getElementById('q-apercu')
  var stockageOk = true

  /* ---------------------------------------------------------------- état */

  function lireReponses() {
    var r = { variante: null, verdict: null, champs: {}, questions: [], vocab: [] }
    var v = form.querySelector('input[name="variante"]:checked')
    if (v) r.variante = parseInt(v.value, 10)
    var d = form.querySelector('input[name="verdict"]:checked')
    if (d) r.verdict = parseInt(d.value, 10)
    form.querySelectorAll('textarea[data-champ]').forEach(function (t) {
      r.champs[t.dataset.champ] = t.value
    })
    form.querySelectorAll('textarea[data-question]').forEach(function (t) {
      r.questions[parseInt(t.dataset.question, 10)] = t.value
    })
    form.querySelectorAll('.q-vocab-ligne').forEach(function (ligne, i) {
      var a = ligne.querySelector('[data-vocab="ecran"]')
      var b = ligne.querySelector('[data-vocab="bon"]')
      r.vocab[i] = { ecran: a ? a.value : '', bon: b ? b.value : '' }
    })
    return r
  }

  function ecrireReponses(r) {
    if (!r) return
    if (r.variante !== null && r.variante !== undefined) {
      var v = form.querySelector('input[name="variante"][value="' + r.variante + '"]')
      if (v) v.checked = true
    }
    if (r.verdict !== null && r.verdict !== undefined) {
      var d = form.querySelector('input[name="verdict"][value="' + r.verdict + '"]')
      if (d) d.checked = true
    }
    Object.keys(r.champs || {}).forEach(function (nom) {
      var t = form.querySelector('textarea[data-champ="' + nom + '"]')
      if (t) t.value = r.champs[nom]
    })
    ;(r.questions || []).forEach(function (val, i) {
      var t = form.querySelector('textarea[data-question="' + i + '"]')
      if (t && val) t.value = val
    })
    ;(r.vocab || []).forEach(function (paire, i) {
      var ligne = form.querySelectorAll('.q-vocab-ligne')[i]
      if (!ligne || !paire) return
      var a = ligne.querySelector('[data-vocab="ecran"]')
      var b = ligne.querySelector('[data-vocab="bon"]')
      if (a) a.value = paire.ecran || ''
      if (b) b.value = paire.bon || ''
    })
  }

  /* ------------------------------------------------------------ stockage */

  function charger() {
    try {
      var brut = window.localStorage.getItem(cle)
      if (brut) {
        ecrireReponses(JSON.parse(brut))
        dire('réponses restaurées', true)
        return
      }
    } catch (e) {
      stockageOk = false
      dire('sauvegarde auto indisponible — pensez à télécharger', false)
      return
    }
    dire('rien de saisi', false)
  }

  var minuteur = null
  function sauver() {
    if (!stockageOk) return
    window.clearTimeout(minuteur)
    minuteur = window.setTimeout(function () {
      try {
        window.localStorage.setItem(cle, JSON.stringify(lireReponses()))
        dire('enregistré dans ce navigateur', true)
      } catch (e) {
        stockageOk = false
        dire('sauvegarde auto indisponible — pensez à télécharger', false)
      }
    }, 400)
  }

  function dire(texte, vert) {
    etat.textContent = texte
    etat.className = 'q-etat' + (vert ? ' ok' : '')
  }

  /* ------------------------------------------------------------ markdown */

  function citer(texte) {
    if (!texte || !texte.trim()) return '> _(sans réponse)_'
    return texte
      .trim()
      .split('\n')
      .map(function (l) {
        return '> ' + l
      })
      .join('\n')
  }

  function construireMarkdown() {
    var r = lireReponses()
    var l = []

    l.push('# ' + modele.code + ' · ' + modele.titre, '')
    l.push('> **Écran** : [' + modele.code + ' — ' + modele.titre + '](../' + modele.slug + '.html)' +
           ' · **Appli** : ' + modele.appli + ' (`' + modele.route + '`)')
    l.push('> **Rôle** : ' + modele.role)
    l.push('>')
    l.push('> Rempli le ' + new Date().toLocaleDateString('fr-FR') + '.')
    l.push('', '---', '')

    l.push('## 1. Quel parti pris retiens-tu ?', '')
    modele.variantes.forEach(function (v, i) {
      l.push('- [' + (r.variante === i ? 'x' : ' ') + '] ' + v)
    })
    l.push('- [' + (r.variante === -1 ? 'x' : ' ') + '] Aucun — voir « à refaire » plus bas')
    l.push('')
    l.push('**Pourquoi ce choix**', '')
    l.push(citer(r.champs.pourquoi), '')
    l.push('**Ce que tu prendrais dans les autres variantes**', '')
    l.push(citer(r.champs.ailleurs), '')
    l.push('---', '')

    var verdicts = [
      '✅ Validé tel quel — on peut coder ça',
      '🟡 Validé avec les réserves ci-dessous',
      '🔴 À refaire — l\'écran ne répond pas au besoin',
    ]
    l.push('## 2. Verdict', '')
    verdicts.forEach(function (v, i) {
      l.push('- [' + (r.verdict === i ? 'x' : ' ') + '] ' + v)
    })
    l.push('', '---', '')

    l.push('## 3. Critiques', '')
    l.push(citer(r.champs.critiques), '')
    l.push('---', '')

    l.push('## 4. Évolutions souhaitées', '')
    l.push(citer(r.champs.evolutions), '')
    l.push('---', '')

    l.push('## 5. Questions ciblées', '')
    modele.questions.forEach(function (q, i) {
      l.push('**' + (i + 1) + '. ' + q + '**', '')
      l.push(citer(r.questions[i]), '')
    })
    l.push('---', '')

    l.push('## 6. Vocabulaire', '')
    var lignes = (r.vocab || []).filter(function (p) {
      return p && (p.ecran.trim() || p.bon.trim())
    })
    l.push('| À l\'écran | Le bon mot |')
    l.push('|---|---|')
    if (lignes.length === 0) {
      l.push('|  |  |')
    } else {
      lignes.forEach(function (p) {
        l.push('| ' + p.ecran.trim() + ' | ' + p.bon.trim() + ' |')
      })
    }
    l.push('', '---', '')

    l.push('## 7. Ce qui manque complètement', '')
    l.push(citer(r.champs.manque), '')

    return l.join('\n')
  }

  /* -------------------------------------------------------------- actions */

  function telecharger() {
    var texte = construireMarkdown()
    var blob = new Blob([texte], { type: 'text/markdown;charset=utf-8' })
    var url = URL.createObjectURL(blob)
    var a = document.createElement('a')
    a.href = url
    a.download = modele.slug + '.md'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.setTimeout(function () {
      URL.revokeObjectURL(url)
    }, 1000)
    dire('téléchargé — à déposer dans questionnaires/', true)
  }

  function copier() {
    var texte = construireMarkdown()
    // navigator.clipboard exige un contexte sécurisé : absent en file://.
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(texte).then(
        function () { dire('markdown copié', true) },
        function () { copierRepli(texte) }
      )
      return
    }
    copierRepli(texte)
  }

  function copierRepli(texte) {
    var zone = document.createElement('textarea')
    zone.value = texte
    zone.setAttribute('readonly', '')
    zone.style.position = 'fixed'
    zone.style.opacity = '0'
    document.body.appendChild(zone)
    zone.select()
    var ok = false
    try {
      ok = document.execCommand('copy')
    } catch (e) {
      ok = false
    }
    document.body.removeChild(zone)
    dire(ok ? 'markdown copié' : 'copie refusée — utilisez « Télécharger »', ok)
  }

  function basculerApercu() {
    var visible = apercu.classList.toggle('visible')
    if (visible) apercu.querySelector('pre').textContent = construireMarkdown()
  }

  function reinitialiser() {
    if (!window.confirm('Effacer toutes les réponses de cet écran ?')) return
    form.reset()
    try {
      window.localStorage.removeItem(cle)
    } catch (e) {
      /* rien à faire : le stockage était déjà indisponible */
    }
    dire('réponses effacées', false)
  }

  /* ---------------------------------------------------------------- câblage */

  form.addEventListener('input', function () {
    sauver()
    if (apercu.classList.contains('visible')) apercu.querySelector('pre').textContent = construireMarkdown()
  })
  form.addEventListener('change', sauver)
  document.getElementById('q-telecharger').addEventListener('click', telecharger)
  document.getElementById('q-copier').addEventListener('click', copier)
  document.getElementById('q-apercu-bouton').addEventListener('click', basculerApercu)
  document.getElementById('q-reinit').addEventListener('click', reinitialiser)

  charger()
})()
