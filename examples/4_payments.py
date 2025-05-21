from src.core.helicone_client import HeliconeClient
import json
from datetime import datetime
import csv
import os
from collections import defaultdict

def create_agent_filter(agent_ids):
    """
    Create a custom filter for multiple agent IDs.
    
    Args:
        agent_ids (list): List of agent IDs to filter by
        
    Returns:
        dict: Custom filter configuration for Helicone query
    """
    if not agent_ids:
        # If no agent IDs are provided, return a filter that matches all requests
        return "all"
    
    # Start with the first agent ID
    filter_conditions = {
        "request_response_rmt": {
            "properties": {
                "agentid": {
                    "equals": agent_ids[0]
                }
            }
        }
    }
    
    # Add remaining agent IDs using OR operator
    for agent_id in agent_ids[1:]:
        filter_conditions = {
            "operator": "or",
            "left": filter_conditions,
            "right": {
                "request_response_rmt": {
                    "properties": {
                        "agentid": {
                            "equals": agent_id
                        }
                    }
                }
            }
        }
    
    return filter_conditions

def process_payments(margin=0.05, usd_to_credit_rate=1000.0, agent_ids=None, limit=10, offset=0):
    """
    Process payment statistics and print summary, including a margin for pricing and credit conversion.
    :param margin: The margin to apply to the total cost (default 5%)
    :param usd_to_credit_rate: Exchange rate from USD to credits (default 1.0)
    :param agent_ids: List of agent IDs to filter by (default None)
    """
    # Initialize the client with your API key
    client = HeliconeClient()

    # Create custom filter based on agent IDs
    custom_filter = create_agent_filter(agent_ids) if agent_ids else "all"

    # Or customize the query parameters
    response = client.query_clickhouse(
        custom_filter=custom_filter,
        is_cached=False,
        limit=limit,
        offset=offset,
        sort_by="created_at",
        sort_order="desc",
        include_inputs=True,
        is_scored=False,
        is_part_of_experiment=False
    )

    # Initialize aggregation variables
    total_requests = 0
    total_input_cost = 0
    total_output_cost = 0
    total_cost = 0
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_time_to_first_token = 0
    total_delay = 0
    model_usage = defaultdict(int)
    provider_usage = defaultdict(int)

    print("length of response", len(response["data"]))

    # Process all requests
    if response["data"] and len(response["data"]) > 0:
        print(f"\nProcessing {len(response['data'])} requests...")
        
        for request in response["data"]:
            total_requests += 1
            request_id = request.get("request_id")
            
            if request_id:
                # Update model and provider usage statistics
                model = request.get('model')
                provider = request.get('provider')
                if model:
                    model_usage[model] += 1
                if provider:
                    provider_usage[provider] += 1
                
                # Accumulate token counts
                total_tokens += int(request.get('total_tokens', 0))
                total_prompt_tokens += int(request.get('prompt_tokens', 0))
                total_completion_tokens += int(request.get('completion_tokens', 0))
                total_time_to_first_token += int(request.get('time_to_first_token', 0))
                total_delay += int(request.get('delay_ms', 0))
                
                # Calculate and accumulate costs
                cost_breakdown = client.calculate_request_cost(request)
                if cost_breakdown:
                    total_input_cost += cost_breakdown['input_cost']
                    total_output_cost += cost_breakdown['output_cost']
                    total_cost += cost_breakdown['total_cost']
                
                # Print individual request details
                print(f"\nRequest {total_requests} Details:")
                print("-" * 50)
                print(f"Request ID: {request.get('request_id')}")
                print(f"Created At: {request.get('request_created_at')}")
                print(f"Model: {model}")
                print(f"Provider: {provider}")
                print(f"Total Tokens: {request.get('total_tokens')}")
                print(f"Prompt Tokens: {request.get('prompt_tokens')}")
                print(f"Completion Tokens: {request.get('completion_tokens')}")
                print(f"Time to First Token: {request.get('time_to_first_token')}ms")
                print(f"Delay: {request.get('delay_ms')}ms")
                
                if cost_breakdown:
                    print(f"\nCost Breakdown:")
                    print(f"Input Cost: ${cost_breakdown['input_cost']:.6f}")
                    print(f"Output Cost: ${cost_breakdown['output_cost']:.6f}")
                    print(f"Total Cost: ${cost_breakdown['total_cost']:.6f}")
                    # Calculate and display credit costs for individual requests
                    credit_cost = cost_breakdown['total_cost'] * usd_to_credit_rate
                    print(f"Credit Cost: {credit_cost:.6f} credits")
                else:
                    print(f"\nNo pricing information found for model {model} from provider {provider}")
        
        # Calculate total price with margin
        total_price = total_cost * (1 + margin)
        avg_price_per_request = total_price / total_requests if total_requests else 0
        
        # Calculate credit prices
        total_credits = total_price * usd_to_credit_rate
        avg_credits_per_request = avg_price_per_request * usd_to_credit_rate
        
        # Print summary statistics
        print("\nSummary Statistics:")
        print("=" * 50)
        print(f"Total Requests Processed: {total_requests}")
        print(f"\nCost Summary:")
        print(f"Total Input Cost: ${total_input_cost:.6f}")
        print(f"Total Output Cost: ${total_output_cost:.6f}")
        print(f"Total Cost: ${total_cost:.6f}")
        print(f"Average Cost per Request: ${total_cost/total_requests:.6f}")
        print(f"\nMargin: {margin*100:.1f}%")
        print(f"Total Price (with margin): ${total_price:.6f}")
        print(f"Average Price per Request (with margin): ${avg_price_per_request:.6f}")
        print(f"\nCredit Summary (Exchange Rate: {usd_to_credit_rate:.2f} credits/USD):")
        print(f"Total Credits Required: {total_credits:.6f}")
        print(f"Average Credits per Request: {avg_credits_per_request:.6f}")
        
        print(f"\nToken Usage Summary:")
        print(f"Total Tokens: {total_tokens}")
        print(f"Total Prompt Tokens: {total_prompt_tokens}")
        print(f"Total Completion Tokens: {total_completion_tokens}")
        print(f"Average Tokens per Request: {total_tokens/total_requests:.2f}")
        
        print(f"\nPerformance Metrics:")
        print(f"Average Time to First Token: {total_time_to_first_token/total_requests:.2f}ms")
        print(f"Average Delay: {total_delay/total_requests:.2f}ms")
        
        print(f"\nModel Usage Distribution:")
        for model, count in model_usage.items():
            print(f"{model}: {count} requests ({count/total_requests*100:.1f}%)")
        
        print(f"\nProvider Usage Distribution:")
        for provider, count in provider_usage.items():
            print(f"{provider}: {count} requests ({count/total_requests*100:.1f}%)")
    else:
        print("No requests found in the response")

if __name__ == "__main__":
    agent_ids = [
        #"1234567890",
        "b24607ff-4934-5ced-b578-c57a69afb660",
        "c2687b82-4249-5b22-8e60-abae67edb2fb"
    ]
    process_payments(agent_ids=agent_ids, limit=50, offset=0)  # Default margin is 5% and default exchange rate is 1.0 credits/USD

# custom_filter = {
# "request_response_rmt": {
# "latency": {
#     "gte": 0
# }
# }
# }