# MÉLODIA — Studio de création musicale IA 🎼

Application **Streamlit en français**, reliée à l’API [ACE Music](https://acemusic.ai/api-key) (ACE-Step 1.5). L’inférence musicale a lieu chez le fournisseur et non sur le PC de l’utilisateur.

## Fonctionnalités

- **Mode Simple** : une description en français suffit ; le modèle crée le style, la structure et les paroles.
- **Mode Personnalisé** : description musicale et paroles structurées avec `[Intro]`, `[Verse 1]`, `[Chorus]`, `[Outro]` ; réglages de durée, tempo, tonalité, format, instrumental.
- **Atelier de paroles** : ébauche locale à partir d’une idée ; génération de véritables paroles IA via le mode Simple d’ACE Music (cette seconde option lance **aussi** une génération audio), édition et traduction vers l’anglais.
- **Préparation FR → EN en arrière-plan** des descriptions et paroles, avec préservation des marqueurs de structure. Le mode Aléatoire dispose directement de descriptions anglaises.
- Lecteur intégré, téléchargements MP3/WAV/FLAC selon l’API, export paroles TXT et fiche JSON, bibliothèque dans la session.

## Utiliser sur Streamlit Community Cloud

1. Ouvrir https://share.streamlit.io et déployer ce dépôt `QuentinLamboley/AImusic`, branche `main`, fichier `app.py`.
2. Saisir sa **propre** clé ACE Music dans la barre latérale de l’application : https://acemusic.ai/api-key
3. Créer une chanson dans l’onglet *Composer*.

Démarrage local (facultatif) :

```bash
pip install -r requirements.txt
streamlit run app.py
```

Aucun GPU local requis. Aucune clé API dans le dépôt, les fichiers, les logs ou le cache. La clé est un champ mot de passe uniquement en mémoire de session ; elle devra être ressaisie après fermeture de session. **Ne pas saisir la clé dans les fichiers Streamlit Secrets publics ou les issues GitHub.**

## Fiabilité de la génération et erreurs HTTP 504

Le client utilise maintenant **`stream: true`** (Server-Sent Events, SSE) et assemble progressivement les métadonnées et l'audio. ACE-Step documente des battements de cœur toutes les 2 secondes pendant la génération, ce qui réduit le risque qu'un proxy coupe une connexion inactive. Le logiciel n'envoie **qu'un POST par clic**, sans relance automatique.

**Attention :** un HTTP 504 peut survenir dès la première tentative, même pour des morceaux courts. Il existe un signalement public côté fournisseur : https://github.com/ace-step/ACE-Step-1.5/issues/1332 (18 septembre 2026). Une connexion SSE ne résout pas une indisponibilité serveur. Le message d'erreur ne signifie pas que la clé est invalide ou que l'utilisateur a dépassé son quota.

Pour un test minimal, utiliser 20 à 40 secondes, MP3, mais un échec reste possible indépendamment du prompt.

## Limites et confidentialité

- L’API hébergée d’ACE Music peut limiter le débit, être indisponible ou retourner des erreurs 504. Nous ne réessayons **jamais automatiquement** une génération susceptible d’avoir déjà abouti. Une attente globale de 240 secondes est appliquée au flux SSE, avec un délai maximal d’inactivité de 40 secondes par lecture. Une génération interrompue côté client peut continuer chez le fournisseur.
- Aucun prix ou quota illimité n’est garanti par ce dépôt.
- La préparation linguistique utilise des services tiers (Google Traduction, interface non officielle, puis MyMemory en secours), avec des délais réseau courts et un budget global de 15 secondes. Les textes sont transmis à ces services ; ne pas y soumettre de contenu confidentiel. Si tous les services échouent, aucune requête musicale avec des instructions françaises non préparées n’est lancée. La qualité stylistique des traductions n’est pas garantie.
- **Ébauche locale** de paroles : modèles de phrases prédéfinis, sans LLM. **Écriture IA** : déclenche une vraie génération musicale ACE Music et récupère les paroles produites dans la réponse ; elle consomme donc une requête API.
- La bibliothèque est uniquement en mémoire de la session Streamlit. Les morceaux ne sont pas persistés sur un serveur ; téléchargez-les avant de fermer la page.
- La disponibilité des formats et les droits d’utilisation des pistes sont soumis aux conditions du service ACE Music.

## API

D’après la [documentation officielle](https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/Openrouter_API_DOC.md) :
- `POST https://api.acemusic.ai/v1/chat/completions`
- Mode Simple : `sample_mode=true`, `messages=[{"role":"user","content":"..."}]`.
- Mode personnalisé : `messages=[{"role":"user","content":"<prompt>...</prompt>\\n<lyrics>...</lyrics>"}]`.
- La réponse peut contenir l’audio comme data URI base64 dans `choices[0].message.audio`.

Tests du client : `python -m unittest discover -s tests -v`.

Projet indépendant non affilié à ACE Music.