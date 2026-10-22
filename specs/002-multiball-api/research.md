# Research: Destination « Multiball »

Source de vérité de l'API : `https://multiball-admin.net/swagger.yaml` (OpenAPI 3.0.1, lu le 2026-10-22).

## R1. Authentification

- **Decision**: `requests.request(..., auth=(api_key, token))`, ce qui produit `Authorization: Basic base64(api_key:token)`.
- **Rationale**: conforme à la spec OpenAPI (basicAuth) et aux tests de l'utilisateur ; l'en-tête est construit par `requests` et n'est jamais manipulé ni journalisé par notre code.
- **Alternatives considered**: construire l'en-tête à la main (inutile, plus de risque de le journaliser).

## R2. Endpoints et corps

| Action | Méthode et chemin | Corps |
|---|---|---|
| lister les terrains | `GET /courts` | aucun |
| état du terrain | `GET /courts/{courtId}` | aucun ; réponse `CourtStatusResponse` : `status`, `title`, `game {id, name, dispName}` |
| jeux installés | `GET /courts/{courtId}/games` | aucun ; réponse `{count, results: [{id, name, dispName, versions}]}` |
| charger | `PUT /courts/{courtId}/switchGame` | `{"gameId": id, "versionNumber": null}` |
| régler | `PUT /courts/{courtId}/setConfiguration` | `{"gameId": id, "values": {"duration": int, "difficulty": float}}` (seules les clés fournies) |
| démarrer | `PUT /games/{gameId}/start` | `{"courtId": courtId}` |
| arrêter | `PUT /games/{gameId}/stop/` | `{"courtId": courtId}` (barre finale conservée comme dans la spec) |

- **Decision**: succès = code HTTP 2xx. Message lisible = `message`, sinon `error`, sinon le texte brut tronqué.
- **Rationale**: les erreurs observées (`{"message": "Invalid api key!"}`, `{"message": "authorization header missing"}`) utilisent `message` ; `BadRequest` du swagger utilise `error`.

## R3. Non-blocage et délai d'attente

- **Decision**: chaque message Multiball lance un thread démon ; `timeout=10` par requête ; les pauses utilisent `threading.Event.wait(delay)` pour être annulables.
- **Rationale**: le serveur OSC (`ThreadingOSCUDPServer`) traite déjà chaque datagramme dans un thread, mais un thread dédié garantit que le routage rend la main immédiatement et isole les erreurs.

## R4. Mémoire et annulation

- **Decision**: état gardé dans `multiball.py`, indexé par `(base_url, court_id)` : `last_loaded`, `last_started`, `cancel_event` de la séquence `start` en cours. `switch`, `stop` et un nouveau `start` déclenchent l'événement d'annulation de la séquence en cours.
- **Rationale**: `expand_connections()` reconstruit les cibles à chaque modification de configuration ; indexer par terrain conserve la mémoire après une modification et partage logiquement l'état si deux connexions visent le même mur.
- **Alternatives considered**: indexer par nom de cible interne (perdu à chaque édition), persister sur disque (non demandé).

## R5. Correspondance du préfixe

- **Decision**: étendre la règle existante `address.startswith(pattern + "/")` aux cibles `multiball`. L'action est le segment unique qui suit (`/start`), en minuscules. Une adresse égale au préfixe ou avec plusieurs segments (`/mb/start/x`) est rejetée avec un message clair.
- **Rationale**: même comportement que OSC vers OSC, documenté ; `/multiball` ne correspond pas à `/mb/`.

## R6. Secrets

- **Decision**:
  - `/get_config` renvoie une copie où chaque `to.token` Multiball est vidé et `to.token_set` vaut `true/false`.
  - `/add_connection` et `/update_connection` retirent `token_set` ; un jeton vide en modification reprend le jeton enregistré de la même connexion.
  - `/export_config` retire les jetons, sauf `?include_secrets=1` (case à cocher + avertissement dans l'interface).
  - `/import_config` : une connexion Multiball sans jeton reprend celui de la configuration actuelle ayant la même clé API.
  - `/multiball_list` : si le jeton n'est pas fourni et qu'un index de connexion l'est, le serveur utilise le jeton **et l'adresse d'API** enregistrés (empêche d'envoyer le jeton enregistré vers une adresse saisie arbitraire).
  - Toute ligne de log du module passe par une fonction qui remplace le jeton par `***` (défense en profondeur).
- **Rationale**: répond à FR-010, FR-012, FR-013 sans changer le format du fichier de configuration.

## R7. Retour OSC

- **Decision**: réutiliser `response_to_osc` (`enabled`, `ip`, `port`, `address`) déjà stocké au niveau de la connexion et recopié dans la route par `expand_connections()`. Arguments : `[action, 1|0, message]` ; pour `status` : `["status", 1, status, nom_du_jeu, game_id]`. Les erreurs de validation (action inconnue, argument manquant) renvoient aussi `0` si le retour est activé.
- **Rationale**: COGS peut réagir à tout échec, y compris de configuration.

## R8. Validation des arguments

- `gameId` : texte non vide (les arguments OSC sont convertis en texte et nettoyés).
- `duration` : nombre ; `<= 0` ou vide = non fourni ; converti en entier.
- `difficulty` : nombre entre 0 et 1 inclus ; vide = non fourni ; hors intervalle = erreur.
- `start_delay` : nombre de 0 à 60, défaut 3 ; valeur invalide en configuration = 3 avec alerte.

## R9. Packaging

- **Decision**: ajouter `"multiball"` à `hiddenimports` du spec PyInstaller.
- **Rationale**: le module est importé statiquement par `mini_osc` et serait détecté, mais `mini_osc` lui-même est en `hiddenimports` ; l'ajout explicite évite toute surprise.
