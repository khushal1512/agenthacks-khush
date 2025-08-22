import os
from dotenv import load_dotenv
from portia import (
    Config,
    DefaultToolRegistry,
    Portia,
    StorageClass,
    LLMProvider
)
import requests
import time
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
        task="Create a new Github issue using the provided structured bug description for the title and body in the 'khushal1512/symptoSense' repository.",
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
        task="Create a new Github issue with the 'enhancement' label using the provided structured feature description in the 'khushal1512/symptoSense' repository.",
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





# planbuilderdemo = PlanBuilderV2("star the repository khushal1512/feedback-engine").single_tool_agent_step(
#     task="Star the github repo for khushal1512/feedback-engine",
#     tool="portia:github::star_repo"
# # ).build()

# portia.run_plan(planbuilderdemo)
# print(planbuilderdemo.outputs)