"""
Find the workspace ID for App Insights resource
"""
from azure.identity import DefaultAzureCredential
from azure.mgmt.applicationinsights import ApplicationInsightsManagementClient
from azure.mgmt.resource import SubscriptionClient

def find_workspace():
    try:
        print("Finding App Insights workspace...")
        print("-" * 60)
        
        # App details from connection string
        app_id = "6d72b15e-fd53-497a-8b31-1576e777d3f6"
        instrumentation_key = "c1eb727b-4792-4be6-85d1-31426081f808"
        
        print(f"\nApp ID: {app_id}")
        print(f"Instrumentation Key: {instrumentation_key}")
        
        # Get credential
        credential = DefaultAzureCredential()
        
        # List all subscriptions
        print("\nListing subscriptions...")
        sub_client = SubscriptionClient(credential)
        subscriptions = list(sub_client.subscriptions.list())
        
        print(f"Found {len(subscriptions)} subscriptions")
        
        # Search in each subscription
        for sub in subscriptions:
            print(f"\nSearching in subscription: {sub.display_name} ({sub.subscription_id})")
            
            try:
                ai_client = ApplicationInsightsManagementClient(credential, sub.subscription_id)
                components = list(ai_client.components.list())
                
                print(f"  Found {len(components)} App Insights resources")
                
                for component in components:
                    if component.app_id == app_id or component.instrumentation_key == instrumentation_key:
                        print(f"\n  ✓ FOUND MATCHING RESOURCE!")
                        print(f"    Name: {component.name}")
                        print(f"    Resource Group: {component.resource_group if hasattr(component, 'resource_group') else 'N/A'}")
                        print(f"    App ID: {component.app_id}")
                        print(f"    Instrumentation Key: {component.instrumentation_key}")
                        
                        # Get workspace ID
                        if hasattr(component, 'workspace_resource_id') and component.workspace_resource_id:
                            workspace_id = component.workspace_resource_id.split('/')[-1]
                            print(f"    Workspace Resource ID: {component.workspace_resource_id}")
                            print(f"    Workspace ID: {workspace_id}")
                            
                            print(f"\n  Update your .env file with:")
                            print(f"  APP_INSIGHTS_WORKSPACE_ID={workspace_id}")
                            return workspace_id
                        else:
                            print(f"    ⚠ This is a classic App Insights (not workspace-based)")
                            print(f"    You need to query using the Application Insights Data Plane API")
                            print(f"    Or migrate to workspace-based App Insights")
                            return None
                            
            except Exception as e:
                print(f"  Error in subscription: {str(e)[:100]}")
        
        print("\n❌ Could not find the App Insights resource in any subscription")
        print("Possible reasons:")
        print("1. You don't have access to the subscription")
        print("2. The resource is in a different tenant")
        print("3. The connection string is incorrect")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_workspace()
