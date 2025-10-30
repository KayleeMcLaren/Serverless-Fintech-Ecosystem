output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # POST /savings-goal
    aws_api_gateway_resource.savings_goal_resource,
    aws_api_gateway_method.create_savings_goal_method,
    aws_api_gateway_integration.create_savings_goal_integration,
    aws_api_gateway_method.create_savings_goal_options_method,
    aws_api_gateway_integration.create_savings_goal_options_integration,
    aws_api_gateway_method_response.create_savings_goal_options_200,
    aws_api_gateway_integration_response.create_savings_goal_options_integration_response,

    # GET /savings-goal/by-wallet/{wallet_id}
    aws_api_gateway_resource.savings_by_wallet_resource,
    aws_api_gateway_resource.savings_by_wallet_id_resource,
    aws_api_gateway_method.get_savings_goals_method,
    aws_api_gateway_integration.get_savings_goals_integration,
    # (No OPTIONS for this simple GET)

    # /savings-goal/{goal_id}
    aws_api_gateway_resource.savings_goal_id_resource,

    # DELETE /savings-goal/{goal_id}
    aws_api_gateway_method.delete_savings_goal_method,
    aws_api_gateway_integration.delete_savings_goal_integration,
    aws_api_gateway_method.delete_savings_goal_options_method,
    aws_api_gateway_integration.delete_savings_goal_options_integration,
    aws_api_gateway_method_response.delete_savings_goal_options_200,
    aws_api_gateway_integration_response.delete_savings_goal_options_integration_response,
    
    # POST /savings-goal/{goal_id}/add
    aws_api_gateway_resource.add_to_goal_resource,
    aws_api_gateway_method.add_to_goal_method,
    aws_api_gateway_integration.add_to_goal_integration,
    aws_api_gateway_method.add_to_goal_options_method,
    aws_api_gateway_integration.add_to_goal_options_integration,
    aws_api_gateway_method_response.add_to_goal_options_200,
    aws_api_gateway_integration_response.add_to_goal_options_integration_response,
    
    # GET /savings-goal/{goal_id}/transactions
    aws_api_gateway_resource.goal_transactions_resource,
    aws_api_gateway_method.get_goal_transactions_method,
    aws_api_gateway_integration.get_goal_transactions_integration,
    aws_api_gateway_method.get_goal_transactions_options_method,
    aws_api_gateway_integration.get_goal_transactions_options_integration,
    aws_api_gateway_method_response.get_goal_transactions_options_200,
    aws_api_gateway_integration_response.get_goal_transactions_options_integration_response,
  ]))
}