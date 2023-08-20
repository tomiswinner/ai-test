import logging

import azure.functions as func
import os
import time
import mimetypes
import urllib.parse
from flask import Flask, request, jsonify
import json

import tiktoken
import openai
import sys


from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient
from approaches.chatlogging import get_user_name, write_error
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from approaches.chatread import ChatReadApproach

# Replace these with your own values, either in environment variables or directly here
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT")
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER")

AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE")
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX")

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_CATEGORY = os.environ.get("KB_FIELDS_CATEGORY") or "category"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"

AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION")

AZURE_OPENAI_DAVINCI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DAVINCI_DEPLOYMENT")
AZURE_OPENAI_GPT_35_TURBO_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT_35_TURBO_DEPLOYMENT")
AZURE_OPENAI_GPT_4_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT_4_DEPLOYMENT")
AZURE_OPENAI_GPT_4_32K_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT_4_32K_DEPLOYMENT")

gpt_models = {
    "text-davinci-003": {
        "deployment": AZURE_OPENAI_DAVINCI_DEPLOYMENT,
        "max_tokens": 4097,
        "encoding": tiktoken.encoding_for_model("text-davinci-003")
    },
    "gpt-3.5-turbo": {
        "deployment": AZURE_OPENAI_GPT_35_TURBO_DEPLOYMENT,
        "max_tokens": 4096,
        "encoding": tiktoken.encoding_for_model("gpt-3.5-turbo")
    },
    "gpt-4": {
        "deployment": AZURE_OPENAI_GPT_4_DEPLOYMENT,
        "max_tokens": 8192,
        "encoding": tiktoken.encoding_for_model("gpt-4")
    },
    "gpt-4-32k": {
        "deployment": AZURE_OPENAI_GPT_4_32K_DEPLOYMENT,
        "max_tokens": 32768,
        "encoding": tiktoken.encoding_for_model("gpt-4-32k")
    }
}

# Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage (no secrets needed, 
# just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the 
# keys for each service
# If you encounter a blocking error during a DefaultAzureCredntial resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
azure_credential = DefaultAzureCredential()

# Used by the OpenAI SDK
openai.api_type = "azure"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = AZURE_OPENAI_API_VERSION

# Comment these two lines out if using keys, set your API key in the OPENAI_API_KEY environment variable instead
openai.api_type = "azure_ad"
openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
openai.api_key = openai_token.token
# openai.api_key = os.environ.get("AZURE_OPENAI_KEY")

# Set up clients for Cognitive Search and Storage
search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX,
    credential=azure_credential)
blob_client = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net", 
    credential=azure_credential)
blob_container = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)

chat_approaches = {
    "rrr": ChatReadRetrieveReadApproach(search_client, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "r": ChatReadApproach()
}

def docsearch():
    ensure_openai_token()
    # approach = request.json["approach"]
    approach = "rrr"
    user_name = get_user_name(request)
    # overrides = request.json.get("overrides")
    overrides = {
        "gptModel": "text-davinci-003",
        "semanticCaptions": True,
        "semanticRanker": True,
        "temperature": "0.0",
        "top": 5,
    }

    selected_model_name = overrides.get("gptModel")

    gpt_chat_model = gpt_models.get("gpt-3.5-turbo")
    gpt_completion_model = gpt_models.get(selected_model_name)

    try:
        impl = chat_approaches.get(approach)
        if not impl:
            return json.dumps({"error": "unknown approach"}), 400
        # r = impl.run(selected_model_name, gpt_chat_model, gpt_completion_model, user_name, request.json["history"], overrides)
        r = impl.run(selected_model_name, gpt_chat_model, gpt_completion_model, user_name, [{"user": "すね毛"}], overrides)

        return json.dumps(r), 200

    except Exception as e:
        write_error("docsearch", user_name, str(e))
        return json.dumps({"error": str(e)}), 500
    
    
def ensure_openai_token():
    global openai_token
    if openai_token.expires_on < int(time.time()) - 60:
        openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token
    # openai.api_key = os.environ.get("AZURE_OPENAI_KEY")






def main(req: func.HttpRequest) -> func.HttpResponse:
    
    try:
        response, status_code = docsearch() # Assuming docsearch handles the request
        return func.HttpResponse(body=response, status_code=status_code, mimetype="application/json")

    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)
