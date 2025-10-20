output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # POST /savings-goal
    aws_api_gateway_resource.savings_goal_resource,
    aws_api_gateway_method.create_savings_goal_method,
    aws_api_gateway_integration.create_savings_goal_integration,
    aws_api_gateway_method.create_savings_goal_options_method,          # ADD
    aws_api_gateway_integration.create_savings_goal_options_integration, # ADD
    aws_api_gateway_method_response.create_savings_goal_options_200,   # ADD
    # Note: integration_response isn't listed directly, method_response is enough

    # GET /savings-goal/by-wallet/{wallet_id}
    aws_api_gateway_resource.savings_by_wallet_resource,
    aws_api_gateway_resource.savings_by_wallet_id_resource,
    aws_api_gateway_method.get_savings_goals_method,
    aws_api_gateway_integration.get_savings_goals_integration,

    # DELETE /savings-goal/{goal_id}
    aws_api_gateway_resource.savings_goal_id_resource,
    aws_api_gateway_method.delete_savings_goal_method,
    aws_api_gateway_integration.delete_savings_goal_integration,

    # POST /savings-goal/{goal_id}/add
    aws_api_gateway_resource.add_to_goal_resource,
    aws_api_gateway_method.add_to_goal_method,
    aws_api_gateway_integration.add_to_goal_integration,
  ]))
}