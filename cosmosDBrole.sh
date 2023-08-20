#!/bin/bash

# ./.envファイルを読み込んで変数として参照できるようにする
source ./.env

# roleId がなかったら作成する 
# roleId=$(az cosmosdb sql role definition create --account-name "$AZURE_COSMOSDB_ACCOUNT" --resource-group "$AZURE_COSMOSDB_RESOURCE_GROUP" --body ./cosmosreadwriterole.json --output tsv --query id)

echo "Role ID: $roleId"
az cosmosdb sql role assignment create --account-name "$AZURE_COSMOSDB_ACCOUNT" --resource-group "$AZURE_COSMOSDB_RESOURCE_GROUP" --scope / --principal-id "$BACKEND_IDENTITY_PRINCIPAL_ID" --role-definition-id $roleId
az cosmosdb sql role assignment create --account-name "$AZURE_COSMOSDB_ACCOUNT" --resource-group "$AZURE_COSMOSDB_RESOURCE_GROUP" --scope / --principal-id "$AZURE_PRINCIPAL_ID" --role-definition-id $roleId
