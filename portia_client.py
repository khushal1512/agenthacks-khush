import os
from dotenv import load_dotenv
from portia import ( Config, DefaultToolRegistry, Portia, StorageClass, )
import requests
from portia import PlanBuilderV2, StepOutput, Input
from portia.cli import CLIExecutionHooks
from pydantic import BaseModel, Field
load_dotenv()

# config = Config.from_default(default_model)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

task0 = "Star the github repo for portiaAI/portia-sdk-python"

my_config = Config.from_default(storage_class=StorageClass.CLOUD, 
                                default_model="google/gemini-2.0-flash",
                                google_api_key=GOOGLE_API_KEY
                            )

portia = Portia(
    config=my_config,
    tools=DefaultToolRegistry(my_config),
    execution_hooks=CLIExecutionHooks(),
)

# plan_run = portia.run(task0)
def query_autorag_api(query: str) -> str:
    """
    Directly queries the Cloudflare AutoRAG API endpoint.
    """
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    rag_id = os.getenv("RAG_ID", "portiarag")

    if not all([api_token, account_id]):
        return "Error: CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID must be set in the .env file."


    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/autorag/rags/{rag_id}/ai-search"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}",
    }
    
    payload = {
        "query": query
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  

        response_data = response.json()
        
        answer = response_data.get("result", {}).get("response", "No answer found in the API response.")
        return answer

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return f"Error: Failed to connect to Cloudflare API. Details: {e}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return f"An unexpected error occurred: {e}"
    
class triage_output(BaseModel):
    triage_report: str = Field(description="A markdown formatted report of the triaged issues, including their titles and URLs.")

class priority_output(BaseModel):
    priority_list: str = Field(description="A markdown formatted list of the priority issues, including their titles and URLs.")

class bug_report_output(BaseModel):
    github_issue_url: str = Field(description="URL of the created Github Issue.")
    linear_ticket_url: str = Field(description="URL of the created Linear Ticket.")
    status: str = Field(description="A Summary of the actions taken")

class feature_request_output(BaseModel):
    github_issue_url: str = Field(description="URL of the created Github Issue.")
    linear_ticket_url: str = Field(description="URL of the updated Linear Ticket.")
    status: str = Field(description="A Summary of the actions taken")

class doc_search_output(BaseModel):
    answer: str = Field(description="The answer to the user's query, generated from the documentation.")

class weekly_digest_output(BaseModel):
    digest_report: str = Field(description="A full markdown report of the weekly digest.")


bug_report_plan = (
    PlanBuilderV2("Full Bug Reporting Workflow")
    .input(name="bug_description", description="A detailed description of the bug.")
    .input(name="user_email", description="The email address of the user who reported the bug")


    .llm_step(
        step_name="extend_bug_description",
        task=(
            "You are a technical writer. Take the following user-submitted bug report "
            "and expand it into a more detailed and structured description. Add sections like "
            "'Steps to Reproduce', 'Expected Behavior', and 'Actual Behavior', inferring "
            "the details from the user's text. Format the output in clean markdown."
        ),
        inputs=[Input("bug_description")],
    )

    
    .single_tool_agent_step(
        step_name="create_github_issue",
        tool="portia:mcp:api.githubcopilot.com:create_issue",
        task="Create a new Github issue using the provided structured bug description for the title and body in the 'khushal1512/portia-demo' repository.",
        inputs=[StepOutput("extend_bug_description")]
    )


    .single_tool_agent_step(
        step_name="send_confirmation_email",
        tool="portia:google:gmail:send_email",
        task="Send a confirmation email to the user who reported the bug. The subject should be 'Bug Report Confirmation' and the body should include the URL of the created GitHub issue.",
        inputs=[Input("user_email"), StepOutput("create_github_issue")]
    )

    .final_output(output_schema=bug_report_output)

    .build()
)


feature_request_plan = (
    PlanBuilderV2("Full Feature Request Workflow")

    .input(name="feature_description", description="A detailed description of the feature request.")
    .input(name="user_email", description="The email address of the user who requested the feature")

   
    .llm_step(
        step_name="extend_feature_description",
        task=(
            "You are a product manager. Take the following user-submitted feature request and expand it "
            "into a more detailed user story. Add sections like 'Problem Statement', 'Proposed Solution', "
            "and 'Acceptance Criteria', inferring the details from the user's text. "
            "Format the output in clean markdown."
        ),
        inputs=[Input("feature_description")],
    )

    
    .single_tool_agent_step(
        step_name="create_github_enhancement",
        tool="portia:mcp:api.githubcopilot.com:create_issue",
        task="Create a new Github issue with the 'enhancement' label using the provided structured feature description in the 'khushal1512/portia-demo' repository.",
        inputs=[StepOutput("extend_feature_description")], 
    )


    .single_tool_agent_step(
        step_name="send_confirmation_email",
        tool="portia:google:gmail:send_email",
        task=(
            "Send a confirmation email to the user. The subject should be 'Feature Request Received'. "
            "The body should thank them for their suggestion and include the links to the "
            "GitHub issue and the Linear ticket."
        ),
        inputs=[
            Input("user_email"),
            StepOutput("create_github_enhancement")
        ],
    )

    .final_output(output_schema=feature_request_output)

    .build()
)


doc_search_plan = (
    PlanBuilderV2("Cloudflare AutoRAG Direct API Search")

    .input(
        name="user_query",
        description="The user's question to search the documentation."
    )

    .function_step(
        step_name="call_autorag_api",
        function=query_autorag_api,
        args={
            "query": Input("user_query")
        }
    )

    .final_output(output_schema=doc_search_output)
    .build()
)



prioritization_plan = (
    PlanBuilderV2("Product Manager Issue Prioritization")

    .single_tool_agent_step(
        step_name="fetch_linear_issues",
        tool="portia:mcp:mcp.linear.app:list_issues",
        task="Fetch all issues, including those in backlog from the 'TestPortiaagent' workspace or team in Linear.",
    )

    .llm_step(
        step_name="prioritize_issues",
        task=(
            "You are an expert Product Manager. Analyze the provided list of issues and identify the top 3 or more most critical issues for the team to focus on next. "
            "Base your decision on the issue's existing priority, title, description, and labels. "
            "Your final output must be a concise, markdown-formatted list including each issue's title and URL."
        ),
        inputs=[StepOutput("fetch_linear_issues")],
    )

    .final_output(output_schema=priority_output)
    .build()
)




triage_plan = (
    PlanBuilderV2("Issue Triage Suggestions")

    .single_tool_agent_step(
        step_name="fetch_linear_issues_for_triage",
        tool="portia:mcp:mcp.linear.app:list_issues",
        task="Fetch all issues, including those in backlog from the 'TestPortiaagent' workspace or team in Linear.",
    )

    .llm_step(
        step_name="suggest_triage_actions",
        task=(
            "You are an AI Triage Engineer. Analyze the provided list of Linear issues. "
            "Your job is to identify any issues that are missing a priority or relevant labels. "
            "Your final output must be a markdown-formatted report listing only the issues that need updates. "
            "For each, suggest a priority (e.g., High, Medium) and labels (e.g., 'bug', 'UI'). "
            "Example: 'SYM-123 - Suggest Priority: High, Suggest Labels: bug, backend'"
            "Also mention the issue URLs"
        ),
        inputs=[StepOutput("fetch_linear_issues_for_triage")],
    )

    .final_output(output_schema=triage_output)
    .build()
)



weekly_digest_plan = (
    PlanBuilderV2("Weekly Team Digest")

    .single_tool_agent_step(
        step_name="fetch_completed_issues",
        tool="portia:mcp:mcp.linear.app:list_issues",
        task="Fetch all issues, including those in backlog from the 'TestPortiaagent' workspace or team in Linear that were moved to the 'Done' status within the last 7 days.",
    )


    .single_tool_agent_step(
        step_name="fetch_new_issues",
        tool="portia:mcp:mcp.linear.app:list_issues",
        task="Fetch all issues, including those in backlog from the 'TestPortiaagent' workspace or team in Linear that were created within the last 7 days.",
    )

    .llm_step(
        step_name="generate_weekly_digest",
        task=(
            "You are a Project Manager writing a 'Weekly Digest' for your team. You have been given two lists: issues that were completed this week, and new issues that were created. "
            "Analyze these lists to create a friendly and informative summary report in Markdown format.\n\n"
            "Your report should have three sections:\n"
            "1. **🏆 This Week's Wins**: Celebrate what the team has shipped. List the completed issues.\n"
            "2. **📝 New on the Radar**: Briefly list the new issues that have been created.\n"
            "3. **✨ Contributor Spotlight**: Identify and thank the team members who were most active (look at who created/completed issues).\n\n"
            "Keep the tone positive and encouraging."
        ),
        inputs=[
            StepOutput("fetch_completed_issues"),
            StepOutput("fetch_new_issues")
        ]
    )

    .final_output(output_schema=weekly_digest_output)

    .build()
)



# planbuilderdemo = PlanBuilderV2("star the repository khushal1512/feedback-engine").single_tool_agent_step(
#     task="Star the github repo for khushal1512/feedback-engine",
#     tool="portia:github::star_repo"
# # ).build()

# portia.run_plan(planbuilderdemo)
# print(planbuilderdemo.outputs)