def generer_tableau_tournoi_avec_positions(joueurs):
    """
    Génère le tableau d'un tournoi avec appariements et positions binaires.

    Args:
        joueurs (list): Liste des joueurs triés par ordre de classement (1 = meilleur joueur).

    Returns:
        dict: Un dictionnaire représentant les tours, où chaque clé est un numéro de tour
              et chaque valeur est une liste de matches avec positions binaires.
    """
    tableau = {}
    n = len(joueurs)
    tour = 1

    # Créer les tours jusqu'à ce qu'il ne reste qu'un joueur
    while n > 1:
        matches = []
        for i in range(n // 2):
            # Apparier le meilleur joueur avec le dernier joueur
            match = (joueurs[i], joueurs[n - i - 1])
            # Calculer la position binaire pour chaque match
            position = format((1 << (n // 2)) - 1 - i, f"0{n // 2}b")
            matches.append((match, position))
        tableau[f"Tour {tour}"] = {f"cible{i + 1}": (match, position) for i, (match, position) in enumerate(matches)}

        # Réduire la liste des joueurs qualifiés pour le prochain tour
        joueurs = joueurs[:n // 2]
        n //= 2
        tour += 1

    return tableau


def afficher_tableau_avec_positions(tableau):
    """
    Affiche le tableau du tournoi avec les appariements et les positions.

    Args:
        tableau (dict): Le tableau du tournoi avec positions.
    """
    for tour, matches in sorted(tableau.items(), key=lambda x: int(x[0].split()[1])):
        print(f"{tour}:")
        for cible, (match, position) in matches.items():
            print(f"    {cible}: {match[0]} vs {match[1]} -> gagnant va en position \"{position}\"")
        print()


# Exemple avec 16 joueurs triés
joueurs = [f"J{str(i)}" for i in range(1, 17)]  # J1 à J16
tableau = generer_tableau_tournoi_avec_positions(joueurs)

# Afficher le tableau avec positions
afficher_tableau_avec_positions(tableau)

"""
tour 1
    cible1: j1 vs j16 -> gagnant va en position "1111"
    cible2: j8 vs j9  -> gagnant va en position "1110"
    cible3: j5 vs j12 -> gagnant va en position "1101"
    cible4: j4 vs j13 -> gagnant va en position "1100"
    cible5: j3 vs j14 -> gagnant va en position "1011"
    cible6: j6 vs j11 -> gagnant va en position "1010"
    cible7: j7 vs j10 -> gagnant va en position "1001"
    cible8: j2 vs j15 -> gagnant va en position "1000"
    
tour 2

    cible1: j1 vs j8 -> gagnant va en position "111"
    cible2: j5 vs j4 -> gagnant va en position "110"
    cible3: j3 vs j6 -> gagnant va en position "101"
    cible4: j7 vs j2 -> gagnant va en position "100"
    
tour 3
    cible1: j1 vs j4 -> gagnant va en position "11"
    cible3: j3 vs j2 -> gagnant va en position "10"
    
tour 3
    cible1: j1 vs j2 -> gagnant va en position "1"
"""