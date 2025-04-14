import boto3
import time
import json
import argparse

def initiate_inventory_job(vault_name, client, account_id='-'):
    """
    Starts an inventory retrieval job to list all archives in the vault.
    Note: The job may take several hours to complete.
    """
    response = client.initiate_job(
        vaultName=vault_name,
        accountId=account_id,
        jobParameters={
            'Type': 'inventory-retrieval',
            'Description': 'Inventory job for vault emptying'
        }
    )
    job_id = response['jobId']
    print(f"Inventory job initiated for vault '{vault_name}'. Job ID: {job_id}")
    return job_id

def wait_for_job_completion(client, vault_name, job_id, account_id='-', wait_interval=600):
    """
    Polls the job status until the inventory retrieval job is completed.
    The default interval is set to 10 minutes (600 seconds). Adjust as needed.
    """
    print("Waiting for the inventory job to complete. This may take several hours...")
    while True:
        response = client.describe_job(vaultName=vault_name, accountId=account_id, jobId=job_id)
        if response.get('Completed', False):
            print("Inventory job completed.")
            break
        print(f"Job not complete yet. Waiting {wait_interval} seconds...")
        time.sleep(wait_interval)
    return

def get_inventory_output(client, vault_name, job_id, account_id='-'):
    """
    Retrieves the output from the completed inventory job.
    The output is a JSON document containing the ArchiveList.
    """
    print("Retrieving the inventory output...")
    response = client.get_job_output(vaultName=vault_name, accountId=account_id, jobId=job_id)
    output = response['body'].read()
    inventory = json.loads(output)
    return inventory

def delete_archives(client, vault_name, archive_list, account_id='-'):
    """
    Iterates over the list of archives and deletes each one.
    """
    for archive in archive_list:
        archive_id = archive['ArchiveId']
        try:
            print(f"Deleting archive {archive_id}...")
            client.delete_archive(vaultName=vault_name, accountId=account_id, archiveId=archive_id)
        except Exception as e:
            print(f"Error deleting archive {archive_id}: {e}")
    return

def main():
    parser = argparse.ArgumentParser(description="Empty an AWS Glacier vault by deleting all archives.")
    parser.add_argument("vault_name", help="The name of the AWS Glacier vault to empty")
    parser.add_argument("--account_id", default='-', help="AWS account ID (default: '-')")
    parser.add_argument("--region", default="us-west-2", help="AWS region (default: us-west-2)")
    args = parser.parse_args()

    # Initialize the Glacier client using boto3
    client = boto3.client("glacier", region_name=args.region)

    # Step 1: Initiate an inventory retrieval job
    job_id = initiate_inventory_job(args.vault_name, client, args.account_id)
    
    # Step 2: Wait until the job completes
    wait_for_job_completion(client, args.vault_name, job_id, args.account_id)
    
    # Step 3: Retrieve the inventory output (the list of archives)
    inventory = get_inventory_output(client, args.vault_name, job_id, args.account_id)
    archive_list = inventory.get("ArchiveList", [])
    
    if not archive_list:
        print("No archives found in the vault. Nothing to delete.")
    else:
        print(f"Found {len(archive_list)} archive(s). Proceeding to delete them...")
        # Step 4: Delete each archive found in the inventory
        delete_archives(client, args.vault_name, archive_list, args.account_id)
        print("Deletion of all archives is complete.")
    
    print("The vault is now empty. You can proceed to delete the vault itself via the AWS console or CLI.")

if __name__ == "__main__":
    main()
