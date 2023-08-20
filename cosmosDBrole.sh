echo "If you want to skip all user prompts, type 'skip'. Otherwise, press Enter to set all the needed information."
read SKIP_PROMPTS

if [ "$SKIP_PROMPTS" != "skip" ]; then
  echo "Enter your cosmosDB account:"
  read AZURE_COSMOSDB_ACCOUNT
  echo "Enter your cosmosDB resource group name:"
  read AZURE_COSMOSDB_RESOURCE_GROUP
  echo "Enter your managed ID:"
  read BACKEND_IDENTITY_PRINCIPAL_ID
  echo "Enter your principal ID:"
  read AZURE_PRINCIPAL_ID
  export AZURE_COSMOSDB_ACCOUNT AZURE_COSMOSDB_RESOURCE_GROUP BACKEND_IDENTITY_PRINCIPAL_ID AZURE_PRINCIPAL_ID
fi

if [ "$roleId" != "" ]; then
  echo "Role ID already exists. Skipping role creation."
  roleId=$(az cosmosdb sql role definition create --account-name "$AZURE_COSMOSDB_ACCOUNT" --resource-group "$AZURE_COSMOSDB_RESOURCE_GROUP" --body ./cosmosreadwriterole.json --output tsv --query id)
  export roleId
fi
echo "Role ID: $roleId"
az cosmosdb sql role assignment create --account-name "$AZURE_COSMOSDB_ACCOUNT" --resource-group "$AZURE_COSMOSDB_RESOURCE_GROUP" --scope / --principal-id "$BACKEND_IDENTITY_PRINCIPAL_ID" --role-definition-id $roleId
az cosmosdb sql role assignment create --account-name "$AZURE_COSMOSDB_ACCOUNT" --resource-group "$AZURE_COSMOSDB_RESOURCE_GROUP" --scope / --principal-id "$AZURE_PRINCIPAL_ID" --role-definition-id $roleId
