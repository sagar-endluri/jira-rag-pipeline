import json
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from autogen import code_execution_config

# Disable Docker execution
# code_execution_config.use_docker = False

class JiraTriageAgent:
    def __init__(self):
        # ---- Agents ----
        self.webhook_agent = UserProxyAgent(
            name="WebhookAgent",
            human_input_mode="NEVER",
        )

        self.summarizer_agent = AssistantAgent(
            name="SummarizerAgent",
            system_message="You are a Jira ticket summarizer. Summarize issues, updates, or comments in 2-3 sentences."
        )

        self.classifier_agent = AssistantAgent(
            name="ClassifierAgent",
            system_message="""You are a Jira issue classifier. 
            Decide the priority (High, Medium, Low) and type (Bug, Task, Feature). 
            If it's a comment, classify sentiment as Positive, Neutral, or Negative."""
        )

        self.assignment_agent = AssistantAgent(
            name="AssignmentAgent",
            system_message="""You assign Jira tickets to the right developer. 
            Base it on components, labels, and history of similar issues. 
            If it's just a comment event, no assignment is needed."""
        )

        self.notifier_agent = AssistantAgent(
            name="NotifierAgent",
            system_message="You notify results back to Jira API or Slack channel in a clean JSON format."
        )

        # ---- Group Chat ----
        self.groupchat = GroupChat(
            agents=[
                self.webhook_agent,
                self.summarizer_agent,
                self.classifier_agent,
                self.assignment_agent,
                self.notifier_agent
            ],
            messages=[]
        )

        self.manager = GroupChatManager(groupchat=self.groupchat)

    def run(self, issue_payload: dict):
        event_type = issue_payload.get("webhookEvent", "unknown")
        issue_key = issue_payload.get("issue", {}).get("key", "N/A")

        cleaned_payload = {
            "event": event_type,
            "issue": issue_key,
            "summary": issue_payload.get("issue", {}).get("fields", {}).get("summary"),
            "priority": issue_payload.get("issue", {}).get("fields", {}).get("priority", {}).get("name"),
            "status": issue_payload.get("issue", {}).get("fields", {}).get("status", {}).get("name"),
            "comment": issue_payload.get("comment", {}).get("body") if "comment" in issue_payload else None,
            "author": issue_payload.get("comment", {}).get("author", {}).get("displayName") if "comment" in issue_payload else None
        }

        message = f"Webhook Event: {event_type}\nPayload: {json.dumps(cleaned_payload, indent=2)}"

        # Run the group chat
        self.webhook_agent.initiate_chat(self.manager, message=message)

        # Return messages for inspection
        return self.groupchat.messages

