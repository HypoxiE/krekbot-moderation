
TOKENS: dict[str, str] = {}

with open("secrets/TOKEN_KrekAdminBot.txt") as file:
	TOKENS = {'KrekAdminBot': file.read()}

with open("secrets/TOKEN_KrekFunBot.txt") as file:
	TOKENS = {'KrekFunBot': file.read()}

with open("secrets/TOKEN_KrekRimagochiBot.txt") as file:
	TOKENS = {'KrekRimagochiBot': file.read()}

with open("secrets/TOKEN_KrekSupBot.txt") as file:
	TOKENS = {'KrekSupBot': file.read()}