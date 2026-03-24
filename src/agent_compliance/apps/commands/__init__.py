from agent_compliance.apps.commands.incubator import register_incubator_commands
from agent_compliance.apps.commands.review import register_review_commands
from agent_compliance.apps.commands.web import register_web_commands

__all__ = [
    "register_incubator_commands",
    "register_review_commands",
    "register_web_commands",
]
