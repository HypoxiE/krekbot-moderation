
import os
TOKENS: dict[str, str] = {}

if os.path.exists("secrets"):
	token_files = {
		'KrekAdminBot': "secrets/TOKEN_KrekAdminBot.txt",
		'KrekFunBot': "secrets/TOKEN_KrekFunBot.txt",
		'KrekRimagochiBot': "secrets/TOKEN_KrekRimagochiBot.txt",
		'KrekSupBot': "secrets/TOKEN_KrekSupBot.txt",
		'KrekModBot': "secrets/TOKEN_KrekModBot.txt"
	}

	for bot, path in token_files.items():
		if os.path.exists(path):
			with open(path, "r") as file:
				TOKENS[bot] = file.read()

token_envs = {
	'KrekAdminBot': "KREKBOT_ADMIN_BOT_TOKEN",
	'KrekFunBot': "KREKBOT_FUN_BOT_TOKEN",
	'KrekRimagochiBot': "KREKBOT_RIMAGOCHI_BOT_TOKEN",
	'KrekSupBot': "KREKBOT_SUPPORT_BOT_TOKEN",
	'KrekModBot': "KREKBOT_MODERATION_BOT_TOKEN"
}

for bot, name in token_envs.items():
	if os.environ[name]:
		TOKENS[bot] = os.environ[name]