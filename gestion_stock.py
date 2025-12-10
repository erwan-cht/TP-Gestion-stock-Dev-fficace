"""
Logiciel de Gestion Optimisée des Stocks Multi-Produits (R3.02).
Auteurs : Mathys VANHEULLE & Erwan CHRIST BUT 2 Groupe 2
Date : 12/2025
Contexte : Gestion FIFO, Alertes Statiques, Colisage LIFO.
"""

import logging
from collections import deque
from typing import Dict, List, Deque, Optional
from pathlib import Path

# --- CONSTANTES (Configuration) ---
SEUIL_ALERTE = 2         # Seuil critique de stock
MAX_LOG_SIZE = 3         # Taille statique du journal d'alertes
FICHIER_ARCHIVE = "archives_alertes.txt"
FICHIER_LOG_APP = "app.log"

# Configuration du logging (Sortie console propre)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


class GestionnaireStock:
    """
    Contrôleur principal de l'entrepôt.
    Respecte l'architecture hiérarchique : N1 -> N2 -> N3.
    """

    def __init__(self) -> None:
        # Structure Plate : { "A1": deque([1, 1, ...]) }
        self.stock: Dict[str, Deque[int]] = {}
        
        # Structure Statique Circulaire pour les alertes
        self.journal_alertes: Deque[str] = deque(maxlen=MAX_LOG_SIZE)

    # =========================================================================
    # GROUPE 1 : GESTION DES ENTRÉES (STOCK)
    # =========================================================================

    def traiter_ajout_produit(self, type_p: str, volume: int) -> None:
        """
        Niveau 1 - VA: Orchestre l'entrée en stock et garantit la sécurité.
        Coordonne l'insertion physique et la vérification immédiate des seuils.
        """
        # Appel N2 : Insertion physique
        cle_produit = self._ajouter_au_stock(type_p, volume)
        
        # Appel N2 : Vérification sécurité
        self._gerer_alerte_seuil(cle_produit)
        
        logging.info(f"Transaction terminée pour {cle_produit}")

    def _ajouter_au_stock(self, type_p: str, vol: int) -> str:
        """
        Niveau 2 - VA: Insère physiquement le produit dans la file FIFO.
        Gère l'initialisation de la file si le produit est nouveau.
        """
        cle = self._generer_cle_unique(type_p, vol)
        
        if cle not in self.stock:
            self.stock[cle] = deque()
            
        # Ajout à droite (Queue) pour respecter FIFO
        self.stock[cle].append(vol)
        return cle

    def _gerer_alerte_seuil(self, cle: str) -> None:
        """
        Niveau 2 - VA: Met à jour le journal d'alertes (Ajout ou Résolution).
        Déclenche l'archivage si le tableau statique déborde.
        """
        qte_actuelle = len(self.stock.get(cle, []))
        
        if qte_actuelle > SEUIL_ALERTE:
            # Cas : Retour à la normale -> On supprime l'alerte
            self._nettoyer_alerte_resolue(cle)
        else:
            # Cas : Seuil critique -> On lève une alerte
            msg = f"ALERTE: Stock critique pour {cle} (Qté: {qte_actuelle})"
            self._enregistrer_dans_log(msg)

    # =========================================================================
    # GROUPE 2 : GESTION DES SORTIES (COLIS)
    # =========================================================================

    def traiter_commande_colis(self, commande: List[str]) -> List[str]:
        """
        Niveau 1 - VA: Transforme une demande brute en un colis stable.
        Orchestre le prélèvement et le tri par volume pour l'empilage.
        """
        # Appel N2 : Récupération FIFO
        produits_bruts = self._recuperer_produits(commande)
        
        # Appel N2 : Organisation spatiale (Pile)
        colis_final = self._trier_produits_volume(produits_bruts)
        
        return colis_final

    def _recuperer_produits(self, liste_cles: List[str]) -> List[str]:
        """
        Niveau 2 - VA: Extrait les produits du stock (FIFO).
        Gère les ruptures de stock (Stratégie Backorder).
        """
        produits_trouves = []
        
        for cle in liste_cles:
            if self._est_disponible(cle):
                # Retrait à gauche (Tête) pour respecter FIFO
                self.stock[cle].popleft()
                produits_trouves.append(cle)
                # Vérif seuil après retrait !
                self._gerer_alerte_seuil(cle)
            else:
                logging.warning(f"RUPTURE: {cle} manquant (Mis en Backorder)")
                
        return produits_trouves

    def _trier_produits_volume(self, produits: List[str]) -> List[str]:
        """
        Niveau 2 - VA: Organise la pile du plus grand au plus petit volume.
        Assure la stabilité physique du colis (Lourd en bas).
        """
        # On décore la liste avec le volume pour trier : (3, "A3")
        temp_list = []
        for p in produits:
            vol = self._extraire_volume_cle(p)
            temp_list.append((vol, p))
            
        # Tri décroissant sur le volume (Index 0)
        # Résultat : [ (3, "B3"), (2, "A2"), (1, "A1") ]
        temp_list.sort(key=lambda x: x[0], reverse=True)
        
        # On reconstruit la liste propre
        return [item[1] for item in temp_list]

    # =========================================================================
    # GROUPE 3 : CONSULTATION (DASHBOARD)
    # =========================================================================

    def afficher_rapport_alertes(self) -> None:
        """
        Niveau 1 - VA: Affiche l'état de sécurité du stock à l'utilisateur.
        """
        print("\n=== RAPPORT DE SÉCURITÉ STOCK ===")
        if not self.journal_alertes:
            print("Aucune alerte active. Stock sain.")
        else:
            historique = self._formater_historique_alertes()
            for ligne in historique:
                print(ligne)
        print("=================================\n")

    def _formater_historique_alertes(self) -> List[str]:
        """
        Niveau 2 - VA: Convertit la structure technique en texte lisible.
        """
        lignes = []
        # On parcourt le deque sans le vider
        for i, alerte in enumerate(self.journal_alertes, 1):
            lignes.append(f"Priorité {i} : {alerte}")
        return lignes

    # =========================================================================
    # NIVEAU 3 : OUTILS TECHNIQUES (HELPERS)
    # =========================================================================

    def _generer_cle_unique(self, type_p: str, vol: int) -> str:
        """Génère la clé unique (Flat Structure). ex: 'A1'."""
        return f"{type_p.upper()}{vol}"

    def _extraire_volume_cle(self, cle: str) -> int:
        """Extrait l'int du volume depuis la clé 'A1' -> 1."""
        try:
            return int(cle[1:])
        except (ValueError, IndexError):
            return 0  # Sécurité

    def _est_disponible(self, cle: str) -> bool:
        """Vérifie la présence physique en stock."""
        return cle in self.stock and len(self.stock[cle]) > 0

    def _enregistrer_dans_log(self, message: str) -> None:
        """Gère le tableau statique. Si plein -> Archive le plus vieux."""
        # Vérification manuelle avant insertion pour gérer l'archivage
        if len(self.journal_alertes) == MAX_LOG_SIZE:
            alerte_ejectee = self.journal_alertes[0] # Le plus vieux
            self._archiver_sur_disque(alerte_ejectee)
            
        # Le deque gère le popleft auto, mais on l'a fait manuellement pour archiver
        self.journal_alertes.append(message)

    def _nettoyer_alerte_resolue(self, cle: str) -> None:
        """Supprime une alerte spécifique (Résolution d'incident)."""
        # Recréation filtrée du deque (Méthode propre Python)
        liste_filtr = [a for a in self.journal_alertes if cle not in a]
        self.journal_alertes = deque(liste_filtr, maxlen=MAX_LOG_SIZE)

    def _archiver_sur_disque(self, message: str) -> None:
        """Écrit l'alerte éjectée dans le fichier d'archives."""
        try:
            path = Path(FICHIER_ARCHIVE)
            with path.open("a", encoding="utf-8") as f:
                f.write(f"[ARCHIVE] {message}\n")
        except IOError:
            logging.error("Échec critique : Impossible d'écrire sur le disque.")


# =============================================================================
# MAIN (SCÉNARIO D'EXÉCUTION)
# =============================================================================

def main() -> None:
    """Simulation du scénario demandé."""
    app = GestionnaireStock()
    
    print("--- 1. INITIALISATION DU STOCK (Mode Rafale) ---")
    # Saisie rapide comme demandé : "A1, A1, B3..."
    donnees_entree = "A1, A1, B3, B3, C2, A1, C2"
    
    for item in donnees_entree.split(','):
        item = item.strip()
        if len(item) >= 2:
            try:
                # Parsing simple
                t_prod = item[0]
                v_prod = int(item[1:])
                app.traiter_ajout_produit(t_prod, v_prod)
            except ValueError:
                logging.error(f"Format incorrect : {item}")

    print("\n--- 2. VÉRIFICATION DES ALERTES (Post-Init) ---")
    # A1 (3 items), B3 (2 items -> Seuil limite), C2 (2 items -> Seuil limite)
    # Rappel : Seuil = 2. Si Qte <= 2 on veut une alerte selon ta logique
    # (Ou Qte < 2 selon le sujet, adapté ici pour la démo)
    app.afficher_rapport_alertes()

    print("--- 3. SORTIE COLIS (Commande Client) ---")
    # Commande mélangée
    commande = ["A1", "C2", "B3"] 
    print(f"Commande client : {commande}")
    
    colis = app.traiter_commande_colis(commande)
    
    # Affichage visuel de la PILE (Le premier élément est le fond du carton)
    print(f"Colis assemblé (Fond -> Haut) : {colis}")
    print("Note : Le plus grand volume doit être au début de la liste (Fond)")

    print("\n--- 4. ÉTAT FINAL & ALERTES ---")
    # Le retrait a dû déclencher des alertes critiques
    app.afficher_rapport_alertes()


if __name__ == "__main__":
    main()