# MÉLODIA — Hébergement de secours

Interface française alternative, accessible par navigateur, indépendante de la disponibilité de Streamlit Community Cloud. Le site et la fonction de génération sont hébergés sur Vercel, tandis que la synthèse musicale est fournie par ACE Music.

## Fonctionnalités

- Modes Simple, Personnalisé et Aléatoire
- Langue chantée française par défaut, six langues possibles
- Paroles personnalisées françaises conservées sans modification
- Préparation de la description musicale en anglais côté serveur
- Atelier de paroles, écoute intégrée, export audio et TXT
- Clé ACE Music saisie temporairement dans le navigateur ; jamais placée dans GitHub ni conservée côté serveur
- Relayage en flux des réponses ACE Music via la route serveur /api/generate, sans second appel automatique
- Gratuit côté hébergement selon les limites en vigueur du fournisseur ; les quotas ACE Music sont indépendants

Ce répertoire est un plan de secours pour le Streamlit original `app.py`. Il ne modifie pas ses fichiers.

## Lancer localement

```sh
npm install
npm run dev
```

Test syntaxe et build : `npm run build`.

Déploiement Vercel : lier le dépôt `QuentinLamboley/AImusic` avec le répertoire racine `web` et le framework Next.js.

## Sécurité et limites

La clé est transmise dans le corps de la requête HTTPS à la fonction hébergée, puis utilisée dans l'en-tête de la requête HTTPS envoyée à ACE Music. Elle n'est pas journalisée, conservée dans une base ou écrite dans un dépôt. Ne pas diffuser de clé dans un lien ou dans des captures d'écran.

En mode personnalisé, les paroles françaises et leurs balises sont transmises telles quelles lorsque la langue française est sélectionnée. La description musicale est traduite côté serveur. Le service de traduction, ACE Music et Vercel peuvent être temporairement indisponibles. Le forfait gratuit Vercel limite la durée des fonctions et peut interrompre des générations particulièrement longues.

Ce projet n'est pas affilié à ACE Music.
