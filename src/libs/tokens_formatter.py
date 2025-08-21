
import os
TOKENS: dict[str, str] = {}

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
			TOKENS = {bot: file.read()}