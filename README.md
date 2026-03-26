### Hexlet tests and linter status:

[![Actions Status](https://github.com/Alex-tolch/devops-engineer-from-scratch-project-315/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/Alex-tolch/devops-engineer-from-scratch-project-315/actions)

### Ansible: Docker and firewall (Google Cloud)

Playbook: `playbook.yml`. Inventory: `hosts`. The target VM should run **Ubuntu** or **Debian** (e.g. **Google Compute Engine**).

1. Install the UFW collection:
   `ansible-galaxy collection install -r requirements.yml`
2. Run the playbook (pass your SSH private key explicitly):
   `ansible-playbook -i hosts playbook.yml --private-key /path/to/private_key`

Re-running the playbook is idempotent: packages and UFW rules converge to the described state without unnecessary changes.

Allowed inbound ports: **22** (SSH), **80**, **443**. All other inbound traffic is denied by the default UFW incoming policy.

**Google Cloud firewall (VPC):** create rules so the instance only receives what you need (typically SSH from your IP or IAP, HTTP/HTTPS from the internet if the app is public). Do **not** expose PostgreSQL **TCP 5432** to `0.0.0.0/0`. With this project’s Docker setup, 5432 is not published on the host anyway; defense in depth still matters if you later change the layout.

### Public URL

- Application: [https://project-devops.ddns.net/](https://project-devops.ddns.net/)
- DDNS hostname points to the same VM as in `hosts` (Google Cloud). If the VM public IP changes, update the DDNS record (unless your provider updates it automatically).

### Application deploy (Docker)

Uses the [community.docker](https://docs.ansible.com/ansible/latest/collections/community/docker/docsite/index.html) collection and role `roles/app_deploy`.

1. Install collections: `ansible-galaxy collection install -r requirements.yml`
2. **Secrets:** `group_vars/all/vault.yml`, set **`postgres_password`** (and registry credentials if the image is private on GHCR). Then `ansible-vault encrypt group_vars/all/vault.yml`. Plaintext `vault.yml` is gitignored; you may commit the **encrypted** file.
3. Adjust defaults in `roles/app_deploy/defaults/main.yml` or overrides in `group_vars/all/main.yml` (e.g. **`app_image`** / tags, ports, Postgres toggles).
4. Deploy:

```bash
make deploy PRIVATE_KEY=~/.ssh/your_key
```

(`Makefile` passes `--vault-password-file` when `VAULT_PASSWORD_FILE` is set.)

Or:

```bash
ansible-playbook -i hosts deploy.yml --private-key /path/to/key --ask-vault-pass
```

**Updates:** the role pulls the image and recreates the app container when the image or declared config changes (`comparisons` include `image: strict`).

**Rollback:** pin a stable tag in `group_vars/all/main.yml`, e.g. `app_image_tag: v1.2.3`, then deploy again. The play can fall back to **`app_rollback_image`** if the primary image task fails.

**Data / logs:** host paths `app_data_dir` and `app_logs_dir` are bind-mounted into the app container; **`postgres_data_dir`** persists the database.

**Nginx (reverse proxy):** `deploy.yml` installs **Nginx** on the VM, listens on **port 80**, and proxies to the app at **`127.0.0.1:8080`** (the Docker app port is bound to loopback only). **Static-like assets** (`*.js`, `*.css`, images, fonts, etc.) are proxied with **`proxy_cache`** (see `roles/app_deploy/tasks/nginx.yml` and templates). Files under **`/uploads/`** are served directly from **`app_data_dir/uploads`** on the host (same tree as the container’s data mount). Set **`app_nginx_enabled: false`** in inventory if you need to bind the app to `:80` directly instead.

**HTTPS (Let’s Encrypt):** when **`app_tls_enabled`** is true, the role adds the **Certbot PPA** on **Ubuntu** and installs the **latest** `certbot` package (avoids a Python 3.11+ bug where failures show as `AttributeError: can't set attribute` instead of the real CA message). Set **`app_tls_domain`** in inventory; optional **`app_tls_email`** for the ACME account. If issuance still fails after that, read **`/var/log/letsencrypt/letsencrypt.log`** on the VM (e.g. rate limits after many failed attempts).

**S3 / GCS (manual steps):**

- **GCS bucket** — create a bucket in the desired region (name matches `STORAGE_S3_BUCKET` in Vault).
- **S3 interoperability (HMAC)** — in Google Cloud Console: _Cloud Storage → Settings → Interoperability_ — create an **HMAC access key + secret** for a service account; store them in Vault as `STORAGE_S3_ACCESSKEY` / `STORAGE_S3_SECRETKEY`.
- **IAM** — grant that service account object access to the bucket (e.g. **Storage Object Admin**, or a tighter custom role if you prefer).
- **Vault env vars** — besides the keys: `STORAGE_S3_ENDPOINT` (`https://storage.googleapis.com`), `STORAGE_S3_REGION` (often `us-east-1` for SigV4 with GCS); set any optional prefix/bucket-related vars per the application docs.
- **Exposure** — keep VM firewall as documented (80/443); do not make the bucket world-writable; app access uses credentials from Vault only.

### Spring Boot environment (application README)

The app container uses **`SPRING_PROFILES_ACTIVE=prod`** so **`application-prod.yml`** applies. Ansible injects **`SPRING_DATASOURCE_*`** for the bundled Postgres. For **S3-compatible storage** (e.g. GCS with HMAC), set **`STORAGE_S3_*`** under **`app_env_secrets`** in Vault — see **`group_vars/all/vault.yml.example`**.
