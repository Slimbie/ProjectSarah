from skills.llm_skill import LlmSkill

skill = LlmSkill()
print(skill.handle("What's my name?"))
print(skill.handle("And what laptop am I using?"))