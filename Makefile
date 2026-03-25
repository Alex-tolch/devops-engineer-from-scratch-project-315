.PHONY: deploy provision

INVENTORY ?= hosts
PRIVATE_KEY ?=
ANSIBLE ?= ansible-playbook
DEPLOY_EXTRA ?=
VAULT_PASSWORD_FILE ?= ~/.vault.pass

vault_opts = $(if $(strip $(VAULT_PASSWORD_FILE)),--vault-password-file $(VAULT_PASSWORD_FILE),)

provision:
	$(ANSIBLE) -i $(INVENTORY) playbook.yml $(if $(PRIVATE_KEY),--private-key $(PRIVATE_KEY),) $(vault_opts) $(DEPLOY_EXTRA)

deploy:
	$(ANSIBLE) -i $(INVENTORY) deploy.yml $(if $(PRIVATE_KEY),--private-key $(PRIVATE_KEY),) $(vault_opts) $(DEPLOY_EXTRA)
