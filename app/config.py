import os
from typing import Union

from dotenv import load_dotenv


def load_environment_variables():
    if os.path.exists("../.env"):
        load_dotenv("../.env")
        # print("Loaded environment variables from .env file.")


def env_variable(name: str, default=None) -> Union[str, bool]:
    value = os.getenv(name, default)
    if value and str(value).lower() == "false":
        return False
    if value and str(value).lower() == "true":
        return True
    return value


### --- Environment Configuration --- ###

IS_DEV = env_variable("IS_DEV")
URL_HOSTNAME = os.getenv("URL_HOSTNAME", "http://localhost:" + os.getenv("PORT", "5312"))
DATA_DIR = "data"

### --- AWS Configuration --- ###

AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")

### --- S3 Configuration --- ###

S3_ERRORDOCS_BUCKET = os.getenv("S3_ERRORDOCS_BUCKET", "assist-error-docs")

### --- LLM / OpenAI Configuration --- ###

LLM_DEFAULT_PROVIDER = "openai"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

# The default LLM used by BedrockHandler (keeping the name for backwards compatibility)
LLM_DEFAULT_MODEL = "gpt-4o"

### --- Chat Configuration --- ###

# This LLM generates the final response to the user's query.
# This model should ideally be of the highest quality.
LLM_CHAT_RESPONSE_MODEL = "gpt-4o"

# This LLM generates the title of the user's chat.
LLM_CHAT_TITLE_MODEL = "gpt-4o"

### --- Central Guidance Configuration --- ###

# This LLM determines if the user query should be enriched
# by the central guidance, or not.
LLM_INDEX_ROUTER = "gpt-4o-mini"

# This LLM takes a user's message and returns a set of OpenSearch queries
LLM_OPENSEARCH_QUERY_GENERATOR = "gpt-4o"

# This LLM determines if the retrieved document chunk
# should be included in the main LLM context.
LLM_CHUNK_REVIEWER = "gpt-4o-mini"


### --- GOV.UK Configuration --- ###

LLM_GOVUK_QUERY_GENERATOR = "gpt-4o"
LLM_DOCUMENT_RELEVANCY_MODEL = "gpt-4o-mini"
LLM_GOV_UK_SEARCH_FOLLOWUP_ASSESMENT = "gpt-4o-mini"


### --- GCS Data API Configuration --- ###
GCS_DATA_API_URL = os.getenv("GCS_DATA_API_URL")


### --- Compaction Configuration --- ###

# This LLM generates summaries of messages for compaction
LLM_COMPACTION_SUMMARISATION_MODEL = "gpt-4o-mini"

# Token threshold for triggering compaction (160k tokens)
COMPACTION_TOKEN_THRESHOLD = 160000

if env_variable("LLM_DEFAULT_MODEL"):
    LLM_DEFAULT_MODEL = env_variable("LLM_DEFAULT_MODEL")

WHITELISTED_URLS = ["https://www.gov.uk"]
BLACKLISTED_URLS = ["https://www.gov.uk/publications"]
WEB_BROWSING_TIMEOUT = 300
GOV_UK_BASE_URL = "https://www.gov.uk"
GOV_UK_SEARCH_MAX_COUNT = 10
