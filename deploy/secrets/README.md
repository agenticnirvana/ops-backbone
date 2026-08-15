# Secrets (never commit real credentials)

Mount optional Google Drive service account JSON here:

```
deploy/secrets/google-service-account.json
```

Share your runbooks Drive folder with the service account email. Set in `.env`:

```
GOOGLE_DRIVE_ENABLED=true
GOOGLE_DRIVE_FOLDER_ID=<folder-id-from-drive-url>
```
