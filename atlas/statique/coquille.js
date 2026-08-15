/* Atlas — coquille : navigation, helpers DOM, rendu Markdown minimal.
 *
 * Script classique, pas de module ES : sur `file://`, les modules sont soumis au CORS et le site
 * se casserait en silence au double-clic tout en marchant parfaitement en `localhost`. Même
 * raison pour les données, servies en `.js` (`window.ATLAS`) et non en `.json`.
 */

/* global window, document */
var Atlas = (function () {
  "use strict";

  var PAGES = [
    { fichier: "index.html", libelle: "Le règlement" },
    { fichier: "decisions.html", libelle: "Les décisions" },
    { fichier: "errata.html", libelle: "Ce qui a changé" },
    { fichier: "controles.html", libelle: "Écarts constatés" },
    { fichier: "recherche.html", libelle: "Rechercher" },
  ];

  function parametre(nom) {
    var trouve = new RegExp("[?&]" + nom + "=([^&#]*)").exec(window.location.search);
    return trouve ? decodeURIComponent(trouve[1].replace(/\+/g, " ")) : "";
  }

  function echapper(texte) {
    return String(texte === undefined || texte === null ? "" : texte)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* Rendu Markdown volontairement minimal : gras, italique, code, liens, listes, paragraphes.
   * On n'implémente pas un moteur complet — le corpus n'emploie que ces formes, et un moteur
   * approximatif qui en couvre davantage produit surtout des rendus faux sur les cas tordus. */
  function markdown(source) {
    var lignes = String(source || "").split("\n");
    var html = "";
    var dansListe = false;
    var tampon = [];

    function viderParagraphe() {
      if (tampon.length) {
        html += "<p>" + enligne(tampon.join(" ")) + "</p>";
        tampon = [];
      }
    }

    function fermerListe() {
      if (dansListe) {
        html += "</ul>";
        dansListe = false;
      }
    }

    lignes.forEach(function (ligne) {
      var puce = /^\s*[-*]\s+(.*)$/.exec(ligne);
      var numerote = /^\s*\d+\.\s+(.*)$/.exec(ligne);
      var contenu = puce ? puce[1] : numerote ? numerote[1] : null;

      if (contenu !== null) {
        viderParagraphe();
        if (!dansListe) {
          html += "<ul>";
          dansListe = true;
        }
        html += "<li>" + enligne(contenu) + "</li>";
        return;
      }
      if (!ligne.trim()) {
        viderParagraphe();
        fermerListe();
        return;
      }
      if (dansListe) {
        /* Continuation indentée d'une puce : on la recolle au dernier <li>. */
        html = html.replace(/<\/li>$/, " " + enligne(ligne.trim()) + "</li>");
        return;
      }
      tampon.push(ligne.trim());
    });

    viderParagraphe();
    fermerListe();
    return html;
  }

  function enligne(texte) {
    return echapper(texte)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (_, libelle, cible) {
        /* Les liens du corpus visent des fichiers du dépôt : on les rend en clair plutôt que
         * cliquables, car l'atlas ne connaît pas l'emplacement du dépôt sur le poste du lecteur. */
        return "<span class='mono'>" + libelle + "</span>";
      })
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  }

  function element(balise, classe, html) {
    var noeud = document.createElement(balise);
    if (classe) noeud.className = classe;
    if (html !== undefined) noeud.innerHTML = html;
    return noeud;
  }

  function poserBandeau(courante) {
    var liens = PAGES.map(function (page) {
      var actuelle = page.fichier === courante ? " aria-current='page'" : "";
      return "<a href='" + page.fichier + "'" + actuelle + ">" + page.libelle + "</a>";
    }).join("");

    var bandeau = element("header", "bandeau");
    bandeau.innerHTML =
      "<div class='bandeau-corps'>" +
      "<div class='marque'><strong>Atlas — Kervignarc</strong>" +
      "<span>ce qui fait règle aujourd'hui, et depuis quand</span></div>" +
      "<details class='menu' open><summary></summary><nav>" +
      liens +
      "</nav></details></div>";
    document.body.insertBefore(bandeau, document.body.firstChild);
  }

  function jour(iso) {
    var morceaux = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return morceaux ? morceaux[3] + "/" + morceaux[2] + "/" + morceaux[1] : String(iso || "");
  }

  function pluriel(nombre, singulier, plurielMot) {
    return nombre + " " + (nombre > 1 ? plurielMot || singulier + "s" : singulier);
  }

  function donnees(cle) {
    return (window.ATLAS && window.ATLAS[cle]) || null;
  }

  function demarrer(courante, rendu) {
    document.addEventListener("DOMContentLoaded", function () {
      poserBandeau(courante);
      var cible = document.querySelector("main");
      try {
        rendu(cible);
      } catch (erreur) {
        cible.innerHTML =
          "<h1>L'atlas n'a pas pu s'afficher</h1><p class='chapo'>" +
          echapper(erreur.message) +
          "</p><p>Les données sont peut-être absentes. Régénère-les : " +
          "<code>cd backend &amp;&amp; python -m atlas</code></p>";
      }
    });
  }

  return {
    demarrer: demarrer,
    donnees: donnees,
    echapper: echapper,
    element: element,
    enligne: enligne,
    jour: jour,
    markdown: markdown,
    parametre: parametre,
    pluriel: pluriel,
  };
})();
