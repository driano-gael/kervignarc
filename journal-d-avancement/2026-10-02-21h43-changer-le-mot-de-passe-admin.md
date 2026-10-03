# 02/10/2026 — Changer l'identifiant ou le mot de passe administrateur (E10US006)

**Ce qui est nouveau.** Dans l'administration, axe « Atelier », un écran **« Compte
administrateur »** permet de changer l'identifiant, le mot de passe, ou les deux, sans ouvrir le
fichier `.env` du serveur. Le mot de passe actuel est toujours demandé.

**Pour l'organisateur.** Faire tourner l'accès est réel : dès le changement, **les autres appareils**
connectés en administrateur sont déconnectés, tandis que celui qui a fait le changement reste
connecté. Une faute de frappe (mot de passe actuel erroné, confirmation différente) affiche un
message clair et **ne déconnecte pas**.

**Limites.** Pas de « mot de passe oublié » : sans internet ni e-mail, le fichier `.env` reste la
porte de secours.
